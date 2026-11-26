---
name: asistencia-teams
description: Usar cuando el usuario adjunte un reporte de asistencia de una reunión de Microsoft Teams (archivo "Attendance report", CSV o XLSX) junto con el Excel «Formato de asistencia» de un curso o diplomado de Educación Continua de la Universidad de La Sabana, o cuando pida actualizar, marcar o pasar la asistencia de una clase. Calcula quién asistió y devuelve el Excel con las marcas de esa clase.
---

# Asistencia desde Teams (Educación Continua, Universidad de La Sabana)

Sirve para cualquier curso o diplomado que use el Excel «Formato de asistencia - <curso>.xlsx». El usuario es un PAT (asistente del curso). Escríbele en español, claro y corto, sin guiones medios.

## Qué debe adjuntar el usuario
1. El reporte de asistencia de Teams de UNA clase (`... Attendance report ....csv` o `.xlsx`).
2. El Excel de asistencia del curso, descargado de SharePoint en ese momento (la versión más reciente).
3. Opcional: `alias-asistencia.json`, si ya lo tiene de una vez anterior.

Si falta el reporte o el Excel, pídelo y explica cómo descargarlo (ver «Ayuda para el usuario»). No sigas sin los dos.

## Procedimiento
Usa el script `scripts/asistencia_teams.py` de esta skill con `python3 -I`. Necesita `openpyxl` (si no está, instálalo con `pip install openpyxl`). Copia los archivos del usuario a una carpeta de trabajo y no cambies sus nombres.

1. Lee el libro:
   `python3 -I scripts/asistencia_teams.py libro LIBRO.xlsx`
   Devuelve las clases (número, columna, fecha, estado, cuántas marcas tiene) y los estudiantes (nombre, fila). Si falla, el archivo no es el «Formato de asistencia»: díselo al usuario y detente.
2. Calcula la asistencia:
   `python3 -I scripts/asistencia_teams.py calcular REPORTE LIBRO.xlsx [alias-asistencia.json]`
   La fecha de la clase sale del reporte (Start time), nunca del nombre del archivo.
3. Revisa antes de escribir y pregunta solo lo necesario, todo en un mismo mensaje:
   - Si `alertas` no está vacío, muéstralo y pregunta si es el reporte correcto.
   - Si el título de la reunión dice «Clase NN» y no coincide con la clase de esa fecha en el libro, avísalo.
   - Si la columna de esa fecha ya tiene marcas, NO sobrescribas: pregunta.
   - `revision_manual` (entre 40 % y 50 %): muestra nombre, porcentaje y minutos, y pregunta si marca 1, 0 o la deja vacía.
   - `sin_coincidencia` (cuentas con 20 % o más que no se emparejaron): pregunta a quién corresponde cada una, entre los estudiantes que quedaron sin registro, o si es alguien no matriculado (profesor, organizador, invitado).
   Si el usuario dice que una cuenta es de un estudiante, agrégala al alias y vuelve a calcular.
4. Escribe las marcas en una COPIA:
   guarda `marcas` (con las decisiones del usuario) en `marcas.json` y ejecuta
   `python3 -I scripts/asistencia_teams.py escribir LIBRO.xlsx "Formato de asistencia - <curso>.xlsx" AAAA-MM-DD marcas.json`
   (si hay dos clases el mismo día, usa `AAAA-MM-DD#N`). El nombre del archivo de salida debe ser exactamente el mismo del original.
   El script cambia solo las celdas de esa clase. No guardes el libro con openpyxl ni con otra herramienta: se dañan la tabla y las fórmulas que usa el sitio de administración.
5. Entrega:
   - El Excel actualizado para descargar.
   - Un informe corto: clase y fecha, cuántos asistieron (1), cuántos faltaron (0), los que quedaron vacíos para revisar, las cuentas no matriculadas y las que se emparejaron por alias.
   - Si hubo alias nuevos, entrega también `alias-asistencia.json` y dile que lo guarde en la carpeta del curso para la próxima vez.
   - Recuérdale cómo subirlo (ver abajo).

## Reglas de asistencia (no las cambies)
- Porcentaje = tiempo presente / duración de la reunión. El tiempo es la UNIÓN de los tramos de entrada y salida de todas las cuentas de la misma persona, no la suma.
- 50 % o más: 1. Entre 40 % y menos de 50 %: vacía y se avisa. Menos de 40 % o sin registro: 0.
- Profesores, organizadores, invitados y personal de la Universidad no se marcan, solo se listan.
- Los estudiantes salen de la columna C de la hoja Asistencia. No agregues ni quites estudiantes, no cambies nombres ni toques las columnas calculadas (grises).

## Alias (`alias-asistencia.json`)
```json
{"correos": {"NOMBRE COMO ESTÁ EN LA COLUMNA C": ["correo@ejemplo.com"]},
 "nombres": {"Nombre de la cuenta de Teams": "NOMBRE COMO ESTÁ EN LA COLUMNA C"},
 "no_matriculados": ["Nombre del profesor u organizador"]}
```
Tiene correos de estudiantes: es solo para la carpeta del curso. No lo publiques ni lo pegues en otros chats.

## Ayuda para el usuario
- **Descargar el reporte de Teams:** en el calendario de Teams abre la reunión de esa clase, pestaña **Asistencia**, botón **Descargar**. Lo puede descargar el organizador de la reunión.
- **Descargar el Excel del curso:** en SharePoint, carpeta del curso, clic en los tres puntos del archivo «Formato de asistencia», **Descargar**.
- **Subir el Excel actualizado:** primero que nadie lo tenga abierto. En la carpeta del curso, **Cargar**, **Archivos**, elige el archivo que entregaste y acepta **Reemplazar**. Si la carpeta del curso está sincronizada con OneDrive en su computador, basta con guardar el archivo encima del anterior en esa carpeta. Si algo sale mal, SharePoint guarda las versiones anteriores (tres puntos, **Historial de versiones**).
- En unos minutos el sitio de administración muestra la asistencia nueva.
