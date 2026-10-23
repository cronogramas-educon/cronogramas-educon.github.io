"""Mensaje de bienvenida de un curso: sale de la plantilla del equipo con datos reales y nunca inventa."""
import json, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import bienvenida as bv
import cursos as cu

G = {"urlSitio": "https://ejemplo.github.io", "siglas": ["ESG", "ALA/CFT"]}
C = {"id": "demo", "codigo": "abc12345", "tipo": "Diplomado", "programa": "Compliance & Riesgo", "programaCorto": "Compliance",
     "teams": {"equipo": "d675843f-951b-4337-8de5-1d25e510b144", "canal": "19:abc@thread.tacv2"}}


def clase(n, fecha, ini, fin):
    return {"id": n, "fecha": fecha, "inicio": f"{fecha}T{ini}:00-05:00", "fin": f"{fecha}T{fin}:00-05:00"}


def datos(**extra):
    d = {"meta": {"inicio": "2026-10-05", "fin": "2026-11-17", "horasTotales": 12, "horasCompletas": True},
         "clases": [clase(1, "2026-10-05", "18:00", "21:00"), clase(2, "2026-10-06", "18:00", "21:00"), clase(3, "2026-10-10", "08:00", "11:00"), clase(4, "2026-11-17", "18:00", "21:00")],
         "unidades": [{"nombre": "GESTIÓN ESG Y ALA/CFT"}, {"nombre": "Ética"}], "asistentesPat": ["Ana Pat", "Luis Pat"]}
    d.update(extra)
    return d


def test_mensaje_lleva_los_datos_reales_del_curso():
    m = bv.mensaje(C, datos(), G, "https://ejemplo.github.io/c/demo-abc12345/")
    assert "Bienvenid@s al Diplomado Compliance &amp; Riesgo de la Universidad de La Sabana" in m  # el nombre se escapa para HTML
    assert "del 5 de octubre al 17 de noviembre de 2026" in m and "12 horas" in m and "2 módulos principales" in m
    assert "<li>Gestión ESG y ALA/CFT</li>" in m and "<li>Ética</li>" in m  # el módulo en mayúsculas pasa a oración y conserva las siglas
    assert "lunes y martes de 6:00 p. m. a 9:00 p. m.; sábado de 8:00 a. m. a 11:00 a. m." in m
    assert "https://ejemplo.github.io/c/demo-abc12345/" in m and "WhatsApp" not in m
    assert "PAT (Programa Aprendamos a Trabajar):</b> {{PAT}}" in m and "Gestora Logística:</b> {{GESTORA}}" in m
    assert m.count("{{NOTA}}") == 1 and m.index("{{NOTA}}") < m.index("exitoso ciclo")  # la nota opcional va justo antes del cierre  # los nombres los escribe quien envía, en el formulario


def test_mensaje_no_inventa_lo_que_falta():
    m = bv.mensaje(C, datos(unidades=[], asistentesPat=[]), G, "u")
    assert "los temas del cronograma" in m and "módulos principales" not in m
    parcial = datos()
    parcial["meta"]["horasCompletas"] = False
    assert "aproximadamente 12 horas" in bv.mensaje(C, parcial, G, "u")


def test_horarios_agrupa_dias_por_franja():
    assert bv.horarios(datos()["clases"]) == "lunes y martes de 6:00 p. m. a 9:00 p. m.; sábado de 8:00 a. m. a 11:00 a. m. (hora de Colombia)"


def test_generar_escribe_solo_cursos_con_grupo_y_cronograma(tmp_path):
    import shutil
    shutil.copytree(RAIZ / "config", tmp_path / "config")
    reg = json.loads((tmp_path / "config/cursos.json").read_text(encoding="utf-8"))
    for c in reg["cursos"]:
        c.pop("teams", None)
    reg["cursos"][0]["teams"] = C["teams"]
    (tmp_path / "config/cursos.json").write_text(json.dumps(reg), encoding="utf-8")
    for c in reg["cursos"][:2]:
        (tmp_path / "cursos" / c["id"] / "data").mkdir(parents=True)
        (tmp_path / "cursos" / c["id"] / "data/data.json").write_text(json.dumps(datos()), encoding="utf-8")
    (tmp_path / "bienvenidas").mkdir()
    (tmp_path / "bienvenidas/viejo.json").write_text("{}", encoding="utf-8")
    assert bv.generar(tmp_path) == [reg["cursos"][0]["id"]]  # el 2.º tiene datos pero no grupo de Teams
    f = json.loads((tmp_path / "bienvenidas" / f"{reg['cursos'][0]['id']}.json").read_text(encoding="utf-8"))
    assert f["equipo"] == C["teams"]["equipo"] and f["canal"] == C["teams"]["canal"] and "Bienvenid@s" in f["mensaje"]
    assert [p.name for p in (tmp_path / "bienvenidas").glob("*.json")] == [f"{reg['cursos'][0]['id']}.json"]  # el resto, incluido el viejo, se limpia
