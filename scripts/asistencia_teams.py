"""Asistencia desde los reportes de Teams, para cualquier curso.

Lee un reporte "Attendance report" de Teams (CSV UTF-16 o XLSX), calcula quién asistió y escribe las marcas
en la columna de esa clase del Excel "Formato de asistencia - <curso>.xlsx". No sabe nada de ningún curso:
los estudiantes salen de la columna C del propio libro y los alias de un archivo aparte por curso
(`alias-asistencia.json`, en la carpeta del curso; lleva correos reales, por eso NUNCA va en este repositorio).

Reglas (las definió el usuario): porcentaje = tiempo presente (UNIÓN de los tramos, no la suma) / duración de la reunión.
>= 50 % marca 1, entre 40 % y 50 % queda vacía y se avisa para decidir a mano, < 40 % o sin registro marca 0.

Uso (todo sale como JSON, así lo puede llamar también el hub o un flujo):
  python3 -I scripts/asistencia_teams.py libro LIBRO.xlsx
  python3 -I scripts/asistencia_teams.py calcular REPORTE LIBRO.xlsx [ALIAS.json]
  python3 -I scripts/asistencia_teams.py escribir LIBRO.xlsx DESTINO.xlsx AAAA-MM-DD[#N] MARCAS.json   (#N = clase, si hay dos el mismo día)
  Con --cuadro CUADRO.xlsx (Cuadro de horas del curso) las fechas salen del Cuadro, y al escribir se copian a la hoja Cronograma del
  Excel de asistencia. Si el libro no tiene la hoja «Alias Teams», escribir la agrega vacía.

Alias (todo opcional): {"correos": {"NOMBRE COMPLETO": ["a@x.com"]}, "nombres": {"cuenta de teams": "NOMBRE COMPLETO"},
"no_matriculados": ["Nombre de un profesor u organizador"]}. "NOMBRE COMPLETO" es el de la columna C del libro.
Los alias también pueden vivir en el propio libro, hoja "Alias Teams" (A estudiante, B cuenta de Teams, C correo, D nota;
"No matriculado" en A marca la cuenta como profesor u organizador): así viajan con el Excel del curso y los comparten todos los PAT.
"""
import csv, datetime, io, json, os, re, shutil, subprocess, sys, tempfile, unicodedata, zipfile
from collections import defaultdict

import openpyxl
from openpyxl.utils import get_column_letter, column_index_from_string
from openpyxl.utils.exceptions import InvalidFileException

MINIMO, REVISION, RELEVANTE = 0.5, 0.4, 0.2
HOJAS = ("Asistencia", "Resumen", "Cronograma")  # las que llevan marcas o cuentas que dependen de ellas


# ---------- reporte de Teams ----------
def _texto(ruta):
    crudo = open(ruta, "rb").read()
    for cod in ("utf-16", "utf-8-sig", "cp1252"):
        try:
            return crudo.decode(cod)
        except UnicodeDecodeError:
            pass
    return crudo.decode("utf-8", "replace")


def _fecha_hora(s):
    for f in ("%m/%d/%y, %I:%M:%S %p", "%m/%d/%Y, %I:%M:%S %p"):
        try:
            return datetime.datetime.strptime(s.strip(), f)
        except ValueError:
            pass
    raise ValueError(f"fecha no reconocida: {s}")


def _duracion(s):
    return sum(int(n) * {"h": 3600, "m": 60, "s": 1}[u] for n, u in re.findall(r"(\d+)\s*([hms])", s))


def leer_reporte(ruta):
    """(resumen, tramos): tramos = filas de la sección 3 (Name, Join Time, Leave Time, Duration, Email, Role)."""
    ruta = str(ruta)
    if ruta.lower().endswith(".xlsx"):
        ws = openpyxl.load_workbook(ruta).active
        filas = [["" if c is None else str(c) for c in f] for f in ws.iter_rows(values_only=True)]
    else:
        filas = list(csv.reader(io.StringIO(_texto(ruta)), delimiter="\t"))
    sec, resumen, tramos = None, {}, []
    for f in filas:
        if not f or not any(c.strip() for c in f):
            continue
        h = f[0].strip()
        m = re.match(r"^([123])\.", h)
        if m:
            sec = int(m.group(1))
        elif sec == 1 and len(f) > 1:
            resumen[h] = f[1].strip()
        elif sec == 3 and h != "Name":
            tramos.append(f)
    return resumen, tramos


