"""Pruebas de humo del frontend con Chromium headless. Se omiten si Playwright no está instalado.
La hora se simula con ?ahora=..., sin tocar el reloj del sistema."""
import functools, http.server, json, threading
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
RAIZ = Path(__file__).resolve().parent.parent


class Silencioso(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def servidor(sitio):
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Silencioso, directory=str(sitio["dir"])))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


@pytest.fixture(scope="module")
def base(servidor, sitio):
    return f"{servidor}/{sitio['a']}/index.html"  # curso completo


@pytest.fixture(scope="module")
def navegador():
    with pw.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as e:  # navegador no descargado
            pytest.skip(f"Chromium no disponible: {e}")
        yield b
        b.close()


@pytest.fixture
def pagina(navegador):
    ctx = navegador.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
    p = ctx.new_page()
    p.errores = []
    p.on("pageerror", lambda e: p.errores.append(str(e)))
    p.on("console", lambda m: m.type == "error" and p.errores.append(m.text))
    yield p
    ctx.close()


def abrir(p, base, q=""):
    p.goto(f"{base}?{q}")
    p.wait_for_selector("#vista .cal-btn, #vista .fila, #vista .vacio", state="attached")
    return p


def test_carga_sin_errores_y_cifras(pagina, base, sitio):
    abrir(pagina, base, "ahora=2026-10-14T10:00:00-05:00")
    assert "35 clases del 1 de octubre de 2026 al 4 de diciembre de 2026" in pagina.inner_text("#lead")
    assert pagina.inner_text("#contador") == "35 clases"
    datos = json.loads(sitio["datos_a"].read_text(encoding="utf-8"))
    assert pagina.locator("#plan-lista .unidad").count() == len(datos["unidades"])
    assert pagina.locator(".chip-docente").count() == len(datos["profesores"])
    assert pagina.errores == []


@pytest.mark.parametrize("ahora,esperado", [
    ("2026-09-20T10:00:00-05:00", "Falta"),
    ("2026-10-01T10:00:00-05:00", "Hoy a las 5:00"),
    ("2026-10-01T18:00:00-05:00", "En vivo ahora"),
    ("2026-12-05T10:00:00-05:00", "El diplomado ha finalizado"),
])
def test_estados_del_panel(pagina, base, ahora, esperado):
    abrir(pagina, base, f"ahora={ahora}")
    assert esperado in pagina.inner_text("#panel")


def test_en_vivo_destaca_teams_y_pasada_se_marca(pagina, base):
    abrir(pagina, base, "ahora=2026-10-01T18:00:00-05:00&vista=lista")
    assert pagina.locator("#panel .btn.rojo").count() == 1
    abrir(pagina, base, "ahora=2026-10-02T09:00:00-05:00&vista=lista")
    pagina.click(".realizadas > summary")
    assert "realizada" in pagina.locator(".fila").first.inner_text().lower()


def test_cuenta_regresiva_avanza(pagina, base):
    abrir(pagina, base, "ahora=2026-10-14T16:59:50-05:00")
    a = pagina.inner_text("#panel [data-cuenta]")
    pagina.wait_for_timeout(2200)
    assert pagina.inner_text("#panel [data-cuenta]") != a


def test_filtro_docente_incluye_clases_con_dos_docentes(pagina, base):
    abrir(pagina, base, "docente=Beatriz%20Londo%C3%B1o%20P&vista=lista")
    filas = pagina.locator(".fila")
    textos = " ".join(filas.all_inner_texts())
    assert "Clase 23" in textos and "Clase 30" in textos  # compartidas con Marta Lucia Ramírez
    assert pagina.is_visible("#filtros")  # con filtros en la URL el panel llega abierto
    pagina.select_option("#f-docente", "Marta Lucia Ramírez")
    assert "Clase 23" in " ".join(pagina.locator(".fila").all_inner_texts())
    assert "docente=" in pagina.url


def test_busqueda_sin_tildes_resalta_y_url(pagina, base):
    abrir(pagina, base, "vista=lista")
    pagina.fill("#f-q", "ramirez")
    pagina.wait_for_selector("mark")
    assert pagina.locator(".fila").count() >= 5 and "q=ramirez" in pagina.url
    pagina.fill("#f-q", "zzzzzz")
    pagina.wait_for_selector(".vacio")
    pagina.click("[data-limpiar]")
    assert pagina.inner_text("#contador") == "35 clases"


