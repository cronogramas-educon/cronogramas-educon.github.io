#!/usr/bin/env python3
"""Mensaje de bienvenida de un curso, listo para publicar en su equipo de Teams.

Uso: python scripts/bienvenida.py generar        escribe bienvenidas/<id>.json de cada curso con grupo de Teams y datos publicados
     python scripts/bienvenida.py registrar EVENTO  anota en estado/bienvenidas-enviadas.json que el flujo publicó la bienvenida de un curso
     python scripts/bienvenida.py ver CURSO      muestra el texto de un curso, sin enviar nada
El texto sale de la plantilla "Mensaje de bienvenida" del equipo, con los datos reales del curso (fechas, horas, horario, módulos y
estudiante PAT). La gestora logística y el estudiante PAT no van fijos: el mensaje lleva los marcadores {{GESTORA}} y {{PAT}} y quien lo envía escribe
los nombres en el formulario (el hub los prellena con el PAT del Excel si existe). Un tercer marcador, {{NOTA}}, es un aviso opcional propio del curso. Lo demás no se inventa.
bienvenidas/<id>.json lleva {equipo, canal, mensaje}: un flujo de Power Automate lo lee, reemplaza los marcadores con las respuestas del formulario y publica el mensaje en el canal General del equipo.
Este script no envía nada. El registro de envíos solo guarda curso y fecha (nunca quién lo envió; eso queda en las respuestas del formulario): el flujo lo consulta
para no publicar dos veces y el sitio de administración lo muestra.
"""
import json, re, sys
from datetime import date
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cursos as cu

PAT, GESTORA, NOTA = "{{PAT}}", "{{GESTORA}}", "{{NOTA}}"  # los reemplaza el flujo con lo que se escribe en el formulario (la nota es opcional: sin texto desaparece)
RAIZ = Path(__file__).resolve().parent.parent
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def _fecha(iso, con_anio=False):
    d = date.fromisoformat(iso)
    return f"{d.day} de {MESES[d.month - 1]}" + (f" de {d.year}" if con_anio else "")


def _hora(iso):
    h, m = int(iso[11:13]), iso[14:16]
    return f"{(h % 12) or 12}:{m} {'a. m.' if h < 12 else 'p. m.'}"


def _lista(xs):
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " y " + xs[-1]


def fechas(meta):
    ini, fin = date.fromisoformat(meta["inicio"]), date.fromisoformat(meta["fin"])
    if ini == fin:
        return _fecha(meta["inicio"], True)
    return f"del {_fecha(meta['inicio'], ini.year != fin.year)} al {_fecha(meta['fin'], True)}"


def horarios(clases):
    """'martes, miércoles y jueves de 6:00 p. m. a 9:00 p. m.' por cada franja distinta, hora de Colombia."""
    por = {}
    for c in clases:
        por.setdefault((_hora(c["inicio"]), _hora(c["fin"])), set()).add(date.fromisoformat(c["fecha"]).weekday())
    franjas = sorted(por.items(), key=lambda kv: (-sum(1 for c in clases if (_hora(c["inicio"]), _hora(c["fin"])) == kv[0]), kv[0]))
    return "; ".join(f"{_lista([DIAS[i] for i in sorted(dias)])} de {ini} a {fin}" for (ini, fin), dias in franjas) + " (hora de Colombia)"


def modulo(nombre, siglas):
    """Los módulos vienen en mayúsculas en el Excel: se pasan a oración y se conservan las siglas."""
    if not nombre.isupper():
        return nombre
    t = nombre.lower().capitalize()
    for s in siglas:
        t = re.sub(rf"(?<![\w]){re.escape(s.lower())}(?![\w])", s, t)
    return t


