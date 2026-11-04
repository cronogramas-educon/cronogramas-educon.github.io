"""Marcas de asistencia desde un reporte de Teams: reglas del usuario y escritura que no toca nada más del libro."""
import sys, zipfile
from pathlib import Path

import openpyxl
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import asistencia_teams as at
import generar_asistencia_xlsx as gen

NOMBRES = ["ANA LUCIA PEREZ RIOS", "BETO ANDRES RUIZ SOTO", "CARLA MARIA GOMEZ LEON", "DARIO JOSE LARA VEGA", "ELENA SOFIA MORA DIAZ"]
CLASES = [{"fecha": "2026-03-02"}, {"fecha": "2026-03-03", "situacion": "Reprogramada", "nueva": "2026-03-10"}, {"fecha": "2026-03-04"}]


@pytest.fixture
def libro(tmp_path, monkeypatch):
    monkeypatch.setattr(at, "_refrescar_cache", lambda ruta: None)  # LibreOffice no es requisito de las pruebas
    ruta = tmp_path / "Formato de asistencia - Curso Falso.xlsx"
    gen.construir({"curso": "Curso Falso", "clases": CLASES, "estudiantes": [{"nombre": n, "cedula": f"900000000{i}"} for i, n in enumerate(NOMBRES)], "minimo": 0.8}, ruta)
    return ruta


def reporte(tmp_path, tramos, inicio="3/2/26, 6:00:00 PM", duracion="2h 0m 0s"):
    """CSV de Teams (UTF-16, tabuladores). tramos = [(nombre, entra, sale, correo)] con horas 'H:MM' del mismo día."""
    f = lambda h: f"3/2/26, {h}:00 PM"
    filas = ["1. Summary", "Meeting title\tClase falsa", f"Start time\t{inicio}", f"Meeting duration\t{duracion}", "", "3. In-Meeting Activities",
             "Name\tJoin Time\tLeave Time\tDuration\tEmail\tRole"]
    filas += [f"{n}\t{f(a)}\t{f(b)}\t0s\t{c}\tPresenter" for n, a, b, c in tramos]
    ruta = tmp_path / "Attendance report.csv"
    ruta.write_bytes(("\n".join(filas) + "\n").encode("utf-16"))
    return ruta


def test_reglas_de_porcentaje_y_union_de_tramos(tmp_path, libro):
    est = at.leer_libro(libro)["estudiantes"]
    r = at.calcular(reporte(tmp_path, [
        ("Ana Lucia Perez", "6:00", "7:55", ""),                                  # 95 %: asistió
        ("Beto Ruiz", "6:00", "6:50", ""), ("Beto Ruiz (Guest)", "6:10", "6:55", ""),  # dos cuentas solapadas: 55 min, no 95
        ("Carla Gomez", "6:00", "6:56", ""),                                       # 46,7 %: revisión manual
        ("Dario Lara", "6:00", "6:30", ""),                                        # 25 %: 0
        ("Profe Invitado", "6:00", "7:55", ""),                                    # no matriculado con mucho tiempo: se avisa
    ], ), est)
    m = {x["nombre"]: x for x in r["estudiantes"]}
    assert m["ANA LUCIA PEREZ RIOS"]["marca"] == 1
    assert m["BETO ANDRES RUIZ SOTO"]["segundos"] == 55 * 60 and m["BETO ANDRES RUIZ SOTO"]["marca"] is None  # unión: 55 de 120 min = 45,8 % (la suma daría 80 min y 1)
    assert r["marcas"][est["CARLA MARIA GOMEZ LEON"]] is None and [x["nombre"] for x in r["revision_manual"]] == ["BETO ANDRES RUIZ SOTO", "CARLA MARIA GOMEZ LEON"]
    assert m["DARIO JOSE LARA VEGA"]["marca"] == 0 and m["ELENA SOFIA MORA DIAZ"]["marca"] == 0
    assert [x["nombre"] for x in r["sin_coincidencia"]] == ["Profe Invitado"] and r["fecha"] == "2026-03-02" and not r["alertas"]


