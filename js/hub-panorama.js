// Panorama general del sitio de administración: indicadores y una matriz con una fila por curso. Sin DOM propio: devuelve HTML y datos.
import { esc, ic } from './ui.js';
import { addDias, cap, fechaCorta, haceCuanto, hoyISO } from './utils-fecha.js';
import { choques, clasesDelDia, salud, urgentes } from './hub-analisis.js';
import { bandeja, nivelAsistencia, sinRegistrar } from './hub-asistencia.js';

export const ETIQUETA_ESTADO = { 'por-empezar': 'Por empezar', 'en-curso': 'En curso', terminado: 'Terminado', 'sin-datos': 'Sin datos' };
const PESO = { rojo: 0, ambar: 1, verde: 2 };

/** Una fila de la matriz: todo lo que se muestra de un curso, ya calculado. */
export function fila(r, t) {
  const sa = salud(r, t), total = r.d?.clases.length ?? 0;
  const sin = sinRegistrar(r, t).length, por = r.asis ? r.asis.lista.filter((x) => ['Perdió el mínimo', 'En riesgo', 'Atención'].includes(x.estado)).length : 0;
  const dudas = urgentes([r], t).length;
  const asis = !r.asis ? { txt: 'Sin Excel', nivel: 'gris' } : { txt: r.asis.promedio == null ? 'Sin marcas' : `${Math.round(r.asis.promedio * 100)} %`, nivel: nivelAsistencia(r, t) };
  return { r, c: r.c, estado: r.estado, nivel: sa.nivel, motivo: sa.motivo, total, hechas: r.hechas, avance: total ? r.hechas / total : 0, proxima: r.proxima, dudas, sin, por, asis };
}

export function indicadores(rs, t) {
  const hoy = hoyISO(t), man = addDias(hoy, 1);
  const u = urgentes(rs, t), ch = choques(rs, t);
  const atender = bandeja(rs.filter((r) => r.asis));
  const cambios = rs.reduce((n, r) => n + r.cambios.length, 0);
  const sinMarcar = rs.reduce((n, r) => n + sinRegistrar(r, t).length, 0);
  return {
    cursos: rs.length, enCurso: rs.filter((r) => r.estado === 'en-curso').length, porEmpezar: rs.filter((r) => r.estado === 'por-empezar').length, sinDatos: rs.filter((r) => r.estado === 'sin-datos').length,
    hoy: clasesDelDia(rs, hoy).length, manana: clasesDelDia(rs, man).length, urgentes: u.length + ch.length, cursosUrgentes: new Set(u.map((x) => x.curso.id)).size,
    atender: atender.length, cursosAtender: new Set(atender.map((x) => x.r.c.id)).size, sinMarcar, cambios,
  };
}

/** Un indicador. `estado` (alerta, aviso, ok) es lo único que cambia de color, y siempre con un rótulo escrito; el número va siempre en blanco. */
const SELLO = { alerta: ['warning', 'Atender ya'], aviso: ['warning', 'Revisar'], ok: ['check', 'Sin pendientes'] };
const kpi = (estado, destino, n, titulo, sub) => {
  const [icono, texto] = SELLO[estado] ?? [];
  return `<a class="kpi ${estado || 'neutro'}" href="${destino}"><span class="kpi-titulo">${esc(titulo)}</span><strong>${n}</strong><small>${esc(sub)}</small>${texto ? `<em class="kpi-sello">${ic(icono)}${texto}</em>` : ''}</a>`;
};

export function htmlIndicadores(k) {
  const pl = (n, s, p) => `${n} ${n === 1 ? s : p}`;
  return `<div class="kpis">
    ${kpi('', '#panorama-matriz', k.cursos, k.cursos === 1 ? 'Curso activo' : 'Cursos activos', `${k.enCurso} en curso, ${k.porEmpezar} por empezar${k.sinDatos ? `, ${k.sinDatos} sin cronograma` : ''}`)}
    ${kpi('', '#mensajes', k.hoy, k.hoy === 1 ? 'Clase hoy' : 'Clases hoy', k.manana ? `${pl(k.manana, 'clase', 'clases')} mañana` : 'Ninguna mañana')}
    ${kpi(k.urgentes ? 'alerta' : 'ok', '#urgente', k.urgentes, 'Urgentes', k.urgentes ? `${pl(k.cursosUrgentes, 'curso', 'cursos')} con clases sin docente, asistente o enlace, o con choques de horario` : 'Todo confirmado en los próximos 14 días')}
    ${kpi(k.atender ? 'alerta' : 'ok', '#cursos', k.atender, k.atender === 1 ? 'Estudiante por atender' : 'Estudiantes por atender', k.atender ? `en riesgo de no certificar por faltas, en ${pl(k.cursosAtender, 'curso', 'cursos')}` : 'Nadie cerca de perder el mínimo de asistencia')}
    ${kpi(k.sinMarcar ? 'aviso' : 'ok', '#cursos', k.sinMarcar, k.sinMarcar === 1 ? 'Clase sin asistencia marcada' : 'Clases sin asistencia marcada', k.sinMarcar ? 'ya pasaron según el cronograma y falta marcar quién asistió' : 'Toda clase dictada tiene su asistencia')}
    ${kpi(k.cambios ? 'aviso' : 'ok', '#cambios', k.cambios, k.cambios === 1 ? 'Cambio de fecha reciente' : 'Cambios de fecha recientes', k.cambios ? 'en clases que todavía no se dictan' : 'Sin cambios vigentes')}
  </div>`;
}

