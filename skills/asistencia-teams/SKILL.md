---
name: asistencia-teams
description: Usar cuando el usuario adjunte un reporte de asistencia de una reunión de Microsoft Teams (archivo "Attendance report", CSV o XLSX) junto con el Excel «Formato de asistencia» de un curso o diplomado de Educación Continua de la Universidad de La Sabana, o cuando pida actualizar, marcar o pasar la asistencia de una clase. Calcula quién asistió y devuelve el Excel con las marcas de esa clase.
---

# Asistencia desde Teams (Educación Continua, Universidad de La Sabana)

Sirve para cualquier curso o diplomado que use el Excel «Formato de asistencia - <curso>.xlsx». El usuario es un PAT (asistente del curso). Escríbele en español, claro y corto, sin guiones medios.

## Qué debe adjuntar el usuario
1. El reporte de asistencia de Teams de UNA clase (`... Attendance report ....csv` o `.xlsx`).
2. El Excel de asistencia del curso, descargado de SharePoint en ese momento (la versión más reciente).
3. Opcional: notas en el chat sobre cómo aparecen algunos estudiantes en Teams (ver «Información extra sobre los nombres»).

Si falta el reporte o el Excel, pídelo y explica cómo descargarlo (ver «Ayuda para el usuario»). No sigas sin los dos.

## Procedimiento
Usa el script `scripts/asistencia_teams.py` de esta skill con `python3 -I`. Necesita `openpyxl` (si no está, instálalo con `pip install openpyxl`). Copia los archivos del usuario a una carpeta de trabajo y no cambies sus nombres.

1. Lee el libro:
   `python3 -I scripts/asistencia_teams.py libro LIBRO.xlsx`
   Devuelve las clases (número, columna, fecha, estado, cuántas marcas tiene), los estudiantes (nombre, fila) y los alias de la hoja «Alias Teams» si el libro la tiene. Si falla, el archivo no es el «Formato de asistencia»: díselo al usuario y detente.
2. Si el usuario dio notas sobre nombres en el chat, conviértelas en `alias-chat.json` (ver abajo). Calcula la asistencia:
   `python3 -I scripts/asistencia_teams.py calcular REPORTE LIBRO.xlsx [alias-chat.json]`
   Los alias de la hoja «Alias Teams» se aplican solos; el JSON se suma a ellos. La fecha de la clase sale del reporte (Start time), nunca del nombre del archivo.
3. Revisa antes de escribir y pregunta solo lo necesario, todo en un mismo mensaje:
   - Si `alertas` no está vacío, muéstralo y pregunta si es el reporte correcto.
   - Si `avisos_alias` no está vacío, muéstralo: son filas de la hoja «Alias Teams» que no se entendieron y hay que corregir en el Excel.
   - Si el título de la reunión dice «Clase NN» y no coincide con la clase de esa fecha en el libro, avísalo.
   - Si la columna de esa fecha ya tiene marcas, NO sobrescribas: pregunta.
   - `revision_manual` (entre 40 % y 50 %): muestra nombre, porcentaje y minutos, y pregunta si marca 1, 0 o la deja vacía.
   - `sin_coincidencia` (cuentas con 20 % o más que no se emparejaron): pregunta a quién corresponde cada una, entre los estudiantes que quedaron sin registro, o si es alguien no matriculado (profesor, organizador, invitado).
   Si el usuario dice que una cuenta es de un estudiante, agrégala a `alias-chat.json` y vuelve a calcular.
4. Escribe las marcas en una COPIA:
   guarda `marcas` (con las decisiones del usuario) en `marcas.json` y ejecuta
   `python3 -I scripts/asistencia_teams.py escribir LIBRO.xlsx "Formato de asistencia - <curso>.xlsx" AAAA-MM-DD marcas.json`
   (si hay dos clases el mismo día, usa `AAAA-MM-DD#N`). El nombre del archivo de salida debe ser exactamente el mismo del original.
   El script cambia solo las celdas de esa clase. No guardes el libro con openpyxl ni con otra herramienta: se dañan la tabla y las fórmulas que usa el sitio de administración.
