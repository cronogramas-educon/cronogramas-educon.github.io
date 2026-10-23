// Sitio base de administración: lee cursos.json (junto a esta página) y el data.json de cada curso.
import { esc, rangos, ic, norm } from './ui.js';
import { addDias, ahora, estadoClase, fechaLarga, fechaLargaAnio, haceCuanto, cambioVigente, cap, hoyISO, mesAnio } from './utils-fecha.js';
import { horario } from './ui.js';
import { urgentes, salud, agenda, choques, reportes, horasTxt, csv } from './hub-analisis.js';
import { resumenAsistencia, bandeja, htmlBandeja, htmlAsistenciaCurso, cierre, htmlCierre, filasCierre, TITULOS_CIERRE } from './hub-asistencia.js';
import { buscar, htmlResultados } from './hub-buscador.js';

const $ = (id) => document.getElementById(id);
const CFG = { diasAvisoCambio: 14 };
const BASE = new URL('../../', location.href); // raíz del sitio

const traer = async (ruta) => {
  try { const r = await fetch(`${ruta}?m=${Math.floor(Date.now() / 60000)}`, { cache: 'no-store' }); return r.ok ? await r.json() : null; } catch { return null; }
};
const urlCurso = (c) => new URL(`${c.ruta}/`, BASE).href;

function analizar(c, d, error) {
  const t = ahora();
  const r = { c, d: d || null, error: error || null, fallo: !!c.tieneDatos && !d, estado: 'sin-datos', proxima: null, hechas: 0, falta: { prof: [], pat: [], link: [] }, cambios: [] };
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

const etiquetaPeriodo = (c) => (c.periodo ? `Periodo ${c.periodo}${c.cohorte ? `, ${c.cohorte}` : ''}` : c.tipo);

let formBienvenida = '', preguntasBienv = {};
const cacheBienvenida = new Map();
/** Vista previa del mensaje de bienvenida y botón que abre el formulario de envío con el curso ya elegido. */
function bienvenidaHtml(c, pat) {
  if (!c.bienvenida) return `<p class="teams-av">${ic('warning')}Sin equipo de Teams o sin cronograma: aún no se puede enviar la bienvenida</p>`;
  const q = (id, v) => (id && v ? `&${id}=${encodeURIComponent(`"${v}"`)}` : '');
  const url = formBienvenida ? `${formBienvenida}${encodeURIComponent(`"${c.id}"`)}${q(preguntasBienv.pat, pat)}` : '';
  return `<details class="curso-asis curso-bienv" data-bienv-curso="${esc(c.id)}"><summary><span class="ca-texto"><strong>Mensaje de bienvenida</strong><small>Para el equipo de Teams de este curso</small></span><span class="asis-abrir" aria-hidden="true"></span></summary>
    <div class="asis-detalle"><div class="bienv-cuerpo">${cacheBienvenida.get(c.id) ?? '<p class="nota">Cargando el mensaje…</p>'}</div>
    <p class="bienv-aviso">Se publica en el canal General del equipo de este curso. Al pulsar el botón se abre un formulario donde escribes el nombre de la gestora logística y del estudiante PAT (el PAT viene escrito si ya está en el Excel). Revisa el mensaje antes de enviarlo y no lo envíes dos veces.</p>
    ${url ? `<a class="btn rojo" href="${esc(url)}" target="_blank" rel="noopener">Enviar al grupo de Teams${ic('arrow-up-right')}</a>` : '<p class="alerta">Falta configurar el formulario de envío.</p>'}</div></details>`;
}

function tarjeta(r) {
  const { c, d, error } = r;
  const prox = r.proxima
    ? `<p class="prox"><span>Próxima</span><strong>${esc(cap(r.proxima.clase.toLowerCase()))}</strong>, ${esc(fechaLarga(r.proxima.fecha))}, ${esc(horario(r.proxima))}<br>${r.proxima.profesores.length ? esc(r.proxima.profesores.join(' y ')) : '<em class="pendiente">Docente por confirmar</em>'}</p>`
    : d ? '<p class="prox"><span>Estado</span>Todas las clases ya se realizaron.</p>'
    : r.fallo ? `<p class="prox"><span>Estado</span>${ic('warning')} No se pudieron cargar los datos de este curso. Prueba con «Actualizar ahora».</p>`
    : '<p class="prox"><span>Estado</span>Aún no hay datos publicados. Se publican al guardar el Excel.</p>';
  const url = urlCurso(c);
  const n = pendientesTxt(r).length;
  const sa = salud(r, ahora());
  return `<article class="curso papel" data-curso="${esc(c.id)}">
    <p class="semaforo ${sa.nivel}" title="${esc(sa.motivo)}"><i aria-hidden="true"></i>${esc(sa.texto)}<small>${esc(sa.motivo)}</small></p>
    <header><span class="sello ${r.estado === 'en-curso' ? 'hoy' : r.estado === 'terminado' ? 'pasada' : 'proxima'}">${ETIQ[r.estado]}</span><p class="tipo">${esc(etiquetaPeriodo(c))}</p></header>
    <h3>${esc(c.programaCorto)}</h3>
    ${error ? `<p class="alerta" role="alert">${ic('warning')}<span>El último guardado del Excel no se pudo leer y se conserva la versión anterior: ${esc(error.mensaje)}</span></p>` : ''}
    ${prox}
    ${d ? `<div class="barra" role="img" aria-label="${r.hechas} de ${d.clases.length} clases realizadas"><i style="width:${Math.round(100 * r.hechas / d.clases.length)}%"></i></div>
    <p class="meta">${r.hechas} de ${d.clases.length} clases realizadas. Datos publicados ${esc(haceCuanto(d.meta.generadoEn))}.</p>` : ''}
    ${htmlAsistenciaCurso(r)}
    ${bienvenidaHtml(c, d?.asistentesPat?.join(' y '))}
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
    ? `<ul class="cambios">${cs.map((x) => `<li>${ic('warning')}<span><strong>${esc(x.curso.programaCorto)}</strong>: ${esc(cap(x.clase.toLowerCase()))} pasó del ${esc(fechaLarga(x.cambio.fechaAnterior))} al ${esc(fechaLarga(x.fecha))}. <small>Detectado ${esc(haceCuanto(x.cambio.detectadoEn))}.</small></span></li>`).join('')}</ul>`
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
    return `<li><span><strong>${esc(r.c.programaCorto)}</strong><small>${esc(r.c.tipo)}${r.c.cohorte ? `, ${esc(r.c.cohorte)}` : ''}, terminó el ${esc(fechaLargaAnio(r.d.meta.fin))}</small></span>
      <a class="btn" href="${esc(url)}" target="_blank" rel="noopener">Abrir${ic('arrow-up-right')}</a>
      <button class="btn" type="button" data-copiar="${esc(url)}">${ic('link-simple')}<span>Copiar enlace</span></button>${r.asis && cierre(r) ? htmlCierre(r) : ''}</li>`;
  }).join('')}</ul></div>`).join('');
}

