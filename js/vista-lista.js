import { esc, resaltar, fichaClase, insignias, legible } from './ui.js';
import { lunesDe, addDias, partes, MESES, diaNombre, cap, estadoClase, cambioVigente } from './utils-fecha.js';

const semanaTxt = (lunes) => {
  const a = partes(lunes), b = partes(addDias(lunes, 6));
  return `Semana del ${a.d} de ${MESES[a.m - 1]} al ${b.d} de ${MESES[b.m - 1]}`;
};

export const expandidas = new Set();

export function renderLista(el, clases, ctx) {
  const { q, t, cfg, proximaId } = ctx;
  const grupos = new Map();
  for (const c of clases) { const k = lunesDe(c.fecha); (grupos.get(k) ?? grupos.set(k, []).get(k)).push(c); }
  el.innerHTML = [...grupos].map(([lunes, cs]) => `<section class="semana" aria-label="${esc(semanaTxt(lunes))}">
    <h3>${esc(semanaTxt(lunes))}</h3>
    ${cs.map((c) => fila(c, { ...ctx, estado: estadoClase(c, t), esProxima: c.id === proximaId, repro: cambioVigente(c, cfg, t) })).join('')}
  </section>`).join('');
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
        <p title="${esc(legible(c.unidad))}">${resaltar(legible(c.unidad), q)}</p></span>
      <span class="fila-prof"><span>Docente</span>${resaltar(c.profesores.join(' y '), q)}</span>
      <span class="fila-estados">${insignias(c, estado, esProxima, repro)}</span>
      <span class="flecha" aria-hidden="true"></span>
    </button>
    <div class="fila-cuerpo" id="cuerpo-${c.id}" ${abierta ? '' : 'hidden'}>${fichaClase(c, ctx)}</div>
  </article>`;
}

export function iniciarLista(el) {
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
