---
name: Cronograma del diplomado
description: Tablero de franela azul marino del que cuelgan las clases como etiquetas de papel, unidas por un hilo rojo continuo.
colors:
  navy-950: "#06102A"
  navy-900: "#0B1B3D"
  navy-800: "#11285E"
  navy-700: "#1D3A78"
  navy-600: "#2E4F9A"
  paper: "#F5F7FC"
  paper-2: "#E4E9F5"
  ink: "#0B1B3D"
  ink-2: "#44537A"
  felt: "#EEF1FA"
  felt-2: "#AEBBD9"
  red: "#C8102E"
  red-hot: "#E3213F"
  red-tint: "#FF7A8C"
  amber: "#FFC857"
  amber-ink: "#5A3B00"
typography:
  display:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "clamp(2.1rem, 4.2vw, 3.8rem)"
    fontWeight: 800
    lineHeight: 1.02
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "clamp(1.9rem, 3.4vw, 2.9rem)"
    fontWeight: 800
    lineHeight: 1.04
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "1.15rem"
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: "normal"
  body:
    fontFamily: "Public Sans, Helvetica Neue, Arial, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: "normal"
  label:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "0.72rem"
    fontWeight: 800
    lineHeight: 1
    letterSpacing: "0.06em"
rounded:
  piece: "8px"
  tag: "12px"
  stamp: "6px"
  pill: "999px"
  sheet: "20px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "36px"
  thread-offset: "24px"
  content-start: "64px"
  thread-width: "3px"
components:
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.felt}"
    rounded: "{rounded.pill}"
    padding: "13px 20px"
  button-ghost-hover:
    backgroundColor: "{colors.navy-800}"
  button-red:
    backgroundColor: "{colors.red}"
    textColor: "#FFFFFF"
    rounded: "{rounded.pill}"
    padding: "13px 20px"
  button-red-hover:
    backgroundColor: "{colors.red-hot}"
  tag-paper:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.tag}"
    padding: "30px 36px 30px 44px"
  row-tag:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.tag}"
    padding: "16px 20px 16px 16px"
  row-tag-past:
    backgroundColor: "{colors.navy-800}"
    textColor: "{colors.felt-2}"
    rounded: "{rounded.tag}"
  stamp-live:
    backgroundColor: "{colors.red}"
    textColor: "#FFFFFF"
    rounded: "{rounded.stamp}"
    padding: "5px 9px"
  stamp-replay:
    backgroundColor: "{colors.amber}"
    textColor: "{colors.amber-ink}"
    rounded: "{rounded.stamp}"
    padding: "5px 9px"
  field-search:
    backgroundColor: "{colors.navy-950}"
    textColor: "{colors.felt}"
    rounded: "{rounded.pill}"
    height: "46px"
  field-select:
    backgroundColor: "{colors.navy-900}"
    textColor: "{colors.felt}"
    rounded: "{rounded.tag}"
    height: "44px"
  chip-teacher:
    backgroundColor: "{colors.navy-800}"
    textColor: "{colors.felt}"
    rounded: "{rounded.pill}"
    padding: "10px 16px"
  calendar-piece:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.piece}"
    padding: "7px 9px"
---

# Design System: Cronograma del diplomado

## Overview

**Creative North Star: "El hilo rojo"**

Un tablero de franela azul marino sobre el que corre un hilo rojo de arriba abajo, y del hilo cuelgan las clases como etiquetas de papel. El azul marino es el suelo, el papel es lo que se lee de cerca y el rojo es la única tinta de acento: hilo, botón principal, sellos de estado y anillo de lo que viene. El tono es de oficina de archivo, sobrio y táctil, pensado para quien llega con prisa a saber qué sigue.

La densidad es media. La página se ordena en una sola columna a la derecha del hilo, con la etiqueta de la próxima clase como pieza grande y el resto en filas apiladas. No hay hero con cifras, tarjetas iguales en rejilla ni paneles de filtros abiertos por defecto: los filtros se pliegan y las clases realizadas también.

Honestidad de materiales: la franela no es una textura fotográfica sino un grano SVG de feTurbulence con opacidad .7 sobre el color plano #0B1B3D. Los sellos usan un filtro SVG de erosión (feTurbulence más feComposite) que les come el borde, sin imagen. Las etiquetas son rectángulos de papel con una esquina superior derecha cortada y un ojal tallado con gradientes radiales y lineales, no recortes reales. Todo es CSS y SVG en línea.

