import { fechaLarga, fechaLargaAnio, hora12, cap } from './utils-fecha.js';
import { ic } from './iconos.js';

const ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ESC[c]);

let siglas = new Set();
export const usarSiglas = (l = []) => { siglas = new Set(l.map((x) => x.toUpperCase())); };
/** Los nombres de unidad vienen en mayúsculas en el Excel: se muestran en minúscula con inicial, salvo las siglas de config. */
export function legible(s) {
  const letras = s.replace(/[^\p{L}]/gu, '');
  if (!letras || letras.replace(/[^\p{Lu}]/gu, '').length / letras.length < 0.8) return s; // ya viene en minúscula con inicial
  return s.toLowerCase().replace(/^\p{L}/u, (m) => m.toUpperCase()).replace(/[\p{L}/]+/gu, (w) => (siglas.has(w.toUpperCase()) ? w.toUpperCase() : w));
}

export const norm = (s) => String(s ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

/** Escapa y resalta coincidencias sin distinguir mayúsculas ni tildes. */
export function resaltar(texto, q) {
  const t = String(texto ?? '');
  const n = norm(q).trim();
  if (!n) return esc(t);
  let plano = '';
  const mapa = [];
  [...t].forEach((ch, i) => { const x = norm(ch); for (const _ of x) mapa.push(i); plano += x; });
  const rangos = [];
  for (let p = plano.indexOf(n); p !== -1; p = plano.indexOf(n, p + n.length)) rangos.push([mapa[p], mapa[p + n.length - 1] + 1]);
  if (!rangos.length) return esc(t);
  const chars = [...t];
  let out = '', pos = 0;
  for (const [a, b] of rangos) { if (a < pos) continue; out += esc(chars.slice(pos, a).join('')) + '<mark>' + esc(chars.slice(a, b).join('')) + '</mark>'; pos = b; }
  return out + esc(chars.slice(pos).join(''));
}

export function nombreCorto(n) {
  if (n === n.toUpperCase()) return n;
  const p = n.split(/\s+/).filter(Boolean);
  if (p.length === 1) return p[0];
  const ap = p.length > 2 && p.at(-1).length <= 2 ? p.at(-2) : p.at(-1); // "Beatriz Londoño P" -> Londoño
  return `${p[0][0]}. ${ap}`;
}
export const iniciales = (n) => { const p = n.split(/\s+/).filter((x) => x.length > 1); return n === n.toUpperCase() ? n[0] : (p[0][0] + (p.length > 1 ? p[p.length - 1][0] : '')).toUpperCase(); };
export const docentesCorto = (c) => (c.profesores.length > 1 ? `${nombreCorto(c.profesores[0])} +${c.profesores.length - 1}` : c.profesores.length ? nombreCorto(c.profesor) : PENDIENTE);

export function rangos(ids) {
  const o = [...ids].sort((a, b) => a - b), out = [];
  for (let i = 0; i < o.length; i++) {
    let j = i;
    while (o[j + 1] === o[j] + 1) j++;
    out.push(j - i >= 2 ? `${o[i]} a ${o[j]}` : o.slice(i, j + 1).join(', '));
    i = j;
  }
  return out.join(', ');
}

export const horario = (c) => `${hora12(c.inicio.slice(11, 16))} a ${hora12(c.fin.slice(11, 16))}`;
export const PENDIENTE = 'Por confirmar';

export function botonTeams(c, cfg, estado) {
  if (!cfg.mostrarLinksTeams || estado === 'pasada') return '';
  if (!c.linkTeams) return `<span class="btn btn-teams btn-pendiente" role="note" aria-disabled="true">${ic('video-camera')}Enlace por confirmar</span>`;
  const prim = estado === 'hoy' || estado === 'envivo';
  return `<a class="btn btn-teams${prim ? ' rojo' : ''}" href="${esc(c.linkTeams)}" target="_blank" rel="noopener noreferrer">${ic('video-camera')}Unirme en Teams</a>`;
}

export function insignias(c, estado, esProxima, repro) {
  const o = [];
  if (repro) o.push('<span class="sello repro">Reprogramada</span>');
  if (estado === 'envivo') o.push('<span class="sello envivo">En vivo</span>');
  else if (estado === 'hoy') o.push('<span class="sello hoy">Hoy</span>');
  else if (estado === 'pasada') o.push('<span class="sello pasada">Realizada</span>');
  if (esProxima && estado !== 'envivo' && estado !== 'hoy') o.push('<span class="sello proxima">Próxima</span>');
  return o.join('');
}

/** Ficha de la clase. Con titulo=true (panel del calendario) repite el nombre y la unidad. */
export function fichaClase(c, ctx) {
  const { cfg, q = '', estado, repro, titulo } = ctx;
  const fecha = repro
    ? `<span class="tachada">${esc(fechaLargaAnio(c.cambio.fechaAnterior))}</span> ${esc(fechaLargaAnio(c.fecha))}`
    : esc(fechaLargaAnio(c.fecha));
  return `<div class="ficha-clase">
    ${titulo ? `<div class="fila-estados" style="justify-content:flex-start;margin-bottom:10px">${insignias(c, estado, ctx.esProxima, repro)}</div>
    <h3>${resaltar(cap(c.clase.toLowerCase()), q)}</h3>${c.unidad ? `<p class="u">${resaltar(legible(c.unidad), q)}</p>` : ''}` : ''}
    <ul class="temas">${c.temaPuntos.map((p) => `<li>${resaltar(p, q)}</li>`).join('')}</ul>
    <dl>
      <dt>Docente</dt><dd>${c.profesores.length ? c.profesores.map((p) => resaltar(p, q)).join(' y ') : `<span class="pendiente">${PENDIENTE}</span>`}</dd>
      <dt>Fecha</dt><dd>${fecha}</dd>
      <dt>Horario</dt><dd>${esc(horario(c))}, hora de Colombia</dd>
      <dt>Te acompaña</dt><dd>${c.asistentePat ? resaltar(c.asistentePat, q) : `<span class="pendiente">${PENDIENTE}</span>`}</dd>
    </dl>
    <div class="acc">${botonTeams(c, cfg, estado)}<button class="btn" type="button" data-ics="${c.id}">${ic('calendar-plus')}Agregar a mi calendario</button></div>
  </div>`;
}
export { fechaLarga, ic };
