# Cronograma del diplomado de Compliance (3er 2026-2)

Página estática, responsiva y pública con el cronograma completo del Diplomado Compliance Anti-corrupción y Anti-lavado (Universidad de La Sabana, Facultad de Estudios Jurídicos, Políticos e Internacionales). Se alimenta de un Excel en SharePoint y se actualiza sola.

El Excel manda. Si contradice la página oficial, la página muestra lo del Excel.

## Qué hace

Cuenta regresiva a la próxima clase en hora de Colombia, calendario mensual y lista por semana, filtros por docente, unidad y estado, buscador sin tildes, aviso de cambios de fecha, botón "Unirme en Teams", archivos `.ics` (por clase, visibles o completo, más suscripción), impresión en PDF y modo sin red.

## Cómo funciona

```
Excel (SharePoint) → Power Automate → GitHub Actions → GitHub Pages → navegador
```

El workflow descarga el Excel, valida, genera `data/data.json`, `estado/cambios.json` y `cronograma.ics`, y despliega. El navegador relee `data.json` cada 60 segundos con la pestaña visible. Detalle del montaje en [docs/MONTAJE.md](docs/MONTAJE.md) y de la operación en [docs/OPERACION.md](docs/OPERACION.md).

## Estructura

| Ruta | Contenido |
|---|---|
| `index.html`, `css/`, `js/` | Sitio sin framework ni compilación (módulos ES). Solo las fuentes van autoalojadas en `assets/fuentes/` |
| `scripts/construir_datos.py` | Lee, valida, detecta cambios y genera datos. También acepta JSON crudo (Plan B) |
| `scripts/generar_ics.py` | Genera `cronograma.ics` (RFC 5545) |
| `config/contenido.json` | Textos, interruptores y datos opcionales. Nada de fechas ni nombres va en el código |
| `data/`, `estado/`, `cronograma.ics` | Generados por el workflow (no editar) |
| `tests/` | Pruebas del parser, cambios, `.ics` y del frontend con Chromium headless |
| `referencias/` | Tokens de diseño, logos y parser de referencia |

## Desarrollo local

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/playwright install chromium
.venv/bin/pytest -q                       # datos, .ics y frontend
.venv/bin/python scripts/construir_datos.py tests/fixtures/muestra_sanitizada.xlsx
python3 -m http.server 8000               # abrir http://localhost:8000
```

Para simular una hora, agrega `?ahora=2026-10-14T17:30:00-05:00` a la dirección (sirve para ver los estados "hoy", "en vivo" o "finalizado"). Para generar capturas de revisión: `.venv/bin/python tests/capturas.py`.

El Excel real (`referencias/datos/cronograma_muestra.xlsx`) y el JSON de referencia traen enlaces reales de Teams, por eso están en `.gitignore`. Las pruebas usan `tests/fixtures/muestra_sanitizada.xlsx`, con enlaces de ejemplo.

## Detalles que conviene saber

- "Datos actualizados hace X" cuenta desde el último cambio real del contenido. Si el Excel no cambia, el `hash` no cambia y no se publica nada nuevo, así que esa marca puede decir "hace 3 días" y los datos seguir al día.
- Los nombres de unidad vienen en mayúsculas en el Excel. La página los muestra en minúscula con inicial (conservando las siglas de `config/contenido.json`). El texto original se usa en la búsqueda y en el Excel.
- Los visitantes no ven su zona horaria como base: todo se calcula en hora de Colombia, y si su zona es distinta se muestra también la hora local.

## Tiempos medidos

Pendiente. Se miden en la prueba de extremo a extremo (paso 6 de `docs/MONTAJE.md`) y se anotan aquí:

| Medición | Resultado |
|---|---|
| Guardar el Excel hasta ver el aviso de cambio en la página | por medir |