def test_alias_por_correo_y_no_matriculados_conocidos(tmp_path, libro):
    est = at.leer_libro(libro)["estudiantes"]
    alias = {"correos": {"ELENA SOFIA MORA DIAZ": ["elena.cuenta.rara@x.com"]}, "nombres": {"quien sea": "DARIO JOSE LARA VEGA"}, "no_matriculados": ["Profe Invitado (Guest)"]}
    r = at.calcular(reporte(tmp_path, [("zzz", "6:00", "7:55", "ELENA.cuenta.rara@x.com"), ("Quien Sea (Unverified)", "6:00", "7:55", ""), ("Profe Invitado", "6:00", "7:55", "")]), est, alias)
    m = {x["nombre"]: x for x in r["estudiantes"]}
    assert m["ELENA SOFIA MORA DIAZ"]["marca"] == 1 and m["ELENA SOFIA MORA DIAZ"]["emparejado_por"] == ["correo"]
    assert m["DARIO JOSE LARA VEGA"]["marca"] == 1 and [x["nombre"] for x in r["no_matriculados"]] == ["Profe Invitado"] and not r["sin_coincidencia"]


def test_reporte_de_otra_cosa_dispara_alerta(tmp_path, libro):
    r = at.calcular(reporte(tmp_path, [("Gente que no es del curso", "6:00", "7:55", "")]), at.leer_libro(libro)["estudiantes"])
    assert r["alertas"] and "no escribas nada" in r["alertas"][0]


def test_libro_lee_clases_fechas_y_estudiantes_sin_cache_de_formulas(libro):
    d = at.leer_libro(libro)
    assert [(c["n"], c["fecha"]) for c in d["clases"][:3]] == [(1, "2026-03-02"), (2, "2026-03-10"), (3, "2026-03-04")]  # la 2 usa su Nueva fecha
    assert list(d["estudiantes"]) == NOMBRES and d["sin_cedula"] == 0


def test_escribir_solo_cambia_la_hoja_y_no_sobrescribe(tmp_path, libro):
    destino = tmp_path / "salida.xlsx"
    marcas = {7: 1, 8: 0, 9: None, 10: 1, 11: 1}
    assert at.escribir_marcas(libro, destino, "2026-03-04", marcas)["n"] == 3
    a, b = zipfile.ZipFile(libro), zipfile.ZipFile(destino)
    cambiadas = sorted(n for n in a.namelist() if a.read(n) != b.read(n))
    assert "xl/worksheets/sheet2.xml" in cambiadas and set(cambiadas) <= {"xl/workbook.xml", "xl/worksheets/sheet2.xml"}
    ws = openpyxl.load_workbook(destino)["Asistencia"]
    assert [ws.cell(r, 6).value for r in range(7, 12)] == [1, 0, None, 1, 1] and "Table1" in ws.tables
    assert [ws.cell(r, 2).value for r in range(7, 12)] == [f"900000000{i}" for i in range(5)]  # la cédula queda intacta
    with pytest.raises(SystemExit, match="ya tiene marca"):
        at.escribir_marcas(destino, tmp_path / "otra.xlsx", "2026-03-04", {7: 1})
    with pytest.raises(SystemExit, match="No hay una clase"):
        at.escribir_marcas(libro, tmp_path / "x.xlsx", "2026-04-01", {7: 1})


def test_dos_clases_el_mismo_dia_pide_elegir(tmp_path, libro, monkeypatch):
    doble = tmp_path / "doble.xlsx"
    gen.construir({"curso": "Doble", "clases": [{"fecha": "2026-03-02"}, {"fecha": "2026-03-02"}], "estudiantes": [{"nombre": NOMBRES[0], "cedula": "1"}], "minimo": 0.8}, doble)
    with pytest.raises(SystemExit, match="decide a cuál"):
        at.escribir_marcas(doble, tmp_path / "x.xlsx", "2026-03-02", {7: 1})
    assert at.escribir_marcas(doble, tmp_path / "y.xlsx", "2026-03-02#2", {7: 1})["n"] == 2
    assert openpyxl.load_workbook(tmp_path / "y.xlsx")["Asistencia"]["E7"].value == 1
