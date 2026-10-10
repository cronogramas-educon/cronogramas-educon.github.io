# Cronogramas de Educación Continua 2026-2

Sitio estático, responsivo y público con el cronograma de cada curso y diplomado de la Facultad de Estudios Jurídicos, Políticos e Internacionales (Universidad de La Sabana). Cada curso tiene **su propia página** y se alimenta de **su propio Excel** en SharePoint. Se actualizan solas.

El Excel manda. Si contradice la página oficial, la página muestra lo del Excel.

## Cómo está organizado

```
https://cronogramas-educon.github.io/
├── c/<curso>-<código>/    página del curso, la única que se comparte con sus estudiantes
├── g/<código>/            sitio base de administración (solo para quienes administran)
└── index.html             página neutra: no lista cursos ni enlaces
```

- **Página de curso.** Etiqueta con la próxima clase y cuenta regresiva en hora de Colombia, calendario mensual y lista por semana, filtros, buscador, aviso de cambios de fecha, botón "Unirme en Teams", archivos `.ics`, impresión en PDF y modo sin red. No enlaza a ningún otro curso ni al sitio base.
- **Sitio base de administración.** Tarjeta por curso (estado, próxima clase, avance, enlace para estudiantes con botón de copiar, carpeta de SharePoint y página oficial), tabla de pendientes por confirmar (docente, asistente PAT y enlace de Teams), estado de la última publicación con aviso si un Excel no se pudo leer, y cambios de fecha recientes de todos los cursos.
- **Datos que faltan.** Un Excel a medio llenar es normal. Docente o asistente PAT en blanco se muestran como "Por confirmar". Sin enlace de Teams el botón aparece apagado con "Enlace por confirmar" y se activa solo cuando se carga el enlace en el Excel. Sin `Unidad` la página oculta el temario por unidades. Sin `Horas` simplemente no se muestran.
- **Privacidad.** Las direcciones llevan un código aleatorio para que no se puedan adivinar. Es discreción, no seguridad: el repositorio es público y `config/cursos.json` lista los códigos. Si se necesita protección real, hace falta otro alojamiento con inicio de sesión.

## Cómo funciona

```
Excel de un curso (SharePoint) → Power Automate (un solo flujo) → GitHub Actions → GitHub Pages
```

El flujo avisa a GitHub con la **ruta de la carpeta** del Excel y sus filas. El workflow reconoce el curso por esa ruta (`config/cursos.json`), reconstruye solo ese curso (`cursos/<id>/data/data.json`, `estado/cambios.json`, `cronograma.ics`) y despliega el sitio completo. Detalle en [docs/MONTAJE.md](docs/MONTAJE.md) y [docs/OPERACION.md](docs/OPERACION.md).

## Estructura

| Ruta | Contenido |
|---|---|
| `config/cursos.json` | Registro: datos comunes y, por curso, id, código de dirección, carpeta de SharePoint, nombre oficial, horario y enlace oficial |
| `cursos/<id>/` | Datos y configuración de cada curso. `config/contenido.json` se genera con `python scripts/cursos.py sincronizar`. `data/`, `estado/` y `cronograma.ics` los escribe el workflow (no editar) |
| `plantilla/` | `curso.html`, `hub.html` y `raiz.html`, de donde sale cada página |
| `css/`, `js/`, `assets/` | Sitio sin framework ni compilación (módulos ES), compartido por todas las páginas. Solo las fuentes van autoalojadas |
| `scripts/construir_datos.py` | Lee, valida, calcula horarios, detecta cambios y genera los datos de un curso |
| `scripts/cursos.py` | Registro, reconocimiento de carpetas y armado del sitio |
| `scripts/generar_ics.py` | Genera `cronograma.ics` (RFC 5545) |
| `tests/` | Pruebas del constructor, del registro, de las páginas con Chromium headless y del sitio base |
| `PRODUCT.md`, `DESIGN.md`, `.impeccable/` | Contexto de producto y dirección visual (no se publican) |

