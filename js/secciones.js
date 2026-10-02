// Secciones que dependen solo de los datos: unidades, docentes, acompañamiento y sobre el programa.
import { esc, horario, legible, ic } from './ui.js';
import { fechaCorta, fechaLarga, cap } from './utils-fecha.js';

const nombreClase = (c) => cap(c.clase.toLowerCase());

export function plan(el, d, abiertas) {
  const porId = new Map(d.clases.map((c) => [c.id, c]));
  el.innerHTML = d.unidades.map((u) => {
    const cs = u.clases.map((id) => porId.get(id));
    return `<details class="unidad" data-slug="${esc(u.slug)}"${abiertas.has(u.slug) ? ' open' : ''}>
      <summary>${esc(legible(u.nombre))}${ic('caret-down')}</summary>
      <div class="unidad-cuerpo">${cs.map((c) => `<div class="unidad-clase">
        <h4>${esc(nombreClase(c))} <span>${esc(fechaLarga(c.fecha))}</span></h4>
        <ul>${c.temaPuntos.map((p) => `<li>${esc(p)}</li>`).join('')}</ul></div>`).join('')}</div></details>`;
  }).join('');
}

/** Cada docente es un botón: al pulsarlo se filtra el cronograma por su nombre. */
export function docentes(el, d) {
  const faltan = d.clases.some((c) => !c.profesores.length);
  el.innerHTML = (d.profesores.length ? '' : `<p class="pendiente-nota">Los docentes se publicarán pronto.</p>`) + d.profesores.map((p) => {
    const n = d.clases.filter((c) => c.profesores.includes(p)).length;
    return `<button class="chip-docente" type="button" data-docente="${esc(p)}" title="Ver las clases de ${esc(p)}">${esc(p)}<small>${n}</small></button>`;
  }).join('') + (faltan && d.profesores.length ? `<p class="pendiente-nota">Algunas clases tienen docente por confirmar.</p>` : '');
}

export function apoyo(el, d) {
  const n = d.asistentesPat;
  el.innerHTML = n.length ? `En las sesiones de Teams te acompañan <strong>${esc(n.join(' y '))}</strong>.` : 'Quién te acompaña en las sesiones de Teams está por confirmar.';
}

export function sobre(el, d, cfg) {
  const link = cfg.urlPaginaOficial
    ? `<a class="btn" href="${esc(cfg.urlPaginaOficial)}" target="_blank" rel="noopener noreferrer">Inscripción y valores${ic('arrow-up-right')}</a>` : '';
  el.innerHTML = `<p>La Universidad puede ajustar el cronograma. Esta página siempre muestra la versión vigente.</p>${link}`;
}
