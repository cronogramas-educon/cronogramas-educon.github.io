# Guía de montaje

Esta guía conecta el Excel de SharePoint con la página pública. Se hace una sola vez y toma unos 30 minutos. Cada paso termina con un recuadro **Cómo sé que funcionó**. No sigas al paso siguiente hasta ver esa señal.

Resumen del recorrido que sigue la información:

```
Excel en SharePoint (Table1)
   │  alguien lo edita y guarda
   ▼
Power Automate: "Cuando se crea o modifica un archivo (solo propiedades)"
   │  acción de GitHub: "Create a repository dispatch event" (evento: excel-actualizado)
   ▼
GitHub Actions: descarga el .xlsx, valida, construye data.json, detecta cambios y genera cronograma.ics
   ▼
GitHub Pages: sirve el sitio estático
   ▼
Navegador del visitante: lee data/data.json y se refresca cada 60 segundos con la pestaña visible
```

Por qué así: una página pública no puede leer SharePoint directamente, porque exige iniciar sesión. GitHub Actions sí puede descargar el Excel desde un vínculo "Cualquier persona con el vínculo". Power Automate solo avisa que hubo un cambio.

**Aviso sobre la velocidad.** El desencadenador de SharePoint en Power Automate consulta cambios cada cierto tiempo, así que no es instantáneo. A eso se suman la ejecución del workflow y el despliegue de Pages. Como red de seguridad, el workflow también corre solo cada 15 minutos. El tiempo real se mide en el paso 6 y se anota en el README.

---

## Paso 1. Repositorio y GitHub Pages

1. En GitHub, crea el repositorio **público** `cronograma-compliance-2026-2` (Repositories > New). No agregues README ni .gitignore.
2. Desde la carpeta del proyecto, sube el código:
   ```bash
   git remote add origin https://github.com/<usuario>/cronograma-compliance-2026-2.git
   git branch -M main
   git push -u origin main
   ```
3. Ve a **Settings > Pages**. En **Build and deployment > Source** elige **GitHub Actions**.

> **Cómo sé que funcionó:** la pestaña Pages muestra la dirección `https://<usuario>.github.io/cronograma-compliance-2026-2/`. Aún puede dar error 404 hasta que corra el primer despliegue (paso 4).

**Alternativa con repositorio privado.** GitHub Pages en repositorio privado exige un plan de pago. Si prefieres repositorio privado, conecta el mismo repositorio a Cloudflare Pages (plan gratuito) con estas opciones: sin comando de construcción y directorio de salida `/`. El workflow seguiría haciendo commit de los datos, y Cloudflare publicaría cada commit. En ese caso se puede quitar el job `desplegar` del workflow. Esta guía continúa con GitHub Pages.

## Paso 2. Compartir el Excel

1. En SharePoint, abre el Excel y pulsa **Compartir**.
2. Abre la configuración del vínculo y elige **Cualquier persona con el vínculo**.
3. Deja el permiso en **Puede ver**. Nunca uses "Puede editar".
4. Pulsa **Copiar vínculo**.
5. Pega el vínculo en una ventana de incógnito del navegador.

> **Cómo sé que funcionó:** en incógnito, el Excel abre o se descarga sin pedir inicio de sesión.

Si la opción "Cualquier persona" no aparece, el inquilino de la Universidad la bloquea. Tienes dos caminos: pedir a TI que la habilite para ese archivo (Plan A), o usar el **Plan B** (anexo al final), que no necesita vínculo anónimo.

## Paso 3. Guardar el vínculo como secreto

1. En el repositorio ve a **Settings > Secrets and variables > Actions > New repository secret**.
2. Nombre: `EXCEL_URL`. Valor: el vínculo copiado en el paso 2.
3. Pulsa **Add secret**.

Nunca pegues el vínculo en el código, en un issue ni en un chat.

> **Cómo sé que funcionó:** `EXCEL_URL` aparece en la lista de secretos del repositorio (su valor no se vuelve a mostrar).

## Paso 4. Primera ejecución del workflow

El archivo `.github/workflows/actualizar-datos.yml` ya viene en el repositorio. Se dispara por tres vías: el aviso de Power Automate (`repository_dispatch`, evento `excel-actualizado`), el botón manual (`workflow_dispatch`) y un temporizador cada 15 minutos.

