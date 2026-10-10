"""Fechas y horas en español de Colombia, para los correos y avisos generados desde GitHub."""
from datetime import date, datetime

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def fecha_larga(iso):
    d = date.fromisoformat(iso)
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}"


def hora12(iso):
    """'2026-10-13T18:00:00-05:00' a '6:00 p. m.'"""
    t = datetime.fromisoformat(iso)
    h = t.hour % 12 or 12
    return f"{h}:{t.minute:02d} {'a. m.' if t.hour < 12 else 'p. m.'}"


def horario(clase):
    return f"{hora12(clase['inicio'])} a {hora12(clase['fin'])}"


def lista_y(items):
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " y " + items[-1]
