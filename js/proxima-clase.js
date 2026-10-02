import { esc, horario, legible, ic, PENDIENTE } from './ui.js';
import { ahora, estadoClase, desglose, hora12, diaNombre, partes, MESES, cap } from './utils-fecha.js';

let el, ctxActual = null, clave = '', primera = true;
const dos = (n) => String(n).padStart(2, '0');

export const proximaDe = (clases, t = ahora()) => clases.find((c) => estadoClase(c, t) !== 'pasada') ?? null;

function zonaLocal(c) {
  const ini = new Date(c.inicio);
  if (ini.getTimezoneOffset() === 300) return '';
  const f = (d) => d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
  return ` En tu zona: ${esc(f(ini))} a ${esc(f(new Date(c.fin)))}.`;
}

function teams(c, cfg, estado) {
  if (!cfg.mostrarLinksTeams) return '';
  if (!c.linkTeams) return `<span class="btn btn-pendiente" role="note" aria-disabled="true">${ic('video-camera')}Enlace por confirmar</span>`;
  const prim = estado === 'envivo' || estado === 'hoy';
  return `<a class="btn${prim ? ' rojo' : ''}" href="${esc(c.linkTeams)}" target="_blank" rel="noopener noreferrer">${ic('video-camera')}Unirme en Teams<span class="flecha-btn">${ic('arrow-up-right')}</span></a>`;
}

function cuentaHTML(c, estado, t) {
  if (estado === 'envivo') return `<p class="cuenta-texto">En vivo ahora</p><p class="cuenta-sub" data-resta></p>`;
  const r = desglose(Date.parse(c.inicio) - t.getTime());
  const bloques = estado === 'hoy' ? [['h', 'horas'], ['m', 'min'], ['s', 'seg']] : [['d', 'días'], ['h', 'horas'], ['m', 'min'], ['s', 'seg']];
  return `${estado === 'hoy' ? `<p class="cuenta-texto">Hoy a las ${hora12(c.inicio.slice(11, 16))}</p>` : '<p class="cuenta-sub">Falta</p>'}
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
    if (clave !== 'fin') { clave = 'fin'; el.innerHTML = `<div class="tag-proxima papel fin"><div class="tag-info"><h2>${meta.tipo === 'Diplomado' ? 'El diplomado ha finalizado' : 'El curso ha finalizado'}</h2><p class="tag-datos">Gracias por acompañarnos. Las clases anteriores siguen en el cronograma.</p></div></div>`; }
    return;
  }
  const estado = estadoClase(c, t);
  const k = `${c.id}|${c.fecha}|${estado}`;
  if (k !== clave) {
    clave = k;
    const p = partes(c.fecha);
    const sub = c.unidad ? legible(c.unidad) : c.temaPuntos[0] ?? '';  // sin unidad en el Excel se muestra el primer tema
    const sello = estado === 'envivo' ? '<span class="sello envivo sello-esquina">En vivo</span>' : estado === 'hoy' ? '<span class="sello hoy sello-esquina">Hoy</span>' : '';
    el.innerHTML = `<div class="tag-proxima papel es-${estado}${primera ? ' nueva' : ''}" role="region" aria-label="Próxima clase">
      <div class="tag-fecha"><span class="dia-sem">${esc(diaNombre(c.fecha))}</span><span class="dia-num">${p.d}</span><span class="mes">${esc(MESES[p.m - 1])}</span></div>
      ${sello}
      <div class="tag-info">
        <h2>${esc(cap(c.clase.toLowerCase()))}</h2>
        ${sub ? `<p class="tag-unidad" title="${esc(sub)}">${esc(sub)}</p>` : ''}
        <p class="tag-datos">${c.profesores.length ? esc(c.profesores.join(' y ')) : `<span class="pendiente">Docente por confirmar</span>`}. ${esc(horario(c))}, hora de Colombia.${zonaLocal(c)}</p>
      </div>
      <div class="tag-cuenta">${cuentaHTML(c, estado, t)}${teams(c, cfg, estado)}</div>
    </div>`;
    primera = false;
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