1. Ve a **Actions > Actualizar datos > Run workflow > Run workflow**.
2. Abre la ejecución y espera a que termine.

Qué hace: descarga el Excel agregando `download=1`, comprueba que sea un .xlsx real, valida, construye `data/data.json`, detecta cambios de fecha y genera `cronograma.ics`. Si el `hash` no cambió, no hace commit ni despliegue. Si cambió, hace commit y despliega a Pages en la misma ejecución.

> **Cómo sé que funcionó:** el resumen de la ejecución muestra "OK: 35 clases, 105 horas, 17 unidades", y la dirección de Pages abre la página con los datos reales.

Si falla, el resumen indica la causa. Las más comunes: el vínculo no tiene permiso para "Cualquier persona" (el archivo recibido es una página HTML), el vínculo expiró, o alguien cambió los encabezados del Excel.

## Paso 5. Flujo de Power Automate

1. Entra a Power Automate > **Crear** > **Flujo de nube automatizado**.
2. Desencadenador: SharePoint > **Cuando se crea o modifica un archivo (solo propiedades)**. Elige el sitio, la biblioteca y la carpeta donde está el Excel.
3. Agrega una **Condición**: **Nombre del archivo** es igual al nombre del cronograma. Así otros archivos de la carpeta no disparan el flujo.
4. En la rama "Sí" agrega la acción **GitHub > Create a repository dispatch event** con estos valores:
   - Propietario del repositorio: tu usuario u organización de GitHub.
   - Nombre del repositorio: `cronograma-compliance-2026-2`.
   - Tipo de evento: `excel-actualizado`.
   - Inicia sesión con la cuenta de GitHub dueña del repositorio.
5. Agrega un paso de correo que te avise si el flujo falla: en la acción de GitHub elige **Configurar ejecución posterior** y marca "ha fallado", luego conecta un paso **Enviar un correo electrónico**.
6. Guarda y prueba con **Probar > Manualmente**.

> **Cómo sé que funcionó:** en la pestaña Actions del repositorio aparece una ejecución nueva con el evento `excel-actualizado`.

**Verifica y confirma:** esta guía supone que tu cuenta ofrece la acción de GitHub "Create a repository dispatch event" como conector estándar. Si no aparece, pídele a quien administra Power Automate que lo confirme. El respaldo cada 15 minutos sigue funcionando aunque el flujo no exista.

Notas: el desencadenador de SharePoint consulta cambios con cierta frecuencia y no es instantáneo. El autoguardado de Excel también puede demorar el aviso.

**Plan C (solo con licencia premium).** En vez de la acción de GitHub, usa la acción **HTTP** con un `POST` a `https://api.github.com/repos/<usuario>/<repositorio>/dispatches`, cuerpo `{"event_type":"excel-actualizado"}` y un token de acceso fino con permiso de contenido solo sobre ese repositorio. No se necesita para este proyecto.

## Paso 6. Prueba de extremo a extremo

Esta prueba es obligatoria y se hace con el flujo ya activo.

1. **Cambio de fecha.** Cambia la fecha de una clase en el Excel y guarda. Cronometra desde que guardas hasta que la página (recargada) muestre la franja ámbar "Cambio de fecha" y la insignia "Reprogramada". Anota el tiempo en el README, sección "Tiempos medidos".
2. **Reversa.** Devuelve la fecha original y confirma que el aviso desaparece. El historial queda en `estado/cambios.json`.
3. **Excel dañado.** Borra un encabezado (por ejemplo `Profesor`) y guarda. Confirma que la ejecución falla con un mensaje claro y que la página sigue mostrando los últimos datos buenos. Restaura el encabezado después.

> **Cómo sé que funcionó:** los tres resultados coinciden con lo descrito.

## Paso 7. Compartir

Comparte la dirección de Pages. Opcionales:
- Código QR: genéralo con cualquier generador y guárdalo en `assets/`.
- Dominio propio: Settings > Pages > Custom domain.
- Pestaña "Sitio web" en el equipo de Teams del diplomado, apuntando a la dirección de Pages.

Antes de compartir, completa `config/contenido.json` si quieres datos de contacto o biografías de docentes (hoy están vacíos a propósito).

## Paso 8. Operación

Quien edite el Excel debe leer `docs/OPERACION.md`.

---

