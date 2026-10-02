import { esc, resaltar, fichaClase, insignias, legible, ic } from './ui.js';
import { estado } from './estado.js';
import { lunesDe, addDias, partes, MESES, diaNombre, cap, estadoClase, cambioVigente } from './utils-fecha.js';

const semanaTxt = (lunes) => {
  const a = partes(lunes), b = partes(addDias(lunes, 6));
  return `Semana del ${a.d} de ${MESES[a.m - 1].slice(0, 3)} al ${b.d} de ${MESES[b.m - 1].slice(0, 3)}`;
};

export const expandidas = new Set();
const pasadas = { abierto: false };

/** La lista es el hilo: cada clase cuelga de él como una etiqueta. Las realizadas van plegadas. */
export function renderLista(el, clases, ctx) {
  const { t, cfg, proximaId } = ctx;
  const inicioRacha = new Set();
  let previa = null;
  for (const c of clases) { if (c.unidadSlug !== previa) inicioRacha.add(c.id); previa = c.unidadSlug; }
  const grupos = (cs) => {
    const g = new Map();
    for (const c of cs) { const k = lunesDe(c.fecha); (g.get(k) ?? g.set(k, []).get(k)).push(c); }
    return [...g].map(([lunes, items]) => `<section class="semana" aria-label="${esc(semanaTxt(lunes))}">
    <h3 class="semana-tit">${esc(semanaTxt(lunes))}</h3>
    <ol class="hilo-lista">${items.map((c, i) => `<li>${fila(c, { ...ctx, mostrarUnidad: inicioRacha.has(c.id) || i === 0, estado: estadoClase(c, t), esProxima: c.id === proximaId, repro: cambioVigente(c, cfg, t) })}</li>`).join('')}</ol>
  </section>`).join('');
  };
  const pas = clases.filter((c) => estadoClase(c, t) === 'pasada');
  const resto = clases.filter((c) => estadoClase(c, t) !== 'pasada');
  if (!pas.length || !resto.length) { el.innerHTML = grupos(clases); return; }
  const abierta = pasadas.abierto || estado.estado === 'realizadas' || !!estado.q;
  el.innerHTML = `<details class="realizadas"${abierta ? ' open' : ''}><summary>${ic('caret-down')}${pas.length} ${pas.length === 1 ? 'clase realizada' : 'clases realizadas'}</summary>${grupos(pas)}</details>${grupos(resto)}`;
}

function fila(c, ctx) {
  const { q, estado, esProxima, repro } = ctx;
  const abierta = expandidas.has(c.id);
  const p = partes(c.fecha);
  const cls = `fila es-${estado}${esProxima && estado === 'futura' ? ' es-proxima' : ''}${repro ? ' es-repro' : ''}`;
  return `<article class="${cls}" data-id="${c.id}">
    <button class="fila-cab" type="button" aria-expanded="${abierta}" aria-controls="cuerpo-${c.id}">
      <span class="fecha-bloque"><small>${esc(diaNombre(c.fecha).slice(0, 3))}</small><b>${p.d}</b><small>${esc(MESES[p.m - 1].slice(0, 3))}</small></span>
      <span class="fila-titulo"><strong>${resaltar(cap(c.clase.toLowerCase()), q)}</strong>
        ${ctx.mostrarUnidad ? `<span class="unidad-txt" title="${esc(legible(c.unidad))}">${resaltar(legible(c.unidad), q)}</span>` : ''}</span>
      <span class="fila-prof">${resaltar(c.profesores.join(' y '), q)}</span>
      <span class="fila-estados">${insignias(c, estado, esProxima, repro)}</span>
      ${ic('caret-down')}
    </button>
    <div class="fila-cuerpo" id="cuerpo-${c.id}" ${abierta ? '' : 'hidden'}>${fichaClase(c, ctx)}</div>
  </article>`;
}

export function iniciarLista(el) {
  el.addEventListener('toggle', (e) => { if (e.target.classList?.contains('realizadas')) pasadas.abierto = e.target.open; }, true);
  el.addEventListener('click', (e) => {
    const b = e.target.closest('.fila-cab');
    if (!b) return;
    const id = Number(b.closest('.fila').dataset.id);
    const abre = b.getAttribute('aria-expanded') !== 'true';
    b.setAttribute('aria-expanded', abre);
    b.nextElementSibling.hidden = !abre;
    abre ? expandidas.add(id) : expandidas.delete(id);
  });
}
