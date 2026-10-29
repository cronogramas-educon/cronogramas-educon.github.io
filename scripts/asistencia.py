#!/usr/bin/env python3
"""Asistencia de un curso, desde las filas de la tabla del Excel "Formato de asistencia" (ver generar_asistencia_xlsx.py).

El Excel manda: las cuentas y el estado de cada estudiante salen de sus columnas calculadas (Faltas, Faltas que le quedan, Estado...).
Aquí solo se resumen y se les quita el nombre y el documento: en el sitio se publica solo "Nombre + primer apellido" (etiqueta) y el número de lista; el hub de administración los muestra como "Estudiante N".
"""
import json, math, re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ESTADOS = ["Perdió el mínimo", "En riesgo", "Atención", "Al día", "Aprobó"]  # de más a menos urgente
BOGOTA = timezone(timedelta(hours=-5))
MINIMO, ATENCION, RIESGO = 0.8, 0.5, 0.8  # reglas de certificación y de aviso (ver docs/ASISTENCIA.md)
NOMBRE, REQUERIDAS = "Nombre del estudiante", ("Asistió", "Faltas", "Faltas que le quedan", "Estado")


def _clave(k):
    """Excel Online codifica los encabezados con símbolos: "N°" llega como "N_x00b0_" y "% hasta hoy" como "_x0025_ hasta hoy"."""
    return re.sub(r"_x([0-9a-fA-F]{4})_", lambda m: chr(int(m.group(1), 16)), str(k))


def normalizar(filas):
    return [{_clave(k): v for k, v in f.items()} if isinstance(f, dict) else f for f in filas] if isinstance(filas, list) else filas


def es_asistencia(filas):
    return isinstance(filas, list) and any(isinstance(f, dict) and NOMBRE in f and "Clase 1" in f for f in normalizar(filas))


def etiqueta(nombre):
    """Nombre + primer apellido, lo único del nombre que se publica. Con 4 o más palabras: 1.ª y 3.ª (dos nombres, dos apellidos); con 3: 1.ª y 2.ª; ponytail: un nombre compuesto con un solo apellido de 3 palabras sale mal, se corrige en el Excel."""
    w = str(nombre or "").split()
    return " ".join(w[:1] + w[2:3] if len(w) >= 4 else w[:2])


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


def _estado(faltas, permitidas, termino):
    if faltas > permitidas:
        return "Perdió el mínimo"
    if termino:
        return "Aprobó"
    usado = faltas / permitidas if permitidas else 0
    return "En riesgo" if usado >= RIESGO and faltas else "Atención" if usado >= ATENCION and faltas else "Al día"


def desde_cuadro(est, clases, ahora):
    """El Cuadro de horas manda: las clases (cuántas son, su número) salen de él; del Excel de asistencia solo se toman las marcas 1 o 0.
    Todo lo demás (faltas permitidas, estado, porcentajes) se calcula aquí, igual que lo hacía el Excel."""
    ids = [c["id"] for c in clases]
    programadas = len(ids)
    permitidas = programadas - math.ceil(MINIMO * programadas - 1e-9)
    marcas = [{i: _ent(f.get(f"Clase {i}")) for i in ids if _ent(f.get(f"Clase {i}")) in (0, 1)} for f in est]
    dictadas_ids = {i for m in marcas for i in m}
    termino = programadas > 0 and len(dictadas_ids) >= programadas
    lista, por_estado, asistio_t, faltas_t, sin_t = [], {e: 0 for e in ESTADOS}, 0, 0, 0
    for n, (f, m) in enumerate(zip(est, marcas), 1):
        a, fa = sum(v == 1 for v in m.values()), sum(v == 0 for v in m.values())
        sin = len(dictadas_ids - set(m))
        e = _estado(fa, permitidas, termino and not sin)
        asistio_t, faltas_t, sin_t = asistio_t + a, faltas_t + fa, sin_t + sin
        por_estado[e] += 1
        lista.append({"n": _ent(f.get("N°")) or n, "etiqueta": etiqueta(f[NOMBRE]), "estado": e, "asistio": a, "faltas": fa, "quedan": permitidas - fa,
                      "porcentaje": a / (a + fa) if a + fa else None, "puedeLlegar": (programadas - fa) / programadas if programadas else None,
                      "seguimiento": str(f.get("Seguimiento") or "").strip(), "marcas": {str(i): v for i, v in m.items()}})
    lista.sort(key=lambda x: (ESTADOS.index(x["estado"]), x["quedan"], x["n"]))
    por_clase = [{"clase": i, "estado": "Dictada" if i in dictadas_ids else "Sin dictar", "asistieron": sum(m.get(i) == 1 for m in marcas),
                  "marcadas": sum(i in m for m in marcas), "de": len(est)} for i in ids]
    return {"actualizado": ahora.isoformat(timespec="seconds"), "programadas": programadas, "dictadas": len(dictadas_ids), "permitidas": permitidas,
            "estudiantes": len(est), "promedio": round(asistio_t / (asistio_t + faltas_t), 4) if asistio_t + faltas_t else None,
            "porEstado": por_estado, "sinMarcar": sin_t, "porClase": por_clase, "lista": lista}


