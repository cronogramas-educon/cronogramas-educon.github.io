#!/usr/bin/env python3
"""Registro de cursos, resolución de carpetas de SharePoint y armado del sitio multicurso.

Uso:
  python scripts/cursos.py resolver "<ruta de la carpeta en SharePoint>"   imprime el id del curso (código 3 si no está registrado)
  python scripts/cursos.py sincronizar                                      escribe cursos/<id>/config/contenido.json desde config/cursos.json
  python scripts/cursos.py sitio SALIDA [VERSION]                           arma el sitio publicable en SALIDA
  python scripts/cursos.py recibir EVENTO                                   lee el aviso de Power Automate y escribe fuente.json y las salidas del workflow
  python scripts/cursos.py registro fuente.json                             fusiona el Excel "Registro de cursos" en config/cursos.json
  python scripts/cursos.py sinregistrar EVENTO                              anota la carpeta de un Excel que no está en el registro
"""
import json, os, re, secrets, shutil, string, sys, unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, unquote

RAIZ = Path(__file__).resolve().parent.parent
CAMPOS_CURSO = ("programa", "programaCorto", "tipo", "marca", "modalidad", "urlPaginaOficial", "periodo", "cohorte")


def registro(raiz=RAIZ):
    return json.loads((Path(raiz) / "config/cursos.json").read_text(encoding="utf-8"))


def sitio_ruta(c):
    """Carpeta pública del curso: el código aleatorio evita que alguien adivine la dirección."""
    return f"c/{c['id']}-{c['codigo']}"


def _norm(s):
    return unicodedata.normalize("NFC", unquote(s)).casefold().replace("\\", "/").strip("/")


def resolver(ruta, reg=None):
    """Id del curso cuya carpeta aparece como tramo completo de la ruta, o None. Elige la coincidencia más específica."""
    reg = reg or registro()
    ruta = "/" + _norm(ruta) + "/"
    mejor = None
    for c in reg["cursos"]:
        if "/" + _norm(c["carpeta"]) + "/" in ruta and (mejor is None or len(c["carpeta"]) > len(mejor["carpeta"])):
            mejor = c
    return mejor["id"] if mejor else None


def base_sharepoint(carpeta, g):
    """Los cursos nuevos viven en el sitio EduContinua (carpetas 'EduContinua 2026-2/...'); los anteriores, en el sitio Especializaciones."""
    nuevo = g.get("sharepointBaseEduContinua")
    return nuevo if nuevo and re.match(r"educontinua \d", carpeta.casefold()) else g["sharepointBase"]


def con_tipo(nombre, tipo):
    """'Derecho Laboral' + 'Diplomado' da 'Diplomado Derecho Laboral', para que nunca se confunda un curso con un diplomado. No duplica el tipo."""
    return nombre if _norm(nombre).startswith(_norm(tipo)) else f"{tipo} {nombre}"


def config_curso(c, g):
    h = dict(c["horario"], zona=g["zona"], desfase=g["desfase"])
    cfg = {k: c[k] for k in CAMPOS_CURSO if k in c}
    for k in ("programa", "programaCorto"):
        cfg[k] = con_tipo(c[k], c["tipo"])
    cfg.update(universidad=g["universidad"], facultad=g["facultad"], horario=h, uidSufijo=f"cronograma-{c['id']}",
               mostrarLinksTeams=g["mostrarLinksTeams"], diasAvisoCambio=g["diasAvisoCambio"],
               profesoresInstitucionales=g["profesoresInstitucionales"], siglas=g["siglas"], id=c["id"])
    return cfg