def test_ocultar_realizadas_y_estado(pagina, base):
    abrir(pagina, base, "ahora=2026-10-14T10:00:00-05:00&vista=lista")
    pagina.click("#abrir-filtros")
    pagina.check("#f-ocultar")
    assert "Mostrando 28 de 35" in pagina.inner_text("#contador")
    pagina.uncheck("#f-ocultar")
    pagina.select_option("#f-estado", "realizadas")
    assert "Mostrando 7 de 35" in pagina.inner_text("#contador")


def test_celular_abre_en_lista_y_sin_scroll_horizontal(navegador, base):
    ctx = navegador.new_context(viewport={"width": 390, "height": 844})
    p = ctx.new_page()
    abrir(p, base, "ahora=2026-10-14T10:00:00-05:00")
    assert p.locator("[data-vista=lista]").get_attribute("aria-pressed") == "true"
    assert p.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    p.click("[data-vista=calendario]")
    p.wait_for_selector(".cal-btn")
    assert p.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    ctx.close()


def test_calendario_teclado_y_detalle(pagina, base):
    abrir(pagina, base, "ahora=2026-10-14T10:00:00-05:00&mes=2026-10")
    pagina.focus('.cal-btn[tabindex="0"]')
    f0 = pagina.evaluate("document.activeElement.dataset.fecha")
    pagina.keyboard.press("ArrowRight")
    assert pagina.evaluate("document.activeElement.dataset.fecha") != f0
    pagina.click('.cal-btn[data-fecha="2026-10-15"]')
    pagina.wait_for_selector("#detalle")
    assert "Unirme en Teams" in pagina.inner_text("#detalle") and "Agregar a mi calendario" in pagina.inner_text("#detalle")
    label = pagina.get_attribute('.cal-btn[data-fecha="2026-10-15"]', "aria-label")
    assert "Clase 9" in label and "jueves 15 de octubre de 2026" in label
    pagina.keyboard.press("Escape")
    assert pagina.locator("#detalle").count() == 0


def test_mostrar_links_teams_apagado(pagina, base, sitio):
    cfg = json.loads(sitio["cfg_a"].read_text(encoding="utf-8"))
    cfg["mostrarLinksTeams"] = False
    pagina.route("**/config/contenido.json*", lambda r: r.fulfill(json=cfg))
    abrir(pagina, base, "ahora=2026-10-01T18:00:00-05:00&vista=lista")
    assert pagina.locator("a[href*='teams.microsoft.com']").count() == 0


def datos_con_cambio(sitio):
    d = json.loads(sitio["datos_a"].read_text(encoding="utf-8"))
    c = d["clases"][6]  # clase 7
    ant = c["fecha"]
    c["cambio"] = {"tipo": "fecha", "fechaAnterior": "2026-10-13", "fechaOriginal": "2026-10-13", "detectadoEn": "2026-10-10T12:00:00Z"}
    c["fecha"] = "2026-10-14"
    c["inicio"], c["fin"] = "2026-10-14T17:00:00-05:00", "2026-10-14T20:00:00-05:00"
    d["meta"]["hash"] = "otro"
    return d


def test_aviso_de_cambio_y_entendido(pagina, base, sitio):
    d = datos_con_cambio(sitio)
    pagina.route("**/data/data.json*", lambda r: r.fulfill(json=d))
    abrir(pagina, base, "ahora=2026-10-11T10:00:00-05:00&vista=lista")
    assert "la Clase 7 pasó del martes 13 de octubre al miércoles 14 de octubre" in pagina.inner_text("#avisos")
    fila = pagina.locator(".fila[data-id='7']")
    assert "reprogramada" in fila.inner_text().lower()
    pagina.click("[data-entendido]")
    assert pagina.locator("#avisos").is_hidden()
    pagina.reload()
    pagina.wait_for_selector(".fila", state="attached")
    assert pagina.locator("#avisos").is_hidden() and "reprogramada" in pagina.locator(".fila[data-id='7']").inner_text().lower()


def test_aviso_de_clase_cancelada(pagina, base, sitio):
    d = json.loads(sitio["datos_a"].read_text(encoding="utf-8"))
    d["canceladas"] = [{"id": 99, "clase": "CLASE 99", "unidad": "", "fecha": "2026-10-20"}]
    pagina.route("**/data/data.json*", lambda r: r.fulfill(json=d))
    abrir(pagina, base, "ahora=2026-10-11T10:00:00-05:00&vista=lista")
    assert "Clase cancelada: la Clase 99 del martes 20 de octubre no se dicta" in pagina.inner_text("#avisos")
    pagina.click("[data-entendido]")
    pagina.reload()
    pagina.wait_for_selector(".fila", state="attached")
    assert pagina.locator("#avisos").is_hidden()