**Key Characteristics:**
- Un solo tema oscuro (`color-scheme: dark`), sin modo claro.
- El rojo `#C8102E` es la única tinta de acento. El ámbar solo marca avisos y repeticiones.
- Rótulos anchos y pesados (Archivo con ancho variable) para fechas y números, texto de lectura neutro (Public Sans).
- Sombras con desplazamiento y desenfoque teñidas de navy, nunca duras.
- Formas de etiqueta a 12px y de botón en píldora.

## Colors

Franela fría, papel azulado y un rojo vivo de bandera, con ámbar solo para avisos.

### Primary
- **Rojo hilo** (`red`): el hilo vertical de 3px, botón principal, estado en vivo, anillo de 3px que marca hoy y próxima, borde de la cabecera, nudos y ojales, selección de texto.
- **Rojo encendido** (`red-hot`): solo hover del botón rojo.
- **Rojo sobre franela** (`red-tint`): texto y flechas rojas legibles sobre azul marino, enlaces de acción y títulos de clase en el temario.

### Secondary
- **Ámbar de aviso** (`amber`) con **tinta ámbar** (`amber-ink`): banda de avisos, sello de repetición, etiqueta de nota en piezas del calendario y marca de búsqueda. El texto oscuro sobre ámbar es el par obligatorio.

### Neutral
- **Franela profunda, base y medios** (`navy-950`, `navy-900`, `navy-800`, `navy-700`, `navy-600`): 950 para pie, campos y calendario hundido, 900 para el fondo de página, 800 para superficies elevadas y filas pasadas, 700 para bordes finos, 600 para bordes de botón y campo.
- **Papel** (`paper`, `paper-2`): etiquetas, panel de detalle y segmento activo. `paper-2` para hover sobre papel y separadores punteados.
- **Tinta** (`ink`, `ink-2`): texto sobre papel, principal y secundario.
- **Texto sobre franela** (`felt`, `felt-2`): principal y secundario sobre azul marino.

### Named Rules
**The One Ink Rule.** El rojo es el único acento y se reserva para el hilo, la acción principal y el estado. Si algo no es hilo, acción o estado, no lleva rojo.

**The Paper Is For Reading Rule.** Todo lo que se lee de cerca (clase, fecha, detalle) va sobre papel con tinta oscura. Lo que se lee de pasada (notas, contadores, leyendas) va sobre franela con `felt-2`.

## Typography

**Display Font:** Archivo, con eje de ancho (62% a 125%) y peso variable, autoalojada en `assets/fuentes`, con Helvetica Neue y Arial de respaldo.
**Body Font:** Public Sans variable, autoalojada, con Helvetica Neue y Arial de respaldo.

**Character:** Rótulo ancho y pesado de tablero contra una lectura neutra. El ensanchado (`font-stretch` de 100% a 112%) crece con la jerarquía: más ancho cuanto más numérico. Todo usa cifras tabulares.

### Hierarchy
- **Display** (800, `clamp(2.1rem, 4.2vw, 3.8rem)`, 1.02, ancho 100%): el h1 de portada, en blanco.
- **Headline** (800, `clamp(1.9rem, 3.4vw, 2.9rem)`, 1.04, ancho 108%): títulos de sección. La etiqueta grande usa `clamp(1.8rem, 3vw, 2.6rem)` y el mes del calendario 1.7rem.
- **Numeral** (800, `clamp(4.2rem, 8vw, 6rem)`, 1, ancho 112%): el día grande de la próxima clase. La cuenta regresiva baja a `clamp(2.2rem, 3.6vw, 3.1rem)` y la fecha de fila a 2.1rem.
- **Title** (800, 1.15rem, 1.2, ancho 105%): título de fila. La ficha de clase usa 1.3rem.
- **Body** (400, 1rem, 1.55): lectura general, notas a 62ch y temas a 68ch. Texto de apoyo entre .85rem y .95rem.
- **Label** (Archivo 800, .72rem, interletraje .06em, mayúsculas): solo sellos de estado.

### Named Rules
**The Wide Numbers Rule.** Fechas, cuentas y títulos de clase van en Archivo ancho y pesado. El texto corrido nunca lo usa.

**The Self Hosted Rule.** Las dos familias se cargan desde `assets/fuentes` con `font-display: swap`. No se añade una tercera familia ni una fuente de sistema como cara de rótulo.

## Layout

Una columna de contenido de máximo 1240px, con el hilo fijado a la izquierda (`--tl`, 24px del borde, 14px en móvil) y el contenido empezando en 64px (`--pl`, 40px en móvil). El relleno lateral es `clamp(16px, 4vw, 40px)`. Cada etiqueta se une al hilo con un tramo rojo horizontal de 3px (`--grosor`) que cruza el hueco entre hilo y contenido.

