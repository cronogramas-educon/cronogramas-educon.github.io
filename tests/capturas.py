"""Genera capturas de revisión en docs/capturas. Uso: .venv/bin/python tests/capturas.py"""
import functools, http.server, json, threading
from pathlib import Path
from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "docs/capturas"


class H(http.server.SimpleHTTPRequestHandler):
    def log_message(s, *a): pass


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(H, directory=str(RAIZ)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
U = f"http://127.0.0.1:{srv.server_address[1]}/index.html"
d = json.loads((RAIZ / "data/data.json").read_text(encoding="utf-8"))
c = d["clases"][6]
c["cambio"] = {"tipo": "fecha", "fechaAnterior": "2026-10-13", "fechaOriginal": "2026-10-13", "detectadoEn": "2026-10-10T12:00:00Z"}
c["fecha"], c["inicio"], c["fin"] = "2026-10-14", "2026-10-14T17:00:00-05:00", "2026-10-14T20:00:00-05:00"
d["meta"]["hash"] = "x"

with sync_playwright() as p:
    b = p.chromium.launch()
    for nombre, w, h, q, accion in [
        ("escritorio-1440-calendario", 1440, 900, "ahora=2026-10-14T10:00:00-05:00&mes=2026-10", "sel"),
        ("escritorio-1440-envivo", 1440, 900, "ahora=2026-10-14T18:00:00-05:00", None),
        ("escritorio-1440-lista", 1440, 900, "ahora=2026-10-14T10:00:00-05:00&vista=lista", "abrir"),
        ("tablet-1024-calendario", 1024, 800, "ahora=2026-10-20T10:00:00-05:00&mes=2026-10", "sel"),
        ("celular-390-inicio", 390, 844, "ahora=2026-10-14T10:00:00-05:00", None),
        ("celular-390-calendario", 390, 844, "ahora=2026-10-14T10:00:00-05:00&vista=calendario&mes=2026-10", "sel"),
        ("celular-390-lista", 390, 844, "ahora=2026-10-14T10:00:00-05:00&vista=lista", "abrir"),
    ]:
        ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
        pg = ctx.new_page()
        if "reprog" not in nombre:
            pg.route("**/data/data.json*", lambda r: r.fulfill(json=d))
        print(nombre); pg.goto(f"{U}?{q}")
        pg.on("pageerror", lambda e: print("ERR", e))
        pg.wait_for_selector("#vista .cal-btn, #vista .fila", timeout=5000)
        if accion == "sel":
            pg.click('.cal-btn[data-fecha="2026-10-15"], .cal-btn[data-fecha="2026-10-22"]')
        if accion == "abrir":
            pg.click(".fila[data-id='7'] .fila-cab")
        pg.evaluate("document.getElementById('cronograma').scrollIntoView()" if nombre.endswith(("calendario", "lista")) else "0")
        pg.wait_for_timeout(250)
        pg.screenshot(path=str(OUT / f"{nombre}.png"), full_page=False)
        ctx.close()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    pg.route("**/data/data.json*", lambda r: r.fulfill(json=d))
    pg.goto(f"{U}?ahora=2026-10-14T10:00:00-05:00&vista=lista")
    pg.wait_for_selector(".fila")
    pg.check("#f-temas")
    pg.evaluate("window.dispatchEvent(new Event('beforeprint'))")
    pg.pdf(path=str(OUT / "impresion.pdf"), landscape=True, format="A4", print_background=True)
    b.close()
print("capturas listas")