# ---------- emparejar participante con estudiante ----------
def _norm(s):
    s = unicodedata.normalize("NFKD", s.replace("�", "?"))
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def _sin_cuenta(n):
    return re.sub(r"\((unverified|guest|invitado)\)", "", _norm(n)).strip()


def _tokens(n):
    return [t for t in re.split(r"[^a-z?0-9]+", _sin_cuenta(n)) if t]


def _igual(t, e):  # U+FFFD (convertido en ?) vale por un carácter cualquiera
    return re.fullmatch(t.replace("?", "."), e) is not None if "?" in t else t == e


def emparejar(nombre, correo, estudiantes, alias):
    """(nombre del estudiante o None, cómo). Primero correo, luego alias de nombre, luego nombre, luego nombre compacto."""
    em = (correo or "").strip().lower()
    for est, correos in alias.get("correos", {}).items():
        if em and em in {c.lower() for c in correos} and est in estudiantes:
            return est, "correo"
    clave = _sin_cuenta(nombre)
    for cuenta, est in alias.get("nombres", {}).items():
        if _sin_cuenta(cuenta) == clave and est in estudiantes:
            return est, "alias de nombre"
    tk = [t for t in _tokens(nombre) if len(t) > 1]
    punt = sorted(((sum(1 for e in set(_tokens(s)) if len(e) > 1 and any(_igual(t, e) for t in tk)), s) for s in estudiantes), reverse=True)
    if punt and punt[0][0] >= 2 and (len(punt) == 1 or punt[0][0] > punt[1][0]):
        return punt[0][1], "nombre"
    compacto = re.sub(r"[^a-z]", "", re.sub(r"\(.*?\)", "", _norm(nombre)))
    for _, s in punt:
        if sum(1 for e in _tokens(s) if len(e) >= 4 and e in compacto) >= 2:
            return s, "nombre compacto (inferido)"
    return None, "sin coincidencia"


def _union(iv):
    out = []
    for a, b in sorted(iv):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def calcular(ruta_reporte, estudiantes, alias=None):
    """estudiantes = {nombre completo: fila}. Devuelve fecha, marcas {fila: 1|0|None} y lo que requiere decisión humana."""
    alias = alias or {}
    try:
        resumen, tramos = leer_reporte(ruta_reporte)
        total = _duracion(resumen["Meeting duration"])
        fecha = _fecha_hora(resumen["Start time"]).date()
        tramos = [(f[0], _fecha_hora(f[1]), _fecha_hora(f[2]), f[4] if len(f) > 4 else "") for f in tramos]
    except (KeyError, ValueError, IndexError, UnicodeError, OSError, csv.Error, zipfile.BadZipFile) as e:
        raise ValueError(f"No parece un reporte de asistencia de Teams (falta o no se entiende: {e!r}). Descárgalo de nuevo desde la reunión, pestaña Asistencia.") from None
    if not total:
        raise ValueError("El reporte dice que la reunión duró 0 segundos: no se puede calcular el porcentaje.")
    por_est, otros = defaultdict(lambda: {"iv": [], "cuentas": set(), "como": set()}), defaultdict(list)
    for nombre, a, b, correo in tramos:
        est, como = emparejar(nombre, correo, estudiantes, alias)
        if est:
            x = por_est[est]
            x["iv"].append((a, b)); x["cuentas"].add(nombre.strip()); x["como"].add(como)
        else:
            otros[nombre.strip()].append((a, b))
    seg = lambda iv: sum((b - a).total_seconds() for a, b in _union(iv))
    lista, marcas, revision = [], {}, []
    for nombre, fila in sorted(estudiantes.items(), key=lambda kv: kv[1]):
        x = por_est.get(nombre)
        s = seg(x["iv"]) if x else 0
        pct = s / total if total else 0
        marca = 1 if pct >= MINIMO else (None if pct >= REVISION else 0)
        if marca is None:
            revision.append({"fila": fila, "nombre": nombre, "porcentaje": round(pct, 3), "minutos": round(s / 60)})
        marcas[fila] = marca
        lista.append({"fila": fila, "nombre": nombre, "segundos": round(s), "porcentaje": round(pct, 3), "marca": marca,
                      "cuentas": sorted(x["cuentas"]) if x else [], "emparejado_por": sorted(x["como"]) if x else []})
    conocidos = {_sin_cuenta(n) for n in alias.get("no_matriculados", [])}
    no_mat, dudosos = [], []
    for nombre, iv in otros.items():
        p = seg(iv) / total if total else 0
        if p >= RELEVANTE:
            (no_mat if _sin_cuenta(nombre) in conocidos else dudosos).append({"nombre": nombre, "porcentaje": round(p, 3)})
    presentes = sum(1 for x in lista if x["segundos"])
    alertas = [] if presentes * 2 >= len(lista) else [f"Solo {presentes} de {len(lista)} estudiantes aparecen en el reporte: no escribas nada hasta confirmar que es el reporte de esa clase."]
    return {"fecha": fecha.isoformat(), "titulo": resumen.get("Meeting title", ""), "duracion_s": total, "estudiantes": lista, "alertas": alertas,
            "marcas": marcas, "revision_manual": revision, "no_matriculados": no_mat, "sin_coincidencia": dudosos}


