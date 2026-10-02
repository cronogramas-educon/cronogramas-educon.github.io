// Sitio base de administración: lee cursos.json (junto a esta página) y el data.json de cada curso.
import { esc, rangos, ic } from './ui.js';
import { ahora, estadoClase, fechaLarga, fechaLargaAnio, haceCuanto, cambioVigente, cap, hoyISO } from './utils-fecha.js';
import { horario } from './ui.js';

const $ = (id) => document.getElementById(id);
const CFG = { diasAvisoCambio: 14 };
const BASE = new URL('../../', location.href); // raíz del sitio

const traer = async (ruta) => {
  try { const r = await fetch(`${ruta}?m=${Math.floor(Date.now() / 60000)}`, { cache: 'no-store' }); return r.ok ? await r.json() : null; } catch { return null; }
};
const urlCurso = (c) => new URL(`${c.ruta}/`, BASE).href;

function analizar(c, d, error) {
  const t = ahora();
  const r = { c, d: d || null, error: error || null, estado: 'sin-datos', proxima: null, hechas: 0, falta: { prof: [], pat: [], link: [] }, cambios: [] };
  if (!d) return r;
  const cs = d.clases;
  r.hechas = cs.filter((x) => estadoClase(x, t) === 'pasada').length;
  r.proxima = cs.find((x) => estadoClase(x, t) !== 'pasada') ?? null;
  r.estado = r.hechas === cs.length ? 'terminado' : (r.hechas || estadoClase(cs[0], t) !== 'futura') ? 'en-curso' : 'por-empezar';
  // lo que ya pasó no se puede confirmar: solo se listan pendientes de clases futuras o en curso
  for (const x of cs) {
    if (estadoClase(x, t) === 'pasada') continue;
    if (!x.profesores.length) r.falta.prof.push(x.id);
    if (!x.asistentePat) r.falta.pat.push(x.id);
    if (!x.linkTeams) r.falta.link.push(x.id);
  }
  r.cambios = cs.filter((x) => cambioVigente(x, CFG, t)).map((x) => ({ ...x, curso: c }));
  return r;
}

const ETIQ = { 'por-empezar': 'Por empezar', 'en-curso': 'En curso', terminado: 'Terminado', 'sin-datos': 'Sin datos' };
const pendientesTxt = (r) => [
  r.falta.prof.length ? `Docente: ${rangos(r.falta.prof)}` : '',
  r.falta.pat.length ? `Asistente PAT: ${rangos(r.falta.pat)}` : '',
  r.falta.link.length ? `Enlace de Teams: ${rangos(r.falta.link)}` : '',
].filter(Boolean);

function tarjeta(r) {
  const { c, d, error } = r;
  const prox = r.proxima
    ? `<p class="prox"><span>Próxima</span><strong>${esc(cap(r.proxima.clase.toLowerCase()))}</strong>, ${esc(fechaLarga(r.proxima.fecha))}, ${esc(horario(r.proxima))}<br>${r.proxima.profesores.length ? esc(r.proxima.profesores.join(' y ')) : '<em class="pendiente">Docente por confirmar</em>'}</p>`
    : d ? '<p class="prox"><span>Estado</span>Todas las clases ya se realizaron.</p>' : '<p class="prox"><span>Estado</span>Aún no hay datos publicados. Se publican al guardar el Excel.</p>';
  const url = urlCurso(c);
  const n = pendientesTxt(r).length;
  return `<article class="curso papel" data-curso="${esc(c.id)}">
    <header><span class="sello ${r.estado === 'en-curso' ? 'hoy' : r.estado === 'terminado' ? 'pasada' : 'proxima'}">${ETIQ[r.estado]}</span><p class="tipo">${esc(c.tipo)}</p></header>
    <h3>${esc(c.programaCorto)}</h3>
    ${error ? `<p class="alerta" role="alert">${ic('warning')}<span>El último guardado del Excel no se pudo leer y se conserva la versión anterior: ${esc(error.mensaje)}</span></p>` : ''}
    ${prox}
    ${d ? `<div class="barra" role="img" aria-label="${r.hechas} de ${d.clases.length} clases realizadas"><i style="width:${Math.round(100 * r.hechas / d.clases.length)}%"></i></div>
    <p class="meta">${r.hechas} de ${d.clases.length} clases realizadas. Datos publicados ${esc(haceCuanto(d.meta.generadoEn))}.</p>` : ''}
    <p class="falta ${n ? '' : 'ok'}">${n ? `${ic('warning')}${n === 1 ? 'Falta confirmar 1 dato' : `Faltan confirmar ${n} datos`}` : `${ic('check')}Nada por confirmar`}</p>
    <div class="acciones-curso">
      <a class="btn rojo" href="${esc(url)}" target="_blank" rel="noopener">Abrir sitio${ic('arrow-up-right')}</a>
      <button class="btn" type="button" data-copiar="${esc(url)}">${ic('link-simple')}<span>Copiar enlace</span></button>
      <a class="btn" href="${esc(c.carpetaSharePoint)}" target="_blank" rel="noopener">${ic('folder-open')}Carpeta en SharePoint</a>
      ${c.urlPaginaOficial ? `<a class="btn" href="${esc(c.urlPaginaOficial)}" target="_blank" rel="noopener">Página oficial${ic('arrow-up-right')}</a>` : ''}
    </div>
    <p class="enlace-est"><small>Enlace para estudiantes</small><code>${esc(url)}</code></p>
  </article>`;
}

