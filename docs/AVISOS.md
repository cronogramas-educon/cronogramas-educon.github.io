# Alertas y avisos automáticos

Dos mecanismos que **no envían nada mientras estén apagados**. Los dos funcionan igual: GitHub calcula qué hay que decir y crea una incidencia en el repositorio **privado** `cronogramas-educon/avisos-internos`. Un flujo de Power Automate la recibe y la convierte en un correo o en un mensaje de Teams.

```
GitHub (calcula)  →  incidencia en el repositorio privado avisos-internos  →  flujo de Power Automate  →  correo o grupo de Teams
```

**Por qué un repositorio privado.** El conector de GitHub de Power Automate solo ofrece disparadores del tipo "incidencia asignada a mí", y asignar la incidencia pondría el nombre de la cuenta personal a la vista en un repositorio público. En el repositorio privado no la ve nadie. Las incidencias se cierran solas apenas se crean y quedan como historial de lo enviado.

**Qué se necesita para que publique (lo hace una persona, una sola vez):**

1. Un token de acceso: GitHub, foto de perfil, Settings, Developer settings, Personal access tokens, **Fine-grained tokens**, Generate new token. Propietario `cronogramas-educon`, solo el repositorio `avisos-internos`, permiso **Issues: Read and write**. Se copia una vez.
2. Guardarlo como secreto del repositorio público: Settings, Secrets and variables, Actions, **New repository secret**, con el nombre `AVISOS_TOKEN`. El token nunca se comparte por chat ni se escribe en un archivo.
3. La variable `RESPONSABLE_AVISOS` (ya existe) indica a qué cuenta se asignan las incidencias: la misma con la que está conectado el flujo de Power Automate.

Mientras falte el secreto, los workflows lo dicen en su resumen y no publican nada.

## 1. Alerta diaria por correo (día anterior)

Todos los días a las 3:00 p. m. de Colombia, `.github/workflows/alertas.yml` revisa las clases de **mañana** y arma un correo solo si hay algo que decir:

- Falta el docente o el enlace de Teams de una clase de mañana (el asistente PAT no cuenta, es opcional).
- Un docente o asistente tiene dos clases a la vez.
- Un Excel de curso o el Excel de registro no se pudo leer.

Destino: `educofdcp@unisabana.edu.co`. El destinatario vive en el flujo `Alertas de cronogramas por correo`, no en el repositorio.

**Ver cómo se vería sin enviar nada:** GitHub, pestaña Actions, `Alertas del día anterior`, Run workflow con "Publicar la alerta de verdad" en falso. El texto aparece en el resumen de la ejecución.

**Activar:** (1) tener el secreto `AVISOS_TOKEN`, (2) encender el flujo `Alertas de cronogramas por correo` en Power Automate y (3) crear la variable del repositorio `ALERTAS_ACTIVAS` con el valor `true` (Settings, Secrets and variables, Actions, Variables). Para apagar, borrar la variable o ponerla en otro valor.

## 2. Avisos de cambio de fecha a los estudiantes, por Teams

Cuando se cambia la fecha de una clase en el Excel del curso, la página ya muestra "Reprogramada". Con este mecanismo, además, se publica un mensaje en el canal General del grupo de Teams de ese curso: qué clase era, para cuándo pasa, el horario y el enlace del cronograma.

- Cada curso necesita su grupo: columna **Grupo de Teams** del Excel de registro, con el enlace que da Teams en "Obtener vínculo al equipo". Si un curso no la tiene, no se avisa y el sitio de administración lo marca con "Sin grupo de Teams para avisos a estudiantes".
- Un mismo cambio se avisa una sola vez. Los cambios que ya existían antes de instalar esto quedaron registrados como vistos, así que al activar solo salen los cambios que ocurran después.
- Si la fecha vuelve a la original o la clase ya pasó, no se avisa.

**Activar:** (1) tener el secreto `AVISOS_TOKEN`, (2) encender el flujo `Avisos a estudiantes por Teams` y (3) crear la variable del repositorio `AVISOS_ESTUDIANTES` con el valor `true`. Hasta entonces, cada cambio se anota como visto y se deja constancia en el resumen de la ejecución, sin publicar nada.

Curso con grupo configurado hasta ahora: Diplomado Compliance Anti-corrupción y Anti-lavado.

## Los flujos de Power Automate

Ambos se disparan con **GitHub, Cuando se me asigna una incidencia** (When an issue is assigned to me) sobre `cronogramas-educon/avisos-internos` y se filtran por etiqueta con una condición de desencadenador. Quedan **apagados** hasta la activación.

**Alertas de cronogramas por correo.** Condición: `@contains(string(triggerOutputs()?['body/labels']), 'alerta-cronogramas')`. Las incidencias de la alerta llevan solo nombres de cursos, clases, fechas y qué falta, nunca docentes ni enlaces.. Acción: Office 365 Outlook, Enviar un correo (V2) a `educofdcp@unisabana.edu.co`, asunto = título de la incidencia, cuerpo = cuerpo de la incidencia (viene en HTML).

**Avisos a estudiantes por Teams.** Condición: `@contains(string(triggerOutputs()?['body/labels']), 'aviso-estudiantes')`. El cuerpo empieza con `<!-- equipo:<id> canal:<id> -->`. Dos acciones Redactar sacan el equipo `first(split(last(split(triggerOutputs()?['body/body'], 'equipo:')), ' '))` y el canal `first(split(last(split(triggerOutputs()?['body/body'], 'canal:')), ' '))`. Acción: Microsoft Teams, Publicar mensaje en un chat o canal, en un canal, con el equipo y el canal obtenidos y como mensaje el cuerpo de la incidencia.

## Seguridad

Nada se envía hasta que alguien enciende **tres cosas**: el secreto, el flujo y la variable. No se hacen envíos de prueba sin autorización expresa.