# ---------- libro de asistencia ----------
def _fecha_de_clase(wb, ws, col, n):
    v = ws.cell(5, col).value
    if isinstance(v, datetime.datetime):
        return v.date()
    if "Cronograma" in wb.sheetnames:  # el libro sin caché de fórmulas: misma regla que la fila 5 (Nueva fecha, si no la original)
        cr = wb["Cronograma"]
        for c in ("E", "B"):
            v = cr[f"{c}{5 + n}"].value
            if isinstance(v, datetime.datetime):
                return v.date()
    return None


def leer_cuadro(ruta):
    """Cuadro de horas del curso: {n: {"fecha": "AAAA-MM-DD" o None, "cancelada": bool}} por cada fila «CLASE N». El Cuadro manda sobre las fechas."""
    try:
        wb = openpyxl.load_workbook(ruta, data_only=True)
    except (OSError, zipfile.BadZipFile, InvalidFileException) as e:
        raise ValueError(f"No se pudo abrir el Cuadro de horas: {e!r}") from None
    for ws in [wb["DISTRIBUCIÓN HORAS"]] if "DISTRIBUCIÓN HORAS" in wb.sheetnames else wb.worksheets:
        for r in range(1, min(ws.max_row, 15) + 1):
            enc = {_norm(str(ws.cell(r, c).value or "")).strip(): c for c in range(1, ws.max_column + 1)}
            if "no. de clase" in enc and "fecha" in enc:
                cn, cf, cs = enc["no. de clase"], enc["fecha"], enc.get("situacion")
                clases = {}
                for f in range(r + 1, ws.max_row + 1):
                    m = re.fullmatch(r"\s*clase\s*(\d+)\s*", _norm(str(ws.cell(f, cn).value or "")))
                    if not m:
                        continue
                    v = ws.cell(f, cf).value
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        v = datetime.datetime(1899, 12, 30) + datetime.timedelta(days=int(v))
                    fecha = v.date().isoformat() if isinstance(v, datetime.datetime) else v.isoformat() if isinstance(v, datetime.date) else None
                    canc = bool(cs) and _norm(str(ws.cell(f, cs).value or "")).startswith("cancelad")
                    clases[int(m.group(1))] = {"fecha": fecha, "cancelada": canc}
                return clases
    raise ValueError("No es el Cuadro de horas: no tiene las columnas «No. de clase» y «Fecha».")


def leer_libro(ruta, cuadro=None):
    try:
        wb = openpyxl.load_workbook(ruta, data_only=True)
        ws = wb["Asistencia"]
    except (KeyError, OSError, zipfile.BadZipFile, InvalidFileException) as e:
        raise ValueError(f"No es el Excel «Formato de asistencia» (no se pudo abrir la hoja Asistencia: {e!r}).") from None
    clases = []
    for c in range(1, ws.max_column + 1):
        m = re.fullmatch(r"Clase (\d+)", str(ws.cell(6, c).value or "").strip())
        if m:
            n = int(m.group(1))
            f = _fecha_de_clase(wb, ws, c, n)
            clases.append({"n": n, "columna": get_column_letter(c), "fecha": f.isoformat() if f else None,
                           "estado": ws.cell(4, c).value, "marcas": sum(1 for r in range(7, ws.max_row + 1) if ws.cell(r, c).value is not None)})
    est = {str(ws.cell(r, 3).value).strip(): r for r in range(7, ws.max_row + 1) if ws.cell(r, 3).value and str(ws.cell(r, 3).value).strip()}
    cedulas = sum(1 for r in est.values() if ws.cell(r, 2).value)
    alias, avisos = _alias_del_libro(wb, est)
    if cuadro:  # el Excel de asistencia puede venir sin fechas (plantilla): las da el Cuadro de horas
        cq = leer_cuadro(cuadro) if not isinstance(cuadro, dict) else cuadro
        for c in clases:
            if c["n"] in cq:
                c["fecha"] = cq[c["n"]]["fecha"]
                if cq[c["n"]]["cancelada"]:
                    c["estado"] = "Cancelada"
        sin_col = sorted(n for n in cq if n > len(clases))
        if sin_col:
            avisos.append(f"El Cuadro tiene clases sin columna en el Excel de asistencia: {sin_col}.")
    if "Alias Teams" not in wb.sheetnames:
        avisos.append("El Excel no tiene la hoja «Alias Teams»: se agrega al escribir las marcas.")
    return {"clases": clases, "estudiantes": est, "sin_cedula": len(est) - cedulas, "alias": alias, "avisos_alias": avisos}