def test_sin_red_usa_ultima_copia(navegador, base):
    ctx = navegador.new_context()
    p = ctx.new_page()
    abrir(p, base, "vista=lista")
    p.route("**/data/data.json*", lambda r: r.abort())
    p.goto(f"{base}?vista=lista")
    p.wait_for_selector(".fila", state="attached")
    assert "última versión guardada" in p.inner_text("#aviso-red")
    ctx.close()


def test_sin_red_ni_copia_no_deja_pagina_en_blanco(navegador, base):
    ctx = navegador.new_context()
    p = ctx.new_page()
    p.route("**/data/data.json*", lambda r: r.abort())
    p.goto(base)
    p.wait_for_selector(".vacio")
    assert "No pudimos cargar" in p.inner_text("#vista")
    ctx.close()


def test_descarga_ics(pagina, base):
    abrir(pagina, base, "docente=Camilo%20Jaimes%20P&vista=lista")
    pagina.click("#menu-ics summary")
    with pagina.expect_download() as d:
        pagina.click("[data-ics-visibles]")
    txt = Path(d.value.path()).read_text(encoding="utf-8")
    n = pagina.locator(".fila").count()
    assert txt.count("BEGIN:VEVENT") == n > 3 and "\r\nTZID" not in txt and "BEGIN:VTIMEZONE" in txt


def test_hoja_de_impresion_respeta_filtros_y_temas(pagina, base, tmp_path):
    abrir(pagina, base, "docente=Camilo%20Jaimes%20P&vista=lista")
    pagina.check("#f-temas")
    pagina.evaluate("window.dispatchEvent(new Event('beforeprint'))")
    filas = pagina.locator("#hoja-impresion tbody").count()
    assert filas == pagina.locator(".fila").count()
    assert pagina.locator("#hoja-impresion td.temas").count() == filas
    assert "Filtros activos" in pagina.inner_text("#hoja-impresion")
    pdf = tmp_path / "cronograma.pdf"
    pagina.pdf(path=str(pdf), landscape=True, format="A4", print_background=True)
    assert pdf.stat().st_size > 5000


def test_curso_sin_datos_dice_que_se_publicara_pronto(pagina, base):
    pagina.route("**/data/data.json*", lambda r: r.fulfill(status=404, body="no existe"))
    pagina.goto(base)
    pagina.wait_for_selector(".vacio")
    assert "se publicará pronto" in pagina.inner_text("#vista")


# --- curso a medio llenar (sin unidad, docente, asistente, enlaces ni horas en algunas clases)
@pytest.fixture
def urlb(servidor, sitio):
    return f"{servidor}/{sitio['b']}/index.html"


def test_curso_incompleto_muestra_por_confirmar(pagina, urlb):
    abrir(pagina, urlb, "ahora=2026-09-20T10:00:00-05:00&vista=lista")
    assert pagina.errores == []
    assert pagina.inner_text("#lead").startswith("Diplomado.") and "Cohorte 1 (primera vez en el semestre)" in pagina.inner_text("#lead")
    assert pagina.locator("#temario").is_hidden() and pagina.locator("#nav [href='#temario']").is_hidden()
    assert pagina.locator("#f-unidad").is_hidden() is True or pagina.locator("#f-unidad").locator("xpath=..").is_hidden()
    assert pagina.locator(".fila").first.locator(".fila-prof").inner_text() == "Por confirmar"
    assert "Docente por confirmar" in pagina.inner_text("#panel")
    assert pagina.locator("#panel .btn-pendiente").inner_text().strip() == "Enlace por confirmar"
    pagina.locator(".fila-cab").first.click()
    ficha = pagina.locator(".fila").first.inner_text()
    assert ficha.count("Por confirmar") >= 3 and "Enlace por confirmar" in ficha  # docente, te acompaña, enlace
    assert pagina.locator("a[href*='teams.microsoft.com']").count() == 0
    assert "Quién te acompaña en las sesiones de Teams está por confirmar" in pagina.inner_text("#apoyo")


def test_curso_incompleto_horario_por_horas(pagina, urlb):
    abrir(pagina, urlb, "ahora=2026-09-20T10:00:00-05:00&vista=lista")
    for n, esperado in ((1, "6:00 p. m. a 7:00 p. m."), (2, "7:00 p. m. a 10:00 p. m."), (3, "8:00 a. m. a 12:00 p. m.")):
        pagina.locator(f".fila[data-id='{n}'] .fila-cab").click()
        assert esperado in pagina.locator(f".fila[data-id='{n}']").inner_text().replace("\u202f", " ").replace("\u00a0", " "), n


