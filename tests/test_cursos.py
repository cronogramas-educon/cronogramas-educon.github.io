"""Registro de cursos, resolución de carpetas de SharePoint y armado del sitio multicurso."""
import json, sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import cursos as cu

REG = cu.registro()


def test_registro_sin_repetidos():
    cs = REG["cursos"]
    for k in ("id", "codigo", "carpeta"):
        assert len({c[k] for c in cs}) == len(cs), k
    assert all(len(c["codigo"]) >= 8 for c in cs) and len(REG["global"]["adminCodigo"]) >= 10
    assert len(cs) == 8


def test_config_de_cada_curso_esta_sincronizada():
    for c in REG["cursos"]:
        ruta = RAIZ / "cursos" / c["id"] / "config/contenido.json"
        assert json.loads(ruta.read_text(encoding="utf-8")) == cu.config_curso(c, REG["global"]), f"{c['id']}: corre 'python scripts/cursos.py sincronizar'"


@pytest.mark.parametrize("ruta,esperado", [
    ("/ESPECIALIZACIONES 2014 - 2023/EDU CONTINUA 2026/Dip en Derecho Laboral", "derecho-laboral"),
    ("Documentos compartidos/ESPECIALIZACIONES 2014 - 2023/EDU CONTINUA 2026/Dip en Derecho Laboral/", "derecho-laboral"),
    ("/ESPECIALIZACIONES%202014%20-%202023/EDU%20CONTINUA%202026/Dip%20Compliance%20Anti-%20Corrupci%C3%B3n", "compliance-anticorrupcion"),
    ("EDU CONTINUA 2026/Dip Compliance y Gobierno Corp", "compliance-gobierno-corporativo"),
    ("EDU CONTINUA 2026/IA en el seclegal III Cohorte/GRUPO 1- Laura", "ia-sector-legal-grupo-1"),
    ("edu continua 2026/ia en el seclegal iii cohorte/grupo 2- valentina/", "ia-sector-legal-grupo-2"),
    ("EDU CONTINUA 2026/Curso en Derecho Minero", "derecho-minero"),
    ("EDU CONTINUA 2026/IA en el seclegal III Cohorte", None),      # carpeta madre: sin grupo no se sabe de cuál es
    ("EDU CONTINUA 2026/DIP COMPLIANCE 2026-1", None),              # cohorte anterior, no registrada
    ("EDU CONTINUA 2026/Dip en Derecho Laboral Viejo", None),       # el nombre debe coincidir como carpeta completa
])
def test_resolver(ruta, esperado):
    assert cu.resolver(ruta, REG) == esperado


@pytest.fixture(scope="module")
def sitio(tmp_path_factory):
    return cu.armar_sitio(tmp_path_factory.mktemp("sitio") / "s", "abc123")


def test_sitio_estructura_y_privacidad(sitio):
    assert "Abre el enlace" in (sitio / "index.html").read_text(encoding="utf-8")  # raíz neutra: no lista cursos
    assert "noindex" in (sitio / "index.html").read_text(encoding="utf-8")
    hub = sitio / "g" / REG["global"]["adminCodigo"]
    assert (hub / "index.html").exists() and (hub / "cursos.json").exists()
    assert not (sitio / "config").exists() and not (sitio / "cursos").exists()  # el registro con códigos no se publica
    for c in REG["cursos"]:
        pag = (sitio / cu.sitio_ruta(c) / "index.html").read_text(encoding="utf-8")
        assert "__" not in pag.replace("__V__", "") and "abc123" in pag and 'name="robots" content="noindex' in pag
        assert f'data-curso="{c["id"]}"' in pag
        assert (sitio / cu.sitio_ruta(c) / "config/contenido.json").exists()


def test_pagina_de_curso_no_enlaza_a_otros_cursos(sitio):
    cs = REG["cursos"]
    for c in cs:
        pag = (sitio / cu.sitio_ruta(c) / "index.html").read_text(encoding="utf-8")
        for o in cs:
            assert o["codigo"] not in pag
        assert REG["global"]["adminCodigo"] not in pag
        datos = (sitio / cu.sitio_ruta(c) / "config/contenido.json").read_text(encoding="utf-8")
        assert REG["global"]["adminCodigo"] not in datos and "sharepoint" not in datos.lower()


