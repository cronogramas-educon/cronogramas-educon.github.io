# Alertas por correo

Una alerta diaria y una revisión semanal que **no envían nada mientras estén apagadas**. GitHub calcula qué hay que decir y crea una incidencia en el repositorio **privado** `cronogramas-educon/avisos-internos`. Un flujo de Power Automate la recibe y la convierte en un correo.

```
GitHub (calcula)  →  incidencia en el repositorio privado avisos-internos  →  flujo de Power Automate  →  correo
```

**Por qué un repositorio privado.** El conector de GitHub de Power Automate no ofrece un disparador por repositorio (el que ofrece, "incidencia asignada a mí", no reaccionó con incidencias de una organización), y una incidencia en un repositorio público dejaría a la vista los avisos. En el repositorio privado no la ve nadie. El flujo de Power Automate la cierra cuando termina de procesarla, así que las cerradas quedan como historial de lo enviado.

Los avisos de cambio de fecha a los estudiantes por Teams se eliminaron en octubre de 2026 porque no se necesitaban. La página del curso sigue mostrando por sí sola la franja "Cambio de fecha".

**Qué se necesita para que publique (hecho el 9 de octubre de 2026):**

1. Un token de acceso: GitHub, foto de perfil, Settings, Developer settings, Personal access tokens, **Fine-grained tokens**, Generate new token. Propietario `cronogramas-educon`, solo el repositorio `avisos-internos`, permiso **Issues: Read and write**. Se copia una vez.
2. Guardarlo como secreto del repositorio público: Settings, Secrets and variables, Actions, **New repository secret**, con el nombre `AVISOS_TOKEN`. El token nunca se comparte por chat ni se escribe en un archivo.
3. La variable `RESPONSABLE_AVISOS` (ya existe) indica a qué cuenta se asignan las incidencias: la misma con la que está conectado el flujo de Power Automate.

Mientras falte el secreto, los workflows lo dicen en su resumen y no publican nada.

## 1. Alerta diaria por correo (día anterior)

Todos los días a las 3:00 p. m. de Colombia, `.github/workflows/alertas.yml` revisa las clases de **mañana** y arma un correo solo si hay algo que decir:

- Falta el docente o el enlace de Teams de una clase de mañana (el asistente PAT no cuenta, es opcional).
- Un docente o asistente tiene dos clases a la vez.
- Un Excel de curso o el Excel de registro no se pudo leer.

**Resumen semanal (cambia en octubre de 2026):** los lunes sale **siempre**, aunque no haya problemas. Lleva las clases de la semana por curso (fecha y hora, sin docentes ni enlaces), los cursos que terminan en los próximos 14 días y, debajo, lo pendiente (datos que faltan, choques, asistencia y Excel con error). El diario sigue saliendo solo si hay algo que decir.

**Revisión semanal (alertas):** los lunes a las 8:00 a. m. (Colombia) el mismo workflow revisa los próximos 7 días con las mismas reglas y publica una incidencia aparte, "revisión semanal", con la fecha de cada clase. Usa la misma variable `ALERTAS_ACTIVAS`.

Destino: `educofdcp@unisabana.edu.co`. El destinatario vive en el flujo `Alertas de cronogramas por correo`, no en el repositorio.

**Ver cómo se vería sin enviar nada:** GitHub, pestaña Actions, `Alertas del día anterior`, Run workflow con "Publicar la alerta de verdad" en falso. El texto aparece en el resumen de la ejecución.

**Activar:** (1) tener el secreto `AVISOS_TOKEN`, (2) dejar encendido el flujo `Alertas de cronogramas por correo` en Power Automate (ya lo está) y (3) crear la variable del repositorio `ALERTAS_ACTIVAS` con el valor `true` (Settings, Secrets and variables, Actions, Variables). Para apagar, borrar la variable o ponerla en otro valor.

## Los flujos de Power Automate

El flujo funciona con este esquema, probado de extremo a extremo el 10 de octubre de 2026: un **reloj (Recurrence) cada 5 minutos**, la acción GitHub **Search Github using Query** (en este conector es una consulta GraphQL, no una búsqueda de incidencias), un bucle **Apply to each** sobre `body('Search_Github_using_Query')?['data']?['repository']?['issues']?['nodes']` y, dentro, la acción de envío seguida de GitHub **Update an Issue** sobre `cronogramas-educon/avisos-internos` con estado `closed`. La incidencia se cierra solo si el envío salió bien, así que no se repite. Los flujos quedan **encendidos**: sin incidencias abiertas no hacen nada, y las incidencias solo existen cuando se activan las variables de abajo.

Consulta de **`Alertas de cronogramas por correo`**: `query { repository(owner:"cronogramas-educon", name:"avisos-internos") { issues(states:OPEN, labels:["alerta-cronogramas"], first:10) { nodes { number title body } } } }`. Acción: Office 365 Outlook, Enviar un correo (V2) a `educofdcp@unisabana.edu.co`, asunto = `items('Apply_to_each')?['title']`, cuerpo = `items('Apply_to_each')?['body']` (viene en HTML). Las incidencias de la alerta llevan solo nombres de cursos, clases, fechas y qué falta, nunca docentes ni enlaces.

Si un flujo deja de reaccionar, mirar primero su historial de ejecuciones en Power Automate: la búsqueda devuelve un error de GraphQL si la consulta se edita mal.

## Seguridad

Nada se publica mientras no exista la variable `ALERTAS_ACTIVAS`. No se hacen envíos de prueba sin autorización expresa.
