import json, shutil, sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from icalendar import Calendar
from openpyxl import load_workbook

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import construir_datos as cd
from generar_ics import generar, plegar

FIX = RAIZ / "tests/fixtures/muestra_sanitizada.xlsx"
CFG = json.loads((RAIZ / "config/contenido.json").read_text(encoding="utf-8"))
T0 = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def raiz(tmp_path):
    (tmp_path / "config").mkdir()
    shutil.copy(RAIZ / "config/contenido.json", tmp_path / "config")
    return tmp_path


def xlsx_con(tmp_path, nombre, editar):
    wb = load_workbook(FIX)
    editar(wb[cd.HOJA])
    p = tmp_path / nombre
    wb.save(p)
    return p


def fila_de(ws, n):
    return next(r for r in range(3, 40) if ws.cell(r, 1).value == n)


def test_muestra_cumple_aceptacion(raiz):
    datos, avisos = cd.construir(FIX, raiz, ahora=T0)
    m = datos["meta"]
    assert (m["totalClases"], m["horasTotales"], len(datos["unidades"])) == (35, 105, 17)
    assert (m["inicio"], m["fin"]) == ("2026-10-01", "2026-12-04")
    assert [c["id"] for c in datos["clases"] if c["temaHeredado"]] == [17, 19, 22, 25, 26]
    assert all(c["profesor"] == "SABANA" for c in datos["clases"][1:6])
    assert "abril" not in json.dumps(datos, ensure_ascii=False).lower()
    assert avisos == []
    c23 = datos["clases"][22]
    assert c23["profesores"] == ["Marta Lucia Ramírez", "Beatriz Londoño P"]
    assert c23["inicio"].endswith("T17:00:00-05:00")


def test_fixture_sin_enlaces_reales():
    ws = load_workbook(FIX)[cd.HOJA]
    assert {ws.cell(r, 10).value for r in range(3, 38)} == {"https://teams.microsoft.com/meet/EJEMPLO"}


def test_sin_cambios_no_reescribe(raiz):
    cd.construir(FIX, raiz, ahora=T0)
    datos, _ = cd.construir(FIX, raiz, ahora=T0)
    assert datos is None


def test_puntos_caso():
    assert cd.puntos("Tema A  CASO  Odebrecht\n- otro") == ["Tema A", "CASO: Odebrecht", "otro"]


def test_fecha_serial_e_iso():
    assert cd.fecha_a_date(46296).isoformat() == "2026-10-01"
    assert cd.fecha_a_date("2026-10-01").isoformat() == "2026-10-01"
    with pytest.raises(cd.ErrorDatos):
        cd.fecha_a_date("pronto")


def test_modo_json_plan_b(raiz, tmp_path):
    datos0, _ = cd.construir(FIX, raiz, ahora=T0)
    ws = load_workbook(FIX)[cd.HOJA]
    filas = [dict(zip(cd.COLS, [ws.cell(r, c).value for c in range(1, 11)])) for r in range(3, 39)]
    for f in filas:
        if hasattr(f["Fecha"], "date"):
            f["Fecha"] = (f["Fecha"].date() - datetime(1899, 12, 30).date()).days  # serial, como Excel Online
    p = tmp_path / "crudo.json"
    p.write_text(json.dumps(filas, default=str), encoding="utf-8")
    r2 = tmp_path / "r2"
    (r2 / "config").mkdir(parents=True)
    shutil.copy(RAIZ / "config/contenido.json", r2 / "config")
    datos, _ = cd.construir(p, r2, modo_json=True, ahora=T0)
    assert datos["meta"]["hash"] == datos0["meta"]["hash"]


# --- errores bloqueantes
def test_no_es_xlsx(raiz, tmp_path):
    p = tmp_path / "x.xlsx"
    p.write_text("<html>inicia sesión</html>")
    with pytest.raises(cd.ErrorDatos, match="no es un .xlsx"):
        cd.construir(p, raiz)