def test_cursos_json_del_sitio_base(sitio):
    meta = json.loads((sitio / "g" / REG["global"]["adminCodigo"] / "cursos.json").read_text(encoding="utf-8"))
    assert len(meta["cursos"]) == 8
    laboral = next(c for c in meta["cursos"] if c["id"] == "derecho-laboral")
    assert laboral["carpetaSharePoint"].endswith("/EDU%20CONTINUA%202026/Dip%20en%20Derecho%20Laboral")
    assert laboral["ruta"].startswith("c/derecho-laboral-")


# ---- Excel "Registro de cursos" ----

def _fila(c, **extra):
    """Fila como la entrega Excel Online: encabezados codificados y la hora como fracción de día."""
    p, cur = c["carpeta"].split("/", 1)
    h = c["horario"]
    hm = lambda t: (int(t[:2]) * 60 + int(t[3:])) / 1440
    f = {"Periodo": c["periodo"], "Carpeta_x0020_del_x0020_periodo": p, "Carpeta_x0020_del_x0020_curso": cur, "Tipo": c["tipo"],
         "Nombre_x0020_del_x0020_curso": c["programaCorto"], "Nombre_x0020_completo": c["programa"], "Modalidad": c["modalidad"],
         "Hora_x0020_de_x0020_inicio": hm(h["inicio"]), "Hora_x0020_de_x0020_fin": hm(h["fin"]) if "fin" in h else "",
         "Inicio_x0020_del_x0020_s_x00e1_bado": hm(h["porDia"]["Sábado"]) if "porDia" in h else "",
         "P_x00e1_gina_x0020_oficial": c.get("urlPaginaOficial", "")}
    return dict(f, **extra)


def _copia():
    import copy
    return copy.deepcopy(REG)


def test_registro_en_excel_reproduce_el_actual_sin_cambios():
    reg = _copia()
    avisos, cambios = cu.fusionar(reg, [_fila(c) for c in REG["cursos"]])
    assert avisos == [] and cambios == [] and reg == REG


def test_registro_crea_curso_nuevo_con_codigo_y_conserva_los_existentes():
    reg = _copia()
    nuevo = dict(REG["cursos"][0], carpeta="EDU CONTINUA 2027-1/Dip Compliance Anti- Corrupción", periodo="2027-1")
    avisos, cambios = cu.fusionar(reg, [_fila(c) for c in REG["cursos"]] + [_fila(nuevo)])
    assert avisos == [] and len(cambios) == 1 and len(reg["cursos"]) == 9
    n = reg["cursos"][-1]
    assert n["id"] == "compliance-anti-corrupcion-y-anti-lavado-2027-1" and len(n["codigo"]) == 8
    assert n["codigo"] not in {c["codigo"] for c in REG["cursos"]} and n["horario"] == REG["cursos"][0]["horario"]
    assert cu.resolver("Documentos/EDU CONTINUA 2027-1/Dip Compliance Anti- Corrupción", reg) == n["id"]  # no se confunde con el de 2026
    assert cu.resolver("Documentos/EDU CONTINUA 2026/Dip Compliance Anti- Corrupción", reg) == "compliance-anticorrupcion"


def test_registro_actualiza_campos_pero_no_cambia_id_ni_codigo():
    reg = _copia()
    c0 = REG["cursos"][0]
    cu.fusionar(reg, [_fila(c0, Hora_x0020_de_x0020_inicio="6:00 PM", Modalidad="Presencial")])
    assert reg["cursos"][0]["horario"] == {"inicio": "18:00", "fin": "20:00"} and reg["cursos"][0]["modalidad"] == "Presencial"
    assert reg["cursos"][0]["id"] == c0["id"] and reg["cursos"][0]["codigo"] == c0["codigo"]