export const ORDENES = {
  curso: (a, b) => a.c.programaCorto.localeCompare(b.c.programaCorto, 'es'),
  estado: (a, b) => PESO[a.nivel] - PESO[b.nivel] || a.c.programaCorto.localeCompare(b.c.programaCorto, 'es'),
  avance: (a, b) => b.avance - a.avance,
  proxima: (a, b) => (a.proxima?.inicio ?? '9').localeCompare(b.proxima?.inicio ?? '9'),
  asistencia: (a, b) => (b.por + b.sin) - (a.por + a.sin) || (a.r.asis?.promedio ?? 2) - (b.r.asis?.promedio ?? 2),
  datos: (a, b) => b.dudas - a.dudas,
};

const COLUMNAS = [['curso', 'Curso'], ['estado', 'Estado del curso'], ['avance', 'Avance'], ['proxima', 'Próxima clase'], ['asistencia', 'Asistencia'], ['datos', 'Datos del cronograma']];

function celdaProxima(f, hoy) {
  const p = f.proxima;
  if (!p) return f.r.d ? '<span class="pan-mudo">Terminó el cronograma</span>' : '<span class="pan-mudo">Sin cronograma</span>';
  const cuando = p.fecha === hoy ? '<em class="cuando">Hoy</em>' : p.fecha === addDias(hoy, 1) ? '<em class="cuando">Mañana</em>' : '';
  const nombre = /\d/.test(p.clase) ? cap(p.clase.toLowerCase()) : `Clase ${p.id}`; // algunos Excel dejan «No. de clase» vacío: se usa su lugar en el cronograma
  const gente = p.profesores.length > 2 ? `${p.profesores.slice(0, 2).join(', ')} y ${p.profesores.length - 2} más` : p.profesores.join(' y ');
  const doc = gente ? `<span title="${esc(p.profesores.join(', '))}">${esc(gente.length > 60 ? `${gente.slice(0, 57)}…` : gente)}</span>` : `<em class="pendiente">${ic('warning')}Falta el docente</em>`;
  return `<strong>${esc(cap(fechaCorta(p.fecha)))}</strong>${cuando}<small>${esc(nombre)}<br>${doc}</small>`;
}

function celdaAsistencia(f) {
  if (f.asis.nivel === 'gris') return `<span class="pan-mudo" title="Este curso aún no tiene un Excel de asistencia publicado">Sin Excel de asistencia</span>`;
  const atender = f.r.asis.porEstado['En riesgo'] || f.r.asis.porEstado['Perdió el mínimo'];
  const chips = [f.por ? `<span class="chip ${atender ? 'rojo' : 'ambar'}" title="Estudiantes que ya usaron muchas de las faltas que se pueden tener">${ic('warning')}${f.por} por atender</span>` : '', f.sin ? `<span class="chip ambar" title="Clases que ya pasaron según el cronograma y no tienen asistencia marcada">${ic('warning')}${f.sin} ${f.sin === 1 ? 'clase' : 'clases'} sin marcar</span>` : ''].join('');
  return `<strong class="pan-pct">${esc(f.asis.txt)}</strong><small>asistencia promedio</small>${chips || `<span class="chip verde">${ic('check')}Al día</span>`}`;
}

const SELLO_NIVEL = { rojo: ['warning', 'Requiere atención'], ambar: ['warning', 'Por revisar'], verde: ['check', 'En orden'] };

