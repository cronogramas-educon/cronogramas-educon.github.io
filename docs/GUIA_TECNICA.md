# Guía técnica del sistema de cronogramas de Educación Continua

Documento de traspaso. Está escrito para que una persona desarrolladora, o una IA a la que se le pegue completo, pueda entender, operar y reparar el sistema sin haber visto nada antes. Estado: octubre de 2026, ya migrado a cuentas institucionales.

## 1. Qué hace el sistema

La Facultad de Estudios Jurídicos, Políticos e Internacionales (Universidad de La Sabana) dicta cursos y diplomados virtuales de Educación Continua. Cada curso tiene un Excel de horas y profesores. Al guardar ese Excel, una página pública del curso se actualiza sola con el cronograma, la próxima clase, el enlace de Teams, el calendario `.ics` y la asistencia. Hay además un sitio de administración, alertas por correo y avisos a estudiantes por Teams.

Regla de oro: **el Excel manda**. Si contradice cualquier otra fuente, la página muestra lo del Excel.

## 2. Cuentas y propiedad

Nada debe quedar a nombre de una persona.

| Pieza | Cuenta institucional | Nota |
|---|---|---|
| Microsoft 365 (SharePoint, Power Automate, Forms, Teams) | `educofdcp@unisabana.edu.co` | Cuenta de la unidad, no de una persona |
| GitHub | organización `cronogramas-educon`, usuario `EducontinuaFEJPI` (Owner) | Debe haber como mínimo un segundo Owner humano |
| Cuenta vieja a retirar | `fabiancoal@unisabana.edu.co` y usuario de GitHub personal | Ya no sostienen ningún flujo activo; los originales están apagados |

Estado del traspaso (octubre de 2026): la organización de GitHub tiene dos Owners (`EducontinuaFEJPI` y una cuenta humana de respaldo); `AVISOS_TOKEN` se emitió desde `EducontinuaFEJPI` y vence el 21 de octubre de 2027 (hay que renovarlo antes); los flujos de Power Automate pertenecen a `educofdcp`.

## 3. Mapa de componentes

```
Formulario de Microsoft Forms (alta de curso)
   |  respuesta
   v
Flujo "Registrar curso nuevo (Forms a carpetas y registro)"
   |  crea carpetas, copia plantillas, crea el equipo de Teams, agrega fila al Registro
   v
SharePoint sitio EduContinuaDerecho
   |  alguien edita el Excel del curso ("Cuadro de horas...") o el Registro
   v
Flujo "Cronograma a GitHub"  (lee Table1, manda las filas)
   |  repository_dispatch, evento excel-actualizado
   v
GitHub Actions "Actualizar datos"  (valida, construye, detecta cambios, commit, despliega)
   v
GitHub Pages  https://cronogramas-educon.github.io/
   |-- c/<curso>-<codigo>/   página de estudiantes (solo esta se comparte)
   |-- g/<codigo>/           sitio de administración
   '-- index.html            página neutra

GitHub Actions "alertas"  --> incidencias en cronogramas-educon/avisos-internos
El flujo "Alertas de cronogramas por correo" lee esas incidencias y envía el correo.
```

El repositorio es público y los registros de Actions también. Por eso la carga útil del evento se lee desde `GITHUB_EVENT_PATH` y jamás desde una variable de entorno (GitHub imprime esas variables en el registro). No cambiar eso. El sitio no guarda nombres de estudiantes: en la asistencia solo existe "Estudiante N". La página de cada curso publica `asistencia.json` (solo n, estado, asistió, faltas, quedan, porcentaje y marcas; sin seguimiento interno) y la sección «Mi asistencia» muestra la fila del número de lista que el estudiante escribe, sin código de seguridad (decisión del usuario: los compañeros pueden ver la asistencia de los demás).

## 4. SharePoint

