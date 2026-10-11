#!/usr/bin/env python3
"""Asistencia de un curso, desde las filas de la tabla del Excel "Formato de asistencia" (ver generar_asistencia_xlsx.py).

El Excel manda: las cuentas y el estado de cada estudiante salen de sus columnas calculadas (Faltas, Faltas que le quedan, Estado...).
Aquí solo se resumen y se les quita el nombre y el documento: en el sitio el estudiante es "Estudiante N", con N su número de lista.
"""
import json, re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ESTADOS = ["Perdió el mínimo", "En riesgo", "Atención", "Al día", "Aprobó"]  # de más a menos urgente
BOGOTA = timezone(timedelta(hours=-5))
NOMBRE, REQUERIDAS = "Nombre del estudiante", ("Asistió", "Faltas", "Faltas que le quedan", "Estado")


def _clave(k):
    """Excel Online codifica los encabezados con símbolos: "N°" llega como "N_x00b0_" y "% hasta hoy" como "_x0025_ hasta hoy"."""
    return re.sub(r"_x([0-9a-fA-F]{4})_", lambda m: chr(int(m.group(1), 16)), str(k))


def normalizar(filas):
    return [{_clave(k): v for k, v in f.items()} if isinstance(f, dict) else f for f in filas] if isinstance(filas, list) else filas


def es_asistencia(filas):
    return isinstance(filas, list) and any(isinstance(f, dict) and NOMBRE in f and "Clase 1" in f for f in normalizar(filas))


def _num(v):
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    try:
        return float(str(v).strip().replace(",", ".").rstrip("%")) / (100 if str(v).strip().endswith("%") else 1)
    except ValueError:
        return None


def _ent(v):
    n = _num(v)
    return None if n is None else int(round(n))


def resumir(filas, ahora=None):
    """Resumen sin nombres. Lanza ValueError con un mensaje claro si el Excel no trae las columnas calculadas."""
    est = [f for f in normalizar(filas) if isinstance(f, dict) and str(f.get(NOMBRE) or "").strip()]
    if not est:
        raise ValueError("El Excel de asistencia no tiene estudiantes: escribe sus nombres en la hoja Asistencia.")
    falta = [c for c in REQUERIDAS if c not in est[0]]
    if falta:
        raise ValueError("Al Excel de asistencia le faltan columnas: " + ", ".join(falta) + ". No cambies los encabezados de las columnas grises.")
    claves = sorted((k for k in est[0] if re.fullmatch(r"Clase \d+", str(k))), key=lambda k: int(k.split()[1]))
    primero = est[0]
    permitidas = _ent(primero["Faltas que le quedan"]) + _ent(primero["Faltas"])
    programadas = _ent(primero.get("Clases programadas")) or len(claves)
    dictadas = (_ent(primero["Asistió"]) or 0) + (_ent(primero["Faltas"]) or 0) + (_ent(primero.get("Sin marcar")) or 0)
    lista, por_estado, asistio_t, faltas_t = [], {e: 0 for e in ESTADOS}, 0, 0
    for i, f in enumerate(est, 1):
        e = str(f["Estado"]).strip()
        a, fa = _ent(f["Asistió"]) or 0, _ent(f["Faltas"]) or 0
        asistio_t, faltas_t = asistio_t + a, faltas_t + fa
        por_estado[e] = por_estado.get(e, 0) + 1
        lista.append({"n": _ent(f.get("N°")) or i, "estado": e, "asistio": a, "faltas": fa, "quedan": _ent(f["Faltas que le quedan"]),
                      "porcentaje": _num(f.get("% hasta hoy")), "puedeLlegar": _num(f.get("Puede llegar hasta"))})
    lista.sort(key=lambda x: (ESTADOS.index(x["estado"]) if x["estado"] in ESTADOS else len(ESTADOS), x["quedan"] if x["quedan"] is not None else 99, x["n"]))
    por_clase = []
    for k in claves:
        marcas = [_ent(f.get(k)) for f in est]
        marcas = [m for m in marcas if m is not None]
        por_clase.append({"clase": int(k.split()[1]), "estado": "Dictada" if marcas else "Sin dictar", "asistieron": sum(1 for m in marcas if m == 1), "de": len(est)})
    ahora = ahora or datetime.now(BOGOTA)
    return {"actualizado": ahora.isoformat(timespec="seconds"), "programadas": programadas, "dictadas": dictadas, "permitidas": permitidas,
            "estudiantes": len(est), "promedio": round(asistio_t / (asistio_t + faltas_t), 4) if asistio_t + faltas_t else None,
            "porEstado": por_estado, "sinMarcar": sum(_ent(f.get("Sin marcar")) or 0 for f in est), "porClase": por_clase, "lista": lista}


def aplicar(filas, carpeta_curso, ahora=None):
    """Escribe estado/asistencia.json del curso. Si el Excel no sirve, conserva el anterior y lanza ValueError."""
    r = resumir(filas, ahora)
    arch = Path(carpeta_curso) / "estado/asistencia.json"
    arch.parent.mkdir(parents=True, exist_ok=True)
    if arch.exists():  # sin cambios no se reescribe (la hora de actualización no cuenta)
        previo = json.loads(arch.read_text(encoding="utf-8"))
        if {k: v for k, v in previo.items() if k != "actualizado"} == {k: v for k, v in r.items() if k != "actualizado"}:
            return r, False
    arch.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    return r, True