/** Matriz de cursos: una fila por curso. `filtro` = {nivel, orden}; las cabeceras ordenan y las fichas filtran. */
export function htmlMatriz(filas, filtro, t) {
  const hoy = hoyISO(t);
  const cuenta = { '': filas.length, rojo: 0, ambar: 0, verde: 0 };
  filas.forEach((f) => { cuenta[f.nivel]++; });
  const vis = filas.filter((f) => !filtro.nivel || f.nivel === filtro.nivel).sort(ORDENES[filtro.orden] ?? ORDENES.estado);
  const ficha = (v, txt) => `<button type="button" class="pan-ficha ${v}" data-pan-nivel="${v}" aria-pressed="${filtro.nivel === v}">${v ? '<i aria-hidden="true"></i>' : ''}${esc(txt)} <span>${cuenta[v]}</span></button>`;
  const cab = COLUMNAS.map(([k, n]) => `<th scope="col" aria-sort="${filtro.orden === k ? 'ascending' : 'none'}"><button type="button" data-pan-orden="${k}">${esc(n)}${filtro.orden === k ? ic('caret-down') : ''}</button></th>`).join('');
  const cuerpo = vis.map((f) => `<tr class="nivel-${f.nivel}" data-pan-curso="${esc(f.c.id)}">
      <th scope="row"><button type="button" class="pan-curso" data-ir-curso="${esc(f.c.id)}" title="Ver el detalle de este curso"><span class="pan-nombre">${esc(f.c.programaCorto)}</span><small>${esc(f.c.periodo ? `${f.c.periodo}${f.c.cohorte ? `, ${f.c.cohorte.replace(/\s*\(.*\)/, '')}` : ''}` : f.c.tipo)}</small></button></th>
      <td data-et="Estado"><span class="sello-nivel ${f.nivel}">${ic(SELLO_NIVEL[f.nivel][0])}${esc(SELLO_NIVEL[f.nivel][1])}</span><small>${esc(f.motivo)}</small></td>
      <td data-et="Avance">${f.total ? `<strong>${f.hechas} de ${f.total}</strong><small>clases realizadas</small><div class="barra" role="img" aria-label="${f.hechas} de ${f.total} clases realizadas"><i style="width:${Math.round(100 * f.avance)}%"></i></div>` : '<span class="pan-mudo">Sin cronograma</span>'}</td>
      <td data-et="Próxima clase">${celdaProxima(f, hoy)}</td>
      <td data-et="Asistencia"${f.asis.nivel === 'gris' ? ' class="sin-dato"' : ''}>${celdaAsistencia(f)}</td>
      <td data-et="Datos por confirmar"${!f.dudas ? ' class="sin-dato"' : ''}>${f.dudas ? `<span class="chip ambar">${ic('warning')}${f.dudas} ${f.dudas === 1 ? 'clase incompleta' : 'clases incompletas'}</span><small>Sin docente, asistente o enlace de Teams en los próximos 14 días</small>` : f.r.d ? `<span class="chip verde">${ic('check')}Todo confirmado</span>` : '<span class="pan-mudo">-</span>'}</td></tr>`).join('');
  return `<div class="pan-fichas" role="group" aria-label="Filtrar por estado">${ficha('', 'Todos')}${ficha('rojo', 'Requieren atención')}${ficha('ambar', 'Por revisar')}${ficha('verde', 'En orden')}</div>
    <dl class="pan-leyenda"><div class="rojo"><dt>Requiere atención</dt><dd>Hoy o mañana falta el docente o el enlace de Teams, o el Excel tiene un error.</dd></div><div class="ambar"><dt>Por revisar</dt><dd>Faltan datos en clases de los próximos 14 días, o el curso aún no tiene cronograma.</dd></div><div class="verde"><dt>En orden</dt><dd>Todo confirmado para los próximos 14 días.</dd></div></dl>
    <div class="tabla-envoltura"><table class="pan-matriz"><caption class="solo-lectores">Resumen de cada curso activo. Los encabezados ordenan la tabla.</caption><thead><tr>${cab}</tr></thead><tbody>${cuerpo || '<tr><td colspan="6" class="pan-vacio">Ningún curso coincide con el filtro.</td></tr>'}</tbody></table></div>
    <p class="nota pan-pie">Toca el nombre de un curso para ver su detalle más abajo. Toca el nombre de una columna para ordenar.</p>`;
}

/** Fecha en que se guardó por última vez el Excel de un curso, o un aviso si nunca se publicó. */
export const guardadoTxt = (d) => (d?.meta.fuenteModificadaEn ? `Excel guardado ${haceCuanto(d.meta.fuenteModificadaEn)}` : d ? `Datos publicados ${haceCuanto(d.meta.generadoEn)}` : '');
