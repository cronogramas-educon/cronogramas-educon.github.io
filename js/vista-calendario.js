import { esc, docentesCorto, fichaClase } from './ui.js';
import { MESES, mesAnio, cap, diaSemana, addDias, partes, fechaLargaAnio, estadoClase, cambioVigente, hoyISO } from './utils-fecha.js';

const num = (c) => c.clase.replace(/\D/g, '') || c.id;
const nombre = (c) => `Clase ${num(c)}`;

export function mesesDe(meta) {
  const out = [];
  let [y, m] = meta.inicio.split('-').map(Number);
  const [yf, mf] = meta.fin.split('-').map(Number);
  while (y < yf || (y === yf && m <= mf)) { out.push(`${y}-${String(m).padStart(2, '0')}`); if (++m > 12) { m = 1; y++; } }
  return out;
}

function pieza(c, ctx) {
  const { t, cfg, proximaId } = ctx;
  const e = estadoClase(c, t);
  const repro = cambioVigente(c, cfg, t);
  const cls = ['pieza', `es-${e}`];
  if (c.id === proximaId && (e === 'futura' || e === 'hoy')) cls.push('es-proxima');
  if (repro) cls.push('es-repro');
  return `<span class="${cls.join(' ')}"><strong><span class="solo-escritorio">Clase </span>${esc(num(c))}${e === 'pasada' ? ' <span aria-hidden="true">✓</span>' : ''}</strong><small>${esc(docentesCorto(c))}</small>${repro ? '<em>Reprogramada</em>' : ''}</span>`;
}

function etiquetaDia(iso, cs, ctx) {
  let s = fechaLargaAnio(iso);
  if (!cs.length) return `${s}, sin clase`;
  return `${s}, ${cs.map((c) => {
    const e = estadoClase(c, ctx.t);
    const est = e === 'pasada' ? 'realizada' : e === 'envivo' ? 'en vivo' : e === 'hoy' ? 'hoy' : c.id === ctx.proximaId ? 'próxima' : '';
    return `${nombre(c)}, ${c.profesor}${cambioVigente(c, ctx.cfg, ctx.t) ? ', reprogramada' : ''}${est ? ', ' + est : ''}`;
  }).join('; ')}`;
}

