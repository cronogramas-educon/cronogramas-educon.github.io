// Todo se calcula en hora de Colombia (UTC-5, sin horario de verano), sin importar la zona del visitante.
const DIAS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
export const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const NBSP = ' ';

// ?ahora=2026-10-14T17:30:00-05:00 simula la hora (el reloj sigue avanzando desde ahí)
const sim = new URLSearchParams(location.search).get('ahora');
const desfase = sim && !isNaN(Date.parse(sim)) ? Date.parse(sim) - Date.now() : 0;
export const ahora = () => new Date(Date.now() + desfase);

export const hoyISO = (d = ahora()) => new Date(d.getTime() - 5 * 3600e3).toISOString().slice(0, 10);
const utc = (iso) => { const [y, m, d] = iso.split('-').map(Number); return new Date(Date.UTC(y, m - 1, d)); };
export const addDias = (iso, n) => new Date(utc(iso).getTime() + n * 864e5).toISOString().slice(0, 10);
export const diaSemana = (iso) => utc(iso).getUTCDay(); // 0 domingo
export const diaNombre = (iso) => DIAS[diaSemana(iso)];
export const lunesDe = (iso) => addDias(iso, -((diaSemana(iso) + 6) % 7));
export const partes = (iso) => { const [y, m, d] = iso.split('-').map(Number); return { y, m, d }; };

export const fechaLarga = (iso) => { const p = partes(iso); return `${diaNombre(iso)} ${p.d} de ${MESES[p.m - 1]}`; };
export const fechaLargaAnio = (iso) => `${fechaLarga(iso)} de ${partes(iso).y}`;
export const fechaCorta = (iso) => { const p = partes(iso); return `${p.d} ${MESES[p.m - 1].slice(0, 3)}`; };
export const mesAnio = (ym) => { const [y, m] = ym.split('-').map(Number); return `${MESES[m - 1]} de ${y}`; };
export const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

export function hora12(hhmm) {
  const [h, m] = hhmm.split(':').map(Number);
  return `${h % 12 || 12}:${String(m).padStart(2, '0')}${NBSP}${h >= 12 ? 'p.' : 'a.'}${NBSP}m.`;
}

/** pasada | envivo | hoy | futura */
export function estadoClase(c, t = ahora()) {
  const ms = t.getTime();
  if (ms >= Date.parse(c.fin)) return 'pasada';
  if (ms >= Date.parse(c.inicio)) return 'envivo';
  return hoyISO(t) === c.fecha ? 'hoy' : 'futura';
}

export function desglose(ms) {
  const s = Math.max(0, Math.floor(ms / 1000));
  return { d: Math.floor(s / 86400), h: Math.floor(s % 86400 / 3600), m: Math.floor(s % 3600 / 60), s: s % 60 };
}

export function haceCuanto(desde, t = ahora()) {
  const s = Math.max(0, (t.getTime() - new Date(desde).getTime()) / 1000);
  if (s < 60) return 'hace un momento';
  if (s < 3600) return `hace ${Math.floor(s / 60)} min`;
  if (s < 86400) return `hace ${Math.floor(s / 3600)} h`;
  const d = Math.floor(s / 86400);
  return `hace ${d} ${d === 1 ? 'día' : 'días'}`;
}

/** Cambio de fecha vigente: no vencido por tiempo y la clase aún no pasó. */
export function cambioVigente(c, cfg, t = ahora()) {
  if (!c.cambio) return false;
  const dias = (t - Date.parse(c.cambio.detectadoEn)) / 864e5;
  return dias <= (cfg.diasAvisoCambio ?? 14) && estadoClase(c, t) !== 'pasada';
}
