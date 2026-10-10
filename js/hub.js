// Sitio base de administración: lee cursos.json (junto a esta página) y el data.json de cada curso.
import { esc, rangos, ic } from './ui.js';
import { addDias, ahora, estadoClase, fechaLarga, fechaLargaAnio, haceCuanto, cambioVigente, cap, hoyISO, mesAnio } from './utils-fecha.js';
import { horario } from './ui.js';
import { urgentes, salud, agenda, choques, reportes, horasTxt, csv } from './hub-analisis.js';

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
  const sa = salud(r, ahora());
  return `<article class="curso papel" data-curso="${esc(c.id)}">
    <p class="semaforo ${sa.nivel}" title="${esc(sa.motivo)}"><i aria-hidden="true"></i>${esc(sa.texto)}<small>${esc(sa.motivo)}</small></p>
    <header><span class="sello ${r.estado === 'en-curso' ? 'hoy' : r.estado === 'terminado' ? 'pasada' : 'proxima'}">${ETIQ[r.estado]}</span><p class="tipo">${c.periodo ? `Periodo ${esc(c.periodo)}` : esc(c.tipo)}</p></header>
    <h3>${esc(c.programaCorto)}</h3>
    ${error ? `<p class="alerta" role="alert">${ic('warning')}<span>El último guardado del Excel no se pudo leer y se conserva la versión anterior: ${esc(error.mensaje)}</span></p>` : ''}
    ${prox}
    ${d ? `<div class="barra" role="img" aria-label="${r.hechas} de ${d.clases.length} clases realizadas"><i style="width:${Math.round(100 * r.hechas / d.clases.length)}%"></i></div>
    <p class="meta">${r.hechas} de ${d.clases.length} clases realizadas. Datos publicados ${esc(haceCuanto(d.meta.generadoEn))}.</p>` : ''}
    <p class="teams-av">${c.avisosTeams ? `${ic('check')}Avisos de cambio de fecha por el grupo de Teams` : `${ic('warning')}Sin grupo de Teams para avisos a estudiantes`}</p>
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

function resumen(rs, archivados) {
  const en = rs.filter((r) => r.estado === 'en-curso').length, por = rs.filter((r) => r.estado !== 'en-curso').length;
  const faltas = rs.reduce((a, r) => a + pendientesTxt(r).length, 0);
  const errores = rs.filter((r) => r.error).length;
  $('resumen').innerHTML = `<strong>${rs.length} ${rs.length === 1 ? 'curso activo' : 'cursos activos'}.</strong> ${en} en curso, ${por} por empezar. ${faltas ? `${faltas} datos por confirmar.` : 'Nada por confirmar.'}${archivados ? ` ${archivados} en el archivo.` : ''}${errores ? ` <span class="mal">${errores} con error al leer el Excel.</span>` : ''}`;
}

/** Cursos terminados: pasan solos al archivo, agrupados por periodo, con su página en modo lectura. */
function archivo(rs) {
  $('archivo').hidden = $('nav-archivo').hidden = !rs.length;
  const por = Map.groupBy(rs, (r) => r.c.periodo || 'Sin periodo');
  $('archivo-lista').innerHTML = [...por].sort((a, b) => b[0].localeCompare(a[0])).map(([periodo, lista]) => `<div class="periodo"><h3>Periodo ${esc(periodo)}</h3><ul>${lista.map((r) => {
    const url = urlCurso(r.c);
    return `<li><span><strong>${esc(r.c.programaCorto)}</strong><small>${esc(r.c.tipo)}, terminó el ${esc(fechaLargaAnio(r.d.meta.fin))}</small></span>
      <a class="btn" href="${esc(url)}" target="_blank" rel="noopener">Abrir${ic('arrow-up-right')}</a>
      <button class="btn" type="button" data-copiar="${esc(url)}">${ic('link-simple')}<span>Copiar enlace</span></button></li>`;
  }).join('')}</ul></div>`).join('');
}

/** Cómo agregar o cambiar cursos, estado del Excel de registro y carpetas que llegaron sin estar registradas. */
function registro(meta) {
  const r = meta.registro ?? {};
  const avisos = [...(r.error ? [`El último guardado del registro no se pudo leer y se conserva el anterior: ${r.error}`] : []), ...(r.avisos ?? [])];
  $('registro-estado').innerHTML = `${avisos.length ? `<ul class="alertas">${avisos.map((a) => `<li class="alerta" role="alert">${ic('warning')}<span>${esc(a)}</span></li>`).join('')}</ul>` : ''}
    ${(meta.sinRegistrar ?? []).length ? `<div class="sin-registrar"><h3>Carpetas con Excel que no están en el registro</h3><p class="nota">Esos Excel se guardaron pero no se publica nada de ellos hasta que agregues el curso al Excel de registro.</p><ul>${meta.sinRegistrar.map((x) => `<li><span>${esc(x.carpeta)}</span><a href="${esc(x.enlace)}" target="_blank" rel="noopener">Abrir carpeta</a></li>`).join('')}</ul></div>` : ''}`;
  $('registro-abrir').hidden = !r.enlace;
  if (r.enlace) $('registro-abrir').href = r.enlace;
  $('registro-pie').textContent = r.actualizado ? `Registro leído ${haceCuanto(r.actualizado)}.` : '';
}

const hora = (c) => horario(c);
const filaClase = (x) => `<strong>${esc(x.curso.programaCorto)}</strong>, ${esc(cap(x.c.clase.toLowerCase()))}`;

/** Lo que hay que resolver ya: clases de los próximos 14 días a las que les falta algo, de todos los cursos juntos. */
function seccionUrgente(rs) {
  const u = urgentes(rs, ahora());
  const fila = (x) => `<tr><th scope="row">${esc(fechaLarga(x.c.fecha))}<small>${esc(hora(x.c))}</small></th><td>${filaClase(x)}</td><td>${x.faltas.map((f) => `<span class="n">${esc(f)}</span>`).join(' ')}</td><td><a href="${esc(x.curso.carpetaSharePoint)}" target="_blank" rel="noopener">Abrir carpeta</a></td></tr>`;
  const tabla = (xs) => `<div class="tabla-envoltura"><table class="tabla-pend tabla-urg"><thead><tr><th>Fecha</th><th>Curso</th><th>Falta confirmar</th><th>Excel</th></tr></thead><tbody>${xs.map(fila).join('')}</tbody></table></div>`;
  $('urgente-lista').innerHTML = u.length
    ? `<p class="resumen-sec"><strong>${u.length}</strong> ${u.length === 1 ? 'clase' : 'clases'} en los próximos 14 días con datos sin confirmar.</p>${tabla(u.slice(0, 8))}${u.length > 8 ? `<details class="mas"><summary>Ver las ${u.length - 8} restantes</summary>${tabla(u.slice(8))}</details>` : ''}`
    : `<p class="nota ok-nota">${ic('check')}Nada urgente: las clases de los próximos 14 días tienen docente, asistente y enlace.</p>`;
}

/** Agenda de las próximas 4 semanas de todos los cursos, con los choques de docentes o asistentes arriba. */
function seccionAgenda(rs) {
  const t = ahora(), ch = choques(rs, t), ag = agenda(rs, t);
  const aviso = ch.length
    ? `<ul class="alertas">${ch.map((k) => `<li class="alerta" role="alert">${ic('warning')}<span><strong>${esc(k.rol)} ${esc(k.nombre)}</strong> tiene dos clases a la vez el ${esc(fechaLarga(k.a.c.fecha))}: ${esc(k.a.curso.programaCorto)} (${esc(hora(k.a.c))}) y ${esc(k.b.curso.programaCorto)} (${esc(hora(k.b.c))}).</span></li>`).join('')}</ul>`
    : `<p class="nota ok-nota">${ic('check')}Sin choques: ningún docente ni asistente tiene dos clases a la vez.</p>`;
  const dia = ([f, lista]) => `<div class="dia-agenda"><h3>${esc(cap(fechaLarga(f)))}</h3><ul>${lista.map((x) => `<li><span class="h">${esc(hora(x.c))}</span><span>${filaClase(x)}<small>${x.c.profesores.length ? esc(x.c.profesores.join(' y ')) : '<em class="pendiente">Docente por confirmar</em>'}</small></span></li>`).join('')}</ul></div>`;
  const tope = addDias(hoyISO(t), 7);
  const pronto = [...Map.groupBy(ag.filter((x) => x.c.fecha <= tope), (x) => x.c.fecha)], luego = [...Map.groupBy(ag.filter((x) => x.c.fecha > tope), (x) => x.c.fecha)];
  $('agenda-lista').innerHTML = aviso + (ag.length
    ? `${pronto.map(dia).join('') || '<p class="nota">No hay clases en los próximos 7 días.</p>'}${luego.length ? `<details class="mas"><summary>Ver las semanas siguientes (${luego.reduce((n, [, l]) => n + l.length, 0)} clases)</summary>${luego.map(dia).join('')}</details>` : ''}`
    : '<p class="nota">No hay clases programadas en las próximas 4 semanas.</p>');
}

/** Horas por docente, por curso y por mes, con descarga a Excel (CSV) y PDF. Se puede filtrar por periodo. */
let periodoSel = '', ultimosRs = [];
function seccionReportes(rs) {
  const periodos = [...new Set(rs.map((r) => r.c.periodo).filter(Boolean))].sort().reverse();
  $('rep-periodo').innerHTML = `<option value="">Todos los periodos</option>${periodos.map((p) => `<option value="${esc(p)}"${p === periodoSel ? ' selected' : ''}>Periodo ${esc(p)}</option>`).join('')}`;
  const sel = rs.filter((r) => !periodoSel || r.c.periodo === periodoSel);
  const rep = reportes(sel, ahora());
  const tabla = (cab, filas) => `<div class="tabla-envoltura"><table class="tabla-pend"><thead><tr>${cab.map((h) => `<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${filas.map((f) => `<tr>${f.map((c, i) => (i ? `<td>${c}</td>` : `<th scope="row">${c}</th>`)).join('')}</tr>`).join('')}</tbody></table></div>`;
  const n1 = (e) => String(Math.round(e * 10) / 10).replace('.', ',');
  $('rep-docentes').innerHTML = `<details class="mas"><summary>Ver los ${rep.docentes.length} docentes</summary>${tabla(['Docente', 'Clases', 'Horas', 'Ya realizadas', 'Cursos'], rep.docentes.map((e) => [esc(e.k), e.clases, esc(horasTxt(e)), n1(e.hechas), esc(e.cursos.join(', '))]))}</details>`;
  $('rep-cursos').innerHTML = tabla(['Curso', 'Periodo', 'Clases', 'Horas', 'Docentes'], rep.cursos.map((e) => [esc(e.nombre), esc(e.periodo || 'Por confirmar'), e.clases, esc(horasTxt(e)), e.docentes]));
  $('rep-meses').innerHTML = tabla(['Mes', 'Clases', 'Horas'], rep.meses.map((e) => [esc(cap(mesAnio(e.k))), e.clases, esc(horasTxt(e))]));
  $('rep-nota').textContent = 'Las horas salen de la columna Horas del Excel. Donde esa casilla está vacía se calculan con el horario del curso y se marcan como estimadas. Una clase con dos docentes cuenta completa para cada uno.';
  reporteActual = rep;
}
let reporteActual = null;
const descargar = (nombre, texto) => { const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(new Blob([texto], { type: 'text/csv;charset=utf-8' })), download: nombre }); a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); };
const csvReporte = () => {
  const r = reporteActual, h = (e) => Math.round(e.horas * 10) / 10;
  return csv(['Tipo', 'Nombre', 'Periodo', 'Clases', 'Horas', 'Horas estimadas con el horario (clases)', 'Horas ya realizadas'], [
    ...r.docentes.map((e) => ['Docente', e.k, '', e.clases, h(e), e.estimadas, Math.round(e.hechas * 10) / 10]),
    ...r.cursos.map((e) => ['Curso', e.nombre, e.periodo, e.clases, h(e), e.estimadas, Math.round(e.hechas * 10) / 10]),
    ...r.meses.map((e) => ['Mes', e.k, '', e.clases, h(e), e.estimadas, Math.round(e.hechas * 10) / 10])]);
};

