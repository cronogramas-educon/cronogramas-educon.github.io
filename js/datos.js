// Carga data.json (y config) sin caché del navegador; si falla la red, usa la última copia guardada.
const CLAVE = 'cronograma:copia';
const url = (ruta) => `${ruta}?m=${Math.floor(Date.now() / 60000)}`; // un valor por minuto: evita que la CDN sirva una copia vieja

const leerCopia = () => { try { return JSON.parse(localStorage.getItem(CLAVE)); } catch { return null; } };
const guardarCopia = (data) => { try { localStorage.setItem(CLAVE, JSON.stringify({ data, guardadoEn: new Date().toISOString() })); } catch { /* sin almacenamiento: se sigue igual */ } };

export async function cargarConfig() {
  try { const r = await fetch(url('config/contenido.json'), { cache: 'no-store' }); if (r.ok) return await r.json(); } catch { /* usa valores por defecto */ }
  return { mostrarLinksTeams: true, diasAvisoCambio: 14, contacto: {}, docentesExtra: {}, profesoresInstitucionales: [], siglas: [] };
}

/** Devuelve { data, desdeCopia, guardadoEn } o lanza si no hay red ni copia. */
export async function cargarDatos() {
  try {
    const r = await fetch(url('data/data.json'), { cache: 'no-store' });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    if (!data?.clases?.length) throw new Error('data.json vacío');
    guardarCopia(data);
    return { data, desdeCopia: false };
  } catch (e) {
    const c = leerCopia();
    if (c?.data) return { data: c.data, desdeCopia: true, guardadoEn: c.guardadoEn };
    throw e;
  }
}