def test_falta_encabezado(raiz, tmp_path):
    p = xlsx_con(tmp_path, "a.xlsx", lambda ws: setattr(ws["F2"], "value", None))
    with pytest.raises(cd.ErrorDatos, match="Profesor"):
        cd.construir(p, raiz)


def test_cero_clases(raiz, tmp_path):
    def vaciar(ws):
        for r in range(3, 38):
            ws.cell(r, 5).value = None
    with pytest.raises(cd.ErrorDatos, match="ninguna clase"):
        cd.construir(xlsx_con(tmp_path, "b.xlsx", vaciar), raiz)


def test_fecha_invalida_y_duplicado(raiz, tmp_path):
    p = xlsx_con(tmp_path, "c.xlsx", lambda ws: setattr(ws["H3"], "value", "pronto"))
    with pytest.raises(cd.ErrorDatos, match="Fecha"):
        cd.construir(p, raiz)
    p = xlsx_con(tmp_path, "d.xlsx", lambda ws: setattr(ws["A4"], "value", 1))
    with pytest.raises(cd.ErrorDatos, match="duplicados"):
        cd.construir(p, raiz)


def test_error_conserva_ultimo_bueno(raiz, tmp_path):
    cd.construir(FIX, raiz, ahora=T0)
    antes = (raiz / "data/data.json").read_text(encoding="utf-8")
    p = xlsx_con(tmp_path, "e.xlsx", lambda ws: setattr(ws["F2"], "value", None))
    with pytest.raises(cd.ErrorDatos):
        cd.construir(p, raiz)
    assert (raiz / "data/data.json").read_text(encoding="utf-8") == antes


# --- advertencias
def test_advertencias(raiz, tmp_path):
    def romper(ws):
        ws["G3"] = "Lunes"      # día no coincide
        ws["J4"] = None         # sin link
        ws["D5"] = 4            # horas != 3
    datos, avisos = cd.construir(xlsx_con(tmp_path, "f.xlsx", romper), raiz, ahora=T0)
    assert len(avisos) == 3 and datos["clases"][0]["diaCalculado"] == "Jueves"


# --- detección de cambios
def cambiar(tmp_path, raiz, nombre, ahora, cambios):
    """cambios: {id: nueva fecha ISO}"""
    def ed(ws):
        for i, f in cambios.items():
            ws.cell(fila_de(ws, i), 8).value = datetime.fromisoformat(f)
    return cd.construir(xlsx_con(tmp_path, nombre, ed), raiz, ahora=ahora)[0]


def dt(d, h=12):
    return datetime(2026, 10, d, h, tzinfo=timezone.utc)


def test_cambio_de_fecha_y_resolucion(raiz, tmp_path):
    cd.construir(FIX, raiz, ahora=T0)  # línea base, sin avisos
    assert json.loads((raiz / "data/data.json").read_text(encoding="utf-8"))["cambios"] == []
    orig = load_workbook(FIX)[cd.HOJA]
    f7 = orig.cell(fila_de(orig, 7), 8).value.date().isoformat()
    d = cambiar(tmp_path, raiz, "g.xlsx", dt(2), {7: "2026-10-14"})
    c7 = d["clases"][6]
    assert c7["cambio"]["fechaAnterior"] == f7 and c7["secuencia"] == 1
    assert d["cambios"][0]["fechaNueva"] == "2026-10-14"
    # vuelve a la original: se resuelve
    d = cambiar(tmp_path, raiz, "h.xlsx", dt(3), {})
    assert d["cambios"] == [] and d["clases"][6]["cambio"] is None and d["clases"][6]["secuencia"] == 2


def test_dos_cambios_seguidos_conservan_original(raiz, tmp_path):
    cd.construir(FIX, raiz, ahora=T0)
    cambiar(tmp_path, raiz, "i.xlsx", dt(2), {7: "2026-10-14"})
    d = cambiar(tmp_path, raiz, "j.xlsx", dt(3), {7: "2026-10-20"})
    x = d["cambios"][0]
    assert (x["fechaAnterior"], x["fechaNueva"]) == ("2026-10-14", "2026-10-20") and x["fechaOriginal"] != "2026-10-14"
    assert len(d["cambios"]) == 1 and d["clases"][6]["secuencia"] == 2