export function renderCalendario(el, clases, ctx) {
  const { meta, mes, sel, t } = ctx;
  const meses = mesesDe(meta);
  const [y, m] = mes.split('-').map(Number);
  const hoy = hoyISO(t);
  const porFecha = new Map();
  for (const c of clases) (porFecha.get(c.fecha) ?? porFecha.set(c.fecha, []).get(c.fecha)).push(c);
  const primero = `${mes}-01`;
  const ultimo = addDias(`${m === 12 ? y + 1 : y}-${String(m === 12 ? 1 : m + 1).padStart(2, '0')}-01`, -1);
  const inicioGrid = addDias(primero, -((diaSemana(primero) + 6) % 7));
  const foco = ctx.foco && ctx.foco.startsWith(mes) ? ctx.foco : (sel && sel.startsWith(mes) ? sel : [...porFecha.keys()].filter((f) => f.startsWith(mes)).sort()[0] ?? primero);
  let filas = '';
  for (let d = inicioGrid; d <= ultimo || diaSemana(d) !== 1; d = addDias(d, 1)) {
    if (diaSemana(d) === 1) filas += '<div class="cal-fila" role="row">';
    const dentro = d >= primero && d <= ultimo;
    const cs = dentro ? porFecha.get(d) ?? [] : [];
    const fds = [0, 6].includes(diaSemana(d));
    const cls = `cal-celda${fds ? ' fds' : ''}${dentro ? '' : ' fuera'}${d === hoy ? ' es-hoy' : ''}`;
    if (!dentro) filas += `<div class="${cls}" role="gridcell" aria-hidden="true"></div>`;
    else filas += `<div class="${cls}" role="gridcell"><button class="cal-btn${sel === d ? ' sel' : ''}" type="button" data-fecha="${d}" tabindex="${d === foco ? 0 : -1}"
      ${cs.length ? `aria-expanded="${sel === d}"` : 'aria-disabled="true"'} aria-label="${esc(etiquetaDia(d, cs, ctx))}">
      <span class="cal-num">${partes(d).d}</span>${cs.map((c) => pieza(c, ctx)).join('')}</button></div>`;
    if (diaSemana(d) === 0) filas += '</div>';
  }
  const dias = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo'];
  const idx = meses.indexOf(mes);
  const detalleCs = sel ? porFecha.get(sel) ?? [] : [];
  const detalle = detalleCs.length ? `<aside class="detalle" id="detalle" role="dialog" aria-label="Detalle de la clase" aria-modal="false">
      <div class="detalle-cab"><p>${esc(cap(fechaLargaAnio(sel)))}</p><button class="detalle-cerrar" type="button" data-cerrar aria-label="Cerrar detalle">×</button></div>
      ${detalleCs.map((c) => fichaClase(c, { ...ctx, estado: estadoClase(c, t), esProxima: c.id === ctx.proximaId, repro: cambioVigente(c, ctx.cfg, t) })).join('')}
    </aside><div class="fondo-detalle on" data-cerrar></div>` : '';
  el.innerHTML = `<div class="cal-layout${detalle ? ' con-detalle' : ''}"><div>
    <div class="cal-cab"><h3>${esc(cap(mesAnio(mes)))}</h3>
      <div class="cal-meses" role="group" aria-label="Mes">
        <button class="nav-mes" type="button" data-mes="${meses[idx - 1] ?? ''}" ${idx <= 0 ? 'disabled' : ''} aria-label="Mes anterior">‹</button>
        ${meses.map((x) => `<button type="button" data-mes="${x}" aria-pressed="${x === mes}">${esc(cap(MESES[+x.slice(5) - 1]))}</button>`).join('')}
        <button class="nav-mes" type="button" data-mes="${meses[idx + 1] ?? ''}" ${idx >= meses.length - 1 ? 'disabled' : ''} aria-label="Mes siguiente">›</button>
      </div></div>
    <div class="cal" role="grid" aria-label="Calendario de ${esc(mesAnio(mes))}">
      <div class="cal-fila" role="row">${dias.map((d) => `<div class="cal-dsem" role="columnheader" aria-label="${d}">${esc(d.slice(0, 3))}</div>`).join('')}</div>${filas}
    </div>
    <div class="leyenda" aria-label="Leyenda"><span><i class="l-proxima"></i>Próxima</span><span><i class="l-hoy"></i>Hoy</span><span><i class="l-envivo"></i>En vivo</span><span><i class="l-pasada"></i>Realizada</span><span><i class="l-repro"></i>Reprogramada</span></div>
  </div>${detalle}</div>`;
}

export function iniciarCalendario(el, { poner, estado, mesesActual }) {
  el.addEventListener('click', (e) => {
    if (e.target.closest('[data-cerrar]')) return poner({ sel: null });
    const mb = e.target.closest('[data-mes]');
    if (mb && mb.dataset.mes) return poner({ mes: mb.dataset.mes, sel: null });
    const b = e.target.closest('.cal-btn');
    if (b && b.getAttribute('aria-disabled') !== 'true') poner({ sel: estado.sel === b.dataset.fecha ? null : b.dataset.fecha });
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && estado.sel) { const f = estado.sel; poner({ sel: null }); el.querySelector(`[data-fecha="${f}"]`)?.focus(); }
  });
  el.addEventListener('keydown', (e) => {
    const b = e.target.closest('.cal-btn');
    const paso = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[e.key];
    if (!b || paso === undefined) return;
    e.preventDefault();
    const destino = addDias(b.dataset.fecha, paso);
    let objetivo = el.querySelector(`[data-fecha="${destino}"]`);
    if (!objetivo) {
      const meses = mesesActual();
      const ym = destino.slice(0, 7);
      if (!meses.includes(ym)) return;
      poner({ mes: ym, foco: destino });
      objetivo = el.querySelector(`[data-fecha="${destino}"]`);
    }
    if (objetivo) { el.querySelectorAll('.cal-btn[tabindex="0"]').forEach((x) => x.tabIndex = -1); objetivo.tabIndex = 0; objetivo.focus(); }
  });
}