function tablaPendientes(rs) {
  const filas = rs.map((r) => {
    if (!r.d) return `<tr><th scope="row">${esc(r.c.programaCorto)}</th><td colspan="3" class="sin">Aún no hay datos publicados</td><td><a href="${esc(r.c.carpetaSharePoint)}" target="_blank" rel="noopener">Abrir carpeta</a></td></tr>`;
    const celda = (a) => (a.length ? `<td><span class="n">${a.length}</span> <small>clases ${esc(rangos(a))}</small></td>` : '<td class="ok">Completo</td>');
    return `<tr><th scope="row">${esc(r.c.programaCorto)}</th>${celda(r.falta.prof)}${celda(r.falta.pat)}${celda(r.falta.link)}
      <td><a href="${esc(r.c.carpetaSharePoint)}" target="_blank" rel="noopener">Abrir carpeta</a></td></tr>`;
  }).join('');
  $('tabla-pendientes').innerHTML = `<table class="tabla-pend"><thead><tr><th>Curso</th><th>Docente</th><th>Asistente PAT</th><th>Enlace de Teams</th><th>Excel</th></tr></thead><tbody>${filas}</tbody></table>`;
}

function listaCambios(rs) {
  const cs = rs.flatMap((r) => r.cambios);
  $('lista-cambios').innerHTML = cs.length
    ? `<ul class="cambios">${cs.map((x) => `<li><strong>${esc(x.curso.programaCorto)}</strong>: ${esc(cap(x.clase.toLowerCase()))} pasó del ${esc(fechaLarga(x.cambio.fechaAnterior))} al ${esc(fechaLarga(x.fecha))}. <small>Detectado ${esc(haceCuanto(x.cambio.detectadoEn))}.</small></li>`).join('')}</ul>`
    : '<p class="nota">No hay cambios de fecha vigentes en ningún curso.</p>';
}

function resumen(rs) {
  const en = rs.filter((r) => r.estado === 'en-curso').length, por = rs.filter((r) => r.estado === 'por-empezar').length;
  const faltas = rs.reduce((a, r) => a + pendientesTxt(r).length, 0);
  const errores = rs.filter((r) => r.error).length;
  $('resumen').innerHTML = `<strong>${rs.length} cursos.</strong> ${en} en curso, ${por} por empezar. ${faltas ? `${faltas} datos por confirmar.` : 'Nada por confirmar.'}${errores ? ` <span class="mal">${errores} con error al leer el Excel.</span>` : ''}`;
}

async function pintar(meta) {
  const rs = await Promise.all(meta.cursos.map(async (c) => {
    const [d, error] = await Promise.all([c.tieneDatos && traer(`${new URL(`${c.ruta}/data/data.json`, BASE)}`), c.tieneError && traer(`${new URL(`${c.ruta}/estado/error.json`, BASE)}`)]);
    return analizar(c, d, error);
  }));
  resumen(rs);
  $('cursos-lista').innerHTML = rs.map(tarjeta).join('');
  tablaPendientes(rs);
  listaCambios(rs);
  $('refresco').textContent = `Actualizado ${fechaLargaAnio(hoyISO())}`;
}

/** Copia con la API moderna y, si el navegador no deja (sin permiso o sin https), con un campo temporal. */
async function copiar(texto) {
  try { await Promise.race([navigator.clipboard.writeText(texto), new Promise((_, no) => setTimeout(no, 700))]); return true; } catch { /* se prueba el plan B */ }
  const t = document.createElement('textarea');
  t.value = texto; t.style.cssText = 'position:fixed;opacity:0'; document.body.appendChild(t); t.select();
  let ok = false;
  try { ok = document.execCommand('copy'); } catch { /* sin soporte */ }
  t.remove();
  return ok;
}

async function arrancar() {
  const meta = await traer('cursos.json');
  if (!meta) { $('cursos-lista').innerHTML = '<p class="nota">No se pudo cargar la lista de cursos.</p>'; return; }
  $('pie-carpeta').innerHTML = `<a href="${esc(meta.sharepointBase)}" target="_blank" rel="noopener">Abrir la carpeta EDU CONTINUA 2026 en SharePoint</a>`;
  await pintar(meta);
  document.addEventListener('click', async (e) => {
    const b = e.target.closest('[data-copiar]');
    if (!b) return;
    const ok = await copiar(b.dataset.copiar);
    const t = b.querySelector('span'); const antes = t.textContent;
    t.textContent = ok ? 'Enlace copiado' : 'Copia el enlace de abajo'; setTimeout(() => { t.textContent = antes; }, 1800);
  });
  setInterval(() => { if (document.visibilityState === 'visible') pintar(meta); }, 60000);
}
arrancar();
