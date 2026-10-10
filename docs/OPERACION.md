# Operación: guía para quien edita los Excel

Cada curso tiene su Excel, llamado `Cuadro de horas módulos y profesores.xlsx`, dentro de su carpeta en **SharePoint > Especializaciones > EDU CONTINUA 2026**. Editar ese archivo es lo único que hay que hacer: al guardar, la página del curso se actualiza sola en uno o dos minutos. No hay que tocar nada más.

El sitio base de administración (la dirección la tiene quien administra) muestra el estado de todos los cursos, qué falta por confirmar y los enlaces para copiar y enviar a los estudiantes.

## Cada periodo: abrir cursos nuevos o repetir los anteriores

Todo se maneja desde un solo Excel, **Registro de cursos**, que está en la carpeta EDU CONTINUA 2026 de SharePoint. Tiene una fila por curso y una hoja Instrucciones. No hace falta GitHub.

1. En SharePoint crea la carpeta del periodo (por ejemplo `EDU CONTINUA 2027-1`) y, adentro, la carpeta de cada curso con su Excel `Cuadro de horas módulos y profesores`.
2. En Registro de cursos copia las filas del periodo anterior, pégalas debajo y cambia **Periodo** y **Carpeta del periodo**. Para un curso nuevo escribe una fila nueva. Guarda.
3. En un par de minutos el curso aparece en el sitio de administración con su **enlace nuevo para estudiantes**. Guarda también el Excel de cada curso para que se publique su cronograma.

Los enlaces del periodo anterior no cambian: cuando termina la última clase, esa página pasa sola a "finalizado", sin botones de Teams, y el curso se mueve al **Archivo** del sitio de administración. Nada se borra.

Si una fila del registro tiene un error (falta el nombre, una hora mal escrita), el sitio de administración lo avisa en **Cursos y periodos** y esa fila no se procesa. Si alguien guarda el Excel de un curso cuya carpeta no está en el registro, la carpeta aparece en esa misma sección como pendiente de registrar.

## Qué muestra el sitio de administración

- **Urgente, próximos 14 días.** Las clases de todos los cursos a las que todavía les falta docente, asistente o enlace de Teams, por fecha.
- **Semáforo por curso.** Rojo: el Excel no se pudo leer, o una clase de hoy o mañana no tiene docente o enlace de Teams. Ámbar: falta algo en los próximos 14 días o el curso aún no tiene cronograma. Verde: nada urgente. El asistente PAT faltante nunca pone en rojo.
- **Agenda de las próximas 4 semanas** de todos los cursos, con un aviso si un docente o un asistente tiene dos clases a la vez (en el mismo curso o en cursos distintos).
- **Reportes de horas** por docente, por curso y por mes, filtrables por periodo. Se descargan para Excel (archivo CSV) o se guardan en PDF. Las horas salen de la columna Horas del Excel. Donde esa casilla está vacía se calculan con el horario del curso y quedan marcadas como estimadas. Una clase con dos docentes cuenta completa para cada uno.

La plantilla en blanco de un curso (con validaciones de día, fecha, horas y enlace) se regenera con `python scripts/generar_plantilla_xlsx.py SALIDA.xlsx`. Se copia a la carpeta del curso y se renombra a `Cuadro de horas módulos y profesores.xlsx`.

## Qué sí puedes cambiar

Dentro de la tabla (hoja `DISTRIBUCIÓN HORAS`, columnas A a J):
- Fechas de las clases. Usa fechas reales de Excel, no texto.
- Unidad, tema, horas, docentes, asistentes PAT y enlaces de Teams (deben empezar por `https://`).
- Agregar o quitar filas dentro de la tabla. Cada fila de clase debe tener `CLASE` en `No. de clase` y un número único en `No.`.

**Si no tienes un dato, déjalo en blanco.** La página muestra "Por confirmar" en docente y asistente, deja el botón de Teams apagado con "Enlace por confirmar" y oculta lo que no aplica (el temario por unidades si ninguna clase tiene unidad, las horas si faltan). Cuando llenes la casilla y guardes, el cambio aparece solo. No escribas "N/A", "pendiente" ni "por definir": eso se publicaría como si fuera un nombre.

Si dejas un tema vacío, la página usa el de la clase anterior. Si la columna `Día` no coincide con la fecha, la página muestra el día correcto.

## Qué no debes hacer

- Renombrar la hoja `DISTRIBUCIÓN HORAS`, la carpeta del curso o el archivo (el nombre debe seguir empezando por `Cuadro de horas`).
- Cambiar, borrar o mover los encabezados (`No.`, `Unidad`, `Tema`, `Horas`, `No. de clase`, `Profesor`, `Día`, `Fecha`, `Asistente PAT`, `Link de reunión`).
- Mover columnas o escribir datos fuera de A:J (se ignoran).
- Repetir un número en la columna `No.`.
- Dejar una fecha como texto que no sea una fecha, por ejemplo "pronto".
- Poner correos, teléfonos o datos de pago en este archivo: todo lo de A:J se publica.
- Mover el Excel a otra carpeta: la página reconoce el curso por la carpeta.

## Qué pasa si algo se rompe

Si el Excel queda con un problema bloqueante (falta un encabezado, no hay clases, una fecha no se entiende o hay `No.` repetidos), esa actualización no se aplica y **la página del curso sigue mostrando los últimos datos buenos**. Nadie ve una página rota. El sitio base muestra una franja ámbar en la tarjeta del curso con la causa. Corrige el Excel y guarda: la siguiente publicación quita el aviso.

Los detalles quedan en GitHub: pestaña **Actions**, última ejecución de "Actualizar datos" (el resumen dice qué encontró).

## Cambios de fecha

Cuando cambias la fecha de una clase, la página muestra una franja "Cambio de fecha" y marca la clase como "Reprogramada" con la fecha anterior tachada. El aviso dura hasta que la clase pase o 14 días. Si devuelves la fecha a la original, el aviso desaparece. El historial queda en `cursos/<curso>/estado/cambios.json`: no lo edites a mano. En el sitio base aparecen los cambios de todos los cursos.

Quienes se suscribieron al calendario reciben la nueva fecha según el ritmo de su aplicación, que puede tardar horas.

## Retirar los enlaces de Teams

En `config/cursos.json`, dentro de `global`, cambia `"mostrarLinksTeams": true` a `false`, ejecuta `python scripts/cursos.py sincronizar` y sube el cambio. Desaparecen los botones de las páginas, del PDF y de los archivos de calendario.

## Forzar una actualización

Vuelve a guardar el Excel. Para republicar el sitio sin cambiar datos: Actions > **Actualizar datos** > **Run workflow**.

## Ajustes por curso

Los de uso normal (nombre, tipo, modalidad, horario, página oficial, periodo) se cambian en el Excel Registro de cursos. Lo siguiente es para quien administra el repositorio (`config/cursos.json`):

- `programa`, `programaCorto`, `tipo` (Diplomado o Curso), `marca` (texto de la cabecera) y `modalidad`.
- `urlPaginaOficial`: enlace al botón "Inscripción y valores".
- `horario`: ventana fija o modo `porHoras` (ver README).
- Dentro de `global`: `siglas` (se conservan en mayúscula al mostrar las unidades), `profesoresInstitucionales` y `diasAvisoCambio`.

Después de editar el registro ejecuta `python scripts/cursos.py sincronizar` y sube el cambio.