/** Cómo agregar o cambiar cursos, estado del Excel de registro y carpetas que llegaron sin estar registradas. */
function registro(meta) {
  const r = meta.registro ?? {};
  const avisos = [...(r.error ? [`El último guardado del registro no se pudo leer y se conserva el anterior: ${r.error}`] : []), ...(r.avisos ?? [])];
  $('registro-estado').innerHTML = `${avisos.length ? `<ul class="alertas">${avisos.map((a) => `<li class="alerta" role="alert">${ic('warning')}<span>${esc(a)}</span></li>`).join('')}</ul>` : ''}
    ${(meta.sinRegistrar ?? []).length ? `<div class="sin-registrar"><h3>Carpetas con Excel que no están en el registro</h3><p class="nota">Esos Excel se guardaron pero no se publica nada de ellos hasta que agregues el curso al Excel de registro.</p><ul>${meta.sinRegistrar.map((x) => `<li><span>${esc(x.carpeta)}</span><a href="${esc(x.enlace)}" target="_blank" rel="noopener">Abrir carpeta</a></li>`).join('')}</ul></div>` : ''}`;
  $('registro-formulario').hidden = !meta.formularioRegistro;
  if (meta.formularioRegistro) $('registro-formulario').href = meta.formularioRegistro;
  $('registro-abrir').hidden = !r.enlace;
  if (r.enlace) $('registro-abrir').href = r.enlace;
  $('registro-pie').textContent = r.actualizado ? `Registro leído ${haceCuanto(r.actualizado)}.` : '';
}

const hora = (c) => horario(c);
const filaClase = (x) => `<strong>${esc(x.curso.programaCorto)}</strong>, ${esc(cap(x.c.clase.toLowerCase()))}`;

const FALTA_TXT = { Docente: 'Sin docente', 'Asistente PAT': 'Sin asistente', 'Enlace de Teams': 'Sin enlace de Teams' };

