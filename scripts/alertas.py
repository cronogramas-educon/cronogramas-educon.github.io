#!/usr/bin/env python3
"""Alertas del día anterior: qué le falta a las clases de mañana, choques y Excel con error.

Uso: python scripts/alertas.py [--fecha AAAA-MM-DD] [--semana] [--html alerta.html]  (--semana revisa los próximos 7 días)
Escribe un cuerpo en HTML (para el correo) y deja en GITHUB_OUTPUT: hay=true|false y titulo. No envía nada: lo envía el workflow solo si está activado.
El texto se publica en una incidencia del repositorio (público): solo lleva nombres de cursos, clases, fechas y qué falta. Nunca docentes, enlaces ni datos de contacto.
"""
import json, os, sys
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cursos as cu
from textos import fecha_larga, horario, lista_y

RAIZ = cu.RAIZ
BOGOTA = timezone(timedelta(hours=-5))
INSTITUCIONAL = {"sabana"}
SEGUIR = ("Perdió el mínimo", "En riesgo", "Atención")


def _json(ruta):
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


def calcular(raiz=RAIZ, hoy=None, incluir_pat=False, dias=1):
    """Alertas para las clases de mañana (o de los próximos `dias` días): {'fecha', 'hasta', 'faltantes', 'choques', 'errores'}."""
    raiz = Path(raiz)
    hoy = hoy or datetime.now(BOGOTA).date()
    manana = (hoy + timedelta(days=1)).isoformat()
    hasta = (hoy + timedelta(days=dias)).isoformat()
    reg = cu.registro(raiz)
    pedir_enlace = reg["global"].get("mostrarLinksTeams", True)
    faltantes, errores, por_persona = [], [], {}
    for c in reg["cursos"]:
        nombre = cu.con_tipo(c["programaCorto"], c["tipo"])
        err = _json(raiz / "cursos" / c["id"] / "estado/error.json")
        if err:
            errores.append({"curso": nombre, "mensaje": err.get("mensaje", "El Excel no se pudo leer")})
        d = _json(raiz / "cursos" / c["id"] / "data/data.json")
        for cl in (d or {"clases": []})["clases"]:
            if not manana <= cl["fecha"] <= hasta:
                continue
            falta = [x for x, hay in (("el docente", bool(cl["profesores"])), ("el enlace de Teams", bool(cl["linkTeams"]) or not pedir_enlace),
                                      ("el asistente PAT", bool(cl["asistentePat"]) or not incluir_pat)) if not hay]
            if falta:
                faltantes.append({"curso": nombre, "clase": cl["clase"].capitalize(), "horario": horario(cl), "falta": falta, "fecha": cl["fecha"]})
            gente = [("docente", p) for p in cl["profesores"]] + ([("asistente PAT", cl["asistentePat"])] if cl["asistentePat"] else [])
            for rol, p in gente:
                k = (rol, " ".join(p.casefold().split()))
                if k[1] not in INSTITUCIONAL:
                    por_persona.setdefault(k, []).append((cl, nombre, p))
    choques = []
    for (rol, _), lista in por_persona.items():
        lista.sort(key=lambda x: x[0]["inicio"])
        previo = lista[0]
        for x in lista[1:]:
            if datetime.fromisoformat(x[0]["inicio"]) < datetime.fromisoformat(previo[0]["fin"]):
                choques.append({"rol": rol, "nombre": x[2], "a": f"{previo[1]} ({horario(previo[0])})", "b": f"{x[1]} ({horario(x[0])})"})
            if datetime.fromisoformat(x[0]["fin"]) > datetime.fromisoformat(previo[0]["fin"]):
                previo = x
    asistencia = _asistencia(raiz, reg, hoy, con_seguimiento=dias > 1)
    reg_estado = _json(raiz / "estado/registro.json")
    if reg_estado and reg_estado.get("error"):
        errores.append({"curso": "Excel Registro de cursos", "mensaje": reg_estado["error"]})
    semana, terminan = _semana(raiz, reg, hoy) if dias > 1 else ([], [])
    return {"fecha": manana, "hasta": hasta, "faltantes": faltantes, "choques": choques, "errores": errores, "asistencia": asistencia, "semana": semana, "terminan": terminan}


