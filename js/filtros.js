import { norm } from './ui.js';
import { estadoClase, fechaLargaAnio, fechaCorta } from './utils-fecha.js';

const pajar = new Map();
function texto(c) {
  const k = `${c.id}|${c.fecha}|${c.tema}|${c.profesor}|${c.asistentePat}`;
  let v = pajar.get(c.id);
  if (!v || v.k !== k) {
    v = { k, t: norm([c.clase, c.unidad, c.tema, c.profesor, c.asistentePat, fechaLargaAnio(c.fecha), fechaCorta(c.fecha), c.fecha].join(' | ')) };
    pajar.set(c.id, v);
  }
  return v.t;
}

export function filtrar(clases, f, t) {
  const q = norm(f.q).trim();
  return clases.filter((c) => {
    if (f.docente && !c.profesores.includes(f.docente)) return false;
    if (f.unidad && c.unidadSlug !== f.unidad) return false;
    const pasada = estadoClase(c, t) === 'pasada';
    if (f.estado === 'proximas' && pasada) return false;
    if (f.estado === 'realizadas' && !pasada) return false;
    if (f.ocultar && pasada) return false;
    return !q || texto(c).includes(q);
  });
}
