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
