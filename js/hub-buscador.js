// Buscador global del sitio de administración: cursos, docentes y clases de todos los cursos, incluidos los terminados.
import { esc } from './ui.js';
import { norm } from './ui.js';
import { estadoClase, fechaLarga, ahora } from './utils-fecha.js';

const LIM = { cursos: 6, docentes: 6, clases: 10 };
const palabras = (q) => norm(q).split(/\s+/).filter(Boolean);
const coincide = (pajar, ps) => ps.every((p) => pajar.includes(p));

/** Resultados para el texto `q`: { cursos, docentes, clases } con el total de cada grupo (los listados vienen recortados). */
export function buscar(rs, q, t = ahora()) {
  const ps = palabras(q);
  if (!ps.length) return null;
  const cursos = rs.filter((r) => coincide(norm([r.c.programaCorto, r.c.programa, r.c.periodo, r.c.cohorte, r.c.tipo].join(' ')), ps));
  const gente = new Map();
  const clases = [];
  for (const r of rs) {
    for (const c of r.d?.clases ?? []) {
      for (const [rol, nombre] of [...c.profesores.map((p) => ['Docente', p]), ...(c.asistentePat ? [['Asistente PAT', c.asistentePat]] : [])]) {
        const k = `${rol}|${norm(nombre).trim()}`;
        if (!gente.has(k)) gente.set(k, { nombre, rol, porCurso: new Map() });
        const g = gente.get(k);
        if (!g.porCurso.has(r.c.id)) g.porCurso.set(r.c.id, { r, clases: [] });
        g.porCurso.get(r.c.id).clases.push(c);
      }
      const pajar = norm([c.clase, c.unidad, c.tema, c.fecha, fechaLarga(c.fecha), c.profesores.join(' '), c.asistentePat, r.c.programaCorto].join(' | '));
      if (coincide(pajar, ps)) clases.push({ c, r });
    }
  }
  const docentes = [...gente.values()].filter((g) => coincide(norm(g.nombre), ps));
  const orden = (a, b) => a.c.inicio.localeCompare(b.c.inicio);
  const futuras = clases.filter((x) => estadoClase(x.c, t) !== 'pasada').sort(orden);
  const pasadas = clases.filter((x) => estadoClase(x.c, t) === 'pasada').sort((a, b) => orden(b, a));
  return { cursos, docentes, clases: [...futuras, ...pasadas], t };
}

const enlace = (r, params) => `${new URL(`${r.c.ruta}/`, new URL('../../', location.href)).href}${params ? `?${new URLSearchParams(params)}` : ''}`;
const periodo = (c) => (c.periodo ? `Periodo ${c.periodo}${c.cohorte ? `, ${c.cohorte}` : ''}` : c.tipo);
const mas = (total, lim) => (total > lim ? `<li class="mas-res">Y ${total - lim} más. Escribe una palabra más para afinar.</li>` : '');
const bloque = (titulo, n, filas) => (n ? `<div class="bg-grupo"><h3>${titulo} <span>${n}</span></h3><ul>${filas}</ul></div>` : '');

export function htmlResultados(res) {
  if (!res) return '';
  const { cursos, docentes, clases, t } = res;
  if (!cursos.length && !docentes.length && !clases.length) return '<p class="nota bg-vacio">No encontré nada con esas palabras. Prueba con el nombre de un curso, el apellido de un docente o el tema de una clase.</p>';
  const fCursos = cursos.slice(0, LIM.cursos).map((r) => `<li><span><strong>${esc(r.c.programaCorto)}</strong><small>${esc(periodo(r.c))}${r.estado === 'terminado' ? ', terminado' : ''}</small></span><a class="btn" href="${esc(enlace(r))}" target="_blank" rel="noopener">Abrir</a></li>`).join('') + mas(cursos.length, LIM.cursos);
  const fDocentes = docentes.slice(0, LIM.docentes).map((g) => {
    const todas = [...g.porCurso.values()].flatMap((x) => x.clases);
    const prox = todas.filter((c) => estadoClase(c, t) !== 'pasada').sort((a, b) => a.inicio.localeCompare(b.inicio))[0];
    return `<li><span><strong>${esc(g.nombre)}</strong><small>${g.rol}, ${todas.length} ${todas.length === 1 ? 'clase' : 'clases'} en ${g.porCurso.size} ${g.porCurso.size === 1 ? 'curso' : 'cursos'}. ${prox ? `Próxima: ${esc(fechaLarga(prox.fecha))}.` : 'Sin clases por dictar.'}</small></span>
      <span class="bg-links">${[...g.porCurso.values()].map(({ r }) => `<a href="${esc(enlace(r, g.rol === 'Docente' ? { docente: g.nombre } : { q: g.nombre }))}" target="_blank" rel="noopener">${esc(r.c.programaCorto)}</a>`).join('')}</span></li>`;
  }).join('') + mas(docentes.length, LIM.docentes);
  const fClases = clases.slice(0, LIM.clases).map(({ c, r }) => {
    const est = estadoClase(c, t);
    return `<li><span><strong>${esc(c.clase[0] + c.clase.slice(1).toLowerCase())}, ${esc(fechaLarga(c.fecha))}</strong><small>${esc(r.c.programaCorto)}. ${c.profesores.length ? esc(c.profesores.join(' y ')) : 'Docente por confirmar'}${est === 'pasada' ? '. Ya se dictó' : ''}</small></span>
      <a class="btn" href="${esc(enlace(r, { q: c.clase.toLowerCase() }))}" target="_blank" rel="noopener">Ver clase</a></li>`;
  }).join('') + mas(clases.length, LIM.clases);
  return bloque('Cursos', cursos.length, fCursos) + bloque('Docentes', docentes.length, fDocentes) + bloque('Clases', clases.length, fClases);
}
