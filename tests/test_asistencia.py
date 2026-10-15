"""Resumen de asistencia por curso: sin nombres, ordenado por urgencia, y cómo se reconoce el Excel."""
import json, sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import asistencia as asi
import cursos as cu


def fila(n, nombre, marcas, estado, faltas, quedan, programadas=10, doc="1020304050"):
    f = {"N°": n, "Documento": doc, "Nombre del estudiante": nombre, "Asistió": sum(m == 1 for m in marcas), "Faltas": faltas,
         "Sin marcar": 0, "Faltas que le quedan": quedan, "% hasta hoy": 1 - faltas / max(len(marcas), 1), "Puede llegar hasta": (programadas - faltas) / programadas,
         "Estado": estado, "Clases programadas": programadas}
    for i in range(programadas):
        f[f"Clase {i + 1}"] = marcas[i] if i < len(marcas) else ""
    return f


FILAS = [fila(1, "Ana Pérez", [1, 1, 1, 1], "Al día", 0, 2), fila(2, "Beto Ruiz", [1, 0, 0, 1], "En riesgo", 2, 0),
         fila(3, "Carla Gómez", [0, 0, 0, 1], "Perdió el mínimo", 3, -1), fila(4, "Dario Lara", [1, 0, 1, 1], "Atención", 1, 1),
         {"N°": "", "Nombre del estudiante": "", "Clase 1": ""}]


def test_resumen_ordena_por_urgencia_y_no_lleva_nombres():
    r = asi.resumir(FILAS)
    assert [x["n"] for x in r["lista"]] == [3, 2, 4, 1]
    assert (r["estudiantes"], r["programadas"], r["dictadas"], r["permitidas"]) == (4, 10, 4, 2)
    assert r["porEstado"]["En riesgo"] == 1 and r["porEstado"]["Perdió el mínimo"] == 1
    assert r["promedio"] == pytest.approx(10 / 16)
    assert [c["estado"] for c in r["porClase"][:5]] == ["Dictada"] * 4 + ["Sin dictar"]
    assert r["porClase"][0]["asistieron"] == 3 and r["porClase"][0]["marcadas"] == 4
    texto = json.dumps(r, ensure_ascii=False)
    for secreto in ("Ana", "Pérez", "Beto", "Carla", "Dario", "1020304050"):
        assert secreto not in texto


def test_sin_columnas_calculadas_o_sin_estudiantes_avisa_claro():
    with pytest.raises(ValueError, match="faltan columnas"):
        asi.resumir([{"Nombre del estudiante": "A", "Clase 1": 1}])
    with pytest.raises(ValueError, match="no tiene estudiantes"):
        asi.resumir([{"Nombre del estudiante": "", "Clase 1": ""}])


def test_valores_como_texto_de_power_automate():
    f = fila(1, "Ana", [1, 0], "Atención", 1, 1)
    f.update({"Asistió": "1", "Faltas": "1.0", "Faltas que le quedan": "1", "% hasta hoy": "0,5", "Clase 1": "1", "Clase 2": "0"})
    r = asi.resumir([f])
    assert r["lista"][0]["porcentaje"] == 0.5 and r["porClase"][1]["asistieron"] == 0 and r["porClase"][1]["estado"] == "Dictada"


def test_aplicar_no_reescribe_sin_cambios_y_conserva_ante_error(tmp_path):
    assert asi.aplicar(FILAS, tmp_path)[1] is True
    arch = tmp_path / "estado/asistencia.json"
    antes = arch.read_text(encoding="utf-8")
    assert asi.aplicar(FILAS, tmp_path)[1] is False
    with pytest.raises(ValueError):
        asi.aplicar([{"Nombre del estudiante": "A", "Clase 1": 1}], tmp_path)
    assert arch.read_text(encoding="utf-8") == antes


def test_recibir_reconoce_el_excel_de_asistencia_por_sus_columnas(tmp_path):
    e = tmp_path / "e.json"
    e.write_text(json.dumps({"client_payload": {"ruta": "Docs/ESP/EDU CONTINUA 2026/Dip en Derecho Laboral", "filas": json.dumps(FILAS)}}), encoding="utf-8")
    assert cu.recibir(e, tmp_path / "f.json")[:2] == (("asistencia", None))
    e.write_text(json.dumps({"client_payload": {"ruta": "Docs/EDU CONTINUA 2099/Otro", "filas": json.dumps(FILAS)}}), encoding="utf-8")
    assert cu.recibir(e, tmp_path / "f.json")[0] == "ninguno"


def test_encabezados_codificados_por_excel_online():
    """Power Automate entrega "N°" como N_x00b0_ y "% hasta hoy" como _x0025_ hasta hoy."""
    codif = [{k.replace("°", "_x00b0_").replace("%", "_x0025_"): v for k, v in f.items()} for f in FILAS]
    assert asi.es_asistencia(codif)
    r = asi.resumir(codif)
    assert [x["n"] for x in r["lista"]] == [3, 2, 4, 1] and r["lista"][0]["porcentaje"] == 0.25


def test_el_cuadro_de_horas_manda_el_numero_de_clases(tmp_path):
    """Agregar una clase al Cuadro cambia faltas permitidas y estados sin tocar el Excel de asistencia."""
    cur = tmp_path / "c"
    (cur / "data").mkdir(parents=True)
    filas = [fila(1, "Ana", [1, 1, 1, 1], "x", 0, 0), fila(2, "Beto", [1, 0, 0, 1], "x", 2, 0)]
    for f in filas:
        f["Clases del curso"] = 3  # dato viejo del Excel: se ignora
    def cuadro(n):
        (cur / "data/data.json").write_text(json.dumps({"clases": [{"id": i} for i in range(1, n + 1)]}))
    cuadro(10)
    r, _ = asi.aplicar(filas, cur)
    assert (r["programadas"], r["permitidas"]) == (10, 2)
    assert {x["n"]: x["estado"] for x in r["lista"]} == {1: "Al día", 2: "En riesgo"}
    assert "Ana" not in json.dumps(r)
    cuadro(20)  # el Cuadro crece a 20 clases: permitidas 4, Beto pasa a Atención
    r, cambio = asi.recalcular(cur)
    assert cambio and (r["programadas"], r["permitidas"]) == (20, 4)
    assert {x["n"]: x["estado"] for x in r["lista"]}[2] == "Atención"
    assert len(r["porClase"]) == 20