def sincronizar(raiz=RAIZ):
    reg = registro(raiz)
    for c in reg["cursos"]:
        ruta = Path(raiz) / "cursos" / c["id"] / "config/contenido.json"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(config_curso(c, reg["global"]), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ---- Excel "Registro de cursos": una fila por curso, lo edita el equipo sin tocar GitHub ----

COLUMNAS = {"periodo": "periodo", "carpetadelperiodo": "carpetaPeriodo", "cohorte": "cohorte", "carpetadelcurso": "carpetaCurso", "tipo": "tipo",
            "nombredelcurso": "programaCorto", "nombrecompleto": "programa", "modalidad": "modalidad", "horadeinicio": "inicio",
            "horadefin": "fin", "iniciodelsabado": "sabado", "paginaoficial": "urlPaginaOficial", "grupodeteams": "enlaceTeams"}
ETIQUETA = {"programaCorto": "Nombre del curso", "inicio": "Hora de inicio", "periodo": "Periodo"}


def _clave(h):
    """Encabezado del Excel Online ("Hora_x0020_de_x0020_inicio", "Duraci_x00f3_n") a una clave sin tildes ni espacios."""
    h = re.sub(r"_x([0-9a-fA-F]{4})_", lambda m: chr(int(m.group(1), 16)), str(h))
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", h).casefold().encode("ascii", "ignore").decode())


def es_registro(filas):
    # basta una de las dos columnas de carpeta: si alguien daña un encabezado, igual se trata como registro y se avisa
    return any(_clave(k) in ("carpetadelcurso", "carpetadelperiodo") for f in filas if isinstance(f, dict) for k in f)


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFD", s).casefold().encode("ascii", "ignore").decode()).strip("-")


def _hhmm(v):
    """'18:00', '6:00 PM', 18 o la fracción de día que entrega Excel (0.75) a 'HH:MM'. None si está vacío."""
    if v in (None, ""):
        return None
    t = str(v).strip().lower()
    try:
        x = float(t.replace(",", "."))
        if 0 <= x < 1:
            m = round(x * 1440)
            return f"{m // 60:02d}:{m % 60:02d}"
    except ValueError:
        pass
    m = re.fullmatch(r"(\d{1,2})(?:[:.h](\d{2}))?\s*(a|p)?\.?\s*m?\.?", t)
    if not m:
        raise ValueError(f"la hora '{v}' no se entiende, escribe por ejemplo 18:00")
    h, mi = int(m[1]), int(m[2] or 0)
    if m[3] == "p" and h < 12:
        h += 12
    if m[3] == "a" and h == 12:
        h = 0
    if h > 23 or mi > 59:
        raise ValueError(f"la hora '{v}' no es válida")
    return f"{h:02d}:{mi:02d}"


def parse_equipo(enlace):
    """Del enlace 'Obtener vínculo al equipo' de Teams saca el equipo y el canal General: {'equipo': guid, 'canal': '19:...@thread.tacv2'}."""
    from urllib.parse import parse_qs, urlparse
    u = urlparse(str(enlace).strip())
    partes = [p for p in u.path.split("/") if p]
    equipo = (parse_qs(u.query).get("groupId") or [""])[0]
    canal = unquote(partes[partes.index("team") + 1]) if "team" in partes and partes.index("team") + 1 < len(partes) else ""
    if "teams" not in (u.hostname or "") or not re.fullmatch(r"[0-9a-f-]{36}", equipo) or not re.fullmatch(r"19:[\w.-]+@thread\.[a-z0-9]+", canal):
        raise ValueError("el enlace del grupo de Teams no se entiende: usa 'Obtener vínculo al equipo' en Teams")
    return {"equipo": equipo, "canal": canal}


def _fila(f):
    d = {}
    for k, v in f.items():
        n = COLUMNAS.get(_clave(k))
        if n and v not in (None, ""):
            d[n] = v if isinstance(v, (int, float)) else str(v).strip()
    return d


def _horario(d, previo):
    """Sin 'Hora de inicio' se conserva el horario que ya tenía. Sin 'Hora de fin' el fin se calcula con las horas de cada clase."""
    if "inicio" not in d:
        return previo
    h = {"inicio": _hhmm(d["inicio"])}
    fin = _hhmm(d.get("fin"))
    if fin:
        h["fin"] = fin
    else:
        h = {"modo": "porHoras", "inicio": h["inicio"], "duracionPorDefecto": (previo or {}).get("duracionPorDefecto", 1)}
        if d.get("sabado"):
            h["porDia"] = {"Sábado": _hhmm(d["sabado"])}
    return h


def fusionar(reg, filas):
    """Aplica las filas del Excel de registro sobre el registro. Nunca borra cursos ni cambia códigos. Devuelve (avisos, cambios)."""
    cursos = reg["cursos"]
    por = {_norm(c["carpeta"]): c for c in cursos}
    codigos = {c["codigo"] for c in cursos} | {reg["global"]["adminCodigo"]}
    ids = {c["id"] for c in cursos}
    avisos, cambios, vistas = [], [], set()
    for n, f in enumerate(filas, 2):  # el encabezado es la fila 1 de la hoja
        d = _fila(f)
        if not d:
            continue
        if not (d.get("carpetaPeriodo") and d.get("carpetaCurso")):
            avisos.append(f"Fila {n}: falta la carpeta del periodo o la carpeta del curso. No se procesó.")
            continue
        # un periodo puede abrir los mismos cursos varias veces: cada apertura es una cohorte, una carpeta dentro del periodo
        carpeta = "/".join(x.strip("/") for x in (d["carpetaPeriodo"], d.get("cohorte", ""), d["carpetaCurso"]) if x)
        llave = _norm(carpeta)
        if llave in vistas:
            avisos.append(f"Fila {n}: la carpeta {carpeta} está repetida. Se usó solo la primera.")
            continue
        vistas.add(llave)
        c = por.get(llave)
        try:
            h = _horario(d, c and c["horario"])
        except ValueError as e:
            avisos.append(f"Fila {n}: {e}. No se procesó.")
            continue
        if "tipo" in d:
            d["tipo"] = d["tipo"].capitalize()
        equipo = None
        if "enlaceTeams" in d:
            try:
                equipo = parse_equipo(d["enlaceTeams"])
            except ValueError as e:
                avisos.append(f"Fila {n}: {e}. El resto de la fila sí se procesó.")
        if c is None:
            falta = [ETIQUETA[k] for k in ("programaCorto", "inicio", "periodo") if k not in d]
            if falta:
                avisos.append(f"Fila {n}: falta {', '.join(falta)}. El curso nuevo no se creó.")
                continue
            base = "-".join(x for x in (_slug(d["programaCorto"]), _slug(d["periodo"]), _slug(d.get("cohorte", ""))) if x)
            i, k = base, 2
            while i in ids:
                i, k = f"{base}-{k}", k + 1
            cod = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
            while cod in codigos:
                cod = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
            c = {"id": i, "codigo": cod, "carpeta": carpeta, "tipo": d.get("tipo", "Curso"), "programa": d.get("programa", d["programaCorto"]),
                 "programaCorto": d["programaCorto"], "modalidad": d.get("modalidad", "Por confirmar"),
                 "urlPaginaOficial": d.get("urlPaginaOficial", ""), "periodo": d["periodo"], "horario": h}
            if d.get("cohorte"):
                c["cohorte"] = d["cohorte"]
            if equipo:
                c["teams"] = equipo
            cursos.append(c)
            ids.add(i); codigos.add(cod); por[llave] = c
            cambios.append(f"Curso nuevo: {c['programaCorto']} ({c['periodo']})")
            continue
        for k in ("tipo", "programa", "programaCorto", "modalidad", "urlPaginaOficial", "periodo", "cohorte"):
            if k in d and c.get(k) != d[k]:
                c[k] = d[k]
                cambios.append(f"{c['programaCorto']}: cambió {k}")
        if equipo and c.get("teams") != equipo:
            c["teams"] = equipo
            cambios.append(f"{c['programaCorto']}: cambió el grupo de Teams")
        if h != c["horario"]:
            c["horario"] = h
            cambios.append(f"{c['programaCorto']}: cambió el horario")
    return avisos, cambios


def _ahora():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _guardar_json(ruta, datos):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def aplicar_registro(fuente, raiz=RAIZ):
    """Fusiona el Excel de registro, sincroniza la configuración de cada curso y deja el resultado en estado/registro.json."""
    raiz = Path(raiz)
    est = raiz / "estado/registro.json"
    try:
        filas = json.loads(Path(fuente).read_text(encoding="utf-8"))
        if not isinstance(filas, list) or not es_registro(filas):
            raise ValueError("El Excel de registro debe tener una tabla con la columna 'Carpeta del curso'")
        reg = registro(raiz)
        avisos, cambios = fusionar(reg, filas)
    except Exception as e:  # el último registro bueno se conserva y el sitio base muestra el error
        _guardar_json(est, {"error": str(e), "avisos": [], "actualizado": _ahora()})
        raise
    _guardar_json(raiz / "config/cursos.json", reg)
    sincronizar(raiz)
    _guardar_json(est, {"error": None, "avisos": avisos, "actualizado": _ahora()})
    return avisos, cambios


def carpeta_de_ruta(ruta):
    """Del ruta completa de SharePoint deja desde la carpeta 'EDU CONTINUA ...' en adelante."""
    partes = [p for p in unicodedata.normalize("NFC", unquote(ruta)).replace("\\", "/").split("/") if p]
    for i, p in enumerate(partes):
        if re.match(r"edu\s?continua(\s|$)", p.casefold()):
            return "/".join(partes[i:])
    return "/".join(partes)


def anotar_sin_registrar(ruta, raiz=RAIZ):
    arch = Path(raiz) / "estado/sin-registrar.json"
    lista = json.loads(arch.read_text(encoding="utf-8")) if arch.exists() else []
    carpeta = carpeta_de_ruta(ruta)
    lista = [x for x in lista if _norm(x["carpeta"]) != _norm(carpeta)] + [{"carpeta": carpeta, "visto": _ahora()}]
    _guardar_json(arch, lista[-30:])


def recibir(evento, fuente="fuente.json", salida=None):
    """Lee el aviso del flujo: escribe las filas en `fuente` y devuelve (tipo, curso, modificado): tipo registro, curso o ninguno."""
    p = json.loads(Path(evento).read_text(encoding="utf-8")).get("client_payload")
    if not p:
        sys.exit("::error::El evento no trae client_payload. Usa el evento excel-actualizado del flujo de Power Automate con la ruta y las filas.")
    filas = p.get("filas", p) if isinstance(p, dict) else p
    filas = json.loads(filas) if isinstance(filas, str) else filas
    Path(fuente).write_text(json.dumps(filas), encoding="utf-8")
    ruta = p.get("ruta", "") if isinstance(p, dict) else ""
    mod = p.get("modificado", "") if isinstance(p, dict) else ""
    curso = None
    if es_registro(filas):
        tipo = "registro"
    else:
        curso = resolver(ruta) if ruta else "compliance-anticorrupcion"  # el flujo anterior no mandaba ruta
        tipo = "curso" if curso else "ninguno"
        if not curso:
            print("::warning::La carpeta del Excel no está en el registro: no se actualiza ningún curso. Agrégala en el Excel Registro de cursos. Ruta recibida: " + ruta)
    if salida:
        with open(salida, "a") as o:
            o.write(f"tipo={tipo}\ncurso={curso or ''}\nmodificado={mod}\n")
    return tipo, curso, mod


def _html(plantilla, **v):
    s = Path(plantilla).read_text(encoding="utf-8")
    for k, x in v.items():
        s = s.replace(f"__{k}__", str(x))
    return s


def _esc(s):
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


def armar_sitio(salida, version="dev", raiz=RAIZ):
    raiz, salida = Path(raiz), Path(salida)
    reg = registro(raiz)
    g = reg["global"]
    if salida.exists():
        shutil.rmtree(salida)
    salida.mkdir(parents=True)
    for d in ("css", "js", "assets"):
        shutil.copytree(raiz / d, salida / d)
    (salida / ".nojekyll").touch()
    neutro = _html(raiz / "plantilla/raiz.html", V=version)
    (salida / "index.html").write_text(neutro, encoding="utf-8")
    (salida / "404.html").write_text(neutro, encoding="utf-8")
    resumen = []
    for c in reg["cursos"]:
        origen, destino = raiz / "cursos" / c["id"], salida / sitio_ruta(c)
        destino.mkdir(parents=True)
        for d in ("config", "data"):
            if (origen / d).exists():
                shutil.copytree(origen / d, destino / d)
        if (origen / "cronograma.ics").exists():
            shutil.copy(origen / "cronograma.ics", destino / "cronograma.ics")
        if (origen / "estado/error.json").exists():  # solo lo lee el sitio base de administración
            (destino / "estado").mkdir()
            shutil.copy(origen / "estado/error.json", destino / "estado/error.json")
        desc = f"Cuándo es tu próxima clase, quién la dicta y el enlace para entrar. {c['programa']}."
        (destino / "index.html").write_text(_html(
            raiz / "plantilla/curso.html", V=version, BASE="../../", ID=c["id"], NOMBRE=_esc(con_tipo(c["programaCorto"], c["tipo"])), DESC=_esc(desc)), encoding="utf-8")
        resumen.append({"id": c["id"], "periodo": c.get("periodo", ""), "cohorte": c.get("cohorte", ""), "ruta": sitio_ruta(c), "tieneDatos": (origen / "data/data.json").exists(),
                        "tieneError": (origen / "estado/error.json").exists(), "avisosTeams": bool(c.get("teams")), "programa": con_tipo(c["programa"], c["tipo"]), "programaCorto": con_tipo(c["programaCorto"], c["tipo"]), "tipo": c["tipo"],
                        "urlPaginaOficial": c.get("urlPaginaOficial", ""), "carpetaSharePoint": quote(f"{base_sharepoint(c['carpeta'], g)}/{c['carpeta']}", safe=":/")})
    hub = salida / "g" / g["adminCodigo"]
    hub.mkdir(parents=True)
    enlace = lambda carpeta: quote(f"{base_sharepoint(carpeta, g)}/{carpeta}", safe=":/")
    leer = lambda nombre, defecto: json.loads((raiz / "estado" / nombre).read_text(encoding="utf-8")) if (raiz / "estado" / nombre).exists() else defecto
    reciente = max(reg["cursos"], key=lambda c: c.get("periodo", ""))["carpeta"].split("/")[0] if reg["cursos"] else ""
    sin = [dict(x, enlace=enlace(x["carpeta"])) for x in leer("sin-registrar.json", []) if not resolver(x["carpeta"], reg)]
    meta = {"cursos": resumen, "sharepointBase": quote(g["sharepointBase"], safe=":/"), "carpetaActual": enlace(reciente), "nombreCarpetaActual": reciente,
            "sinRegistrar": sin, "formularioRegistro": g.get("formularioRegistro", ""), "registro": dict(leer("registro.json", {"error": None, "avisos": [], "actualizado": ""}), enlace=(quote(g["registroUrl"], safe=":/") if g.get("registroUrl") else enlace(g["registroRuta"]) if g.get("registroRuta") else "") + "?web=1")}
    (hub / "cursos.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    (hub / "index.html").write_text(_html(raiz / "plantilla/hub.html", V=version, BASE="../../"), encoding="utf-8")
    return salida


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "resolver":
        r = resolver(sys.argv[2])
        if not r:
            print("Curso no registrado", file=sys.stderr)
            sys.exit(3)
        print(r)
    elif cmd == "sincronizar":
        sincronizar()
    elif cmd == "recibir":
        recibir(sys.argv[2], salida=os.environ.get("GITHUB_OUTPUT"))
    elif cmd == "registro":
        avisos, cambios = aplicar_registro(sys.argv[2])
        print("\n".join(cambios) or "Sin cambios en el registro.")
        print("\n".join(f"::warning::{a}" for a in avisos))
    elif cmd == "sinregistrar":
        p = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8")).get("client_payload") or {}
        if isinstance(p, dict) and p.get("ruta"):
            anotar_sin_registrar(p["ruta"])
    elif cmd == "sitio":
        armar_sitio(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "dev")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
