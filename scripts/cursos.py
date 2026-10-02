#!/usr/bin/env python3
"""Registro de cursos, resolución de carpetas de SharePoint y armado del sitio multicurso.

Uso:
  python scripts/cursos.py resolver "<ruta de la carpeta en SharePoint>"   imprime el id del curso (código 3 si no está registrado)
  python scripts/cursos.py sincronizar                                      escribe cursos/<id>/config/contenido.json desde config/cursos.json
  python scripts/cursos.py sitio SALIDA [VERSION]                           arma el sitio publicable en SALIDA
"""
import json, re, shutil, sys, unicodedata
from pathlib import Path
from urllib.parse import quote, unquote

RAIZ = Path(__file__).resolve().parent.parent
CAMPOS_CURSO = ("programa", "programaCorto", "tipo", "marca", "modalidad", "urlPaginaOficial")


def registro(raiz=RAIZ):
    return json.loads((Path(raiz) / "config/cursos.json").read_text(encoding="utf-8"))


def sitio_ruta(c):
    """Carpeta pública del curso: el código aleatorio evita que alguien adivine la dirección."""
    return f"c/{c['id']}-{c['codigo']}"


def _norm(s):
    return unicodedata.normalize("NFC", unquote(s)).casefold().replace("\\", "/").strip("/")


def resolver(ruta, reg=None):
    """Id del curso cuya carpeta aparece como tramo completo de la ruta, o None. Elige la coincidencia más específica."""
    reg = reg or registro()
    ruta = "/" + _norm(ruta) + "/"
    mejor = None
    for c in reg["cursos"]:
        if "/" + _norm(c["carpeta"]) + "/" in ruta and (mejor is None or len(c["carpeta"]) > len(mejor["carpeta"])):
            mejor = c
    return mejor["id"] if mejor else None


def config_curso(c, g):
    h = dict(c["horario"], zona=g["zona"], desfase=g["desfase"])
    cfg = {k: c[k] for k in CAMPOS_CURSO if k in c}
    cfg.update(universidad=g["universidad"], facultad=g["facultad"], horario=h, uidSufijo=f"cronograma-{c['id']}",
               mostrarLinksTeams=g["mostrarLinksTeams"], diasAvisoCambio=g["diasAvisoCambio"],
               profesoresInstitucionales=g["profesoresInstitucionales"], siglas=g["siglas"], id=c["id"])
    return cfg


def sincronizar(raiz=RAIZ):
    reg = registro(raiz)
    for c in reg["cursos"]:
        ruta = Path(raiz) / "cursos" / c["id"] / "config/contenido.json"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(config_curso(c, reg["global"]), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _html(plantilla, **v):
    s = Path(plantilla).read_text(encoding="utf-8")
    for k, x in v.items():
        s = s.replace(f"__{k}__", str(x))
    return s


def _esc(s):
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


def armar_sitio(salida, version="dev", raiz=RAIZ):
    raiz, salida = Path(raiz), Path(salida)
    reg = registro(raiz)
    g = reg["global"]
    if salida.exists():
        shutil.rmtree(salida)
    salida.mkdir(parents=True)
    for d in ("css", "js", "assets"):
        shutil.copytree(raiz / d, salida / d)
    (salida / ".nojekyll").touch()
    neutro = _html(raiz / "plantilla/raiz.html", V=version)
    (salida / "index.html").write_text(neutro, encoding="utf-8")
    (salida / "404.html").write_text(neutro, encoding="utf-8")
    resumen = []
    for c in reg["cursos"]:
        origen, destino = raiz / "cursos" / c["id"], salida / sitio_ruta(c)
        destino.mkdir(parents=True)
        for d in ("config", "data"):
            if (origen / d).exists():
                shutil.copytree(origen / d, destino / d)
        if (origen / "cronograma.ics").exists():
            shutil.copy(origen / "cronograma.ics", destino / "cronograma.ics")
        if (origen / "estado/error.json").exists():  # solo lo lee el sitio base de administración
            (destino / "estado").mkdir()
            shutil.copy(origen / "estado/error.json", destino / "estado/error.json")
        desc = f"Cuándo es tu próxima clase, quién la dicta y el enlace para entrar. {c['programa']}."
        (destino / "index.html").write_text(_html(
            raiz / "plantilla/curso.html", V=version, BASE="../../", ID=c["id"], NOMBRE=_esc(c["programaCorto"]), DESC=_esc(desc)), encoding="utf-8")
        resumen.append({"id": c["id"], "ruta": sitio_ruta(c), "tieneDatos": (origen / "data/data.json").exists(),
                        "tieneError": (origen / "estado/error.json").exists(), "programa": c["programa"], "programaCorto": c["programaCorto"], "tipo": c["tipo"],
                        "urlPaginaOficial": c.get("urlPaginaOficial", ""), "carpetaSharePoint": quote(f"{g['sharepointBase']}/{c['carpeta']}", safe=":/")})
    hub = salida / "g" / g["adminCodigo"]
    hub.mkdir(parents=True)
    (hub / "cursos.json").write_text(json.dumps({"cursos": resumen, "sharepointBase": quote(g["sharepointBase"], safe=":/")}, ensure_ascii=False), encoding="utf-8")
    (hub / "index.html").write_text(_html(raiz / "plantilla/hub.html", V=version, BASE="../../"), encoding="utf-8")
    return salida


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "resolver":
        r = resolver(sys.argv[2])
        if not r:
            print("Curso no registrado", file=sys.stderr)
            sys.exit(3)
        print(r)
    elif cmd == "sincronizar":
        sincronizar()
    elif cmd == "sitio":
        armar_sitio(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "dev")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