## Anexo: Plan B (sin vínculo anónimo)

Úsalo si el inquilino no permite "Cualquier persona". El flujo de Power Automate lee la tabla y envía las filas dentro del propio evento. El workflow acepta ese JSON en lugar de descargar el Excel.

1. En el repositorio crea la variable **MODO_ENTRADA** con valor `json` (Settings > Secrets and variables > Actions > pestaña Variables).
2. En Power Automate, cambia el flujo así:
   1. Desencadenador igual que en el paso 5.
   2. **Excel Online (Business) > Enumerar filas presentes en una tabla**: archivo del cronograma, tabla `Table1`.
   3. **Seleccionar**: en "De" pon el resultado de la acción anterior. En "Asignar" crea estas 10 claves, cada una con el valor de la columna que lleva el mismo nombre: `No.`, `Unidad`, `Tema`, `Horas`, `No. de clase`, `Profesor`, `Día`, `Fecha`, `Asistente PAT`, `Link de reunión`.
   4. **GitHub > Create a repository dispatch event** con tipo `excel-actualizado` y, en la carga útil del cliente (client payload), el JSON `{"filas": <salida del paso Seleccionar>}`.
3. Las fechas llegan como números seriales de Excel. El procesador ya los convierte.
4. GitHub limita la carga útil del evento a unos 65 mil caracteres. Los datos actuales (35 filas) caben con holgura. Verifica el límite vigente en la documentación de GitHub si el programa crece mucho.
5. En este modo no hace falta el secreto `EXCEL_URL`.
6. En este modo el temporizador de 15 minutos se omite (no hay Excel que descargar), así que solo el aviso de Power Automate actualiza la página. Para forzar una actualización, vuelve a guardar el Excel o ejecuta el flujo manualmente.

---

## Cómo quedó el montaje real (Plan B en funcionamiento)

El inquilino de la Universidad no permite vínculos "Cualquier persona", así que este proyecto usa el Plan B. Datos concretos, por si hay que repararlo:

- **Variable del repositorio:** `MODO_ENTRADA = json` (Settings > Secrets and variables > Actions > Variables). No existe el secreto `EXCEL_URL`. El temporizador de 15 minutos se omite en este modo.
- **Flujo de Power Automate:** `Cronograma a GitHub`, cuenta institucional del propietario del flujo, con cuatro pasos:
  1. SharePoint, **Cuando se crea o modifica un archivo (solo propiedades)**. Sitio `Información cursos y diplomados FEJPI` (`/sites/InformacincursosydiplomadosFEJPI`), biblioteca `Documents`, sin carpeta. En Configuración tiene una **condición de desencadenador** que solo deja pasar archivos cuyo nombre contenga `3er 2026_2 (3)`.
  2. Excel Online (Business), **Enumerar filas presentes en una tabla**: ese mismo archivo y la tabla `Table1`.
  3. **Seleccionar**: arma las 10 columnas. Excel Online codifica el punto de los encabezados, por eso `No.` se lee como `No_x002e_` y `No. de clase` como `No_x002e_ de clase`. El procesador de datos también decodifica estos nombres.
  4. GitHub, **Create a repository dispatch event** (conector estándar, en vista previa): propietario y repositorio, evento `excel-actualizado` y carga útil `{"filas":"@{string(body('Select'))}"}`.
- **Qué archivo editar:** la copia `Cuadro de horas módulos y profesores - 3er 2026_2 (3).xlsx` del sitio FEJPI. Existe otra copia en el sitio `Especializaciones` que **no** alimenta la página. Si se renombra el archivo, hay que actualizar la condición del desencadenador y la ruta del paso de Excel.
- **Privacidad de los registros:** el repositorio es público, y los registros de Actions también. El workflow lee la carga útil del archivo del evento (`GITHUB_EVENT_PATH`) y nunca de una variable de entorno, porque GitHub imprime esas variables en el registro. No cambiar eso.
- **Fechas:** el conector entrega la fecha como número serial de Excel en texto (por ejemplo `"46296"`). El procesador la convierte.
- **Reintento:** si una ejecución falla por un dato del Excel, se corrige el Excel y se vuelve a guardar. Si falló por un error de código ya corregido, en GitHub se puede usar `Re-run failed jobs` sobre la ejecución fallida (reutiliza el mismo evento).