def mensaje(c, d, g, url):
    """HTML del mensaje para Teams. c: curso del registro, d: data.json del curso, g: configuración global, url: página del curso."""
    m = d["meta"]
    nombre = escape(cu.con_tipo(c["programa"], c["tipo"]))
    horas = m.get("horasTotales")
    intensidad = (f"{'' if m.get('horasCompletas', True) else 'aproximadamente '}{horas} horas") if horas else "por confirmar"
    unidades = [modulo(u["nombre"], g.get("siglas", [])) for u in d.get("unidades", [])]
    if unidades:
        contenido = f"<p>A lo largo de las {horas} horas abordaremos {len(unidades)} {'módulo principal' if len(unidades) == 1 else 'módulos principales'}:</p><ul>{''.join(f'<li>{escape(u)}</li>' for u in unidades)}</ul>" if horas else \
            f"<p>Abordaremos {len(unidades)} {'módulo principal' if len(unidades) == 1 else 'módulos principales'}:</p><ul>{''.join(f'<li>{escape(u)}</li>' for u in unidades)}</ul>"
    else:
        contenido = f"<p>{f'A lo largo de las {horas} horas abordaremos' if horas else 'Abordaremos'} los temas del cronograma, que pueden consultar en la página del curso.</p>"
    return f"""<p><b>¡Bienvenid@s al {nombre} de la Universidad de La Sabana! 🎓✨</b></p>
<p>Agradecemos su confianza en la Facultad de Estudios Jurídicos, Políticos e Internacionales para continuar fortaleciendo su desarrollo personal y profesional.</p>
<p>Para asegurar una excelente experiencia académica y logística, compartimos la información clave del curso:</p>
<p><b>🗓️ Datos Generales del Curso</b></p>
<ul><li><b>Fechas:</b> {fechas(m)}</li><li><b>Intensidad total:</b> {intensidad}</li><li><b>Modalidad:</b> Sincrónica - Remota vía Microsoft Teams.</li><li><b>Horarios:</b> {horarios(d['clases'])}</li></ul>
<p><b>📚 Contenido Académico</b></p>
{contenido}
<p><b>💻 Conexión a Clases y Material</b></p>
<ul><li><b>Acceso a Teams:</b> Las invitaciones a las sesiones en vivo se compartirán en este grupo los días de clase. Agradecemos conectarse 5 minutos antes y asegurar una buena conexión a internet. Pueden consultar el cronograma actualizado y los enlaces en <a href="{escape(url)}">la página del curso</a>.</li>
<li><b>Grabaciones:</b> Las sesiones serán grabadas exclusivamente para control interno de la universidad; por políticas institucionales, no serán compartidas con los estudiantes.</li>
<li><b>Material de apoyo:</b> Oportunamente se compartirá un enlace a la carpeta compartida en Google Drive. La disponibilidad de diapositivas o guías dependerá del criterio y autonomía académica de cada docente.</li></ul>
<p><b>📜 Asistencia y Certificación</b></p>
<ul><li><b>Requisito de asistencia:</b> Se exige una asistencia mínima del 80% de las clases programadas para optar al certificado.</li>
<li><b>Inasistencias:</b> Si se supera el 20% de inasistencias, no se expedirá la certificación. No se aceptan excusas extemporáneas ni justificaciones fuera de la política institucional.</li>
<li><b>Entrega del certificado:</b> El certificado en formato PDF se enviará al correo electrónico registrado en un plazo máximo de 40 días hábiles posteriores a la finalización del curso.</li></ul>
<p><b>🤝 Acompañamiento Logístico y Administrativo</b></p>
<p>Durante todo el programa contarán con el apoyo constante del equipo de coordinación y logística:</p>
<ul><li><b>Estudiante PAT (Programa Aprendamos a Trabajar):</b> {PAT}</li><li><b>Gestora Logística:</b> {GESTORA}</li></ul>
<p><b>ℹ️ Términos y Trámites Institucionales</b></p>
<ul><li><b>Ajustes:</b> La Universidad de La Sabana se reserva el derecho de realizar modificaciones en la programación o en la plantilla docente por razones de fuerza mayor, las cuales serán notificadas previamente.</li>
<li><b>Novedades administrativas:</b> Los trámites de aplazamiento, devolución o cancelación se rigen según el Reglamento de Estudiantes de la Universidad de La Sabana.</li></ul>
<p><b>📲 ¿Dudas o inconvenientes con Teams?</b></p>
<p>Si presentan dificultades para ingresar a las salas de clase o alguna consulta logística, pueden escribirnos directamente por este medio.</p>
{NOTA}
<p>¡Les deseamos un exitoso ciclo de aprendizaje y una experiencia muy enriquecedora! 🚀🌟</p>"""


def del_curso(c, g, raiz=RAIZ):
    """Mensaje de un curso o None si todavía no tiene cronograma publicado."""
    ruta = Path(raiz) / "cursos" / c["id"] / "data/data.json"
    if not ruta.exists():
        return None
    d = json.loads(ruta.read_text(encoding="utf-8"))
    if not d.get("clases"):
        return None
    return mensaje(c, d, g, f"{g['urlSitio'].rstrip('/')}/{cu.sitio_ruta(c)}/")


def generar(raiz=RAIZ):
    """Escribe bienvenidas/<id>.json de cada curso con grupo de Teams y cronograma. Borra los de cursos que ya no cumplen. Devuelve los ids escritos."""
    reg = cu.registro(raiz)
    carpeta = Path(raiz) / "bienvenidas"
    carpeta.mkdir(exist_ok=True)
    escritos = []
    for c in reg["cursos"]:
        m = del_curso(c, reg["global"], raiz) if c.get("teams") else None
        if m:
            nuevo = json.dumps({"equipo": c["teams"]["equipo"], "canal": c["teams"]["canal"], "mensaje": m}, ensure_ascii=False, indent=2) + "\n"
            f = carpeta / f"{c['id']}.json"
            if not f.exists() or f.read_text(encoding="utf-8") != nuevo:
                f.write_text(nuevo, encoding="utf-8")
            escritos.append(c["id"])
    for f in carpeta.glob("*.json"):
        if f.stem not in escritos:
            f.unlink()
    return escritos


def registrar(evento, raiz=RAIZ):
    """Lee el aviso del flujo (client_payload con curso y fecha) y anota el envío. Devuelve el id anotado o None si el curso no existe."""
    p = json.loads(Path(evento).read_text(encoding="utf-8")).get("client_payload") or {}
    curso, fecha = p.get("curso", ""), p.get("fecha", "")
    if curso not in {c["id"] for c in cu.registro(raiz)["cursos"]} or not re.fullmatch(r"\d{4}-\d\d-\d\dT[\d:.]+Z?[+\-\d:]*", fecha):
        print("::warning::Aviso de bienvenida enviada con curso o fecha inválidos; no se anotó.")
        return None
    f = Path(raiz) / "estado/bienvenidas-enviadas.json"
    datos = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    datos.setdefault(curso, {"fecha": fecha})  # el primer envío manda: un aviso repetido no cambia la fecha
    f.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return curso


if __name__ == "__main__":
    if sys.argv[1:2] == ["generar"]:
        print("\n".join(generar()) or "ningún curso con grupo de Teams y cronograma")
    elif sys.argv[1:2] == ["registrar"] and len(sys.argv) == 3:
        registrar(sys.argv[2])
    elif sys.argv[1:2] == ["ver"] and len(sys.argv) == 3:
        reg = cu.registro()
        c = next((x for x in reg["cursos"] if x["id"] == sys.argv[2]), None)
        sys.exit("curso no encontrado" if not c else (del_curso(c, reg["global"]) or "ese curso aún no tiene cronograma publicado"))
    else:
        sys.exit(__doc__)
