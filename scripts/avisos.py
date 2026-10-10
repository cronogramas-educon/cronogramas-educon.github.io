#!/usr/bin/env python3
"""Avisos a estudiantes por el grupo de Teams de cada curso.

Uso: python scripts/avisos.py CURSO SALIDA.json     calcula los avisos nuevos de un curso y los anota como vistos
     python scripts/avisos.py --linea-base          anota como vistos los cambios que ya existen, sin avisar (se corre una vez al instalar)
No envía nada. Escribe en SALIDA.json la lista [{titulo, cuerpo}] de avisos nuevos de cursos con grupo de Teams; el workflow los publica solo si está activado.
Un cambio ya visto no vuelve a avisarse, esté o no activado el envío. Así, al activarlo solo salen los cambios que ocurran después.
El cuerpo empieza con un comentario HTML con el equipo y el canal, que el flujo de Power Automate usa para publicar en el grupo correcto.
"""
import json, sys
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cursos as cu
from textos import fecha_larga, horario

RAIZ = cu.RAIZ
BOGOTA = timezone(timedelta(hours=-5))


def _llave(x):
    return f"{x['id']}|{x['fechaAnterior']}|{x['fechaNueva']}|{x['detectadoEn']}"


def _cambios(raiz, curso_id):
    ruta = Path(raiz) / "cursos" / curso_id / "estado/cambios.json"
    return json.loads(ruta.read_text(encoding="utf-8")).get("cambios", []) if ruta.exists() else []


def _vistos_ruta(raiz, curso_id):
    return Path(raiz) / "cursos" / curso_id / "estado/avisados.json"


def linea_base(raiz=RAIZ):
    reg = cu.registro(raiz)
    for c in reg["cursos"]:
        ruta = _vistos_ruta(raiz, c["id"])
        if not ruta.exists():
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text(json.dumps(sorted(_llave(x) for x in _cambios(raiz, c["id"])), indent=2) + "\n", encoding="utf-8")


def mensaje(c, g, clase, x):
    e = escape
    url = f"{g['urlSitio'].rstrip('/')}/{cu.sitio_ruta(c)}/"
    prog = cu.con_tipo(c["programaCorto"], c["tipo"])
    return (f"<p><strong>Cambio de fecha</strong> en el {e(prog)}.</p>"
            f"<p>La {e(clase['clase'].lower())} era el {e(fecha_larga(x['fechaAnterior']))} y ahora es el <strong>{e(fecha_larga(x['fechaNueva']))}, {e(horario(clase))}</strong>.</p>"
            f"<p>Consulta el cronograma actualizado: <a href=\"{e(url)}\">{e(url)}</a></p>")


def pendientes(raiz, curso_id, hoy=None):
    """Avisos nuevos de un curso. Anota todos los cambios actuales como vistos. Sin grupo de Teams no hay aviso, pero igual se anotan."""
    raiz = Path(raiz)
    hoy = hoy or datetime.now(BOGOTA).date()
    reg = cu.registro(raiz)
    c = next(c for c in reg["cursos"] if c["id"] == curso_id)
    ruta = _vistos_ruta(raiz, curso_id)
    cambios = _cambios(raiz, curso_id)
    existia = ruta.exists()
    vistos = set(json.loads(ruta.read_text(encoding="utf-8"))) if existia else set()
    nuevos = [x for x in cambios if _llave(x) not in vistos and not x.get("resuelto") and date.fromisoformat(x["fechaNueva"]) >= hoy] if existia else []
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(sorted({_llave(x) for x in cambios} | vistos), indent=2) + "\n", encoding="utf-8")
    if not nuevos or not c.get("teams"):
        return []
    datos = json.loads((raiz / "cursos" / curso_id / "data/data.json").read_text(encoding="utf-8"))
    por_id = {cl["id"]: cl for cl in datos["clases"]}
    t = c["teams"]
    return [{"titulo": f"Aviso a estudiantes: {cu.con_tipo(c['programaCorto'], c['tipo'])}, {x['clase'].lower()}",
             "cuerpo": f"<!-- equipo:{t['equipo']} canal:{t['canal']} -->\n" + mensaje(c, reg["global"], por_id[x["id"]], x)}
            for x in nuevos if x["id"] in por_id]


def main(argv):
    if argv[:1] == ["--linea-base"]:
        linea_base()
        return
    avisos = pendientes(RAIZ, argv[0])
    Path(argv[1]).write_text(json.dumps(avisos, ensure_ascii=False), encoding="utf-8")
    print(f"Avisos nuevos para estudiantes: {len(avisos)}")


if __name__ == "__main__":
    main(sys.argv[1:])
