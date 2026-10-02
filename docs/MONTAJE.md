# Guía de montaje

Cómo se conectan los Excel de SharePoint con el sitio público. Se hace una sola vez. Un curso nuevo no exige repetirla: solo se agrega al registro (ver README).

```
Excel de un curso en SharePoint (tabla Table1)
   │  alguien lo edita y guarda
   ▼
Power Automate (un solo flujo "Cronograma a GitHub")
   │  Excel Online lee las filas · GitHub: "Create a repository dispatch event" (excel-actualizado)
   │  carga útil: {"ruta": carpeta del Excel, "modificado": fecha, "filas": las filas}
   ▼
GitHub Actions: reconoce el curso por la ruta (config/cursos.json), valida, construye cursos/<id>/data/data.json,
detecta cambios de fecha, genera cronograma.ics, hace commit y despliega TODO el sitio
   ▼
GitHub Pages: c/<curso>-<código>/ (estudiantes), g/<código>/ (administración)
```

Por qué así: el inquilino de la Universidad no permite vínculos "Cualquier persona", así que GitHub no puede descargar el Excel. Power Automate lee la tabla con la cuenta institucional y manda las filas dentro del propio aviso.

## 1. Repositorio y GitHub Pages

- Repositorio público `cursos-educacion-continua-2026` (antes `cronograma-compliance-2026-2`).
- Settings > Pages > Source: **GitHub Actions**.
- Variable del repositorio `MODO_ENTRADA = json` (heredada; el workflow ya solo trabaja en este modo). No existe el secreto `EXCEL_URL`.

## 2. Registro de cursos

`config/cursos.json` es la única lista de cursos. Por curso: `id`, `codigo` (aleatorio, forma parte de la dirección), `carpeta` (ruta dentro de `EDU CONTINUA 2026`), nombre, tipo, modalidad, horario y enlace oficial. `python scripts/cursos.py sincronizar` genera `cursos/<id>/config/contenido.json`.

El workflow reconoce el curso porque la ruta recibida **contiene la carpeta completa como tramo**. Si la carpeta no está registrada, esa ejecución no actualiza nada y deja una advertencia en el resumen.

## 3. El flujo de Power Automate (`Cronograma a GitHub`)

Un flujo vigila toda la carpeta `EDU CONTINUA 2026`. Cuatro pasos:

1. **SharePoint, Cuando se crea o modifica un archivo (solo propiedades).** Sitio `https://unisabanaedu.sharepoint.com/sites/Especializaciones`, biblioteca `Documents`, sin carpeta. En Configuración tiene **una condición de desencadenador**:
   `@and(contains(triggerOutputs()?['body/{FilenameWithExtension}'], 'Cuadro de horas'), contains(triggerOutputs()?['body/{Path}'], 'EDU CONTINUA 2026'))`
   Si se renombra un archivo para que ya no empiece por `Cuadro de horas`, deja de disparar.
2. **Excel Online (Business), Enumerar filas presentes en una tabla.** Ubicación: el sitio Especializaciones. Biblioteca: `Documentos`. **Archivo: contenido dinámico `Identifier` del paso 1** (`@{triggerOutputs()?['body/{Identifier}']}`), de modo que lee el Excel que cambió. **Tabla: el nombre `Table1`** (no el identificador interno: ese cambia de un archivo a otro).
3. **Seleccionar.** Arma las 10 columnas. Excel Online codifica el punto de los encabezados: `No.` llega como `No_x002e_` y `No. de clase` como `No_x002e_ de clase`. El procesador decodifica estos nombres.
4. **GitHub, Create a repository dispatch event.** Propietario y repositorio `cursos-educacion-continua-2026`, evento `excel-actualizado` y carga útil:
   ```
   { "ruta": "@{triggerOutputs()?['body/{Path}']}", "modificado": "@{utcNow()}",
     "filas": "@{string(body('Select'))}" }
   ```

Fechas: el conector las entrega como número serial de Excel en texto (por ejemplo `"46296"`). El procesador las convierte.

Requisito de cada Excel: hoja `DISTRIBUCIÓN HORAS` con una tabla de Excel llamada **`Table1`** y los encabezados exactos de A a J.

## 4. Privacidad de los registros

El repositorio es público y los registros de Actions también. El workflow lee la carga útil del archivo del evento (`GITHUB_EVENT_PATH`) y nunca de una variable de entorno, porque GitHub imprime esas variables en el registro. No cambiar eso.

## 5. Primera carga de un curso

Una página de curso muestra "El cronograma de este curso se publicará pronto" hasta el primer guardado de su Excel con el flujo activo. Para cargarlo sin cambiar nada visible: abre el Excel en SharePoint, escribe una letra en una celda fuera de la tabla (por ejemplo `K1`), bórrala y cierra. El flujo avisa a GitHub y en uno o dos minutos la página tiene los datos. El sitio base de administración (tarjeta del curso) muestra cuándo se publicó.

## 6. Prueba de extremo a extremo

1. **Cambio de fecha.** Cambia la fecha de una clase y guarda. La franja ámbar "Cambio de fecha" y la insignia "Reprogramada" deben aparecer. Luego devuelve la fecha original: el aviso desaparece.
2. **Excel dañado.** Borra un encabezado (por ejemplo `Profesor`) y guarda. La ejecución falla con un mensaje claro, la página sigue con los últimos datos buenos y el sitio base muestra la franja de error en la tarjeta del curso. Restaura el encabezado.

## 7. Reparaciones frecuentes

- **El flujo no dispara:** revisar en el paso 1, Configuración, la condición del desencadenador, y que el archivo siga llamándose `Cuadro de horas ...` dentro de `EDU CONTINUA 2026`.
- **El flujo corre pero GitHub dice "carpeta no registrada":** agregar el curso a `config/cursos.json` (la ruta recibida se ve en el resumen de la ejecución).
- **El paso de Excel falla con "table not found":** el archivo no tiene una tabla llamada `Table1`.
- **Una ejecución falló por un error de código ya corregido:** en GitHub, `Re-run failed jobs` reutiliza el mismo evento.
- **Al cambiar de archivo o de sitio en el diseñador,** los campos Biblioteca y Tabla conservan identificadores viejos: bórralos con la X y vuelve a elegir.