async function pintar(meta) {
  const rs = await Promise.all(meta.cursos.map(async (c) => {
    const [d, error] = await Promise.all([c.tieneDatos && traer(`${new URL(`${c.ruta}/data/data.json`, BASE)}`), c.tieneError && traer(`${new URL(`${c.ruta}/estado/error.json`, BASE)}`)]);
    return analizar(c, d, error);
  }));
  ultimosRs = rs;
  const activos = rs.filter((r) => r.estado !== 'terminado');
  resumen(activos, rs.length - activos.length);
  $('cursos-lista').innerHTML = activos.length ? activos.map(tarjeta).join('') : '<p class="nota">No hay cursos activos. Agrega los del nuevo periodo en el Excel de registro.</p>';
  tablaPendientes(activos);
  listaCambios(activos);
  archivo(rs.filter((r) => r.estado === 'terminado'));
  seccionUrgente(activos);
  seccionAgenda(activos);
  seccionReportes(rs);
  registro(meta);
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
  $('pie-carpeta').innerHTML = `<a href="${esc(meta.carpetaActual)}" target="_blank" rel="noopener">Abrir la carpeta ${esc(meta.nombreCarpetaActual)} en SharePoint</a>`;
  await pintar(meta);
  $('rep-periodo').onchange = (e) => { periodoSel = e.target.value; seccionReportes(ultimosRs); };
  $('rep-csv').onclick = () => descargar(`reporte-horas${periodoSel ? `-${periodoSel}` : ''}.csv`, csvReporte());
  $('rep-pdf').onclick = () => window.print();
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
