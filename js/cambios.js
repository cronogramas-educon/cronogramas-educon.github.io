import { esc } from './ui.js';
import { fechaLarga, cambioVigente, cap, ahora } from './utils-fecha.js';

const clave = (c) => `cronograma:visto:${document.documentElement.dataset.curso || 'curso'}:${c.id}:${c.cambio.detectadoEn}`;
const visto = (c) => { try { return localStorage.getItem(clave(c)) === '1'; } catch { return false; } };

export function cambiosVisibles(clases, cfg, t = ahora()) {
  return clases.filter((c) => cambioVigente(c, cfg, t) && !visto(c));
}

export function renderAvisos(el, clases, cfg, t) {
  const cs = cambiosVisibles(clases, cfg, t);
  if (!cs.length) { el.hidden = true; el.innerHTML = ''; return; }
  el.hidden = false;
  el.innerHTML = `<div class="dentro"><ul>${cs.map((c) =>
    `<li>Cambio de fecha: la ${esc(cap(c.clase.toLowerCase()))} pasó del ${esc(fechaLarga(c.cambio.fechaAnterior))} al ${esc(fechaLarga(c.fecha))}</li>`).join('')}</ul>
    <button class="btn" type="button" data-entendido>Entendido</button></div>`;
  el.querySelector('[data-entendido]').onclick = () => {
    cs.forEach((c) => { try { localStorage.setItem(clave(c), '1'); } catch { /* sin almacenamiento: el aviso vuelve al recargar */ } });
    el.hidden = true;
  };
}