- Sitio: `https://unisabanaedu.sharepoint.com/sites/EduContinuaDerecho`, título "EduContinua". Biblioteca real: `Documentos compartidos` (en inglés `Documents`; por REST la carpeta se llama `Documentos compartidos`).
- Estructura: `EduContinua <periodo>/<Cohorte N (descripción)>/<Tipo Nombre del curso>/` con, adentro, `Cuadro de horas módulos y profesores.xlsx`, `Formato de asistencia - <curso>.xlsx` y subcarpetas.
- `Plantillas/PLANTILLA horas y profesores.xlsx` y `Plantillas/PLANTILLA asistencia.xlsx`: lo que se copia a cada curso nuevo. Se regeneran con `scripts/generar_plantilla_xlsx.py` y `scripts/generar_asistencia_xlsx.py`.
- `Registro de cursos.xlsx` en la raíz: una fila por curso. Hoja `Registro` con tabla `Table1` y hoja de instrucciones. Columnas: Periodo, Carpeta del periodo, Cohorte, Carpeta del curso, Tipo, Nombre del curso, Nombre completo, Modalidad, Hora de inicio, Hora de fin, Inicio del sábado, Página oficial, Grupo de Teams, Clave (se calcula sola), Estado.
- Hoy la columna Cohorte va vacía y la cohorte viaja dentro de `Carpeta del curso` (`Cohorte 1 (primera vez en el semestre)/Diplomado ...`). La Clave resultante debe coincidir con `carpeta` en `config/cursos.json`.
- Un curso se identifica por su `carpeta` completa. Cambiar la carpeta crea un curso nuevo. Si hay que renombrar una carpeta, hay que corregir también la ruta en `config/cursos.json` o se creará un curso nuevo; `fusionar` nunca borra cursos.

Requisito de cada Excel de curso: hoja `DISTRIBUCIÓN HORAS`, tabla llamada exactamente `Table1`, encabezados de A a J: `No.`, `Unidad`, `Tema`, `Horas`, `No. de clase`, `Profesor`, `Día`, `Fecha`, `Asistente PAT`, `Link de reunión`. La columna K es `Situación` y acepta `Cancelada`: la clase queda fuera del cálculo de asistencia y se avisa en la página. El Cuadro es la matriz principal: nombre y horas salen de ahí.

Acceso por REST desde un navegador con sesión (útil para auditar): `/_api/web/GetFolderByServerRelativePath(decodedurl='...')/Files`. Para modificar archivos sin Excel se puede descargar el `.xlsx`, abrirlo como zip y reescribir el XML de la hoja, quitando `xl/calcChain.xml` (y su referencia en `[Content_Types].xml` y `xl/_rels/workbook.xml.rels`) si se borran fórmulas.

## 5. Power Automate (cuenta educofdcp, Mis flujos)

Power Automate no permite cambiar el propietario principal de un flujo que no está en una solución. Por eso, en octubre de 2026 cada flujo se copió con "Save As" desde educofdcp y se apagaron los originales. Las copias propias:

| Flujo | Id | Disparador | Qué hace |
|---|---|---|---|
| Cronograma a GitHub | `f5f81148-f63f-4e01-8494-22c1ac7daf5a` | SharePoint: archivo creado o modificado (solo propiedades), sitio EduContinuaDerecho, biblioteca Documents | Excel Online `List rows present in a table` (tabla `Table1`), `Select` que mapea columnas, GitHub `Create a repository dispatch event` en `cronogramas-educon/cronogramas-educon.github.io`, evento `excel-actualizado`, carga `{ruta, modificado, filas}` |
| Registrar curso nuevo (Forms a carpetas y registro) | `55107d8c-a7a7-4c3f-a928-0e48869e91f0` | Forms: nueva respuesta | Lee la respuesta, crea la carpeta del curso, copia las plantillas (Cuadro y asistencia), crea el equipo de Teams, obtiene su enlace y agrega la fila al Registro |
| Alertas de cronogramas por correo | `29bcb4b9-bb09-406b-b483-ae6f9ba4e809` | Recurrencia cada 5 minutos | GitHub GraphQL busca incidencias abiertas con etiqueta `alerta-cronogramas` en `cronogramas-educon/avisos-internos`, envía correo con Outlook y cierra la incidencia |
| Enviar bienvenida a un grupo de Teams (Forms a Teams) | `2019b090-6f76-4348-ac4d-51d04b674442` | Forms: nueva respuesta (formulario de bienvenida) | `Get response details`, GitHub GraphQL lee `bienvenidas/<id>.json` del repo público, Teams `Post message in a chat or channel` como Flow bot en el equipo y canal del JSON (`json(body('Search_Github_using_Query')?['data']?['repository']?['object']?['text'])?['equipo'|'canal'|'mensaje']`; el mensaje pasa por `replace()` con las respuestas de gestora y PAT) |

