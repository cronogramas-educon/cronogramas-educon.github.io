# Asistencia por curso

El sitio de administración muestra cómo va la asistencia de cada curso, a partir de un Excel que se guarda en la carpeta del curso, junto al Cuadro de horas.

```
Excel de asistencia (SharePoint)  →  flujo de Power Automate (evento excel-actualizado)  →  GitHub guarda el resumen  →  sección Asistencia del hub y «Mi asistencia» de cada curso
```

## El Excel

Se genera con `python scripts/generar_asistencia_xlsx.py DATOS.json SALIDA.xlsx` (el formato de `DATOS.json` está en el encabezado del script). Los datos de estudiantes nunca viven en el repositorio, que es público: el JSON se escribe fuera de él.

Hojas: **Instrucciones**, **Asistencia** (tabla `Table1`, una columna por clase), **Resumen** (reglas y cuentas) y **Cronograma** (fecha y situación de cada clase).

- Se marca 1 (asistió) o 0 (faltó). Una clase con alguna marca pasa sola a Dictada. Una clase sin marcas no se ha dictado.
- Una clase **cancelada** se marca en el Cuadro de horas, columna K "Situación" = Cancelada (no se borra la fila). Deja de contar en horas, asistencia, calendario y alertas, la página de estudiantes avisa, y las demás clases conservan su número. Una clase reprogramada solo cambia de fecha en el Cuadro.
- **El Cuadro de horas manda.** El número de clases sale del Cuadro: si se agrega, quita o reprograma una clase allí, el sitio recalcula las faltas permitidas y el estado de cada estudiante sin tocar este Excel. Del Excel de asistencia el sitio solo toma las marcas 1 o 0 de las columnas Clase 1, Clase 2, etc. (la clase N del Cuadro es la columna Clase N).
- Las columnas grises del Excel (Asistió, Faltas, Estado, "Clases del curso"...) son una ayuda para quien lo llena. El sitio no las lee y las recalcula con las mismas reglas; si alguna vez difieren, vale el sitio. No hace falta escribir "Clases del curso".

## Cuándo se avisa

Las reglas se calculan sobre las **faltas permitidas** del curso, no sobre un número fijo, para que valgan igual con 35 clases o con 8.

- Mínimo para certificar: 80 % (editable en la hoja Resumen). Asistencias mínimas = el 80 % de las clases programadas, redondeado hacia arriba. Faltas permitidas = programadas menos mínimas.
- **Al día**: ha usado menos de la mitad de las faltas permitidas.
- **Atención**: ha usado la mitad o más (en un diplomado de 35 clases, desde la cuarta falta).
- **En riesgo**: ha usado el 80 % o más (desde la sexta falta, le queda una).
- **Perdió el mínimo**: ya superó las faltas permitidas.
- **Aprobó**: terminaron todas las clases y cumplió el mínimo.

Los umbrales (80 % para certificar, 50 % para Atención y 80 % para En riesgo) están en `scripts/asistencia.py` (`MINIMO`, `ATENCION`, `RIESGO`).

## Qué se publica y qué no

El flujo manda todas las filas de la tabla, nombres incluidos. `scripts/asistencia.py` guarda en `cursos/<curso>/estado/asistencia.json` un resumen con el número de lista y la etiqueta «Nombre + primer apellido» (con 4 o más palabras, la 1.ª y la 3.ª; con 3, la 1.ª y la 2.ª; con inicial mayúscula), sin documentos. El hub (`g/<código>/asistencia/`) lo muestra como «Estudiante 7». Cada página de curso publica `asistencia.json` con n, etiqueta, estado, asistió, faltas, quedan, porcentaje y marcas (sin seguimiento interno) para la sección «Mi asistencia», sin código de seguridad por decisión de la coordinación. La carga útil no se imprime en el registro de Actions.

## Alertas

El workflow de alertas suma una sección **Asistencia** al correo:

- Diaria: clases que ya pasaron y no tienen asistencia marcada.
- Los lunes (revisión semanal): además, los estudiantes en Atención, En riesgo o que perdieron el mínimo, con su número de lista y cuántas faltas les quedan.

## Qué hace falta para que funcione de punta a punta

El flujo "Cronograma a GitHub" tiene que reaccionar también al Excel de asistencia: además de `Registro de cursos.xlsx` y los `Cuadro de horas`, su condición debe incluir los archivos cuyo nombre contenga `Formato de asistencia`. La acción "List rows present in a table" lee `Table1`, igual que con los demás. El sitio reconoce el Excel por sus columnas y el curso por la ruta de su carpeta.