def resumir(filas, ahora=None, clases=None):
    """Resumen sin nombres. Lanza ValueError con un mensaje claro si el Excel no trae las columnas calculadas."""
    est = [f for f in normalizar(filas) if isinstance(f, dict) and str(f.get(NOMBRE) or "").strip()]
    if not est:
        raise ValueError("El Excel de asistencia no tiene estudiantes: escribe sus nombres en la hoja Asistencia.")
    if clases:
        return desde_cuadro(est, clases, ahora or datetime.now(BOGOTA))
    falta = [c for c in REQUERIDAS if c not in est[0]]
    if falta:
        raise ValueError("Al Excel de asistencia le faltan columnas: " + ", ".join(falta) + ". No cambies los encabezados de las columnas grises.")
    claves = sorted((k for k in est[0] if re.fullmatch(r"Clase \d+", str(k))), key=lambda k: int(k.split()[1]))
    ncl = _ent(est[0].get("Clases del curso"))  # el archivo trae 40 columnas de clases: solo cuentan las del curso
    if ncl:
        claves = claves[:ncl]
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
        lista.append({"n": _ent(f.get("N°")) or i, "etiqueta": etiqueta(f[NOMBRE]), "estado": e, "asistio": a, "faltas": fa, "quedan": _ent(f["Faltas que le quedan"]),
                      "porcentaje": _num(f.get("% hasta hoy")), "puedeLlegar": _num(f.get("Puede llegar hasta")),
                      "seguimiento": str(f.get("Seguimiento") or "").strip()})
    lista.sort(key=lambda x: (ESTADOS.index(x["estado"]) if x["estado"] in ESTADOS else len(ESTADOS), x["quedan"] if x["quedan"] is not None else 99, x["n"]))
    por_clase = []
    for k in claves:
        marcas = [_ent(f.get(k)) for f in est]
        marcas = [m for m in marcas if m is not None]
        por_clase.append({"clase": int(k.split()[1]), "estado": "Dictada" if marcas else "Sin dictar", "asistieron": sum(1 for m in marcas if m == 1), "marcadas": len(marcas), "de": len(est)})
    ahora = ahora or datetime.now(BOGOTA)
    return {"actualizado": ahora.isoformat(timespec="seconds"), "programadas": programadas, "dictadas": dictadas, "permitidas": permitidas,
            "estudiantes": len(est), "promedio": round(asistio_t / (asistio_t + faltas_t), 4) if asistio_t + faltas_t else None,
            "porEstado": por_estado, "sinMarcar": sum(_ent(f.get("Sin marcar")) or 0 for f in est), "porClase": por_clase, "lista": lista}


def _clases(carpeta_curso):
    d = Path(carpeta_curso) / "data/data.json"
    return json.loads(d.read_text(encoding="utf-8")).get("clases") if d.exists() else None


def recalcular(carpeta_curso, ahora=None):
    """Vuelve a calcular la asistencia con las clases actuales del Cuadro de horas, a partir de las marcas ya guardadas (sin nombres).
    Se llama cuando cambia el Cuadro: agregar o quitar una clase se refleja sin tocar el Excel de asistencia."""
    arch = Path(carpeta_curso) / "estado/asistencia.json"
    clases = _clases(carpeta_curso)
    if not arch.exists() or not clases:
        return None, False
    previo = json.loads(arch.read_text(encoding="utf-8"))
    if not all("marcas" in x for x in previo.get("lista", [])) or not previo.get("lista"):
        return None, False
    filas = [{"N°": x["n"], NOMBRE: x.get("etiqueta") or "x", "Seguimiento": x.get("seguimiento", ""), **{f"Clase {i}": v for i, v in x["marcas"].items()}} for x in previo["lista"]]
    return _escribir(resumir(filas, ahora, clases), arch)


def aplicar(filas, carpeta_curso, ahora=None):
    """Escribe estado/asistencia.json del curso. Si el Excel no sirve, conserva el anterior y lanza ValueError."""
    r = resumir(filas, ahora, _clases(carpeta_curso))
    return _escribir(r, Path(carpeta_curso) / "estado/asistencia.json")


def _escribir(r, arch):
    arch.parent.mkdir(parents=True, exist_ok=True)
    if arch.exists():  # sin cambios no se reescribe (la hora de actualización no cuenta)
        previo = json.loads(arch.read_text(encoding="utf-8"))
        if {k: v for k, v in previo.items() if k != "actualizado"} == {k: v for k, v in r.items() if k != "actualizado"}:
            return r, False
    arch.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    return r, True
