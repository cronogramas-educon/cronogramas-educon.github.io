// Estado de la vista, sincronizado con la URL para compartir filtros.
const CAMPOS = { q: 'q', docente: 'docente', unidad: 'unidad', estado: 'estado', vista: 'vista', mes: 'mes', ocultar: 'ocultar' };
export const estado = { vista: null, q: '', docente: '', unidad: '', estado: 'todas', ocultar: false, temas: false, mes: null, sel: null };
const oyentes = new Set();
export const suscribir = (f) => oyentes.add(f);

export function leerURL() {
  const p = new URLSearchParams(location.search);
  for (const k of Object.keys(CAMPOS)) if (p.has(k)) estado[k] = k === 'ocultar' ? p.get(k) === '1' : p.get(k);
}
function escribirURL() {
  const p = new URLSearchParams(location.search);
  for (const k of Object.keys(CAMPOS)) p.delete(k);
  if (estado.q) p.set('q', estado.q);
  if (estado.docente) p.set('docente', estado.docente);
  if (estado.unidad) p.set('unidad', estado.unidad);
  if (estado.estado !== 'todas') p.set('estado', estado.estado);
  if (estado.ocultar) p.set('ocultar', '1');
  if (estado.vista) p.set('vista', estado.vista);
  if (estado.mes) p.set('mes', estado.mes);
  const s = p.toString();
  try { history.replaceState(null, '', `${location.pathname}${s ? '?' + s : ''}${location.hash}`); } catch { /* file:// u otros */ }
}
export function poner(cambios) {
  Object.assign(estado, cambios);
  escribirURL();
  oyentes.forEach((f) => f());
}
export const hayFiltros = () => !!(estado.q || estado.docente || estado.unidad || estado.estado !== 'todas' || estado.ocultar);