/** Lo que hay que resolver ya: clases de los próximos 14 días a las que les falta algo y choques de horario, de todos los cursos juntos. */
function seccionUrgente(rs) {
  const t = ahora(), u = urgentes(rs, t), ch = choques(rs, t), hoy = hoyISO(t), manana = addDias(hoy, 1);
  const n = u.length + ch.length;
  $('ins-urgente').hidden = !n;
  $('ins-urgente').innerHTML = n ? `${n}<span class="solo-lectores"> ${n === 1 ? 'asunto urgente' : 'asuntos urgentes'}</span>` : '';
  const dia = (f) => (f === hoy ? '<em class="cuando">Hoy</em>' : f === manana ? '<em class="cuando">Mañana</em>' : '');
  const item = (x) => `<li><span class="urg-fecha">${dia(x.c.fecha)}<strong>${esc(fechaLarga(x.c.fecha))}</strong><small>${esc(hora(x.c))}</small></span>
    <span class="urg-clase">${filaClase(x)}</span>
    <span class="urg-faltas">${x.faltas.map((f) => `<span class="falta-chip">${ic('warning')}${esc(FALTA_TXT[f] ?? f)}</span>`).join('')}</span>
    <a class="urg-enlace" href="${esc(x.curso.carpetaSharePoint)}" target="_blank" rel="noopener">${ic('folder-open')}Corregir en SharePoint</a></li>`;
  const lista = (xs) => `<ul class="urg-lista">${xs.map(item).join('')}</ul>`;
  const aviso = ch.length
    ? `<div class="urg-choques"><h3 class="sub-rep">Choques de horario <span class="cuenta">${ch.length}</span></h3><ul class="alertas">${ch.map((k) => `<li class="alerta" role="alert">${ic('warning')}<span><strong>${esc(k.rol)} ${esc(k.nombre)}</strong> tiene dos clases a la vez el ${esc(fechaLarga(k.a.c.fecha))}: ${esc(k.a.curso.programaCorto)} (${esc(hora(k.a.c))}) y ${esc(k.b.curso.programaCorto)} (${esc(hora(k.b.c))}).</span></li>`).join('')}</ul></div>` : '';
  $('urgente-lista').innerHTML = n
    ? `<p class="resumen-sec">${u.length ? `<strong>${u.length}</strong> ${u.length === 1 ? 'clase' : 'clases'} con datos sin confirmar` : 'Todas las clases tienen sus datos'}${ch.length ? `, <strong>${ch.length}</strong> ${ch.length === 1 ? 'choque' : 'choques'} de horario` : ''}.</p>${aviso}${u.length ? `<h3 class="sub-rep">Datos por confirmar <span class="cuenta">${u.length}</span></h3>${lista(u.slice(0, 8))}${u.length > 8 ? `<details class="mas"><summary>Ver las ${u.length - 8} restantes</summary>${lista(u.slice(8))}</details>` : ''}` : ''}`
    : `<p class="vacio-ok">${ic('check')}<span><strong>Todo en orden.</strong> Las clases de los próximos 14 días tienen docente, asistente y enlace, y no hay choques de horario.</span></p>`;
}

/** Agenda de las próximas 4 semanas de todos los cursos, con los choques de docentes o asistentes arriba. */
function seccionAgenda(rs) {
  const t = ahora(), ag = agenda(rs, t);
  const dia = ([f, lista]) => `<div class="dia-agenda"><h3>${esc(cap(fechaLarga(f)))}</h3><ul>${lista.map((x) => `<li><span class="h">${esc(hora(x.c))}</span><span>${filaClase(x)}<small>${x.c.profesores.length ? esc(x.c.profesores.join(' y ')) : '<em class="pendiente">Docente por confirmar</em>'}</small></span></li>`).join('')}</ul></div>`;
  const tope = addDias(hoyISO(t), 7);
  const pronto = [...Map.groupBy(ag.filter((x) => x.c.fecha <= tope), (x) => x.c.fecha)], luego = [...Map.groupBy(ag.filter((x) => x.c.fecha > tope), (x) => x.c.fecha)];
  $('agenda-lista').innerHTML = (ag.length
    ? `${pronto.map(dia).join('') || '<p class="nota">No hay clases en los próximos 7 días.</p>'}${luego.length ? `<details class="mas"><summary>Ver las semanas siguientes (${luego.reduce((n, [, l]) => n + l.length, 0)} clases)</summary>${luego.map(dia).join('')}</details>` : ''}`
    : '<p class="nota">No hay clases programadas en las próximas 4 semanas.</p>');
}