def _semana(raiz, reg, hoy, dias_aviso=14):
    """Resumen de la semana: clases de los próximos 7 días por curso (solo curso, clase, fecha y hora) y cursos que terminan en los próximos `dias_aviso` días.
    Nunca docentes ni enlaces: el texto se publica en una incidencia de un repositorio público."""
    manana, hasta, limite = (hoy + timedelta(days=1)).isoformat(), (hoy + timedelta(days=7)).isoformat(), (hoy + timedelta(days=dias_aviso)).isoformat()
    semana, terminan = [], []
    for c in reg["cursos"]:
        d = _json(raiz / "cursos" / c["id"] / "data/data.json")
        if not d or not d["clases"]:
            continue
        nombre = cu.con_tipo(c["programaCorto"], c["tipo"])
        proximas = [cl for cl in d["clases"] if manana <= cl["fecha"] <= hasta]
        if proximas:
            semana.append({"curso": nombre, "clases": [{"clase": cl["clase"].capitalize(), "fecha": cl["fecha"], "horario": horario(cl)} for cl in sorted(proximas, key=lambda x: x["inicio"])]})
        fin = max(cl["fecha"] for cl in d["clases"])
        if manana <= fin <= limite:
            terminan.append({"curso": nombre, "fin": fin, "quedan": sum(1 for cl in d["clases"] if cl["fecha"] >= manana)})
    terminan.sort(key=lambda x: x["fin"])
    return semana, terminan


def _asistencia(raiz, reg, hoy, con_seguimiento):
    """Por curso con Excel de asistencia: clases ya pasadas sin asistencia marcada (siempre) y, en la revisión semanal, quién está por perder.
    Solo número de lista y estado: nunca nombres."""
    out = []
    for c in reg["cursos"]:
        a = _json(raiz / "cursos" / c["id"] / "estado/asistencia.json")
        d = _json(raiz / "cursos" / c["id"] / "data/data.json")
        if not a or not d:
            continue
        dictadas = {x["clase"] for x in a["porClase"] if x["estado"] == "Dictada"}
        sin = [{"clase": cl["id"], "fecha": cl["fecha"]} for cl in d["clases"] if cl["fecha"] < hoy.isoformat() and cl["id"] not in dictadas]
        seguir = [{"n": x["n"], "estado": x["estado"], "quedan": max(x["quedan"], 0)} for x in a["lista"] if x["estado"] in SEGUIR] if con_seguimiento else []
        if sin or seguir:
            out.append({"curso": cu.con_tipo(c["programaCorto"], c["tipo"]), "sinRegistrar": sin, "seguimiento": seguir})
    return out


def hay(a):
    return semanal(a) or bool(a["faltantes"] or a["choques"] or a["errores"] or a["asistencia"])  # el resumen del lunes sale siempre


def semanal(a):
    return a["hasta"] != a["fecha"]


def titulo(a):
    if semanal(a):
        return f"Resumen semanal de cronogramas, del {fecha_larga(a['fecha'])} al {fecha_larga(a['hasta'])}"
    return f"Alerta de cronogramas: clases del {fecha_larga(a['fecha'])}"