## Horario de cada curso

El Excel no trae hora. Cada curso la define en `config/cursos.json`:

- `{"inicio": "18:00", "fin": "21:00"}`: todas las clases en esa ventana.
- `{"modo": "porHoras", "inicio": "18:00", "porDia": {"Sábado": "08:00"}, "duracionPorDefecto": 1}`: el inicio depende del día, el fin es el inicio más las horas de la clase (o `duracionPorDefecto` si la casilla está vacía) y las clases del mismo día van una tras otra. Es el caso de Derecho Laboral.

## Desarrollo local

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/playwright install chromium
.venv/bin/pytest -q                                     # constructor, registro, .ics, páginas y sitio base
.venv/bin/python scripts/cursos.py sitio _sitio dev      # arma el sitio completo
python3 -m http.server 8000 --directory _sitio           # abrir http://localhost:8000/c/<curso>-<código>/
```

Para simular una hora, agrega `?ahora=2026-10-14T17:30:00-05:00` a la dirección de cualquier página.

## Agregar un curso o abrir un periodo

Lo hace el equipo desde el Excel **Registro de cursos** (carpeta EDU CONTINUA 2026 en SharePoint), sin GitHub. Una fila por curso: periodo, carpetas, tipo, nombre, modalidad, horario y página oficial. El flujo de Power Automate manda ese Excel igual que los de cada curso, y el workflow lo fusiona en `config/cursos.json`: crea los cursos nuevos con id y código aleatorio, actualiza los existentes y **nunca borra ni cambia códigos**. `scripts/generar_registro_xlsx.py` regenera el Excel desde el registro si se pierde. Guía para el equipo en [docs/OPERACION.md](docs/OPERACION.md).

- **Periodos.** Cada fila tiene `periodo` y la carpeta incluye la carpeta del periodo (`EDU CONTINUA 2027-1/Dip ...`), así que dos periodos del mismo curso son cursos distintos con enlace distinto.
- **Cierre y archivo.** No hay estado que mantener: cuando pasa la última clase la página del curso se muestra "finalizado" (sin botones de Teams) y el sitio de administración lo mueve al Archivo, agrupado por periodo.
- **Carpeta sin registrar.** Si llega un Excel de una carpeta que no está en el registro, no se publica y el sitio de administración la lista como pendiente.
- Manualmente sigue valiendo editar `config/cursos.json` y correr `python scripts/cursos.py sincronizar`.

## Detalles que conviene saber

- "Datos publicados hace X" cuenta desde el último cambio real del contenido. Si el Excel no cambia, el `hash` no cambia y no se publica nada nuevo.
- Los nombres de unidad vienen en mayúsculas en el Excel. La página los muestra en minúscula con inicial, conservando las siglas y números romanos de `config/cursos.json`.
- Todo se calcula en hora de Colombia. Si la zona del visitante es distinta, se muestra también su hora local.
- Si dos Excel se guardan casi al mismo tiempo se procesan en orden. Si un mismo curso se guarda varias veces seguidas, gana el último.

## Tiempos medidos

Medidos el 2 de octubre de 2026 con el flujo de un solo curso:

| Tramo | Resultado |
|---|---|
| Guardar el Excel hasta el aviso en GitHub | unos 20 segundos |
| Aviso recibido hasta página publicada (pruebas, construcción, commit y despliegue) | 30 a 60 segundos |

## Diseño

Dirección "El hilo rojo": tablero azul marino, etiquetas de papel para cada clase y un hilo rojo que las une. Sin logos de la Universidad (solo su nombre como texto en el pie). Fuentes autoalojadas: Archivo (títulos y números) y Public Sans (lectura). Íconos Phosphor (MIT) en `js/iconos.js`. Tema único oscuro, con los colores de `css/tokens.css`. El sitio base usa las mismas piezas.