Conexiones que usan: Office 365 Outlook (educofdcp), Microsoft Teams (educofdcp), SharePoint, Excel Online (Business), Microsoft Forms, y GitHub como `EducontinuaFEJPI`. Crear una conexión nueva exige que una persona pulse "Sign in" en el panel; no se puede automatizar.

Los originales de fabiancoal siguen apagados en "Compartidos conmigo" (ids viejos: Cronograma `5c150819-50a9-46ec-a249-af356f228fd2`, Registrar `c806ad0f-16bd-4be7-87e9-9b74cbd8f8c9`, Alertas `094603b8-7929-4706-aa30-80b3350462ca`, Avisos `8715082c-3e19-4a5e-a03a-4998b3a4bf17`). Se pueden borrar cuando la cuenta vieja se dé de baja.

Mensaje de bienvenida: `scripts/bienvenida.py` genera `bienvenidas/<id>.json` (`{equipo, canal, mensaje}`) en cada ejecución de "Actualizar datos", solo para cursos con `teams` y cronograma. El hub muestra la vista previa y un botón que abre el formulario de bienvenida (`global.formularioBienvenida` en `config/cursos.json`) con el curso prellenado (`AllowPrefill` activo). Quien lo envía inicia sesión con la cuenta de la Universidad y queda registrado en las respuestas. El formulario pregunta además el nombre de la gestora logística, del estudiante PAT y una nota adicional opcional (el hub prellena el PAT con el del Excel si existe; ids de las preguntas en `global.preguntasBienvenida`). El mensaje de `bienvenidas/<id>.json` trae los marcadores `{{GESTORA}}`, `{{PAT}}` y `{{NOTA}}`, que el flujo reemplaza con `replace()` y las respuestas de `Get response details`. Si la nota queda vacía, `{{NOTA}}` desaparece; si no, se publica como párrafo «Nota adicional» antes del cierre. Ids de las preguntas: gestora `r1e206a8a…`, PAT `r481e533e…`, nota `r9b7a4761…` (los dos primeros en `global.preguntasBienvenida`; la nota solo la usa el flujo). Sin `teams` en el registro del curso no hay botón.

Pasos del flujo (en orden): `Get response details`; `Search Github using Query` (lee `bienvenidas/<id>.json`); `Search Github using Query 1` (lee `estado/bienvenidas-enviadas.json`); tres `Compose` (`Gestora limpia`, `PAT limpio`, `Nota limpia`) que escapan `&`, `<` y `>` y convierten saltos de línea en `<br>`; `Post message in a chat or channel`; `Create a repository dispatch event` (evento `bienvenida-enviada` con `{curso, fecha}`, que el workflow anota en `estado/bienvenidas-enviadas.json`); `Correo enviada` (confirmación al remitente) y `Correo problema` (corre solo si lo anterior falló, se saltó o venció; escribe a quien envió y a educofdcp). **Bloqueo de doble envío:** si el id del curso ya está en el registro de envíos, el campo Team llega vacío (`if(contains(...),null,...)`), Teams rechaza la acción y `Correo problema` explica que ya se había enviado. Para volver a enviar de verdad, borra el curso de `estado/bienvenidas-enviadas.json`. Hay una ventana de uno o dos minutos entre el envío y el registro en la que un segundo envío pasaría. Probado el 23 de octubre de 2026 con un curso de prueba: envío con nota, escape de HTML, doble envío bloqueado y correo de aviso.
Gotcha: el diseñador no dejó guardar una `Condition` con una rama de correo y `Terminate` (error «contains invalid expression» sin causa clara); por eso el bloqueo se hace con el campo Team y no con una condición.