El ritmo vertical es amplio entre secciones (`clamp(56px, 8vw, 104px)`) y compacto dentro de ellas: filas separadas 12px, semanas 36px, controles 12 a 14px. La portada se parte en dos columnas (1.4fr y 1fr) y colapsa a una bajo 900px. La etiqueta de la próxima clase usa tres columnas (fecha, información, cuenta regresiva), baja a dos bajo 960px y a una bajo 560px.

Puntos de quiebre usados: 1100px (el detalle del calendario pasa de panel lateral de 340px a hoja inferior), 960px, 900px, 760px, 720px (menú plegable y calendario en celdas de 54px con piezas circulares de 32px) y 560px. El calendario es una rejilla de 7 columnas con celdas de 116px mínimo.

### Named Rules
**The Thread Rule.** Toda etiqueta de clase se conecta al hilo con su tramo rojo de 3px. Una pieza grande de la página sin hilo rompe la composición.

**The Fold Away Rule.** Lo que no es urgente se pliega: filtros, clases realizadas, temario. Lo próximo es siempre lo primero.

## Elevation & Depth

Híbrido: capas tonales para el suelo (950, 900 y 800 apilados) y sombras suaves con desplazamiento para lo que cuelga. La profundidad dice qué está colgado y qué está hundido: campos y calendario son más oscuros que la página (hundidos), las etiquetas de papel proyectan sombra (colgadas). Las filas pasadas pierden sombra y se aplanan.

Lo único que flota con desenfoque es la cabecera fija (`blur(14px)` sobre navy al 84%), porque es lo único que se superpone al contenido al hacer scroll.

### Shadow Vocabulary
- **Etiqueta grande** (`box-shadow: 0 22px 40px -18px rgba(2,8,24,.75), 0 2px 6px rgba(2,8,24,.35)`): etiqueta de la próxima clase, panel de detalle y menú de descargas.
- **Etiqueta chica** (`box-shadow: 0 8px 18px -10px rgba(2,8,24,.7)`): filas de la lista y piezas del calendario.
- **Anillo de estado** (`box-shadow: 0 0 0 3px #C8102E, <sombra chica>`): fila o pieza de hoy, en vivo o próxima. La etiqueta grande en vivo usa 4px.

### Named Rules
**The Hang Not Float Rule.** Solo cuelga lo que es papel. Las superficies de franela son planas y se distinguen por tono, y el desenfoque queda reservado a la cabecera.

## Shapes

Dos familias de forma. Botones, campos de búsqueda, segmentos, chips y contadores son píldoras (`999px`). Etiquetas, filas, campos de selección, calendario y paneles son rectángulos de 12px (`--r-tag`). Piezas del calendario a 8px, sellos a 6px y la hoja inferior móvil a 20px arriba. Las piezas del calendario pasan a círculos de 32px en móvil.

Lo característico es la etiqueta de papel: esquina superior derecha cortada y ojal tallado a la izquierda por donde pasa el hilo, hechos con gradientes (dos radiales para el ojal y uno lineal a 225 grados para la esquina). Los separadores dentro del papel son punteados de 2px en `paper-2`. Los sellos giran 2 grados en sentido antihorario y llevan borde de 2px en color actual con el filtro de erosión.

## Components

### Buttons
- **Shape:** píldora (999px), borde de 1.5px, peso 700, .92rem, relleno 13px por 20px.
- **Primary (`.btn.rojo`):** fondo `red`, texto blanco, hover `red-hot`. Una sola acción roja por vista: entrar a Teams.
- **Default:** transparente con borde `navy-600` y texto `felt`. Hover rellena `navy-800` y aclara el borde a `felt-2`. Sobre papel pasa a borde `ink-2` y texto `ink`.
- **States:** `:active` escala .97, la flecha interna se desplaza 2px arriba a la derecha al hover. Foco con contorno blanco de 3px y separación de 3px (tinta sobre papel).

### Signature: Etiqueta de la próxima clase
Papel con 12px, relleno 30px por 36px, sombra grande, ojal rojo con centro navy donde entra el hilo y tramo rojo de 3px hacia el hilo. Tres zonas: día enorme con divisor punteado, información y cuenta regresiva con el botón rojo. Un sello de esquina cuelga fuera del borde superior. Al cargar columpia 3.5 grados durante 1.6s con `--ease`.

### Signature: Fila de clase
Etiqueta colgada con ojal tallado, tramo rojo y nudo rojo en el hilo. Cabecera de cinco columnas (fecha 84px, título, docente hasta 220px, sellos, caret) que despliega la ficha. Pasada: fondo `navy-800`, texto `felt-2`, sin sombra, hilo en `navy-600`. Hoy, en vivo y próxima: anillo rojo de 3px.

