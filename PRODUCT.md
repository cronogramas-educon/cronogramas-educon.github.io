# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: estudiantes inscritos en cada curso o diplomado de Educación Continua 2026-2 (Compliance Anti-corrupción, Compliance y Gobierno Corporativo, Conflictos Societarios, Contratación Estatal, Derecho Laboral, Derecho Minero Ambiental e IA en el Sector Legal, grupos 1 y 2). Cada grupo recibe solo el enlace de su curso. Entran desde el computador o el celular, casi siempre con una prisa concreta: saber cuándo es la próxima clase (de 5:00 p. m. a 8:00 p. m., hora de Colombia), quién la dicta y entrar a Teams.

Administración: quienes manejan todos los cursos usan un sitio base (con dirección no enlazada) para ver estados, pendientes por confirmar, errores de lectura de los Excel y copiar los enlaces para estudiantes. Secundarios, no confirmados como foco: aspirantes y docentes.

## Product Purpose

Una página pública por curso que muestra su cronograma completo y se actualiza sola cuando se edita su Excel de SharePoint, más un sitio base de administración. Un curso no enlaza a otro. Éxito: un estudiante sabe qué sigue y entra a la clase en pocos segundos, sin leer datos que no necesita.

## Positioning

Es la única fuente que siempre refleja el Excel vigente: avisa cuando cambia la fecha de una clase y calcula todo en hora de Colombia. Una página de la universidad o un PDF no se actualizan solos.

## Operating Context

Los datos viven en un Excel en SharePoint. Power Automate avisa a GitHub, que publica en GitHub Pages en unos segundos. El sitio es estático, sin framework ni compilación (HTML, CSS y módulos ES), y no tiene backend. Las clases son por Microsoft Teams.

## Capabilities and Constraints

Funciones existentes que deben conservarse: cuenta regresiva a la próxima clase con estados (hoy, en vivo, finalizado), calendario mensual y lista por semana, filtros y buscador, aviso de cambio de fecha, botón "Unirme en Teams", archivos .ics (por clase, visibles, completo y suscripción), PDF por impresión, modo sin red con última copia guardada. Todo texto visible en español de Colombia. Sin datos inventados: no hay biografías, fotos ni contactos de docentes.

Limitaciones: sin dependencias en tiempo de ejecución salvo fuentes autoalojadas. Los datos llegan con la forma de `data.json` y no se cambian. Los datos que faltan en el Excel se muestran como "Por confirmar"; nunca se inventan.

## Brand Commitments

Conservar la gama de color azul marino (#0B1B3D) y rojo (#C8102E) con blanco como identidad. El usuario pidió quitar TODOS los logos de la Universidad de La Sabana (encabezado, pie, favicon y hoja de impresión). Se permite el nombre de la Universidad y de la Facultad solo como texto discreto en el pie, sin escudo ni logotipo.

Prosa en español sin guiones largos ni medios como signo de puntuación y con poco punto y coma.

## Evidence on Hand

Datos reales en `cursos/<id>/data/data.json` (por ejemplo, 35 clases en Compliance Anti-corrupción, temas por clase, docentes, asistentes PAT, enlaces de Teams). Capturas de la versión anterior en `docs/capturas/`. No hay fotografías, ilustraciones, testimonios ni cifras de inscripción, y no deben fabricarse.

## Product Principles

1. Lo primero que se ve responde "¿qué sigue y cómo entro?".
2. Menos datos por pantalla: cada dato extra debe ganar su lugar o plegarse.
3. La próxima clase y el calendario son los protagonistas, junto con las herramientas de filtrar, imprimir y suscribirse.
4. Los datos se leen igual de bien en celular que en computador.
5. Nada decorativo que no ayude a entender una fecha, una clase o una persona.

## Accessibility & Inclusion

Contraste AA, navegación por teclado completa, foco visible, `prefers-reduced-motion` respetado, funcional desde 360 px de ancho, `lang="es"`.