def test_curso_incompleto_hoja_de_impresion_y_ics_sin_enlace(pagina, urlb):
    abrir(pagina, urlb, "vista=lista")
    pagina.evaluate("window.dispatchEvent(new Event('beforeprint'))")
    hoja = pagina.inner_text("#hoja-impresion")
    assert "Por confirmar" in hoja and "Cohorte" not in hoja and "Unidad" not in hoja
    pagina.click("#menu-ics summary")
    with pagina.expect_download() as d:
        pagina.click("[data-ics-todas]")
    txt = Path(d.value.path()).read_text(encoding="utf-8").replace("\n ", "")  # las líneas largas del .ics vienen plegadas
    assert "\nURL:" not in txt and "Docente: por confirmar" in txt and "X-WR-CALNAME:Diplomado Derecho Laboral\n" in txt


def test_una_pagina_no_lee_la_copia_de_otra(navegador, servidor, sitio):
    ctx = navegador.new_context()
    p = ctx.new_page()
    abrir(p, f"{servidor}/{sitio['a']}/index.html", "vista=lista")
    claves = p.evaluate("Object.keys(localStorage)")
    assert f"cronograma:copia:{A_ID}" in claves and not any(k.endswith(B_ID) for k in claves)
    ctx.close()


A_ID, B_ID = "compliance-anticorrupcion", "derecho-laboral"


# --- sitio base de administración
def test_sitio_base_muestra_cursos_pendientes_y_errores(pagina, servidor, sitio):
    pagina.goto(f"{servidor}/{sitio['hub']}/index.html?ahora=2026-09-20T10:00:00-05:00")
    pagina.wait_for_selector(".curso")
    assert pagina.errores == []
    assert pagina.locator(".curso").count() == 2
    assert 'content="noindex' in pagina.content()
    tarjeta = pagina.locator(".curso", has_text="Derecho Laboral")
    assert "El último guardado del Excel no se pudo leer" in tarjeta.inner_text() and "Falta la columna Profesor" in tarjeta.inner_text()
    assert tarjeta.locator("a:has-text('Abrir sitio')").get_attribute("href").endswith(f"/{sitio['b']}/")
    assert "sharepoint.com" in tarjeta.locator("a:has-text('Carpeta en SharePoint')").get_attribute("href")
    tabla = pagina.inner_text("#tabla-pendientes")
    assert "clases 1 a 3" in tabla and "Completo" in tabla  # docente falta en 1 a 3; el otro curso está completo
    assert "1 con error" in pagina.inner_text("#resumen")
    tarjeta.locator("[data-copiar]").click()
    tarjeta.locator("[data-copiar] span:text('Enlace copiado')").wait_for(timeout=4000)
    assert "No hay cambios de fecha" in pagina.inner_text("#lista-cambios")


def test_raiz_no_lista_cursos(pagina, servidor):
    pagina.goto(f"{servidor}/index.html")
    assert "Abre el enlace" in pagina.inner_text("body") and pagina.locator("a").count() == 0


def test_curso_no_enlaza_a_nada_interno(pagina, base):
    abrir(pagina, base, "vista=lista")
    hrefs = pagina.eval_on_selector_all("a[href]", "es => es.map(e => e.getAttribute('href'))")
    assert all(h.startswith(("#", "https://", "webcal:")) for h in hrefs), hrefs


# --- cierre automático y archivo
def test_curso_terminado_queda_en_modo_lectura(pagina, base):
    abrir(pagina, base, "ahora=2027-06-01T10:00:00-05:00&vista=lista")
    assert "finalizado" in pagina.inner_text("#lead") and "Periodo 2026-2" in pagina.inner_text("#lead")
    assert "ha finalizado" in pagina.inner_text("#panel")
    assert pagina.locator("a[href*='teams.microsoft.com']").count() == 0 and pagina.locator(".btn-pendiente").count() == 0
    assert pagina.errores == []


def test_sitio_base_archiva_los_cursos_terminados(pagina, servidor, sitio):
    pagina.goto(f"{servidor}/{sitio['hub']}/index.html?ahora=2027-06-01T10:00:00-05:00")
    pagina.wait_for_selector("#archivo-lista li")
    assert pagina.locator(".curso").count() == 0 and pagina.locator("#archivo-lista li").count() == 2
    assert "periodo 2026-2" in pagina.inner_text("#archivo-lista").lower() and "2 en el archivo" in pagina.inner_text("#resumen")
    assert pagina.errores == []