def _estudiante_de(texto, est):
    """El nombre de la columna C al que se refiere lo que escribió el PAT: igual sin tildes ni mayúsculas, o el único que comparte dos palabras."""
    t = _norm(str(texto)).strip()
    for s in est:
        if _norm(s).strip() == t:
            return s
    tk = set(_tokens(t))
    hits = [s for s in est if len(tk & set(_tokens(s))) >= 2]
    return hits[0] if len(hits) == 1 else None


def _alias_del_libro(wb, est):
    """Hoja "Alias Teams" (opcional): alias en el formato de los JSON y avisos de filas que no se entienden."""
    alias, avisos = {"correos": {}, "nombres": {}, "no_matriculados": []}, []
    if "Alias Teams" not in wb.sheetnames:
        return alias, avisos
    for r, fila in enumerate(wb["Alias Teams"].iter_rows(min_row=2, max_col=3, values_only=True), 2):
        quien, cuenta, correo = (str(x).strip() if x not in (None, "") else "" for x in fila)
        if not (quien or cuenta or correo):
            continue
        if not (cuenta or correo):
            avisos.append(f"Fila {r} de Alias Teams: falta el nombre o el correo de Teams.")
        elif _norm(quien).startswith("no matricul"):
            alias["no_matriculados"].append(cuenta or correo)
        elif (s := _estudiante_de(quien, est)) is None:
            avisos.append(f"Fila {r} de Alias Teams: «{quien}» no coincide con ningún estudiante de la hoja Asistencia.")
        else:
            if cuenta:
                alias["nombres"][cuenta] = s
            if correo:
                alias["correos"].setdefault(s, []).append(correo.lower())
    return alias, avisos


def unir_alias(*fuentes):
    out = {"correos": {}, "nombres": {}, "no_matriculados": []}
    for a in fuentes:
        for s, cs in (a or {}).get("correos", {}).items():
            out["correos"].setdefault(s, []).extend(cs)
        out["nombres"].update((a or {}).get("nombres", {}))
        out["no_matriculados"] += (a or {}).get("no_matriculados", [])
    return out


def _columna(libro, fecha):
    """fecha = 'AAAA-MM-DD', o 'AAAA-MM-DD#N' para elegir la clase N cuando hay dos clases el mismo día."""
    fecha, _, n = fecha.partition("#")
    cs = [c for c in libro["clases"] if c["fecha"] == fecha and (not n or c["n"] == int(n))]
    if not cs:
        raise SystemExit(f"No hay una clase con fecha {fecha} en el Excel de asistencia. Si sus fechas están vacías, pide el Cuadro de horas del curso y usa --cuadro. No inventes columna: avisa al usuario.")
    if len(cs) > 1:
        raise SystemExit(f"Hay {len(cs)} clases con la fecha {fecha} ({', '.join('Clase %d' % c['n'] for c in cs)}): decide a cuál va.")
    return cs[0]


def _zip(zin, destino, cambios, nuevos=None):
    destino = str(destino)
    tmp = destino + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for it in zin.infolist():
            datos = cambios[it.filename].encode("utf8") if it.filename in cambios else zin.read(it.filename)
            zout.writestr(it, datos, compress_type=zipfile.ZIP_DEFLATED)
        for nombre, texto in (nuevos or {}).items():
            zout.writestr(nombre, texto.encode("utf8"), compress_type=zipfile.ZIP_DEFLATED)
    os.replace(tmp, destino)