5. Entrega:
   - El Excel actualizado para descargar.
   - Un informe corto: clase y fecha, cuántos asistieron (1), cuántos faltaron (0), los que quedaron vacíos para revisar, las cuentas no matriculadas y las que se emparejaron por alias.
   - Si hubo alias nuevos (del chat o de tus preguntas), dale una tabla con las filas exactas para agregar a la hoja «Alias Teams» (columnas Estudiante, Nombre o cuenta en Teams, Correo en Teams, Nota), para que la próxima vez se reconozcan solos. No las escribas tú en el libro.
   - Recuérdale cómo subirlo (ver abajo).

## Reglas de asistencia (no las cambies)
- Porcentaje = tiempo presente / duración de la reunión. El tiempo es la UNIÓN de los tramos de entrada y salida de todas las cuentas de la misma persona, no la suma.
- 50 % o más: 1. Entre 40 % y menos de 50 %: vacía y se avisa. Menos de 40 % o sin registro: 0.
- Profesores, organizadores, invitados y personal de la Universidad no se marcan, solo se listan.
- Los estudiantes salen de la columna C de la hoja Asistencia. No agregues ni quites estudiantes, no cambies nombres ni toques las columnas calculadas (grises).

## Información extra sobre los nombres
A veces la cuenta de Teams no se parece al nombre de la lista (apodos, cuentas de la empresa, de un familiar, «Invitado», correos sin nombre). Hay dos formas de decírselo a la skill:

1. **Hoja «Alias Teams» del Excel del curso** (la forma permanente; la comparten todos los PAT del curso). Una fila por cuenta:
   - A, Estudiante: el nombre como está en la columna C de Asistencia (sirve sin tildes ni mayúsculas, o con dos palabras del nombre si no hay otro igual). Para un profesor, organizador o invitado escribe `No matriculado`.
   - B, Nombre o cuenta en Teams: tal como sale en el reporte, por ejemplo `LAURAPR88 (Guest)`.
   - C, Correo en Teams: el correo de esa cuenta, si sale en el reporte. Es lo más seguro para emparejar.
   - D, Nota: libre.
   Los cursos creados desde noviembre de 2026 ya traen la hoja. Si el libro no la tiene, explícale al usuario que agregue en Excel una hoja llamada exactamente `Alias Teams` con esos cuatro encabezados en la fila 1.
2. **Notas en el chat** (para esta vez). Ejemplos: «En Teams, Lau P es Laura Pérez», «el correo jgomez@empresa.com es de Juan Gómez», «Carolina es la profesora». Conviértelas en `alias-chat.json` usando el nombre exacto de la columna C. Si una nota puede referirse a dos estudiantes, pregunta antes de calcular. Al final dale las filas para la hoja «Alias Teams».

Formato de `alias-chat.json` (el script también lo acepta si el usuario trae uno de antes):
```json
{"correos": {"NOMBRE COMO ESTÁ EN LA COLUMNA C": ["correo@ejemplo.com"]},
 "nombres": {"Nombre de la cuenta de Teams": "NOMBRE COMO ESTÁ EN LA COLUMNA C"},
 "no_matriculados": ["Nombre del profesor u organizador"]}
```
Los alias tienen correos de estudiantes: solo van en el Excel del curso. No los publiques ni los compartas fuera.

## Ayuda para el usuario
- **Descargar el reporte de Teams:** en el calendario de Teams abre la reunión de esa clase, pestaña **Asistencia**, botón **Descargar**. Lo puede descargar el organizador de la reunión.
- **Descargar el Excel del curso:** en SharePoint, carpeta del curso, clic en los tres puntos del archivo «Formato de asistencia», **Descargar**.
- **Subir el Excel actualizado:** primero que nadie lo tenga abierto. En la carpeta del curso, **Cargar**, **Archivos**, elige el archivo que entregaste y acepta **Reemplazar**. Si la carpeta del curso está sincronizada con OneDrive en su computador, basta con guardar el archivo encima del anterior en esa carpeta. Si algo sale mal, SharePoint guarda las versiones anteriores (tres puntos, **Historial de versiones**).
- En unos minutos el sitio de administración muestra la asistencia nueva.