def test_sitio_base_enlaza_el_registro_de_cursos(pagina, servidor, sitio):
    pagina.goto(f"{servidor}/{sitio['hub']}/index.html?ahora=2026-09-20T10:00:00-05:00")
    pagina.wait_for_selector(".curso")
    assert pagina.locator("#archivo").is_hidden()
    assert "sharepoint.com" in pagina.locator("#registro-abrir").get_attribute("href")
    assert "EduContinua%202026-2" in pagina.locator("#pie-carpeta a").get_attribute("href")


# --- sitio base: urgentes, semáforo, agenda con choques y reportes
def abrir_hub(pagina, servidor, sitio, ahora):
    pagina.goto(f"{servidor}/{sitio['hub']}/index.html?ahora={ahora}")
    pagina.wait_for_selector(".curso")


def test_hub_urgentes_y_semaforo(pagina, servidor, sitio):
    abrir_hub(pagina, servidor, sitio, "2026-10-02T10:00:00-05:00")
    u = pagina.inner_text("#urgente-lista")
    assert "Derecho Laboral" in u and "sin docente" in u.lower() and "sin enlace de teams" in u.lower()
    assert "dos clases a la vez" in u and pagina.locator("#ins-urgente").is_visible()  # el sitio de prueba repite el mismo Excel en dos cursos, así que hay choques reales
    laboral = pagina.locator(".curso", has_text="Derecho Laboral")
    assert "rojo" in laboral.locator(".semaforo").get_attribute("class") and "requiere atención" in laboral.inner_text().lower()
    assert pagina.locator(".curso .semaforo").count() == 2 and pagina.errores == []


def test_hub_agenda_reportes_y_csv(pagina, servidor, sitio):
    abrir_hub(pagina, servidor, sitio, "2026-10-02T10:00:00-05:00")
    assert pagina.locator("#agenda-lista .dia-agenda").count() >= 1
    assert "Diplomado Derecho Laboral" in pagina.inner_text("#rep-cursos") and "estimada" in pagina.inner_text("#rep-cursos")
    assert pagina.locator("#rep-docentes tbody tr").count() >= 3 and pagina.locator("#rep-meses tbody tr").count() >= 2
    pagina.select_option("#rep-periodo", "2026-2")
    with pagina.expect_download() as d:
        pagina.click("#rep-csv")
    txt = Path(d.value.path()).read_text(encoding="utf-8")
    assert txt.startswith("﻿Tipo;Nombre;Periodo;Clases;Horas") and "\nDocente;" in txt and "\nCurso;Diplomado Derecho Laboral" in txt and ";2026-2;" in txt and "\nMes;2026-10;" in txt


def test_analisis_detecta_choques_y_horas(pagina, servidor, sitio):
    abrir_hub(pagina, servidor, sitio, "2026-10-02T10:00:00-05:00")
    r = pagina.evaluate("""async () => {
      const m = await import('../../js/hub-analisis.js');
      const cl = (id, ini, fin, prof, pat = '') => ({ id, clase: 'CLASE ' + id, fecha: ini.slice(0, 10), inicio: ini, fin, profesores: prof, asistentePat: pat, linkTeams: 'x', horas: null });
      const curso = (n, clases) => ({ c: { id: n, programaCorto: n, periodo: '2026-2' }, d: { clases } });
      const rs = [curso('A', [cl(1, '2026-10-05T18:00:00-05:00', '2026-10-05T20:00:00-05:00', ['Ana Gómez'], 'Luis'), cl(2, '2026-10-06T18:00:00-05:00', '2026-10-06T20:00:00-05:00', ['SABANA'])]),
                  curso('B', [cl(1, '2026-10-05T19:00:00-05:00', '2026-10-05T21:00:00-05:00', ['ana gomez'], 'Luis'), cl(2, '2026-10-06T19:00:00-05:00', '2026-10-06T21:00:00-05:00', ['SABANA'])])];
      const t = new Date('2026-10-02T10:00:00-05:00');
      // sesión paralela: dos clases del mismo curso a la misma hora con la misma asistente no son un choque; un asistente de varios nombres sí choca por cada nombre
      const par = [curso('P', [cl(1, '2026-10-07T18:00:00-05:00', '2026-10-07T21:00:00-05:00', ['Ana Gómez'], 'Sofía'), cl(2, '2026-10-07T18:00:00-05:00', '2026-10-07T21:00:00-05:00', ['Luis Pérez'], 'Sofía')])];
      const multi = [curso('M', [cl(1, '2026-10-08T18:00:00-05:00', '2026-10-08T20:00:00-05:00', ['X'], 'Sofía y Teo')]), curso('N', [cl(1, '2026-10-08T19:00:00-05:00', '2026-10-08T21:00:00-05:00', ['Y'], 'Teo')])];
      return { paralela: m.choques(par, t).length, multi: m.choques(multi, t).map((k) => [k.rol, k.nombre]), ch: m.choques(rs, t).map((k) => [k.rol, k.a.curso.id, k.b.curso.id]), h: m.horasDe(rs[0].d.clases[0]), hx: m.horasDe({ horas: 3, inicio: 'a', fin: 'b' }), csv: m.csv(['a', 'b'], [['x;y', 'z"w']]) };
    }""")
    assert r["ch"] == [["Docente", "A", "B"], ["Asistente PAT", "A", "B"]]  # el docente institucional SABANA no choca consigo mismo
    assert r["paralela"] == 0 and r["multi"] == [["Asistente PAT", "Teo"]]
    assert r["h"] == {"h": 2, "estimada": True} and r["hx"] == {"h": 3, "estimada": False}
    assert r["csv"] == '﻿a;b\r\n"x;y";"z""w"'


