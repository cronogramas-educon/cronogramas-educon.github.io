import { esc, horario, legible } from './ui.js';
import { ahora, estadoClase, desglose, hora12, diaNombre, partes, MESES, cap } from './utils-fecha.js';

let el, ctxActual = null, clave = '';
const dos = (n) => String(n).padStart(2, '0');

export const proximaDe = (clases, t = ahora()) => clases.find((c) => estadoClase(c, t) !== 'pasada') ?? null;

function zonaLocal(c, meta) {
  const ini = new Date(c.inicio);
  if (ini.getTimezoneOffset() === 300) return '';
  const f = (d) => d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
  return `<span><b>En tu zona</b> ${esc(f(ini))} a ${esc(f(new Date(c.fin)))}</span>`;
}

function teams(c, cfg, estado) {
  if (!cfg.mostrarLinksTeams || !c.linkTeams) return '';
  return `<a class="chevron-cta${estado === 'envivo' || estado === 'hoy' ? ' solid' : ''}" href="${esc(c.linkTeams)}" target="_blank" rel="noopener noreferrer">Unirme en Teams</a>`;
}

function cuentaHTML(c, estado, t) {
  if (estado === 'envivo') return `<p class="cuenta-texto">En vivo ahora</p><p class="cuenta-sub" data-resta></p>`;
  const r = desglose(Date.parse(c.inicio) - t.getTime());
  const bloques = estado === 'hoy' ? [['h', 'horas'], ['m', 'min'], ['s', 'seg']] : [['d', 'días'], ['h', 'horas'], ['m', 'min'], ['s', 'seg']];
  return `${estado === 'hoy' ? `<p class="cuenta-texto">Hoy a las ${hora12(c.inicio.slice(11, 16))}</p>` : ''}
    <div class="cuenta-num" data-cuenta>${bloques.map(([k, l]) => `<div><strong>${dos(r[k])}</strong><span>${l}</span></div>`).join('')}</div>`;
}

export function renderPanel(contenedor, clases, meta, cfg) {
  el = contenedor;
  ctxActual = { clases, meta, cfg };
  clave = '';
  tick();
}

export function tick() {
  if (!ctxActual) return;
  const { clases, meta, cfg } = ctxActual;
  const t = ahora();
  const c = proximaDe(clases, t);
  if (!c) {
    if (clave !== 'fin') { clave = 'fin'; el.innerHTML = `<div class="panel fin"><div class="panel-cuerpo"><p class="panel-estado">Cronograma completo</p><h2>El diplomado ha finalizado</h2><p class="panel-unidad">Gracias por acompañarnos. Las clases anteriores siguen disponibles en el cronograma.</p></div></div>`; }
    return;
  }
  const estado = estadoClase(c, t);
  const k = `${c.id}|${c.fecha}|${estado}`;
  if (k !== clave) {
    clave = k;
    const p = partes(c.fecha);
    const etiqueta = estado === 'envivo' ? '<span class="punto-vivo" aria-hidden="true"></span>En vivo ahora' : estado === 'hoy' ? 'Próxima clase, hoy' : 'Próxima clase';
    const prim = c.temaPuntos[0] ? `<p class="panel-unidad">${esc(c.temaPuntos[0])}</p>` : '';
    el.innerHTML = `<div class="panel${estado === 'envivo' ? ' envivo' : ''}" role="region" aria-label="Próxima clase">
      <div class="ficha"><span class="dia-sem">${esc(diaNombre(c.fecha).slice(0, 3))}</span><span class="dia-num">${p.d}</span><span class="mes">${esc(MESES[p.m - 1])}</span></div>
      <div class="panel-cuerpo">
        <p class="panel-estado">${etiqueta}</p>
        <h2>${esc(cap(c.clase.toLowerCase()))}</h2>
        <p class="panel-unidad" title="${esc(legible(c.unidad))}"><strong style="color:#fff">${esc(legible(c.unidad))}</strong></p>${prim}
        <div class="panel-datos"><span><b>Docente</b> ${esc(c.profesores.join(' y '))}</span><span><b>Horario</b> ${esc(horario(meta))}, hora de Colombia</span>${zonaLocal(c, meta)}</div>
      </div>
      <div class="cuenta">${cuentaHTML(c, estado, t)}${teams(c, cfg, estado)}</div>
    </div>`;
  }
  if (estado === 'envivo') {
    const r = desglose(Date.parse(c.fin) - t.getTime());
    const s = el.querySelector('[data-resta]');
    if (s) s.textContent = `Termina en ${r.h ? r.h + ' h ' : ''}${r.m} min`;
  } else {
    const r = desglose(Date.parse(c.inicio) - t.getTime());
    const ks = estado === 'hoy' ? ['h', 'm', 's'] : ['d', 'h', 'm', 's'];
    el.querySelectorAll('[data-cuenta] strong').forEach((n, i) => { n.textContent = dos(r[ks[i]]); });
  }
}
