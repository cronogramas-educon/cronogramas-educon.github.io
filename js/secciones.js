// Secciones que dependen solo de los datos: cifras, plan de estudios, docentes, equipo de apoyo, sobre el programa.
import { esc, iniciales, rangos, horario, legible } from './ui.js';
import { fechaCorta, fechaLarga, cap, cambioVigente, ahora } from './utils-fecha.js';

const nombreClase = (c) => cap(c.clase.toLowerCase());

export function cifras(el, d, cfg) {
  const inst = new Set(cfg.profesoresInstitucionales ?? []);
  const docentes = d.profesores.filter((p) => !inst.has(p)).length;
  const items = [[d.meta.totalClases, 'clases'], [d.meta.horasTotales, 'horas'], [d.unidades.length, 'unidades'], [docentes, 'docentes']];
  el.innerHTML = items.map(([n, l]) => `<div><strong>${n}</strong><span>${l}</span></div>`).join('');
}

export function plan(el, d, abiertas) {
  const porId = new Map(d.clases.map((c) => [c.id, c]));
  el.innerHTML = d.unidades.map((u) => {
    const cs = u.clases.map((id) => porId.get(id));
    const rango = cs.length > 1 ? `${fechaCorta(cs[0].fecha)} a ${fechaCorta(cs.at(-1).fecha)}` : fechaCorta(cs[0].fecha);
    return `<details class="plan-unidad" data-slug="${esc(u.slug)}"${abiertas.has(u.slug) ? ' open' : ''}>
      <summary><strong>${esc(legible(u.nombre))}</strong><small>${u.clases.length} ${u.clases.length === 1 ? 'clase' : 'clases'} · ${u.horas} h · ${esc(rango)}</small><span class="flecha" aria-hidden="true"></span></summary>
      <div class="unidad-cuerpo">${cs.map((c) => `<div class="unidad-clase">
        <h4>${esc(nombreClase(c))}<span>${esc(fechaLarga(c.fecha))}<br>${esc(c.profesor)}</span></h4>
        <ul>${c.temaPuntos.map((p) => `<li>${esc(p)}</li>`).join('')}</ul></div>`).join('')}</div></details>`;
  }).join('');
}

export function docentes(el, d, cfg) {
  const t = ahora();
  el.innerHTML = d.profesores.map((p) => {
    const cs = d.clases.filter((c) => c.profesores.includes(p));
    const extra = cfg.docentesExtra?.[p];
    return `<li class="persona"><span class="iniciales" aria-hidden="true">${esc(iniciales(p))}</span><div>
      <h3>${esc(p)}</h3><p>${cs.length} ${cs.length === 1 ? 'clase' : 'clases'}</p>
      ${extra?.bio ? `<p>${esc(extra.bio)}</p>` : ''}
      <div class="chips">${cs.map((c) => `<span class="chip${cambioVigente(c, cfg, t) ? ' repro' : ''}">${esc(nombreClase(c))} · ${esc(fechaCorta(c.fecha))}</span>`).join('')}</div></div></li>`;
  }).join('');
}

export function equipo(el, d) {
  el.innerHTML = d.asistentesPat.map((p) => {
    const ids = d.clases.filter((c) => c.asistentePat === p).map((c) => c.id);
    return `<li class="persona"><span class="iniciales" aria-hidden="true">${esc(iniciales(p))}</span><div>
      <h3>${esc(p)}</h3><p>Acompaña las clases ${esc(rangos(ids))}</p></div></li>`;
  }).join('');
}

export function sobre(el, d, cfg) {
  const link = cfg.urlPaginaOficial
    ? `<a class="chevron-cta solid" href="${esc(cfg.urlPaginaOficial)}" target="_blank" rel="noopener noreferrer">Ver inscripción y detalles oficiales</a>` : '';
  el.innerHTML = `<div><p class="nota">La Universidad puede ajustar el cronograma durante el programa. Esta página muestra siempre la versión vigente y avisa cuando cambia la fecha de una clase. Para inscripción, valor y descuentos, consulta la página oficial.</p>${link}</div>
    <dl><dt>Programa</dt><dd>${esc(d.meta.programa)}</dd><dt>Cohorte</dt><dd>${esc(d.meta.cohorte)}</dd>
    <dt>Modalidad</dt><dd>${esc(d.meta.modalidad)}</dd><dt>Horario</dt><dd>${esc(horario(d.meta))}, hora de Colombia</dd>
    <dt>Intensidad</dt><dd>${d.meta.horasTotales} horas en ${d.meta.totalClases} clases</dd></dl>`;
}