def test_hub_asistencia_bandeja_tablero_y_contactado(pagina, servidor, sitio):
    abrir_hub(pagina, servidor, sitio, "2026-10-02T10:00:00-05:00")
    pagina.click("#asis-seguimiento summary")
    pagina.wait_for_selector("#asis-bandeja tbody tr")
    assert pagina.locator("#asistencia").count() == 0  # ya no hay una sección de asistencia aparte
    filas = pagina.locator("#asis-bandeja tbody tr")
    assert filas.count() == 3 and "Perdió el mínimo" in filas.nth(0).inner_text() and "En riesgo" in filas.nth(1).inner_text() and "N.º 3" in filas.nth(1).inner_text() and "Atención" in filas.nth(2).inner_text()
    assert "Estudiante de prueba" not in pagina.inner_text("body") and pagina.locator("#asis-lista").count() == 0  # el detalle por curso ya no es una lista aparte
    assert pagina.locator("#cursos-lista [data-asis-curso].rojo").count() == 2
    compliance = pagina.locator("#cursos-lista .curso", has_text="Compliance")
    compliance.locator("[data-asis-curso] summary").click()
    assert "28 de 35" in compliance.inner_text() and compliance.locator(".asis-barras li").count() == 35
    pagina.locator("[data-contactado]").first.check()  # la primera es la de Derecho Laboral, que perdió el mínimo
    assert "1 ya contactado" in pagina.inner_text("#asis-bandeja caption").lower() and pagina.locator("#cursos-lista [data-asis-curso][open]").count() == 1
    pagina.reload()
    pagina.click("#asis-seguimiento summary")
    pagina.wait_for_selector("#asis-bandeja tbody tr")
    assert pagina.locator("[data-contactado]").first.is_checked() and pagina.errores == []


def test_hub_buscador_global_encuentra_curso_docente_y_clase(pagina, servidor, sitio):
    abrir_hub(pagina, servidor, sitio, "2026-10-02T10:00:00-05:00")
    docente = json.loads(sitio["datos_a"].read_text(encoding="utf-8"))["clases"][0]["profesores"][0]
    apellido = docente.split()[-1]
    pagina.fill("#bg-q", "laboral")
    assert "Derecho Laboral" in pagina.inner_text("#bg-resultados")
    pagina.fill("#bg-q", apellido)
    r = pagina.inner_text("#bg-resultados")
    assert docente in r and "Docente" in r and "Ver clase" in r
    assert "docente=" in pagina.locator(".bg-links a").first.get_attribute("href")
    pagina.fill("#bg-q", "zzzxyz")
    assert "No encontré nada" in pagina.inner_text("#bg-resultados")
    pagina.fill("#bg-q", "")
    assert pagina.inner_text("#bg-resultados") == ""
    pagina.keyboard.press("Escape")
    pagina.locator("body").click(position={"x": 5, "y": 400})
    pagina.keyboard.press("/")
    assert pagina.evaluate("document.activeElement.id") == "bg-q" and pagina.errores == []


