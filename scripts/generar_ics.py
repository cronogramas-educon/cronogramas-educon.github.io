"""Genera cronograma.ics (RFC 5545) desde el dict de data.json."""
import re

VTIMEZONE = [
    "BEGIN:VTIMEZONE", "TZID:America/Bogota",
    "BEGIN:STANDARD", "DTSTART:19700101T000000", "TZOFFSETFROM:-0500", "TZOFFSETTO:-0500", "TZNAME:-05", "END:STANDARD",
    "END:VTIMEZONE",
]


def escapar(s):
    return re.sub(r"([,;\\])", r"\\\1", s.replace("\r\n", "\n")).replace("\n", "\\n")


def plegar(linea):
    """Plegado a 75 octetos sin partir caracteres UTF-8."""
    if len(linea.encode()) <= 75:
        return linea
    partes, actual, n = [], "", 0
    for ch in linea:
        b = len(ch.encode())
        if n + b > (75 if not partes else 74):  # las continuaciones llevan un espacio inicial
            partes.append(actual)
            actual, n = "", 0
        actual += ch
        n += b
    partes.append(actual)
    return "\r\n ".join(partes)


def evento(c, cfg, stamp):
    h = cfg["horario"]
    dia = c["fecha"].replace("-", "")
    nombre = c["clase"].title()
    desc = [c["unidad"], "", "Tema:"] + [f"- {p}" for p in c["temaPuntos"]] + ["", f"Docente: {c['profesor']}"]
    if c["asistentePat"]:
        desc.append(f"Asistente PAT: {c['asistentePat']}")
    url = c["linkTeams"] if cfg.get("mostrarLinksTeams", True) and c["linkTeams"] else ""
    if url:
        desc += ["", f"Unirme en Teams: {url}"]
    lineas = [
        "BEGIN:VEVENT", f"UID:clase-{c['id']:02d}@{cfg['uidSufijo']}", f"DTSTAMP:{stamp}",
        f"SEQUENCE:{c.get('secuencia', 0)}",
        f"DTSTART;TZID=America/Bogota:{dia}T{h['inicio'].replace(':', '')}00",
        f"DTEND;TZID=America/Bogota:{dia}T{h['fin'].replace(':', '')}00",
        f"SUMMARY:{escapar(nombre)}: {escapar(cfg['programaCorto'])}",
        f"DESCRIPTION:{escapar(chr(10).join(desc))}", "LOCATION:Microsoft Teams",
    ]
    if url:
        lineas.append(f"URL:{url}")
    lineas += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{escapar(nombre)} comienza en 30 minutos",
               "TRIGGER:-PT30M", "END:VALARM", "END:VEVENT"]
    return lineas


def generar(datos, cfg):
    stamp = datos["meta"]["generadoEn"].replace("-", "").replace(":", "")
    lineas = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Cronograma Compliance//ES", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
              f"X-WR-CALNAME:{escapar(cfg['programaCorto'])} {escapar(cfg['cohorte'])}", "X-WR-TIMEZONE:America/Bogota"]
    lineas += VTIMEZONE
    for c in datos["clases"]:
        lineas += evento(c, cfg, stamp)
    lineas.append("END:VCALENDAR")
    return "\r\n".join(plegar(l) for l in lineas) + "\r\n"