Gotchas conocidos del diseñador:
- Los pasos Initialize variable no se pueden anidar.
- En `Select` la tilde de `Situación` va literal; con `Situaci_x00f3_n` llega vacío. Los puntos de los encabezados llegan codificados (`No_x002e_`); el procesador los decodifica.
- Las fechas llegan como número serial de Excel en texto; el procesador las convierte.
- `Do until` exige `@` en las expresiones. Usar `int()` donde haga falta.
- Al guardar, verificar que el campo "Modified" de la página de detalles cambió; un clic en Save a veces no se registra.
- Al cambiar de archivo o sitio en un paso, los campos Biblioteca y Tabla conservan identificadores viejos: borrarlos con la X y volver a elegir.
- Excel Online no recibe bien teclas automatizadas: para editar celdas masivamente es más fiable reescribir el XML.

## 6. GitHub

- Repositorio público `cronogramas-educon/cronogramas-educon.github.io`. Settings > Pages > Source: GitHub Actions.
- Organización: Settings > Third-party access > OAuth application policy debe decir "No restrictions"; si no, el conector de GitHub de Power Automate recibe Forbidden.
- Repositorio privado auxiliar `cronogramas-educon/avisos-internos`: solo guarda las incidencias que activan las alertas por correo.
- Variables del repositorio: `MODO_ENTRADA=json` (heredada), `RESPONSABLE_AVISOS=EducontinuaFEJPI` (a quién se asignan las incidencias; debe ser la cuenta con la que está conectado el flujo) y `ALERTAS_ACTIVAS=true` (interruptor de las alertas por correo; si no existe o vale otra cosa, solo se anota en el resumen de la ejecución).
- Secreto `AVISOS_TOKEN`: token con permiso de escribir incidencias en `avisos-internos`. Debe emitirse desde `EducontinuaFEJPI` (token de acceso con alcance solo a ese repositorio). Si el token deja de valer, las alertas dejan de crearse.
- Workflows: `.github/workflows/actualizar-datos.yml` (evento `excel-actualizado`, también manual) y `.github/workflows/alertas.yml` (revisión diaria a las 3:00 p. m. y revisión semanal los lunes a las 8:00 a. m., hora de Colombia).

## 7. Código del repositorio

```
config/cursos.json     lista única de cursos (id, codigo, carpeta, tipo, horario, cohorte, periodo)
cursos/<id>/           config/contenido.json (generado), data/data.json, estado/cambios.json, cronograma.ics (los escribe el workflow)
scripts/construir_datos.py   lee, valida y genera data.json de un curso; detecta cambios de fecha y clases canceladas
scripts/cursos.py            registro, fusión, resolución de carpetas, armado del sitio, base_sharepoint
scripts/asistencia.py        calcula asistencia desde el Cuadro (mínimo 80 %)
scripts/alertas.py, generar_ics.py, generar_*_xlsx.py
plantilla/ css/ js/ assets/  sitio estático sin framework ni compilación (módulos ES)
tests/                       pytest; las pruebas de páginas usan Chromium headless
```