def test_hub_cierre_de_curso_lista_y_descarga(pagina, servidor, sitio):
    abrir_hub(pagina, servidor, sitio, "2026-10-02T10:00:00-05:00")
    tarjeta = pagina.locator("#cursos-lista .curso", has_text="Derecho Laboral")
    tarjeta.locator("[data-asis-curso] > summary").click()
    fila = tarjeta.locator("details.cierre")
    fila.locator("summary").click()
    assert "Resultado final" in fila.inner_text() and "Estudiante de prueba" not in fila.inner_text()
    assert pagina.locator(".cierre-col.aprueba p").inner_text() == "1, 2" and pagina.locator(".cierre-col.no-aprueba p").inner_text() == "3"
    with pagina.expect_download() as d:
        fila.locator("[data-cierre]").click()
    texto = Path(d.value.path()).read_text(encoding="utf-8-sig")
    assert d.value.suggested_filename.startswith("cierre-") and "Número de lista;Resultado" in texto
    assert ";1;Aprueba;" in texto and ";3;No aprueba;" in texto and "Estudiante de prueba" not in texto and pagina.errores == []


def test_hub_navegacion_pestanas_y_estados(pagina, servidor, sitio):
    abrir_hub(pagina, servidor, sitio, "2026-10-02T10:00:00-05:00")
    enlaces = pagina.locator("#nav-hub a:visible").all_inner_texts()
    for s_ in ("Buscar", "Urgente", "Cursos", "Pendientes", "Agenda", "Cambios", "Reportes"):
        assert any(e.startswith(s_) for e in enlaces), s_
    assert pagina.locator(".btn-registrar").is_visible() and pagina.locator("#inicio[aria-busy]").count() == 0
    assert "Último cambio publicado" in pagina.inner_text("#act-texto") or "Página revisada" in pagina.inner_text("#act-texto")
    # pestañas de reportes: una tabla a la vez y navegación con flechas
    assert pagina.locator("#panel-docentes").is_visible() and not pagina.locator("#panel-cursos").is_visible()
    pagina.locator("#tab-docentes").focus()
    pagina.keyboard.press("ArrowRight")
    assert pagina.locator("#panel-cursos").is_visible() and pagina.locator("#tab-cursos").get_attribute("aria-selected") == "true"
    # volver arriba aparece al bajar y el menú marca la sección
    pagina.evaluate("window.scrollTo(0, document.getElementById('reportes').offsetTop)")
    pagina.wait_for_selector("#subir:not([hidden])")
    pagina.wait_for_selector("#nav-hub a[aria-current]")
    pagina.click("#subir")
    pagina.wait_for_function("window.scrollY < 50")
    assert pagina.errores == []


def test_hub_mensaje_de_bienvenida_vista_previa_y_boton_de_envio(pagina, servidor, sitio):
    def con_formulario(ruta):
        meta = ruta.fetch().json()
        meta["formularioBienvenida"] = "https://forms.example/r?id=1&r5="
        meta["preguntasBienvenida"] = {"gestora": "rG", "pat": "rP"}
        ruta.fulfill(json=meta)
    pagina.route("**/g/*/cursos.json*", con_formulario)
    abrir_hub(pagina, servidor, sitio, "2026-10-02T10:00:00-05:00")
    tarjeta = pagina.locator("#cursos-lista .curso", has_text="Compliance")
    tarjeta.locator("[data-bienv-curso] > summary").click()
    pagina.wait_for_function("document.querySelector('[data-bienv-curso] .bienv-cuerpo').innerText.includes('Bienvenid')")
    cuerpo = tarjeta.locator(".bienv-cuerpo").inner_text()
    assert "Universidad de La Sabana" in cuerpo and "Datos Generales del Curso" in cuerpo and "WhatsApp" not in cuerpo
    assert "no lo envíes dos veces" in tarjeta.inner_text()
    # el curso va ya elegido en el enlace del formulario
    assert "nombre que escribes al enviar" in cuerpo and "{{" not in cuerpo  # los marcadores no se ven crudos en la vista previa
    href = tarjeta.locator(".curso-bienv a.btn").get_attribute("href")
    assert href.startswith("https://forms.example/r?id=1&r5=%22compliance-anticorrupcion%22")
    assert "&rP=%22" in href and "&rG=" not in href  # el PAT del Excel va prellenado; la gestora la escribe quien envía
    # los identificadores del equipo de Teams nunca llegan al navegador
    assert "d675843f" not in pagina.content() and pagina.errores == []