def _partes(zin):
    """Nombre de hoja -> parte XML, leído del propio libro: Excel Online puede renumerar los sheetN.xml al guardar."""
    import xml.etree.ElementTree as ET
    ns, nr = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}", "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(zin.read("xl/_rels/workbook.xml.rels"))}
    destino = lambda t: t.lstrip("/") if t.startswith("/") else "xl/" + t
    return {h.get("name"): destino(rels[h.get(nr + "id")]) for h in ET.fromstring(zin.read("xl/workbook.xml")).iter(ns + "sheet")}


def _col_num(ref):
    return column_index_from_string(re.match(r"[A-Z]+", ref).group(0))


def _poner(hoja, ref, valor):
    """Escribe una celda en el XML de una hoja (número, texto o vacío), creándola si no existe y conservando su estilo."""
    if valor is None:
        contenido, tipo = "", ""
    elif isinstance(valor, str):
        t = valor.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        contenido, tipo = f"<is><t>{t}</t></is>", ' t="inlineStr"'
    else:
        contenido, tipo = f"<v>{valor}</v>", ""
    mm = re.search(r'<c r="%s"((?:\s[^>]*?)?)(?:/>|>.*?</c>)' % ref, hoja, re.S)
    if mm:
        attrs = re.sub(r'\st="[^"]*"', "", mm.group(1))
        nueva = f'<c r="{ref}"{attrs}{tipo}>{contenido}</c>' if contenido else f'<c r="{ref}"{attrs}/>'
        return hoja[:mm.start()] + nueva + hoja[mm.end():]
    if not contenido:
        return hoja
    fila = int(re.search(r"\d+", ref).group(0))
    celda = f'<c r="{ref}"{tipo}>{contenido}</c>'
    mr = re.search(r'<row r="%d"[^>]*?(?:/>|>(.*?)</row>)' % fila, hoja, re.S)
    if mr:
        if mr.group(0).endswith("/>"):
            return hoja[:mr.start()] + mr.group(0)[:-2] + ">" + celda + "</row>" + hoja[mr.end():]
        cuerpo, ini = mr.group(1), mr.start(1)
        for mc in re.finditer(r'<c r="([A-Z]+\d+)"', cuerpo):
            if _col_num(mc.group(1)) > _col_num(ref):
                return hoja[:ini + mc.start()] + celda + hoja[ini + mc.start():]
        return hoja[:mr.end(1)] + celda + hoja[mr.end(1):]
    for mr in re.finditer(r'<row r="(\d+)"', hoja):
        if int(mr.group(1)) > fila:
            return hoja[:mr.start()] + f'<row r="{fila}">{celda}</row>' + hoja[mr.start():]
    if "<sheetData/>" in hoja:
        return hoja.replace("<sheetData/>", f'<sheetData><row r="{fila}">{celda}</row></sheetData>', 1)
    return hoja.replace("</sheetData>", f'<row r="{fila}">{celda}</row></sheetData>', 1)


ALIAS_ENCABEZADOS = ("Estudiante (como está en la hoja Asistencia)", "Nombre o cuenta en Teams", "Correo en Teams", "Nota")


