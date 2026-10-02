# Operación: guía para quien edita el Excel

El Excel es la única fuente de verdad. El archivo que alimenta la página es `Cuadro de horas módulos y profesores - 3er 2026_2 (3).xlsx`, en el sitio SharePoint **Información cursos y diplomados FEJPI**. Editar la otra copia (en el sitio Especializaciones) no actualiza la página. Cuando guardas un cambio, la página se actualiza sola en unos minutos (el tiempo medido está en el README). No hay que tocar nada más.

## Qué sí puedes cambiar

Dentro de la tabla `Table1` (hoja `DISTRIBUCIÓN HORAS`, columnas A a J):
- Fechas de las clases. Usa fechas reales de Excel, no texto.
- Docentes, asistentes PAT y temas.
- Enlaces de Teams (deben empezar por `https://`).
- Agregar o quitar filas dentro de la tabla. Cada fila de clase debe tener `CLASE` en la columna `No. de clase` y un número único en `No.`.

Si dejas un tema vacío, la página usa el de la clase anterior. Si la columna `Día` no coincide con la fecha, la página muestra el día correcto y el resumen de la ejecución lo marca como advertencia.

## Qué no debes hacer

- Renombrar la hoja `DISTRIBUCIÓN HORAS`.
- Cambiar, borrar o mover los encabezados (`No.`, `Unidad`, `Tema`, `Horas`, `No. de clase`, `Profesor`, `Día`, `Fecha`, `Asistente PAT`, `Link de reunión`).
- Mover columnas o escribir datos fuera de A:J (se ignoran).
- Repetir un número en la columna `No.`.
- Dejar una fecha como texto que no sea una fecha, por ejemplo "pronto".
- Cambiar el permiso del vínculo compartido ni borrar el archivo.

## Qué pasa si algo se rompe

Si el Excel queda con un problema bloqueante (falta un encabezado, no hay clases, una fecha no se entiende, hay `No.` repetidos o el vínculo dejó de funcionar), la actualización falla y **la página sigue mostrando los últimos datos buenos**. Nadie ve una página rota. Para saber la causa:

1. En GitHub abre la pestaña **Actions** y entra a la última ejecución de "Actualizar datos".
2. Lee el resumen: dice qué encontró, por ejemplo "No se encontró la fila de encabezados exactos. Columnas que faltan: ['Profesor']".
3. Corrige el Excel y guárdalo. La siguiente ejecución lo toma sola.

Las advertencias (día que no coincide, enlace vacío, horas distintas de 3) no detienen nada. Se publican y quedan listadas en el resumen.

## Forzar una actualización manual

Actions > **Actualizar datos** > **Run workflow** > **Run workflow**. Sirve si acabas de corregir algo y no quieres esperar.

## Cambios de fecha y el aviso a los visitantes

Cuando cambias la fecha de una clase, la página muestra una franja "Cambio de fecha" y marca la clase como "Reprogramada" con la fecha anterior tachada. El aviso dura hasta que la clase pase o hasta 14 días (valor `diasAvisoCambio` en `config/contenido.json`). Si devuelves la fecha a la original, el aviso desaparece. El historial queda en `estado/cambios.json`: no lo edites a mano.

Quienes se suscribieron al calendario reciben la nueva fecha según el ritmo de su aplicación, que puede tardar horas.

## Retirar los enlaces de Teams

En `config/contenido.json` cambia `"mostrarLinksTeams": true` a `false` y guarda el cambio en GitHub. Desaparecen los botones "Unirme en Teams" de la página, del PDF y de los archivos de calendario.

## Otros ajustes en `config/contenido.json`

- `urlPaginaOficial`: enlace a la página oficial del diplomado.
- `contacto`: datos de contacto institucional (hoy vacío, por eso el pie no los muestra).
- `docentesExtra`: biografía opcional por docente, por ejemplo `"Marta Lucia Ramírez": {"bio": "..."}`.
- `profesoresInstitucionales`: nombres que se listan pero no se cuentan como docentes (hoy `SABANA`).
- `siglas`: siglas que se conservan en mayúscula cuando se muestran los nombres de unidad en minúscula.
