# Alertas y avisos automáticos

Dos mecanismos que **no envían nada mientras estén apagados**. Los dos funcionan igual: GitHub calcula qué hay que decir y crea una incidencia en el repositorio **privado** `cronogramas-educon/avisos-internos`. Un flujo de Power Automate la recibe y la convierte en un correo o en un mensaje de Teams.

```
GitHub (calcula)  →  incidencia en el repositorio privado avisos-internos  →  flujo de Power Automate  →  correo o grupo de Teams
```

**Por qué un repositorio privado.** El conector de GitHub de Power Automate solo ofrece disparadores del tipo "incidencia asignada a mí", y asignar la incidencia pondría el nombre de la cuenta personal a la vista en un repositorio público. En el repositorio privado no la ve nadie. El flujo de Power Automate cierra la incidencia cuando termina de procesarla, así que las cerradas quedan como historial de lo enviado.

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

Ambos se disparan con **GitHub, Cuando se abre una incidencia nueva asignada a mí** (el conector no ofrece un disparador por repositorio, por eso la incidencia se asigna a la cuenta con la que está conectado el flujo) y se filtran con una condición de desencadenador sobre el título. Terminan con la acción GitHub **Update an Issue** sobre `cronogramas-educon/avisos-internos` con estado `closed`. Ambos están **apagados** hasta la activación.

**`Alertas de cronogramas por correo`** (listo). Condición: `@contains(toLower(string(triggerBody())), 'alerta de cronogramas:')`. Acción: Office 365 Outlook, Enviar un correo (V2) a `educofdcp@unisabana.edu.co`, asunto = título de la incidencia, cuerpo = cuerpo de la incidencia (viene en HTML). Las incidencias de la alerta llevan solo nombres de cursos, clases, fechas y qué falta, nunca docentes ni enlaces.

**`Avisos a estudiantes por Teams`** (listo). Condición: `@contains(toLower(string(triggerBody())), 'aviso a estudiantes:')`. Dos acciones Redactar sacan el equipo y el canal del comentario `<!-- equipo:<id> canal:<id> -->` con el que empieza el cuerpo. Después, Microsoft Teams, Publicar mensaje en un chat o canal: Publicar como Flow bot, en un canal, con Equipo = `@{outputs('Compose')}`, Canal = `@{outputs('Compose_1')}` y Mensaje = el cuerpo sin el comentario (`last(split(triggerBody()?['body'], '-->'))`). La conexión de Teams es "Teams institucional Personal". Al probar por primera vez, comprobar que el mensaje sale bien en el canal (si Flow bot no puede publicar en ese canal, cambiar Publicar como a Usuario).

## Seguridad

Nada se envía hasta que alguien enciende **tres cosas**: el secreto, el flujo y la variable. No se hacen envíos de prueba sin autorización expresa.
