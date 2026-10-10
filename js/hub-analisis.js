// Cálculos del sitio de administración sobre los datos de todos los cursos. Sin DOM: reciben los resultados de analizar() y devuelven datos.
import { norm } from './ui.js';
import { addDias, estadoClase, hoyISO } from './utils-fecha.js';

const INSTITUCIONAL = new Set(['sabana']); // "SABANA" es la universidad, no una persona que pueda chocar consigo misma
const FALTAS = [['Docente', (c) => !c.profesores.length], ['Asistente PAT', (c) => !c.asistentePat], ['Enlace de Teams', (c) => !c.linkTeams]];

const clases = (rs) => rs.filter((r) => r.d).flatMap((r) => r.d.clases.map((c) => ({ c, curso: r.c })));

/** Clases de los próximos `dias` días a las que aún les falta docente, asistente o enlace, por fecha. */
export function urgentes(rs, t, dias = 14) {
  const hoy = hoyISO(t), tope = addDias(hoy, dias);
  return clases(rs)
    .filter(({ c }) => c.fecha >= hoy && c.fecha <= tope && estadoClase(c, t) !== 'pasada')
    .map(({ c, curso }) => ({ c, curso, faltas: FALTAS.filter(([, f]) => f(c)).map(([n]) => n) }))
    .filter((x) => x.faltas.length)
    .sort((a, b) => a.c.inicio.localeCompare(b.c.inicio));
}

/** Semáforo de un curso: rojo si no se pudo leer el Excel o a una clase de hoy o mañana le falta docente o enlace (sin eso los estudiantes no entran), ámbar si falta algo en 14 días o no hay datos. */
export function salud(r, t) {
  if (r.error) return { nivel: 'rojo', texto: 'Requiere atención', motivo: 'El último guardado del Excel no se pudo leer' };
  if (!r.d) return { nivel: 'ambar', texto: 'Por revisar', motivo: 'Aún no hay cronograma publicado' };
  const u = urgentes([r], t);
  const hoy = hoyISO(t);
  const critica = u.find((x) => x.c.fecha <= addDias(hoy, 1) && x.faltas.some((f) => f !== 'Asistente PAT'));
  if (critica) return { nivel: 'rojo', texto: 'Requiere atención', motivo: `${critica.c.clase[0] + critica.c.clase.slice(1).toLowerCase()} ${critica.c.fecha === hoy ? 'es hoy' : 'es mañana'} y falta ${critica.faltas.filter((f) => f !== 'Asistente PAT').map((f) => (f === 'Docente' ? 'el docente' : 'el enlace de Teams')).join(' y ')}` };
  if (u.length) return { nivel: 'ambar', texto: 'Por revisar', motivo: `${u.length} ${u.length === 1 ? 'clase de los próximos 14 días tiene' : 'clases de los próximos 14 días tienen'} datos sin confirmar` };
  return { nivel: 'verde', texto: 'Todo en orden', motivo: 'Nada urgente por confirmar' };
}

/** Clases que empiezan en los próximos `dias` días, por hora de inicio, de todos los cursos. */
export function agenda(rs, t, dias = 28) {
  const hoy = hoyISO(t), tope = addDias(hoy, dias);
  return clases(rs).filter(({ c }) => c.fecha >= hoy && c.fecha <= tope && estadoClase(c, t) !== 'pasada').sort((a, b) => a.c.inicio.localeCompare(b.c.inicio));
}

/** Docentes o asistentes con dos clases a la vez, en el mismo curso o en cursos distintos. Solo clases que aún no pasan. */
export function choques(rs, t) {
  const por = new Map();
  for (const x of clases(rs)) {
    if (estadoClase(x.c, t) === 'pasada') continue;
    const gente = [...x.c.profesores.map((p) => ['Docente', p]), ...(x.c.asistentePat ? [['Asistente PAT', x.c.asistentePat]] : [])];
    for (const [rol, nombre] of gente) {
      const k = norm(nombre).trim();
      if (INSTITUCIONAL.has(k)) continue;
      if (!por.has(`${rol}|${k}`)) por.set(`${rol}|${k}`, { rol, nombre, lista: [] });
      por.get(`${rol}|${k}`).lista.push(x);
    }
  }
  const out = [];
  for (const { rol, nombre, lista } of por.values()) {
    lista.sort((a, b) => a.c.inicio.localeCompare(b.c.inicio));
    let previo = lista[0];
    for (const x of lista.slice(1)) {
      if (Date.parse(x.c.inicio) < Date.parse(previo.c.fin)) out.push({ rol, nombre, a: previo, b: x });
      if (Date.parse(x.c.fin) > Date.parse(previo.c.fin)) previo = x;
    }
  }
  return out.sort((p, q) => p.a.c.inicio.localeCompare(q.a.c.inicio));
}

/** Horas de una clase: las del Excel si están, y si no las del horario (marcadas como estimadas). */
export function horasDe(c) {
  return typeof c.horas === 'number' ? { h: c.horas, estimada: false } : { h: (Date.parse(c.fin) - Date.parse(c.inicio)) / 3600e3, estimada: true };
}

/** Totales por docente, por curso y por mes. Una clase con dos docentes cuenta completa para cada uno. */
export function reportes(rs, t) {
  const doc = new Map(), cur = new Map(), mes = new Map();
  const suma = (m, k, extra) => { const e = m.get(k) ?? { clases: 0, horas: 0, hechas: 0, estimadas: 0, ...extra }; m.set(k, e); return e; };
  for (const { c, curso } of clases(rs)) {
    const { h, estimada } = horasDe(c), hecha = estadoClase(c, t) === 'pasada';
    const acum = (e) => { e.clases++; e.horas += h; if (hecha) e.hechas += h; if (estimada) e.estimadas++; return e; };
    const ec = acum(suma(cur, curso.id, { nombre: curso.programaCorto + (curso.cohorte ? `, ${curso.cohorte}` : ''), periodo: curso.periodo || '', docentes: new Set() }));
    c.profesores.forEach((p) => { ec.docentes.add(p); acum(suma(doc, p, { cursos: new Set() })).cursos.add(curso.programaCorto); });
    acum(suma(mes, c.fecha.slice(0, 7), {}));
  }
  const ord = (m, f) => [...m.entries()].map(([k, v]) => ({ k, ...v })).sort(f);
  return {
    docentes: ord(doc, (a, b) => b.horas - a.horas || a.k.localeCompare(b.k, 'es')).map((e) => ({ ...e, cursos: [...e.cursos] })),
    cursos: ord(cur, (a, b) => a.nombre.localeCompare(b.nombre, 'es')).map((e) => ({ ...e, docentes: e.docentes.size })),
    meses: ord(mes, (a, b) => a.k.localeCompare(b.k)),
  };
}

const num = (n) => (Math.round(n * 10) / 10).toString().replace('.', ',');
export const horasTxt = (e) => `${num(e.horas)}${e.estimadas ? ` (${e.estimadas} ${e.estimadas === 1 ? 'clase estimada' : 'clases estimadas'} con el horario)` : ''}`;

/** CSV con punto y coma y BOM: Excel en español lo abre en columnas al hacer doble clic. */
export function csv(titulos, filas) {
  const celda = (v) => { const s = String(v ?? ''); return /[;"\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
  return '﻿' + [titulos, ...filas].map((f) => f.map(celda).join(';')).join('\r\n');
}
