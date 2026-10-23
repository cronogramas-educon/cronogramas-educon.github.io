"""Alertas del día anterior: se calculan, nunca se envían desde aquí."""
import json, shutil, sys
from datetime import date
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import alertas as al
import cursos as cu

A, B = "compliance-anticorrupcion", "derecho-laboral"
MANANA = "2026-10-13"
HOY = date(2026, 10, 12)


def _clase(i, fecha, ini, fin, pat):
    return {"id": i, "clase": f"CLASE {i}", "fecha": fecha, "inicio": f"{fecha}T{ini}:00-05:00", "fin": f"{fecha}T{fin}:00-05:00",
            "profesores": ["Docente Uno"], "profesor": "Docente Uno", "asistentePat": pat, "linkTeams": "https://teams.microsoft.com/l/meetup-join/x"}


@pytest.fixture()
def repo(tmp_path):
    """Dos cursos sintéticos con una clase mañana (2026-10-13) y otra hoy, todo completo."""
    shutil.copytree(RAIZ / "config", tmp_path / "config")
    reg = json.loads((tmp_path / "config/cursos.json").read_text(encoding="utf-8"))
    reg["cursos"] = [c for c in reg["cursos"] if c["id"] in (A, B)]
    (tmp_path / "config/cursos.json").write_text(json.dumps(reg, ensure_ascii=False), encoding="utf-8")
    for c in (A, B):
        (tmp_path / "cursos" / c / "data").mkdir(parents=True)
        (tmp_path / "cursos" / c / "estado").mkdir()
        datos(tmp_path, c).write_text(json.dumps({"clases": [_clase(1, "2026-10-12", "18:00", "20:00", f"Apoyo {c[:3]}"), _clase(2, MANANA, "18:00", "20:00", f"Apoyo {c[:3]}")]}), encoding="utf-8")
        (tmp_path / "cursos" / c / "estado/cambios.json").write_text(json.dumps({"cambios": []}), encoding="utf-8")
    return tmp_path


def datos(repo, curso):
    return repo / "cursos" / curso / "data/data.json"


def clase_de_manana(repo, curso, **cambios):
    d = json.loads(datos(repo, curso).read_text(encoding="utf-8"))
    c = next(c for c in d["clases"] if c["fecha"] == MANANA)
    c.update(cambios)
    datos(repo, curso).write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return c


def test_alerta_de_faltantes_sin_pat_por_defecto(repo):
    clase_de_manana(repo, A, linkTeams="", profesores=[], profesor="", asistentePat="")
    a = al.calcular(repo, HOY)
    x = next(x for x in a["faltantes"] if x["curso"].startswith("Diplomado Compliance Anti"))
    assert x["falta"] == ["el docente", "el enlace de Teams"] and al.hay(a)
    assert "el asistente PAT" in next(x for x in al.calcular(repo, HOY, incluir_pat=True)["faltantes"] if x["curso"].startswith("Diplomado Compliance Anti"))["falta"]
    h = al.html(a)
    assert "falta el docente y el enlace de Teams" in h and "mañana, martes 13 de octubre" in h and "sharepoint.com" not in h.lower() and "https://" not in h and "Docente Uno" not in h


def test_sin_alertas_cuando_manana_no_hay_clase(repo):
    a = al.calcular(repo, date(2030, 1, 1))
    assert a == {"fecha": "2030-01-02", "hasta": "2030-01-02", "faltantes": [], "choques": [], "errores": [], "asistencia": []} and not al.hay(a)


def test_alerta_de_choque_error_y_registro(repo):
    ca = clase_de_manana(repo, A, linkTeams="x", profesores=["Ana Gómez"], inicio=f"{MANANA}T18:00:00-05:00", fin=f"{MANANA}T20:00:00-05:00")
    clase_de_manana(repo, B, linkTeams="x", profesores=["ana  gómez"], inicio=f"{MANANA}T19:00:00-05:00", fin=f"{MANANA}T21:00:00-05:00")
    (repo / "cursos" / A / "estado/error.json").write_text(json.dumps({"mensaje": "Falta la columna <Profesor>"}), encoding="utf-8")
    (repo / "estado").mkdir()
    (repo / "estado/registro.json").write_text(json.dumps({"error": "mal registro"}), encoding="utf-8")
    a = al.calcular(repo, HOY)
    assert len(a["choques"]) == 1 and a["choques"][0]["rol"] == "docente"
    assert [e["curso"] for e in a["errores"]] == ["Diplomado Compliance Anti-corrupción y Anti-lavado", "Excel Registro de cursos"]
    h = al.html(a)
    assert "&lt;Profesor&gt;" in h and "<Profesor>" not in h  # el contenido se escapa
    assert ca["clase"]


def test_docente_institucional_no_choca_consigo_mismo(repo):
    clase_de_manana(repo, A, linkTeams="x", profesores=["SABANA"])
    clase_de_manana(repo, B, linkTeams="x", profesores=["SABANA"], inicio=f"{MANANA}T18:00:00-05:00", fin=f"{MANANA}T19:00:00-05:00")
    assert al.calcular(repo, HOY)["choques"] == []
