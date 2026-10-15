import { esc } from './ui.js';
import { fechaLarga, cambioVigente, cap, ahora, hoyISO } from './utils-fecha.js';

const clave = (c) => `cronograma:visto:${document.documentElement.dataset.curso || 'curso'}:${c.id}:${c.cambio.detectadoEn}`;
const visto = (c) => { try { return localStorage.getItem(clave(c)) === '1'; } catch { return false; } };
const claveCancelada = (c) => `cronograma:visto:${document.documentElement.dataset.curso || 'curso'}:cancelada:${c.id}:${c.fecha}`;
const vistaCancelada = (c) => { try { return localStorage.getItem(claveCancelada(c)) === '1'; } catch { return false; } };
/** Clases canceladas que todavía importan: su fecha no ha pasado (o no tiene fecha) y la persona no las ha descartado. */
export const canceladasVisibles = (canceladas = [], t = ahora()) => canceladas.filter((c) => (!c.fecha || c.fecha >= hoyISO(t)) && !vistaCancelada(c));

export function cambiosVisibles(clases, cfg, t = ahora()) {
  return clases.filter((c) => cambioVigente(c, cfg, t) && !visto(c));
}

export function renderAvisos(el, clases, cfg, t, canceladas = []) {
  const cs = cambiosVisibles(clases, cfg, t);
  const ca = canceladasVisibles(canceladas, t);
  if (!cs.length && !ca.length) { el.hidden = true; el.innerHTML = ''; return; }
  el.hidden = false;
  el.innerHTML = `<div class="dentro"><ul>${ca.map((c) =>
    `<li>Clase cancelada: la ${esc(cap(c.clase.toLowerCase()))}${c.fecha ? ` del ${esc(fechaLarga(c.fecha))}` : ''} no se dicta</li>`).join('')}${cs.map((c) =>
    `<li>Cambio de fecha: la ${esc(cap(c.clase.toLowerCase()))} pasó del ${esc(fechaLarga(c.cambio.fechaAnterior))} al ${esc(fechaLarga(c.fecha))}</li>`).join('')}</ul>
    <button class="btn" type="button" data-entendido>Entendido</button></div>`;
  el.querySelector('[data-entendido]').onclick = () => {
    const marcar = (k) => { try { localStorage.setItem(k, '1'); } catch { /* sin almacenamiento: el aviso vuelve al recargar */ } };
    cs.forEach((c) => marcar(clave(c)));
    ca.forEach((c) => marcar(claveCancelada(c)));
    el.hidden = true;
  };
}
