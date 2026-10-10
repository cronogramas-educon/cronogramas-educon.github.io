"""Alertas del día anterior y avisos a estudiantes: se calculan, nunca se envían desde aquí."""
import json, shutil, sys
from datetime import date
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import alertas as al
import avisos as av
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
    assert a == {"fecha": "2030-01-02", "hasta": "2030-01-02", "faltantes": [], "choques": [], "errores": []} and not al.hay(a)


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


# ---- avisos a estudiantes
def agregar_cambio(repo, curso, **extra):
    ruta = repo / "cursos" / curso / "estado/cambios.json"
    e = json.loads(ruta.read_text(encoding="utf-8"))
    d = json.loads(datos(repo, curso).read_text(encoding="utf-8"))
    c = next(c for c in d["clases"] if c["fecha"] == MANANA)
    e["cambios"].append(dict({"id": c["id"], "clase": c["clase"], "fechaOriginal": "2026-10-10", "fechaAnterior": "2026-10-10", "fechaNueva": MANANA,
                              "detectadoEn": "2026-10-12T15:00:00Z", "resuelto": False}, **extra))
    ruta.write_text(json.dumps(e), encoding="utf-8")


def test_avisos_linea_base_y_un_aviso_por_cambio(repo):
    assert av.pendientes(repo, A, HOY) == []                      # primera vez: línea base, nada que avisar
    assert (repo / "cursos" / A / "estado/avisados.json").exists()
    agregar_cambio(repo, A)
    r = av.pendientes(repo, A, HOY)
    assert len(r) == 1
    t = r[0]
    assert t["cuerpo"].startswith("<!-- equipo:d675843f-951b-4337-8de5-1d25e510b144 canal:19:oE9nYUX5BgFCdcDqvAcLqtcgyqA5D1DPwl66NyZaTdU1@thread.tacv2 -->")
    assert "era el sábado 10 de octubre y ahora es el <strong>martes 13 de octubre, " in t["cuerpo"] and "p. m." in t["cuerpo"]
    assert "Diplomado Compliance Anti-corrupción y Anti-lavado" in t["titulo"] and "/c/compliance-anticorrupcion-s9hv2xzn/" in t["cuerpo"]
    assert av.pendientes(repo, A, HOY) == []                      # ya visto: no se repite


def test_avisos_curso_sin_grupo_de_teams_se_anota_pero_no_se_avisa(repo):
    av.pendientes(repo, B, HOY)
    agregar_cambio(repo, B)
    assert av.pendientes(repo, B, HOY) == []
    visto = json.loads((repo / "cursos" / B / "estado/avisados.json").read_text(encoding="utf-8"))
    assert any(k.startswith(f"{json.loads(datos(repo, B).read_text(encoding='utf-8'))['clases'][0]['id']}|") or "|2026-10-13|" in k for k in visto)


def test_avisos_no_avisa_cambios_resueltos_ni_de_clases_pasadas(repo):
    av.pendientes(repo, A, HOY)
    agregar_cambio(repo, A, resuelto=True)
    assert av.pendientes(repo, A, HOY) == []
    agregar_cambio(repo, A, detectadoEn="2026-10-12T16:00:00Z", fechaNueva="2026-10-13")
    assert av.pendientes(repo, A, date(2026, 10, 20)) == []        # la clase ya pasó


def test_revision_semanal_incluye_los_proximos_7_dias(repo):
    clase_de_manana(repo, A, linkTeams="", profesores=[], profesor="", asistentePat="")
    a = al.calcular(repo, HOY, dias=7)
    assert al.semanal(a) and not al.semanal(al.calcular(repo, HOY))
    assert len(a["faltantes"]) >= len(al.calcular(repo, HOY)["faltantes"])
    assert "revisión semanal" in al.titulo(a) and "https://" not in al.html(a)