def test_registro_avisa_de_filas_incompletas_sin_inventar():
    reg = _copia()
    malas = [{"Carpeta_x0020_del_x0020_curso": "Solo curso"},
             {"Periodo": "2027-1", "Carpeta_x0020_del_x0020_periodo": "EDU CONTINUA 2027-1", "Carpeta_x0020_del_x0020_curso": "Sin nombre"},
             {"Periodo": "2027-1", "Carpeta_x0020_del_x0020_periodo": "EDU CONTINUA 2027-1", "Carpeta_x0020_del_x0020_curso": "Hora mala",
              "Nombre_x0020_del_x0020_curso": "X", "Hora_x0020_de_x0020_inicio": "tarde"}]
    avisos, cambios = cu.fusionar(reg, malas)
    assert len(avisos) == 3 and cambios == [] and reg == REG


def test_registro_hora_fin_vacia_calcula_por_horas():
    reg = _copia()
    nuevo = {"Periodo": "2027-1", "Carpeta_x0020_del_x0020_periodo": "EDU CONTINUA 2027-1", "Carpeta_x0020_del_x0020_curso": "Laboral",
             "Nombre_x0020_del_x0020_curso": "Laboral", "Hora_x0020_de_x0020_inicio": "18:00", "Inicio_x0020_del_x0020_s_x00e1_bado": "8:00 AM"}
    cu.fusionar(reg, [nuevo])
    assert reg["cursos"][-1]["horario"] == {"modo": "porHoras", "inicio": "18:00", "duracionPorDefecto": 1, "porDia": {"Sábado": "08:00"}}
    assert reg["cursos"][-1]["tipo"] == "Curso" and reg["cursos"][-1]["modalidad"] == "Por confirmar"


def test_recibir_distingue_registro_curso_y_carpeta_sin_registrar(tmp_path):
    def evento(ruta, filas):
        e = tmp_path / "e.json"
        e.write_text(json.dumps({"client_payload": {"ruta": ruta, "modificado": "x", "filas": json.dumps(filas)}}), encoding="utf-8")
        return e
    f = tmp_path / "f.json"
    assert cu.recibir(evento("Docs/EDU CONTINUA - Registro de cursos", [_fila(REG["cursos"][0])]), f)[0] == "registro"
    assert cu.recibir(evento("Docs/ESP/EDU CONTINUA 2026/Dip en Derecho Laboral", [{"Profesor": "A"}]), f)[:2] == ("curso", "derecho-laboral")
    assert cu.recibir(evento("Docs/ESP/EDU CONTINUA 2027-1/Curso Nuevo", [{"Profesor": "A"}]), f)[:2] == ("ninguno", None)
    cu.anotar_sin_registrar("Docs/ESP/EDU CONTINUA 2027-1/Curso%20Nuevo", tmp_path)
    cu.anotar_sin_registrar("Docs/ESP/EDU CONTINUA 2027-1/Curso Nuevo", tmp_path)
    assert json.loads((tmp_path / "estado/sin-registrar.json").read_text(encoding="utf-8"))[0]["carpeta"] == "EDU CONTINUA 2027-1/Curso Nuevo"


def test_aplicar_registro_escribe_estado_y_conserva_ante_error(tmp_path):
    import shutil
    shutil.copytree(RAIZ / "config", tmp_path / "config")
    f = tmp_path / "f.json"
    f.write_text(json.dumps([_fila(c) for c in REG["cursos"]]), encoding="utf-8")
    assert cu.aplicar_registro(f, tmp_path) == ([], [])
    assert json.loads((tmp_path / "estado/registro.json").read_text(encoding="utf-8"))["error"] is None
    f.write_text(json.dumps([{"Otra": 1}]), encoding="utf-8")
    with pytest.raises(ValueError):
        cu.aplicar_registro(f, tmp_path)
    assert "Carpeta del curso" in json.loads((tmp_path / "estado/registro.json").read_text(encoding="utf-8"))["error"]
    assert cu.registro(tmp_path) == REG