def html(a):
    e = escape
    cuando = f"los próximos días, <strong>del {e(fecha_larga(a['fecha']))} al {e(fecha_larga(a['hasta']))}</strong>" if semanal(a) else f"<strong>mañana, {e(fecha_larga(a['fecha']))}</strong>"
    partes = [f"<p>Este es el resumen de {cuando}.</p>" if semanal(a) else f"<p>Estas son las alertas para las clases de {cuando}.</p>"]
    if semanal(a):
        partes.append("<h3>Clases de la semana</h3>" + ("<ul>" + "".join(
            f"<li><strong>{e(x['curso'])}</strong>, {len(x['clases'])} {'clase' if len(x['clases']) == 1 else 'clases'}: " + e("; ".join(f"{y['clase']}, {fecha_larga(y['fecha'])}, {y['horario']}" for y in x["clases"])) + ".</li>" for x in a["semana"]) + "</ul>"
            if a["semana"] else "<p>No hay clases programadas esta semana.</p>"))
        if a["terminan"]:
            partes.append("<h3>Cursos que terminan pronto</h3><ul>" + "".join(
                f"<li><strong>{e(x['curso'])}</strong> termina el {e(fecha_larga(x['fin']))} (quedan {x['quedan']} {'clase' if x['quedan'] == 1 else 'clases'}). Conviene preparar certificados y encuesta.</li>" for x in a["terminan"]) + "</ul>")
        partes.append("<h3>Pendientes</h3>" + ("" if (a["faltantes"] or a["choques"] or a["errores"] or a["asistencia"]) else "<p>Nada pendiente: las clases de la semana tienen sus datos y no hay choques ni Excel con error.</p>"))
    if a["faltantes"]:
        partes.append("<h3>Falta confirmar</h3><ul>" + "".join(
            f"<li><strong>{e(x['curso'])}</strong>, {e(x['clase'])}{(' del ' + e(fecha_larga(x['fecha']))) if semanal(a) else ''} ({e(x['horario'])}): falta {e(lista_y(x['falta']))}.</li>" for x in a["faltantes"]) + "</ul>")
    if a["choques"]:
        partes.append("<h3>Dos clases a la vez</h3><ul>" + "".join(
            f"<li>El {e(x['rol'])} <strong>{e(x['nombre'])}</strong> tiene {e(x['a'])} y {e(x['b'])}.</li>" for x in a["choques"]) + "</ul>")
    if a["asistencia"]:
        items = []
        for x in a["asistencia"]:
            if x["sinRegistrar"]:
                items.append(f"<li><strong>{e(x['curso'])}</strong>: sin asistencia marcada en " + e(lista_y([f"la clase {y['clase']} ({fecha_larga(y['fecha'])})" for y in x["sinRegistrar"]])) + ". Si se reprogramó, cambia la fecha en el Excel del curso.</li>")
            if x["seguimiento"]:
                items.append(f"<li><strong>{e(x['curso'])}</strong>, estudiantes a quienes conviene escribirles: " + e(lista_y([f"Estudiante {y['n']} ({y['estado'].lower()}, le quedan {y['quedan']} {'falta' if y['quedan'] == 1 else 'faltas'})" for y in x["seguimiento"]])) + ". El nombre está en el Excel de asistencia.</li>")
        partes.append("<h3>Asistencia</h3><ul>" + "".join(items) + "</ul>")
    if a["errores"]:
        partes.append("<h3>Excel que no se pudo leer</h3><ul>" + "".join(
            f"<li><strong>{e(x['curso'])}</strong>: {e(x['mensaje'])}. Se conserva la última versión buena.</li>" for x in a["errores"]) + "</ul>")
    partes.append("<p>Para corregirlo, abre el Excel del curso en SharePoint y guárdalo: la página se actualiza sola en un par de minutos. Este mensaje se genera automáticamente.</p>")
    return "\n".join(partes)


def main(argv):
    fecha = argv[argv.index("--fecha") + 1] if "--fecha" in argv else None
    salida = argv[argv.index("--html") + 1] if "--html" in argv else "alerta.html"
    hoy = date.fromisoformat(fecha) - timedelta(days=1) if fecha else None  # --fecha es el día de las clases
    a = calcular(hoy=hoy, dias=7 if "--semana" in argv else 1)
    Path(salida).write_text(html(a), encoding="utf-8")
    print(titulo(a) + "\n" + (f"{len(a['faltantes'])} clases con datos por confirmar, {len(a['choques'])} choques, {len(a['errores'])} Excel con error, {len(a['asistencia'])} cursos con asistencia por atender." if hay(a) else "Sin alertas para mañana."))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as o:
            o.write(f"hay={'true' if hay(a) else 'false'}\ntitulo={titulo(a)}\n")


if __name__ == "__main__":
    main(sys.argv[1:])