def test_aviso_caduca_a_los_14_dias(raiz, tmp_path):
    cd.construir(FIX, raiz, ahora=T0)
    cambiar(tmp_path, raiz, "k.xlsx", dt(2), {7: "2026-12-01"})
    d = cambiar(tmp_path, raiz, "l.xlsx", datetime(2026, 10, 17, 12, tzinfo=timezone.utc), {7: "2026-12-01"})
    assert d["cambios"] == [] and d["clases"][6]["cambio"] is None


def test_cambio_a_fecha_pasada_no_avisa(raiz, tmp_path):
    cd.construir(FIX, raiz, ahora=datetime(2026, 10, 20, tzinfo=timezone.utc))
    d = cambiar(tmp_path, raiz, "m.xlsx", datetime(2026, 10, 21, tzinfo=timezone.utc), {20: "2026-10-05"})
    assert d["cambios"] == []


def test_clase_agregada_y_eliminada(raiz, tmp_path):
    def sin_35(ws):
        ws.delete_rows(fila_de(ws, 35))
    cd.construir(xlsx_con(tmp_path, "n.xlsx", sin_35), raiz, ahora=T0)  # base de 34
    d, _ = cd.construir(FIX, raiz, ahora=dt(2))                          # reaparece la 35
    assert d["meta"]["totalClases"] == 35 and d["cambios"] == []
    d, _ = cd.construir(xlsx_con(tmp_path, "o.xlsx", sin_35), raiz, ahora=dt(3))
    estado = json.loads((raiz / "estado/cambios.json").read_text(encoding="utf-8"))
    assert d["meta"]["totalClases"] == 34 and "35" not in estado["base"]


# --- .ics
def test_ics_valido_y_horas(raiz):
    datos, _ = cd.construir(FIX, raiz, ahora=T0)
    ics = (raiz / "cronograma.ics").read_bytes()
    assert b"\r\n" in ics and b"\n" not in ics.replace(b"\r\n", b"")
    for linea in ics.split(b"\r\n"):
        assert len(linea) <= 75
    cal = Calendar.from_ical(ics)
    evs = [e for e in cal.walk("VEVENT")]
    assert len(evs) == 35
    e = evs[0]
    assert str(e["UID"]) == "clase-01@cronograma-compliance-2026-2"
    ini = e["DTSTART"].dt.astimezone(timezone.utc)
    fin = e["DTEND"].dt.astimezone(timezone.utc)
    assert (ini.hour, fin.hour) == (22, 1) and fin.day == 2  # 17:00 a 20:00 Bogotá = 22:00 a 01:00 UTC
    assert str(e["LOCATION"]) == "Microsoft Teams" and "Marta Lucia" in str(e["DESCRIPTION"])
    assert e.walk("VALARM")[0]["TRIGGER"].dt.total_seconds() == -1800


def test_ics_sequence_sube_con_cambio(raiz, tmp_path):
    cd.construir(FIX, raiz, ahora=T0)
    cambiar(tmp_path, raiz, "p.xlsx", dt(2), {7: "2026-10-14"})
    e = [e for e in Calendar.from_ical((raiz / "cronograma.ics").read_bytes()).walk("VEVENT") if "clase-07" in str(e["UID"])][0]
    assert int(e["SEQUENCE"]) == 1 and e["DTSTART"].dt.day == 14


def test_ics_escape_y_plegado_utf8():
    larga = "DESCRIPTION:" + "áéíóú, ñ; " * 30
    plegada = plegar(larga)
    assert all(len(p.encode()) <= 75 for p in plegada.split("\r\n"))
    assert plegada.replace("\r\n ", "") == larga