def _hoja_alias(zin, cambios):
    """Agrega la hoja «Alias Teams» (vacía, con encabezados) a un libro que no la tiene. Devuelve las partes nuevas."""
    ns_r = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    usadas = {n for n in zin.namelist() if n.startswith("xl/worksheets/sheet")}
    k = 1
    while f"xl/worksheets/sheet{k}.xml" in usadas:
        k += 1
    rels = cambios.get("xl/_rels/workbook.xml.rels") or zin.read("xl/_rels/workbook.xml.rels").decode("utf8")
    ids = {int(x) for x in re.findall(r'Id="rId(\d+)"', rels)}
    rid = f"rId{max(ids, default=0) + 1}"
    rels = rels.replace("</Relationships>", f'<Relationship Id="{rid}" Type="{ns_r}/worksheet" Target="worksheets/sheet{k}.xml"/></Relationships>')
    wb = cambios.get("xl/workbook.xml") or zin.read("xl/workbook.xml").decode("utf8")
    sid = max((int(x) for x in re.findall(r'sheetId="(\d+)"', wb)), default=0) + 1
    pref = re.search(r'xmlns:(\w+)="%s"' % re.escape(ns_r), wb)
    rpref = pref.group(1) if pref else "r"
    if not pref:
        wb = wb.replace("<workbook ", f'<workbook xmlns:r="{ns_r}" ', 1)
    wb = wb.replace("</sheets>", f'<sheet name="Alias Teams" sheetId="{sid}" {rpref}:id="{rid}"/></sheets>', 1)
    ct = cambios.get("[Content_Types].xml") or zin.read("[Content_Types].xml").decode("utf8")
    ct = ct.replace("</Types>", f'<Override PartName="/xl/worksheets/sheet{k}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
    cambios.update({"xl/_rels/workbook.xml.rels": rels, "xl/workbook.xml": wb, "[Content_Types].xml": ct})
    enc = "".join(f'<c r="{chr(65 + i)}1" t="inlineStr"><is><t>{h}</t></is></c>' for i, h in enumerate(ALIAS_ENCABEZADOS))
    hoja = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
            '<cols><col min="1" max="1" width="44" customWidth="1"/><col min="2" max="3" width="34" customWidth="1"/><col min="4" max="4" width="40" customWidth="1"/></cols>'
            f'<sheetData><row r="1">{enc}</row></sheetData></worksheet>')
    return {f"xl/worksheets/sheet{k}.xml": hoja}


def _sincronizar_cronograma(zin, partes, cuadro, cambios):
    """Copia al Excel de asistencia las fechas (y cancelaciones) del Cuadro de horas: hoja Cronograma columna B, y «Clases del curso»."""
    if "Cronograma" not in partes:
        return
    wbv = None
    cr = cambios.get(partes["Cronograma"]) or zin.read(partes["Cronograma"]).decode("utf8")
    for n, d in cuadro.items():
        if n > 40:
            continue
        if d["fecha"]:
            serial = (datetime.date.fromisoformat(d["fecha"]) - datetime.date(1899, 12, 30)).days
            cr = _poner(cr, f"B{5 + n}", serial)
            cr = _poner(cr, f"E{5 + n}", None)  # la fecha vigente ya es la del Cuadro
        if d["cancelada"]:
            cr = _poner(cr, f"D{5 + n}", "Cancelada")
    cambios[partes["Cronograma"]] = cr
    if "Resumen" in partes and cuadro:
        rs = cambios.get(partes["Resumen"]) or zin.read(partes["Resumen"]).decode("utf8")
        cambios[partes["Resumen"]] = _poner(rs, "C5", max(cuadro))


def escribir_marcas(origen, destino, fecha, marcas, cuadro=None):
    """Parchea solo el XML de las celdas de la clase de esa fecha (no usa openpyxl para guardar: la tabla, los comentarios
    y los estilos deben quedar intactos). marcas = {fila: 1|0|None}. Se detiene si la columna ya tiene marcas."""
    cq = leer_cuadro(cuadro) if cuadro else None
    libro = leer_libro(origen, cq)
    clase = _columna(libro, fecha)
    col = clase["columna"]
    ws = openpyxl.load_workbook(origen, data_only=True)["Asistencia"]
    ci = column_index_from_string(col)
    for r in marcas:
        if not ws.cell(int(r), 3).value:
            raise SystemExit(f"La fila {r} no tiene estudiante en la columna C.")
        if ws.cell(int(r), ci).value is not None:
            raise SystemExit(f"{col}{r} ya tiene marca ({ws.cell(int(r), ci).value}). Avisa al usuario y pregunta antes de sobrescribir.")
    zin = zipfile.ZipFile(origen)
    parte = _partes(zin)["Asistencia"]
    hoja = zin.read(parte).decode("utf8")
    for r, m in marcas.items():
        ref = f"{col}{int(r)}"
        mm = re.search(r'<c r="%s"((?:\s[^>]*?)?)(?:/>|>.*?</c>)' % ref, hoja, re.S)
        if not mm:
            raise SystemExit(f"No existe la celda {ref} en el XML de la hoja.")
        attrs = re.sub(r'\st="[^"]*"', "", mm.group(1))
        nueva = f'<c r="{ref}"{attrs}/>' if m is None else f'<c r="{ref}"{attrs}><v>{int(m)}</v></c>'
        hoja = hoja[:mm.start()] + nueva + hoja[mm.end():]
    wb = zin.read("xl/workbook.xml").decode("utf8")
    if "fullCalcOnLoad" not in wb:
        wb = re.sub(r"<calcPr([^>]*?)/>", r'<calcPr\1 fullCalcOnLoad="1"/>', wb)
    cambios, partes = {parte: hoja, "xl/workbook.xml": wb}, _partes(zin)
    if cq:
        _sincronizar_cronograma(zin, partes, cq, cambios)
    nuevos = _hoja_alias(zin, cambios) if "Alias Teams" not in partes else {}
    if str(origen) != str(destino):
        shutil.copy(origen, destino)
    _zip(zin, destino, cambios, nuevos)
    _refrescar_cache(destino)
    return clase