Comandos:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/playwright install chromium
.venv/bin/pytest -q                                   # puede haber una prueba de .ics lenta bajo carga
.venv/bin/python scripts/cursos.py sincronizar        # regenera contenido.json
.venv/bin/python scripts/cursos.py sitio _sitio dev   # arma el sitio local
python3 -m http.server 8000 --directory _sitio
```

Reglas de asistencia: mínimo 80 % (`MINIMO = 0.8`); estados Perdió el mínimo, En riesgo, Atención, Al día y Aprobó, con alertas relativas a las faltas permitidas. Todos los cursos son virtuales. Las marcas se guardan sin nombres.

**Alias de nombres.** Si una misma persona aparece escrita de dos maneras en los Excel (por ejemplo «Melissa Dukuara» y «Melissa Alejandra Dukuara»), los reportes de horas la cuentan como dos. En `config/cursos.json`, dentro de `global`, `aliasPersonas` es una tabla `{"variante": "nombre oficial"}` (se ignoran tildes y mayúsculas); `construir_datos.py` la aplica a docentes y asistentes al reconstruir cada curso, en las páginas de estudiantes y en el hub. Vacía por defecto. El cambio se ve cuando se vuelve a guardar el Excel de cada curso.

**Avisos del hub.** «Urgente» muestra primero lo de hoy y mañana clase por clase, y el resto agrupado por curso (con cuántas clases tienen cada falta). Si un curso en marcha lleva 7 días o más sin guardarse el Excel y ya tuvo clases desde entonces, su tarjeta lo avisa (no cambia el semáforo).

**Mensaje del día para WhatsApp (hub, sección «Mensaje del día»).** Arma en el navegador el texto de la plantilla 3 del equipo («Muy buenos días… tenemos programada la clase N del curso… horario, profesor, enlace… Los esperamos») con los datos del Excel, para hoy o para mañana, un mensaje por clase y un botón «Copiar mensaje». Lo que falta (docente o enlace) sale como «Por confirmar» y se avisa. No envía nada. Código: `mensajeWhatsapp` y `clasesDelDia` en `js/hub-analisis.js`.

**Resumen semanal.** Cada lunes la incidencia/correo sale siempre (ver `docs/ALERTAS.md`), con las clases de la semana por curso (sin docentes ni enlaces), los cursos que terminan en 14 días y lo pendiente.

**Cierre del curso (hub).** La tarjeta de un curso que termina en 7 días o ya terminó trae «Cierre del curso»: dos pasos que se comprueban solos (clases realizadas, asistencia final) y tres que marca el equipo (certificados, encuesta, horas); las marcas se guardan en el navegador de quien las hace. Con `global.encuestaSatisfaccion` configurado, ofrece el mensaje de la encuesta listo para copiar.

**Encuesta de satisfacción.** `global.encuestaSatisfaccion` en `config/cursos.json` (vacío hasta crear la encuesta en Microsoft Forms con la cuenta educofdcp y permitir respuestas de cualquier persona). Con enlace, `armar_sitio` lo agrega a la configuración de cada curso y la página de estudiantes lo muestra solo cuando el curso termina.

**Información del curso (estudiantes).** Sección con asistencia, certificado, grabaciones, material, conexión, cambios y ayuda (`INFO_CURSO` en `js/secciones.js`); un curso puede cambiarla con `infoCurso` en su configuración.

## 8. Operación diaria

- Abrir un curso: llenar el formulario "Nuevo curso o diplomado de Educación Continua" (enlace en `global.formularioRegistro` de `config/cursos.json`). El flujo crea todo. Después cargar el cronograma en el Excel del curso.
- Cambiar una fecha: editar el Excel del curso y guardar. La página marca "Reprogramada".
- Cancelar una clase: escribir `Cancelada` en la columna Situación.
- Forzar publicación: Actions > Actualizar datos > Run workflow.
- Si un Excel queda dañado, la página conserva los últimos datos buenos y el sitio de administración muestra la causa.

## 9. Diagnóstico rápido

| Síntoma | Dónde mirar |
|---|---|
| Guardé el Excel y no cambia la página | Flujo Cronograma a GitHub: historial de ejecuciones; luego Actions de GitHub; la ruta debe coincidir con `carpeta` |
| "Carpeta no registrada" en el resumen | Falta la fila en el Registro, o la carpeta del curso cambió de nombre y ya no coincide con `config/cursos.json` |
| "table not found" en Excel Online | El archivo no tiene tabla `Table1` |
| Se duplicó un curso | Se cambió el nombre de la carpeta; borrar el duplicado en `config/cursos.json` y `cursos/` y dejar la ruta correcta |
| El flujo de Forms falla al crear el equipo | Revisar la conexión de Teams y permisos de creación de grupos |
| No llegan alertas | `ALERTAS_ACTIVAS`, validez de `AVISOS_TOKEN`, flujo de Alertas encendido, conexión de Outlook |
| Forbidden al enviar a GitHub | Política OAuth de la organización o conexión de GitHub caducada |

## 10. Lista de verificación de traspaso

1. Renovar `AVISOS_TOKEN` antes del 21 de octubre de 2027 (token fine-grained de `EducontinuaFEJPI`, solo el repositorio `avisos-internos`, Issues en lectura y escritura).
2. Copropietarios en los equipos de Teams de cada curso.
3. Retirar la cuenta vieja y el registro viejo del sitio Especializaciones cuando ya no se necesiten: ningún flujo activo depende de ellos.