def test_hub_bienvenida_sin_formulario_lo_avisa(pagina, servidor, sitio):
    def sin_formulario(ruta):
        meta = ruta.fetch().json()
        meta["formularioBienvenida"] = ""
        ruta.fulfill(json=meta)
    pagina.route("**/g/*/cursos.json*", sin_formulario)
    abrir_hub(pagina, servidor, sitio, "2026-10-02T10:00:00-05:00")
    tarjeta = pagina.locator("#cursos-lista .curso", has_text="Compliance")
    tarjeta.locator("[data-bienv-curso] > summary").click()
    assert "Falta configurar el formulario de envío" in tarjeta.inner_text()
    assert "aún no se puede enviar la bienvenida" in pagina.locator("#cursos-lista .curso", has_text="Derecho Laboral").inner_text()  # sin equipo de Teams


def test_hub_bienvenida_ya_enviada_no_ofrece_el_boton(pagina, servidor, sitio):
    def enviada(ruta):
        meta = ruta.fetch().json()
        meta["formularioBienvenida"] = "https://forms.example/r?id=1&r5="
        for c in meta["cursos"]:
            if c["id"] == "compliance-anticorrupcion":
                c["bienvenidaEnviada"] = "2026-10-23T17:49:00Z"
        ruta.fulfill(json=meta)
    pagina.route("**/g/*/cursos.json*", enviada)
    abrir_hub(pagina, servidor, sitio, "2026-10-02T10:00:00-05:00")
    tarjeta = pagina.locator("#cursos-lista .curso", has_text="Compliance")
    assert "Ya enviado al equipo de Teams" in tarjeta.locator("[data-bienv-curso] > summary").inner_text()
    tarjeta.locator("[data-bienv-curso] > summary").click()
    assert "Ya se envió el viernes 23 de octubre de 2026" in tarjeta.locator(".bienv-enviada").inner_text()
    assert tarjeta.locator(".curso-bienv a.btn").count() == 0 and pagina.errores == []


def test_hub_urgentes_agrupados_por_curso(pagina, servidor, sitio):
    abrir_hub(pagina, servidor, sitio, "2026-10-02T10:00:00-05:00")
    grupos = pagina.locator("#urgente-lista .urg-curso")
    assert grupos.count() >= 1
    resumen = grupos.first.locator("summary").inner_text().lower()
    assert "clases sin confirmar" in resumen and " en " in resumen and "clase" in resumen  # conteo de cada falta, no una fila por clase repetida
    assert grupos.first.locator("li").count() >= 1 and pagina.errores == []


def test_hub_avisa_si_el_excel_lleva_dias_sin_guardarse(pagina, servidor, sitio):
    # el sitio de prueba se generó hace tiempo respecto a esta fecha: ya hubo clases desde el último guardado
    abrir_hub(pagina, servidor, sitio, "2026-12-01T10:00:00-05:00")
    assert pagina.locator("#cursos-lista .meta-viejo").count() >= 1
    assert "último guardado del Excel" in pagina.locator("#cursos-lista .meta-viejo").first.inner_text() and pagina.errores == []


def test_hub_mensaje_de_whatsapp_del_dia(pagina, servidor, sitio):
    abrir_hub(pagina, servidor, sitio, "2026-10-06T08:00:00-05:00")
    assert pagina.locator("#msj-lista .msj-clase").count() >= 1
    texto = pagina.locator("#msj-lista .msj-texto").first.inner_text()
    assert texto.startswith("Muy buenos días") and "Les recuerdo que el día de hoy, 6 de octubre de 2026" in texto
    assert "⏰ Horario:" in texto and "(hora de Colombia)" in texto and "Profesor" in texto and "🔗 Enlace de la clase:" in texto and texto.endswith("Los esperamos 🤓")
    pagina.select_option("#msj-cuando", "mañana")
    assert "mañana, 7 de octubre de 2026" in pagina.locator("#msj-lista").inner_text() or "No hay clases" in pagina.locator("#msj-lista").inner_text()
    assert pagina.errores == []


def test_pagina_de_estudiantes_trae_la_informacion_del_curso(pagina, base):
    abrir(pagina, base, "ahora=2026-10-14T10:00:00-05:00")
    info = pagina.inner_text("#info-contenido")
    assert "80 %" in info and "40 días hábiles" in info and "grupo del curso" in info
    assert pagina.locator("#info-contenido .tarjeta").count() == 7 and pagina.locator('#nav a[href="#info"]').count() == 1
    assert pagina.errores == []