def _refrescar_cache(ruta):
    """Excel Online recalcula al leer (el flujo del sitio lee así), pero quien abra el archivo sin recalcular vería cuentas viejas:
    con LibreOffice se actualizan; sin él se avisa y el libro queda con fullCalcOnLoad."""
    if not shutil.which("soffice"):
        print("Aviso: sin LibreOffice no se refresca el caché de las fórmulas; Excel recalcula al abrir.", file=sys.stderr)
        return
    td = tempfile.mkdtemp()
    try:
        z = zipfile.ZipFile(ruta)
        sin_cache = {p: re.sub(r"(</f>|<f[^>]*?/>)<v>.*?</v>", r"\1", z.read(p).decode("utf8"), flags=re.S)
                     for p in z.namelist() if p.startswith("xl/worksheets/sheet") and p.endswith(".xml")}
        _zip(z, os.path.join(td, "t.xlsx"), sin_cache)
        subprocess.run(["soffice", "--headless", "--convert-to", "xlsx", "--outdir", os.path.join(td, "out"), os.path.join(td, "t.xlsx")],
                       capture_output=True, timeout=150)
        calc = openpyxl.load_workbook(os.path.join(td, "out", "t.xlsx"), data_only=True)
        zin, cambios = zipfile.ZipFile(ruta), {}
        partes = _partes(zin)
        for nombre in HOJAS:
            parte = partes[nombre]
            xml, ws = zin.read(parte).decode("utf8"), calc[nombre]

            def arreglar(m):
                ref, attrs, f = m.group(1), re.sub(r'\st="[^"]*"', "", m.group(2)), m.group(3)
                v = ws[ref].value
                if isinstance(v, datetime.datetime):
                    v = (v - datetime.datetime(1899, 12, 30)).days
                if isinstance(v, bool):
                    return f'<c r="{ref}"{attrs} t="b">{f}<v>{int(v)}</v></c>'
                if isinstance(v, (int, float)):
                    return f'<c r="{ref}"{attrs}>{f}<v>{repr(float(v)) if isinstance(v, float) and v != int(v) else int(v)}</v></c>'
                s = "" if v is None else str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                return f'<c r="{ref}"{attrs} t="str">{f}<v>{s}</v></c>'
            cambios[parte] = re.sub(r'<c r="([A-Z]+\d+)"([^>]*)>(<f[^>]*?(?:/>|>.*?</f>))(?:<v>.*?</v>)?</c>', arreglar, xml, flags=re.S)
        _zip(zin, ruta, cambios)
    finally:
        shutil.rmtree(td, ignore_errors=True)


def main(argv):
    uso = __doc__.split("Uso", 1)[1].split("Alias", 1)[0]
    if len(argv) < 3:
        raise SystemExit("Uso" + uso)
    cuadro = None
    if "--cuadro" in argv:
        i = argv.index("--cuadro")
        cuadro, argv = argv[i + 1], argv[:i] + argv[i + 2:]
    cmd = argv[1]
    if cmd == "libro":
        salida = leer_libro(argv[2], cuadro)
    elif cmd == "calcular":
        libro = leer_libro(argv[3], cuadro)
        extra = json.load(open(argv[4], encoding="utf8")) if len(argv) > 4 and os.path.exists(argv[4]) else {}
        salida = calcular(argv[2], libro["estudiantes"], unir_alias(libro["alias"], extra))
        salida["avisos_alias"] = libro["avisos_alias"]
    elif cmd == "escribir":
        marcas = {int(k): v for k, v in json.load(open(argv[5], encoding="utf8")).items()}
        salida = escribir_marcas(argv[2], argv[3], argv[4], marcas, cuadro)
    else:
        raise SystemExit("Uso" + uso)
    print(json.dumps(salida, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main(sys.argv)