### Sellos de estado
Mayúsculas Archivo 800 .72rem con filtro de erosión. Hoy en rojo, en vivo relleno rojo, próxima y pasada en tinta, repetición en ámbar con borde `amber-ink`. Un estado nunca depende solo del color: lleva siempre texto.

### Inputs / Fields
- **Búsqueda:** píldora de 46px, fondo `navy-950`, borde 1.5px `navy-700`, lupa a la izquierda, hover `navy-600`.
- **Selects:** 44px, fondo `navy-900`, borde `navy-600`, 12px de radio. Dentro de un panel `navy-950` con borde `navy-700`.
- **Casilla:** 18px con `accent-color: red`.
- **Foco:** contorno blanco de 3px con separación de 2px.

### Segmentos y meses
Píldora hundida en `navy-950` con borde `navy-700`. El activo se rellena de papel con texto `ink`. Los botones de mes usan borde `navy-600` y se activan igual.

### Calendario
Rejilla de 7 columnas sobre `rgba(6,16,42,.55)` con bordes `navy-700`. Las piezas son etiquetas de papel pequeñas. Al elegir un día el resto baja a opacidad .38 y saturación .4, aislando lo seleccionado, y la pieza elegida lleva contorno blanco de 3px. Pasada en `navy-800`, en vivo en rojo, próxima y hoy con anillo rojo, repetición con nota ámbar. Leyenda con cuadros de 14px.

### Detalle de clase
Papel con sombra grande, panel pegajoso de 340px en escritorio y hoja inferior de 82vh bajo 1100px, con velo `rgba(2,8,24,.6)`.

### Chips de docente y desplegables
Chips en píldora `navy-800` con borde `navy-700` que se vuelven papel al hover. Unidades, realizadas y temario son `details` con caret que gira 180 grados en .3s, separados por filetes de 1px `navy-700`.

### Avisos y cabecera
Banda ámbar a todo el ancho para avisos. Cabecera fija de 60px con filete inferior rojo de 3px y navegación en píldoras que se rellenan `navy-800` al hover. Bajo 720px la navegación se pliega en un menú.

### Motion
Curva única `cubic-bezier(0.16, 1, 0.3, 1)` en transiciones de .2 a .35s. El hilo se tiende con `scaleY` en 1.5s al cargar y la etiqueta columpia 1.6s. Con `prefers-reduced-motion: reduce` las transiciones bajan a .01ms y las animaciones de entrada no corren.

## Do's and Don'ts

### Do:
- **Do** usar el rojo `#C8102E` solo para hilo, acción principal y estado, y `red-tint` para texto rojo sobre franela.
- **Do** poner todo lo que se lee de cerca sobre papel con `ink`, y cuidar el par `amber` con `amber-ink` en avisos.
- **Do** unir cada etiqueta nueva al hilo con su tramo de 3px y su ojal o nudo.
- **Do** dar a cada estado un sello con texto, no solo un color.
- **Do** usar la curva `cubic-bezier(0.16, 1, 0.3, 1)` y respetar `prefers-reduced-motion`.
- **Do** mantener un foco visible: contorno blanco de 3px sobre franela y `ink` sobre papel.
- **Do** plegar lo secundario (filtros, realizadas, temario) para que lo próximo quede primero.

### Don't:
- **Don't** añadir un segundo color de acento ni usar el ámbar como decoración.
- **Don't** usar sombras duras sin desenfoque ni desplazamientos rígidos: las sombras son suaves y teñidas de navy.
- **Don't** usar Archivo ancho en texto corrido ni introducir una tercera familia tipográfica.
- **Don't** usar logos de la institución: el nombre va solo como texto en el pie.
- **Don't** repetir tarjetas iguales en rejilla ni abrir los filtros por defecto.
- **Don't** presentar el grano, el sello erosionado o el ojal como materiales fotográficos: son SVG y gradientes, y así deben seguir.

## Deriva y defectos conocidos (no canonizados)

- El detector marca un `radial-gradient` en `.fila` como halo. Es el ojal tallado de la etiqueta, no un halo decorativo, y se mantiene.
- El detector marca un contraste insuficiente que es falso positivo, ya que los pares de tinta sobre papel y ámbar sobre ámbar oscuro cumplen.
- La etiqueta es de papel azulado (`#F5F7FC`), no blanco puro como describía la intención original, y el radio es de 12px, mayor que el "radio pequeño" planeado.
- Los fondos translúcidos del calendario (`rgba(6,16,42,.55)` a `.85`) y algunas sombras usan valores sueltos que no están en `tokens.css`.
- Algunos detalles menores señalados en la revisión final quedaron sin aplicar y no se registran como regla.