/** Horas por docente, por curso y por mes, con descarga a Excel (CSV) y PDF. Se puede filtrar por periodo. */
let periodoSel = '', ultimosRs = [], activosVivos = [];
function seccionReportes(rs) {
  const periodos = [...new Set(rs.map((r) => r.c.periodo).filter(Boolean))].sort().reverse();
  $('rep-periodo').innerHTML = `<option value="">Todos los periodos</option>${periodos.map((p) => `<option value="${esc(p)}"${p === periodoSel ? ' selected' : ''}>Periodo ${esc(p)}</option>`).join('')}`;
  const sel = rs.filter((r) => !periodoSel || r.c.periodo === periodoSel);
  const rep = reportes(sel, ahora());
  const tabla = (cab, filas) => `<div class="tabla-envoltura"><table class="tabla-pend"><thead><tr>${cab.map((h) => `<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${filas.map((f) => `<tr>${f.map((c, i) => (i ? `<td>${c}</td>` : `<th scope="row">${c}</th>`)).join('')}</tr>`).join('')}</tbody></table></div>`;
  const n1 = (e) => String(Math.round(e * 10) / 10).replace('.', ',');
  $('rep-docentes').innerHTML = tabla(['Docente', 'Clases', 'Horas', 'Ya realizadas', 'Cursos'], rep.docentes.map((e) => [esc(e.k), e.clases, esc(horasTxt(e)), n1(e.hechas), esc(e.cursos.join(', '))]));
  $('rep-sel').textContent = `Mostrando: ${periodoSel ? `periodo ${periodoSel}` : 'todos los periodos'}. ${rep.docentes.length} ${rep.docentes.length === 1 ? 'docente' : 'docentes'}, ${rep.cursos.length} ${rep.cursos.length === 1 ? 'curso' : 'cursos'}.`;
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
  formBienvenida = meta.formularioBienvenida || '';
  preguntasBienv = meta.preguntasBienvenida || {};
  const rs = await Promise.all(meta.cursos.map(async (c) => {
    const [d, error, asis] = await Promise.all([c.tieneDatos && traer(`${new URL(`${c.ruta}/data/data.json`, BASE)}`), c.tieneError && traer(`${new URL(`${c.ruta}/estado/error.json`, BASE)}`), c.tieneAsistencia && traer(`asistencia/${c.id}.json`)]);
    return Object.assign(analizar(c, d, error), { asis: asis || null });
  }));
  ultimosRs = rs;
  const fallos = rs.filter((r) => r.fallo);
  $('aviso-carga').hidden = !fallos.length;
  $('aviso-carga').innerHTML = fallos.length ? `${ic('warning')}<span>No se pudieron cargar los datos de ${fallos.length} ${fallos.length === 1 ? 'curso' : 'cursos'} (${esc(fallos.map((r) => r.c.programaCorto).join(', '))}). Lo que ves puede estar incompleto.</span><button class="btn" type="button" data-reintentar>Reintentar</button>` : '';
  const activos = rs.filter((r) => r.estado !== 'terminado');
  resumen(activos, rs.length - activos.length);
  activosVivos = activos;
  filtrosCursos(activos);
  pintarCursos();
  seccionAsistencia(activos);
  tablaPendientes(activos);
  listaCambios(activos);
  archivo(rs.filter((r) => r.estado === 'terminado'));
  seccionUrgente(activos);
  seccionAgenda(activos);
  seccionReportes(rs);
  registro(meta);
  buscarGlobal();
  const publicados = rs.map((r) => r.d?.meta.generadoEn).filter(Boolean).sort().at(-1);
  const hh = new Date().toLocaleTimeString('es-CO', { hour: 'numeric', minute: '2-digit', timeZone: 'America/Bogota' });
  $('act-texto').textContent = `${publicados ? `Último cambio publicado ${haceCuanto(publicados)}. ` : ''}Página revisada a las ${hh}`;
  $('refresco').textContent = `Revisado ${fechaLargaAnio(hoyISO())}, ${hh}`;
  document.getElementById('inicio').removeAttribute('aria-busy');
}

/** Asistencia: bandeja de seguimiento de todos los cursos y un tablero con una fila por curso. Solo aparece si algún curso activo tiene el Excel de asistencia publicado. */
let asisCursos = [];
const LLAVE_CONTACTADOS = 'asistencia-contactados';
const leerContactados = () => { try { return new Set(JSON.parse(localStorage.getItem(LLAVE_CONTACTADOS) || '[]')); } catch { return new Set(); } };
const guardarContactados = (set) => { try { localStorage.setItem(LLAVE_CONTACTADOS, JSON.stringify([...set])); } catch { /* sin almacenamiento: la marca dura mientras la página esté abierta */ } };
let contactados = leerContactados();

function seccionAsistencia(activos) {
  asisCursos = activos.filter((r) => r.c.tieneAsistencia);
  $('asis-seguimiento').hidden = !asisCursos.length;
  if (!asisCursos.length) return;
  const n = bandeja(asisCursos).length;
  $('asis-cuenta').textContent = n;
  $('asis-resumen').textContent = n ? resumenAsistencia(asisCursos) : '';
  pintarAsistencia();
}

/** La bandeja de seguimiento junta a los estudiantes de todos los cursos; el detalle de cada curso está en su tarjeta. */
function pintarAsistencia() {
  const lista = bandeja(asisCursos);
  const hechos = new Set([...contactados].filter((id) => lista.some((x) => x.id === id))); // una marca de un estudiante que ya no está en la lista se descarta
  $('asis-bandeja').innerHTML = htmlBandeja(lista, hechos);
}

/** Filtros de la lista de cursos: texto, periodo y cohorte, y semáforo. Solo aparecen cuando hay más de unos pocos cursos. */
function filtrosCursos(activos) {
  const grupos = [...new Set(activos.map((r) => etiquetaPeriodo(r.c)))].sort().reverse();
  const previo = $('cur-grupo').value;
  $('cur-grupo').innerHTML = `<option value="">Todos</option>${grupos.map((g) => `<option value="${esc(g)}"${g === previo ? ' selected' : ''}>${esc(g)}</option>`).join('')}`;
  $('filtros-cursos').hidden = activos.length < 4;
}

function pintarCursos() {
  const q = norm($('cur-buscar').value || '').trim();
  const g = $('cur-grupo').value;
  const sem = $('cur-semaforo').value;
  const vis = activosVivos.filter((r) => (!q || norm(r.c.programaCorto).includes(q)) && (!g || etiquetaPeriodo(r.c) === g) && (!sem || salud(r, ahora()).nivel === sem));
  const llave = (d) => (d.dataset.asisCurso ? `a:${d.dataset.asisCurso}` : `b:${d.dataset.bienvCurso}`);
  const abiertos = new Set([...document.querySelectorAll('#cursos-lista details[open][data-asis-curso], #cursos-lista details[open][data-bienv-curso]')].map(llave));
  $('cursos-lista').innerHTML = vis.length ? vis.map(tarjeta).join('')
    : `<p class="nota">${activosVivos.length ? 'Ningún curso coincide con el filtro.' : 'No hay cursos activos. Agrega los del nuevo periodo en el Excel de registro.'}</p>`;
  for (const d of document.querySelectorAll('#cursos-lista details[data-asis-curso], #cursos-lista details[data-bienv-curso]')) d.open = abiertos.has(llave(d));
  $('cur-conteo').textContent = activosVivos.length >= 4 ? `Mostrando ${vis.length} de ${activosVivos.length} cursos activos.` : '';
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

/** Buscador global: cursos, docentes y clases de todos los cursos, incluidos los terminados. */
function buscarGlobal() {
  $('bg-resultados').innerHTML = htmlResultados(buscar(ultimosRs, $('bg-q').value));
}

async function arrancar() {
  const meta = await traer('cursos.json');
  if (!meta) {
    const err = '<div class="error-carga" role="alert"><span>No se pudo cargar la información. Puede ser tu conexión o que el sitio esté actualizándose.</span><button class="btn" type="button" data-reintentar>Reintentar</button></div>';
    $('cursos-lista').innerHTML = $('urgente-lista').innerHTML = err;
    $('act-texto').textContent = 'No se pudo cargar la información.';
    return;
  }
  document.querySelectorAll('[data-ic]').forEach((e) => { e.outerHTML = ic(e.dataset.ic); });
  $('inicio').setAttribute('aria-busy', 'true');
  $('pie-carpeta').innerHTML = `<a href="${esc(meta.carpetaActual)}" target="_blank" rel="noopener">Abrir la carpeta ${esc(meta.nombreCarpetaActual)} en SharePoint</a>`;
  await pintar(meta);
  for (const id of ['cur-buscar', 'cur-grupo', 'cur-semaforo']) $(id).addEventListener(id === 'cur-buscar' ? 'input' : 'change', pintarCursos);
  document.addEventListener('change', (e) => {
    const c = e.target.closest('[data-contactado]');
    if (!c) return;
    contactados[c.checked ? 'add' : 'delete'](c.dataset.contactado);
    guardarContactados(contactados);
    pintarAsistencia();
  });
  $('bg-q').addEventListener('input', buscarGlobal);
  $('bg-q').addEventListener('keydown', (e) => { if (e.key === 'Escape') { $('bg-q').value = ''; buscarGlobal(); } });
  $('nav-buscar').addEventListener('click', () => setTimeout(() => $('bg-q').focus({ preventScroll: true }), 50));
  document.addEventListener('keydown', (e) => {
    if (e.key !== '/' || e.ctrlKey || e.metaKey || e.altKey || /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName)) return;
    e.preventDefault();
    $('buscar').scrollIntoView({ behavior: 'smooth', block: 'center' });
    $('bg-q').focus({ preventScroll: true });
  });
  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-cierre]');
    if (!b) return;
    const r = ultimosRs.find((x) => x.c.id === b.dataset.cierre);
    if (r && cierre(r)) descargar(`cierre-${r.c.id}.csv`, csv(TITULOS_CIERRE, filasCierre(r)));
  });
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
  const refrescar = async () => { const m = await traer('cursos.json'); if (m) await pintar(m); };
  setInterval(() => { if (document.visibilityState === 'visible') refrescar(); }, 60000);
  document.addEventListener('click', async (e) => {
    const a = e.target.closest('#act-ahora');
    const r = e.target.closest('[data-reintentar]');
    if (!a && !r) return;
    const b = a || r, antes = b.textContent;
    b.disabled = true; b.textContent = 'Actualizando…';
    await refrescar();
    if (b.isConnected) { b.disabled = false; b.textContent = antes; }
  });
  document.addEventListener('toggle', async (e) => {
    const d = e.target;
    if (!d.matches?.('.curso-bienv') || !d.open) return;
    const id = d.dataset.bienvCurso;
    if (!cacheBienvenida.has(id)) cacheBienvenida.set(id, (await traer(`bienvenida/${id}.json`))?.mensaje?.replace(/\{\{(PAT|GESTORA)\}\}/g, '<mark>[nombre que escribes al enviar]</mark>') ?? '<p class="nota">No se pudo cargar el mensaje. Prueba con «Actualizar ahora».</p>');
    const el = d.querySelector('.bienv-cuerpo');
    if (el) el.innerHTML = cacheBienvenida.get(id);
  }, true);
  pestanasReportes();
  navegacion();
}

/** Pestañas de los reportes: una tabla a la vez, con flechas del teclado. */
function pestanasReportes() {
  const tabs = [...document.querySelectorAll('#reportes [role=tab]')];
  const abrir = (t, foco) => {
    for (const x of tabs) {
      const on = x === t;
      x.setAttribute('aria-selected', on); x.tabIndex = on ? 0 : -1;
      $(x.getAttribute('aria-controls')).hidden = !on;
    }
    if (foco) t.focus();
  };
  tabs.forEach((t, i) => {
    t.addEventListener('click', () => abrir(t));
    t.addEventListener('keydown', (e) => {
      const paso = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
      if (paso) { e.preventDefault(); abrir(tabs[(i + paso + tabs.length) % tabs.length], true); }
      if (e.key === 'Home') { e.preventDefault(); abrir(tabs[0], true); }
      if (e.key === 'End') { e.preventDefault(); abrir(tabs.at(-1), true); }
    });
  });
}

/** Menú fijo que marca la sección que se está leyendo, y botón para volver arriba. */
function navegacion() {
  const enlaces = new Map([...document.querySelectorAll('#nav-hub a')].map((a) => [a.getAttribute('href').slice(1), a]));
  const marcar = (id) => { for (const [k, a] of enlaces) { if (k === id) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current'); } };
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((es) => {
      const vis = es.filter((x) => x.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
      if (vis) marcar(vis.target.id === 'buscar' ? 'buscar' : vis.target.id);
    }, { rootMargin: '-20% 0px -65% 0px' });
    for (const id of [...enlaces.keys(), 'registro']) { const el = $(id); if (el) io.observe(el); }
  }
  const subir = $('subir');
  const mostrar = () => { subir.hidden = window.scrollY < 700; };
  window.addEventListener('scroll', mostrar, { passive: true });
  subir.addEventListener('click', () => window.scrollTo({ top: 0, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' }));
  mostrar();
}
arrancar();
