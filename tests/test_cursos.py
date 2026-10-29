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
    assert len(cs) >= 8


def test_config_de_cada_curso_esta_sincronizada():
    for c in REG["cursos"]:
        ruta = RAIZ / "cursos" / c["id"] / "config/contenido.json"
        assert json.loads(ruta.read_text(encoding="utf-8")) == cu.config_curso(c, REG["global"]), f"{c['id']}: corre 'python scripts/cursos.py sincronizar'"


C1 = "EduContinua 2026-2/Cohorte 1 (primera vez en el semestre)"


@pytest.mark.parametrize("ruta,esperado", [
    (f"{C1}/Diplomado Derecho Laboral", "derecho-laboral"),
    (f"/sites/EduContinuaDerecho/Documentos compartidos/{C1}/Diplomado Derecho Laboral/Material de clases/x.pdf", "derecho-laboral"),
    ("/EduContinua%202026-2/Cohorte%201%20(primera%20vez%20en%20el%20semestre)/Diplomado%20Derecho%20Laboral/a.xlsx", "derecho-laboral"),
    (f"{C1}/Diplomado Compliance y Gobierno Corporativo en la práctica", "compliance-gobierno-corporativo"),
    (f"{C1}/Curso IA en el Sector Legal, Grupo 1", "ia-sector-legal-grupo-1"),
    (f"{C1.lower()}/curso ia en el sector legal, grupo 2/", "ia-sector-legal-grupo-2"),
    (f"{C1}/Curso Derecho Minero Ambiental", "derecho-minero"),
    (f"{C1}/Curso IA en el Sector Legal", None),        # sin el grupo no se sabe de cuál es
    ("EDU CONTINUA 2026/Dip en Derecho Laboral", None),  # las rutas del sitio viejo ya no se reconocen
    (f"{C1}/Diplomado Derecho Laboral Viejo", None),     # el nombre debe coincidir como carpeta completa
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
    assert len(meta["cursos"]) == len(REG["cursos"])
    laboral = next(c for c in meta["cursos"] if c["id"] == "derecho-laboral")
    assert laboral["carpetaSharePoint"].endswith("/EduContinua%202026-2/Cohorte%201%20%28primera%20vez%20en%20el%20semestre%29/Diplomado%20Derecho%20Laboral")
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
    assert avisos == [] and len(cambios) == 1 and len(reg["cursos"]) == len(REG["cursos"]) + 1
    n = reg["cursos"][-1]
    assert n["id"] == "compliance-anti-corrupcion-y-anti-lavado-2027-1" and len(n["codigo"]) == 8
    assert n["codigo"] not in {c["codigo"] for c in REG["cursos"]} and n["horario"] == REG["cursos"][0]["horario"]
    assert cu.resolver("Documentos/EDU CONTINUA 2027-1/Dip Compliance Anti- Corrupción", reg) == n["id"]  # no se confunde con el de 2026
    assert cu.resolver("Documentos/EDU CONTINUA 2026/Dip Compliance Anti- Corrupción", reg) is None  # la ruta del sitio viejo ya no cuenta


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
    assert cu.recibir(evento(f"Docs/{C1}/Diplomado Derecho Laboral", [{"Profesor": "A"}]), f)[:2] == ("curso", "derecho-laboral")
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


def test_registro_con_encabezado_danado_se_avisa_sin_tocar_nada():
    reg = _copia()
    filas = [dict(_fila(c), Column1=_fila(c).pop("Carpeta_x0020_del_x0020_curso")) for c in REG["cursos"]]
    for f in filas:
        del f["Carpeta_x0020_del_x0020_curso"]
    assert cu.es_registro(filas)
    avisos, cambios = cu.fusionar(reg, filas)
    assert len(avisos) == len(REG["cursos"]) and cambios == [] and reg == REG


def test_el_nombre_siempre_dice_si_es_curso_o_diplomado(sitio):
    assert cu.con_tipo("Derecho Laboral", "Diplomado") == "Diplomado Derecho Laboral"
    assert cu.con_tipo("Curso en IA", "Curso") == "Curso en IA"                       # no se duplica
    assert cu.con_tipo("Diplomado en Derecho Laboral", "Diplomado") == "Diplomado en Derecho Laboral"
    for c in REG["cursos"]:
        cfg = cu.config_curso(c, REG["global"])
        assert cfg["programaCorto"].startswith(c["tipo"]) and cfg["programa"].startswith(c["tipo"]), c["id"]
    meta = json.loads((sitio / "g" / REG["global"]["adminCodigo"] / "cursos.json").read_text(encoding="utf-8"))
    assert all(c["programaCorto"].startswith(c["tipo"]) for c in meta["cursos"])
    assert "<title>Diplomado Derecho Laboral" in (sitio / cu.sitio_ruta(next(c for c in REG["cursos"] if c["id"] == "derecho-laboral")) / "index.html").read_text(encoding="utf-8")




def test_una_cohorte_nueva_del_mismo_curso_en_el_mismo_periodo_es_otro_curso():
    reg = _copia()
    c = REG["cursos"][4]
    base = len(reg["cursos"])
    avisos, cambios = cu.fusionar(reg, [_fila(c, Cohorte="Cohorte 1", Carpeta_x0020_del_x0020_periodo="EduContinua 2026-2"),
                                        _fila(c, Cohorte="Cohorte 2", Carpeta_x0020_del_x0020_periodo="EduContinua 2026-2")])
    nuevos = reg["cursos"][base:]
    assert not avisos and len(nuevos) == 2
    assert [x["carpeta"].split("/")[1] for x in nuevos] == ["Cohorte 1", "Cohorte 2"]
    assert len({x["id"] for x in nuevos}) == 2 and len({x["codigo"] for x in nuevos}) == 2
    assert nuevos[0]["cohorte"] == "Cohorte 1" and nuevos[0]["periodo"] == c["periodo"]
    assert cu.resolver("/sites/EduContinua/Docs/EduContinua 2026-2/Cohorte 2/" + c["carpeta"].split("/", 1)[1] + "/a.xlsx", reg) == nuevos[1]["id"]


def test_la_cohorte_se_toma_de_la_ruta_si_el_registro_no_tiene_la_columna():
    """El registro del sitio actual no tiene columna Cohorte: el formulario pone la ruta 2026-2/Cohorte 2/Diplomado X en Carpeta del curso."""
    reg = _copia()
    c = REG["cursos"][4]
    base = len(reg["cursos"])
    fila = lambda n: _fila(c, Carpeta_x0020_del_x0020_periodo="EDU CONTINUA 2026", Carpeta_x0020_del_x0020_curso=f"2026-2/Cohorte {n}/Diplomado X")
    avisos, _ = cu.fusionar(reg, [fila(1), fila(2)])
    nuevos = reg["cursos"][base:]
    assert not avisos and [x["cohorte"] for x in nuevos] == ["Cohorte 1", "Cohorte 2"]
    assert [x["carpeta"] for x in nuevos] == ["EDU CONTINUA 2026/2026-2/Cohorte 1/Diplomado X", "EDU CONTINUA 2026/2026-2/Cohorte 2/Diplomado X"]
    assert len({x["id"] for x in nuevos}) == 2 and nuevos[0]["id"].endswith("cohorte-1")
    assert cu.resolver("/sites/Especializaciones/Documentos compartidos/ESPECIALIZACIONES 2014 - 2023/EDU CONTINUA 2026/2026-2/Cohorte 2/Diplomado X/a.xlsx", reg) == nuevos[1]["id"]
    assert all(x["cohorte"].startswith("Cohorte 1") for x in reg["cursos"][:8])  # los 8 cursos de siempre tienen su cohorte y no cambian


def test_contactos_del_curso_mandan_sobre_los_generales():
    g = {"zona": "z", "desfase": 0, "universidad": "U", "facultad": "F", "mostrarLinksTeams": True, "diasAvisoCambio": 14,
         "profesoresInstitucionales": [], "siglas": []}
    c = {"id": "x", "tipo": "Curso", "programa": "X", "programaCorto": "X", "horario": {"inicio": "18:00", "fin": "20:00"}}
    gen = [{"nombre": "A", "cargo": "Gestora", "correo": "a@unisabana.edu.co"}]
    propio = [{"nombre": "B", "cargo": "Jefa", "correo": "b@unisabana.edu.co"}]
    assert "contactos" not in cu.config_curso(c, g)
    assert cu.config_curso(c, {**g, "contactos": gen})["contactos"] == gen
    assert cu.config_curso({**c, "contactos": propio}, {**g, "contactos": gen})["contactos"] == propio


def test_sitio_marca_la_bienvenida_ya_enviada(tmp_path):
    import shutil
    raiz = tmp_path / "r"
    shutil.copytree(cu.RAIZ, raiz, ignore=shutil.ignore_patterns(".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", "_sitio"))
    cid = cu.registro(raiz)["cursos"][0]["id"]
    (raiz / "estado/bienvenidas-enviadas.json").write_text(json.dumps({cid: {"fecha": "2026-10-23T17:49:00Z"}}), encoding="utf-8")
    s = cu.armar_sitio(tmp_path / "s", "v", raiz)
    meta = json.loads((s / "g" / REG["global"]["adminCodigo"] / "cursos.json").read_text(encoding="utf-8"))
    por_id = {c["id"]: c for c in meta["cursos"]}
    assert por_id[cid]["bienvenidaEnviada"] == "2026-10-23T17:49:00Z"
    assert all(c["bienvenidaEnviada"] == "" for k, c in por_id.items() if k != cid)
    assert "alguien@" not in json.dumps(meta)


def test_sitio_lleva_el_enlace_de_la_encuesta_a_cada_curso(tmp_path):
    import shutil
    raiz = tmp_path / "r"
    shutil.copytree(cu.RAIZ, raiz, ignore=shutil.ignore_patterns(".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", "_sitio"))
    reg = json.loads((raiz / "config/cursos.json").read_text(encoding="utf-8"))
    reg["global"]["encuestaSatisfaccion"] = "https://forms.example/encuesta"
    (raiz / "config/cursos.json").write_text(json.dumps(reg, ensure_ascii=False), encoding="utf-8")
    s = cu.armar_sitio(tmp_path / "s", "v", raiz)
    for c in reg["cursos"]:
        cfg = json.loads((s / cu.sitio_ruta(c) / "config/contenido.json").read_text(encoding="utf-8"))
        assert cfg["encuesta"] == "https://forms.example/encuesta"
    s2 = cu.armar_sitio(tmp_path / "s2", "v", cu.RAIZ)  # sin enlace configurado, ningún curso lo trae
    assert all("encuesta" not in json.loads((s2 / cu.sitio_ruta(c) / "config/contenido.json").read_text(encoding="utf-8")) for c in reg["cursos"])
