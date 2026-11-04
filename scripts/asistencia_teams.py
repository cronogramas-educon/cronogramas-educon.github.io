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

Alias (todo opcional): {"correos": {"NOMBRE COMPLETO": ["a@x.com"]}, "nombres": {"cuenta de teams": "NOMBRE COMPLETO"},
"no_matriculados": ["Nombre de un profesor u organizador"]}. "NOMBRE COMPLETO" es el de la columna C del libro.
"""
import csv, datetime, io, json, os, re, shutil, subprocess, sys, tempfile, unicodedata, zipfile
from collections import defaultdict

import openpyxl
from openpyxl.utils import get_column_letter, column_index_from_string

MINIMO, REVISION, RELEVANTE = 0.5, 0.4, 0.2
HOJAS = {"Asistencia": "xl/worksheets/sheet2.xml", "Resumen": "xl/worksheets/sheet3.xml"}


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
        if _norm(cuenta).strip() == clave and est in estudiantes:
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
    resumen, tramos = leer_reporte(ruta_reporte)
    total = _duracion(resumen["Meeting duration"])
    fecha = _fecha_hora(resumen["Start time"]).date()
    por_est, otros = defaultdict(lambda: {"iv": [], "cuentas": set(), "como": set()}), defaultdict(list)
    for f in tramos:
        a, b = _fecha_hora(f[1]), _fecha_hora(f[2])
        est, como = emparejar(f[0], f[4] if len(f) > 4 else "", estudiantes, alias)
        if est:
            x = por_est[est]
            x["iv"].append((a, b)); x["cuentas"].add(f[0].strip()); x["como"].add(como)
        else:
            otros[f[0].strip()].append((a, b))
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


def leer_libro(ruta):
    wb = openpyxl.load_workbook(ruta, data_only=True)
    ws = wb["Asistencia"]
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
    return {"clases": clases, "estudiantes": est, "sin_cedula": len(est) - cedulas}


def _columna(libro, fecha):
    """fecha = 'AAAA-MM-DD', o 'AAAA-MM-DD#N' para elegir la clase N cuando hay dos clases el mismo día."""
    fecha, _, n = fecha.partition("#")
    cs = [c for c in libro["clases"] if c["fecha"] == fecha and (not n or c["n"] == int(n))]
    if not cs:
        raise SystemExit(f"No hay una clase con fecha {fecha} en la fila 5. No inventes columna: avisa al usuario.")
    if len(cs) > 1:
        raise SystemExit(f"Hay {len(cs)} clases con la fecha {fecha} ({', '.join('Clase %d' % c['n'] for c in cs)}): decide a cuál va.")
    return cs[0]


def _zip(zin, destino, cambios):
    destino = str(destino)
    tmp = destino + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for it in zin.infolist():
            datos = cambios[it.filename].encode("utf8") if it.filename in cambios else zin.read(it.filename)
            zout.writestr(it, datos, compress_type=zipfile.ZIP_DEFLATED)
    os.replace(tmp, destino)


def escribir_marcas(origen, destino, fecha, marcas):
    """Parchea solo el XML de las celdas de la clase de esa fecha (no usa openpyxl para guardar: la tabla, los comentarios
    y los estilos deben quedar intactos). marcas = {fila: 1|0|None}. Se detiene si la columna ya tiene marcas."""
    libro = leer_libro(origen)
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
    hoja = zin.read(HOJAS["Asistencia"]).decode("utf8")
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
    if str(origen) != str(destino):
        shutil.copy(origen, destino)
    _zip(zin, destino, {HOJAS["Asistencia"]: hoja, "xl/workbook.xml": wb})
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
        for nombre, parte in HOJAS.items():
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
    cmd = argv[1]
    if cmd == "libro":
        salida = leer_libro(argv[2])
    elif cmd == "calcular":
        libro = leer_libro(argv[3])
        alias = json.load(open(argv[4], encoding="utf8")) if len(argv) > 4 and os.path.exists(argv[4]) else {}
        salida = calcular(argv[2], libro["estudiantes"], alias)
    elif cmd == "escribir":
        marcas = {int(k): v for k, v in json.load(open(argv[5], encoding="utf8")).items()}
        salida = escribir_marcas(argv[2], argv[3], argv[4], marcas)
    else:
        raise SystemExit("Uso" + uso)
    print(json.dumps(salida, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main(sys.argv)
