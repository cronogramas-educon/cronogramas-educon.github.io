// Asistencia en el sitio de administración. Cada estudiante se muestra como «Nombre + primer apellido» y su número de lista; la cédula nunca se publica (en la página del curso, el estudiante se encuentra con ella).
import { esc, ic, rangos } from './ui.js';
import { ahora, estadoClase, fechaLarga } from './utils-fecha.js';

export const nombre = (x) => x.etiqueta || `Estudiante ${x.n}`;
const pct = (x) => (x == null ? 'Sin datos' : `${Math.round(x * 100)} %`);
const ESTADOS = ['Perdió el mínimo', 'En riesgo', 'Atención', 'Al día', 'Aprobó'];
const SEGUIR = ['Perdió el mínimo', 'En riesgo', 'Atención']; // a quienes conviene escribirles
const CLASE_ESTADO = { 'Perdió el mínimo': 'perdio', 'En riesgo': 'riesgo', Atención: 'atencion', 'Al día': 'aldia', Aprobó: 'aprobo' };

/** Clases que ya pasaron según el cronograma pero no tienen ninguna marca de asistencia. */
export function sinRegistrar(r, t = ahora()) {
  if (!r.d || !r.asis) return [];
  const dictadas = new Set(r.asis.porClase.filter((x) => x.estado === 'Dictada').map((x) => x.clase));
  return r.d.clases.filter((c) => estadoClase(c, t) === 'pasada' && !dictadas.has(c.id));
}

export const urgentesAsistencia = (r) => (r.asis ? r.asis.lista.filter((x) => SEGUIR.includes(x.estado)) : []);

const etiquetaPeriodo = (c) => (c.periodo ? `Periodo ${c.periodo}${c.cohorte ? `, ${c.cohorte}` : ''}` : c.tipo);

/** Semáforo del curso: rojo si alguien está en riesgo o ya perdió el mínimo, ámbar si hay Atención o asistencia sin marcar, verde si todo va bien. */
export function nivelAsistencia(r, t = ahora()) {
  const a = r.asis;
  if (!a) return 'gris';
  if ((a.porEstado['En riesgo'] || 0) + (a.porEstado['Perdió el mínimo'] || 0)) return 'rojo';
  return a.porEstado.Atención || a.sinMarcar || sinRegistrar(r, t).length ? 'ambar' : 'verde';
}
const NIVEL_TXT = { rojo: 'Requiere atención', ambar: 'Por revisar', verde: 'Todo en orden', gris: 'Sin asistencia publicada' };

/** Estudiantes a quienes conviene escribirles, de todos los cursos, de más a menos urgente. */
export function bandeja(rs) {
  const orden = ['Perdió el mínimo', 'En riesgo', 'Atención'];
  return rs.flatMap((r) => urgentesAsistencia(r).map((x) => ({ ...x, r, id: `${r.c.id}|${x.n}|${x.faltas}` })))
    .sort((p, q) => orden.indexOf(p.estado) - orden.indexOf(q.estado) || p.quedan - q.quedan || p.r.c.programaCorto.localeCompare(q.r.c.programaCorto) || p.n - q.n);
}

/** Texto listo para pegar, con el primer nombre del estudiante (o [nombre] si el Excel aún no lo trae). */
export function mensajeSeguimiento(x) {
  const q = Math.max(x.quedan, 0);
  const cierre = x.estado === 'Perdió el mínimo'
    ? 'Con las clases que llevamos ya no se alcanza el mínimo de asistencia para certificar, y quisiera que hablemos de cómo seguir.'
    : `Te ${q === 1 ? 'queda 1 falta' : `quedan ${q} faltas`} antes de no alcanzar el mínimo de asistencia para certificar.`;
  const pila = x.etiqueta ? x.etiqueta.split(' ')[0] : '[nombre]';
  return `Hola ${pila}, te escribo del ${x.r.c.programaCorto}. Llevas ${x.faltas} ${x.faltas === 1 ? 'falta' : 'faltas'} en las clases. ${cierre} ¿Todo bien? Cuéntame si pasó algo y miramos cómo te podemos apoyar.`;
}

export function htmlBandeja(lista, hechos = new Set()) {
  if (!lista.length) return `<p class="ok-nota asis-ok">${ic('check')}<span>Nadie está cerca de perder el mínimo de asistencia por ahora.</span></p>`;
  const pendientes = lista.filter((x) => !hechos.has(x.id)).length;
  return `<div class="tabla-envoltura"><table class="tabla-pend tabla-asis"><caption>${pendientes} por contactar${lista.length > pendientes ? `, ${lista.length - pendientes} ya ${lista.length - pendientes === 1 ? 'contactado' : 'contactados'}` : ''}. De más a menos urgente.</caption>
    <thead><tr><th scope="col">Estudiante</th><th scope="col">Curso</th><th scope="col">Faltas</th><th scope="col">Le quedan</th><th scope="col">Seguimiento</th></tr></thead>
    <tbody>${lista.map((x) => `<tr${hechos.has(x.id) ? ' class="hecho"' : ''}><th scope="row"><span class="est-asis ${CLASE_ESTADO[x.estado]}">${esc(x.estado)}</span> ${esc(nombre(x))}<small>N.º ${x.n}</small></th><td>${esc(x.r.c.programaCorto)}<small>${esc(etiquetaPeriodo(x.r.c))}</small></td><td>${x.faltas}</td><td>${Math.max(x.quedan, 0)}</td>
      <td><div class="acciones-asis"><button class="btn" type="button" data-copiar="${esc(mensajeSeguimiento(x))}">${ic('link-simple')}<span>Copiar mensaje</span></button>
      <label class="contactado"><input type="checkbox" data-contactado="${esc(x.id)}"${hechos.has(x.id) ? ' checked' : ''}> Contactado</label></div></td></tr>`).join('')}</tbody></table></div>
    <p class="nota">El número es el de la lista en el Excel de asistencia. La marca Contactado se guarda en este navegador y se reinicia si el estudiante vuelve a faltar.</p>`;
}

const ESTADOS_AYUDA = [
  ['Aprobó', 'aprobo', 'Ya completó el curso con el mínimo de asistencia.'],
  ['Al día', 'aldia', 'Va bien: le sobran faltas.'],
  ['Atención', 'atencion', 'Ya usó la mitad de las faltas que puede tener.'],
  ['En riesgo', 'riesgo', 'Casi no le quedan faltas: otra o dos y no certifica.'],
  ['Perdió el mínimo', 'perdio', 'Ya no alcanza el 80 % aunque asista a todo lo que queda.'],
];

/** Explicación y cifras del curso, reparto de estudiantes por estado y la matriz estudiante por clase. */
function detalle(r, t) {
  const a = r.asis;
  const minimo = a.programadas - a.permitidas;
  const pasadas = sinRegistrar(r, t);
  const dictadas = a.porClase.filter((c) => c.estado === 'Dictada');
  const total = a.estudiantes || 1;
  const avisos = [
    pasadas.length ? `${pasadas.length === 1 ? 'La clase' : 'Las clases'} ${rangos(pasadas.map((x) => x.id))} (${pasadas.length === 1 ? 'del' : 'desde el'} ${fechaLarga(pasadas[0].fecha)}${pasadas.length > 1 ? ` ${'hasta el'} ${fechaLarga(pasadas.at(-1).fecha)}` : ''}) ya ${pasadas.length === 1 ? 'pasó' : 'pasaron'} según el cronograma y no ${pasadas.length === 1 ? 'tiene' : 'tienen'} asistencia marcada. Si se reprogramó, cambia la fecha en el Excel del curso; si se dictó, marca la asistencia.` : '',
    a.sinCedula ? `${a.sinCedula === 1 ? 'Un estudiante no tiene' : `${a.sinCedula} estudiantes no tienen`} cédula en el Excel de asistencia, así que ${a.sinCedula === 1 ? 'no puede' : 'no pueden'} consultar su asistencia en la página del curso. Escríbela en la columna Cédula.` : '',
    a.sinMarcar ? `Hay ${a.sinMarcar} ${a.sinMarcar === 1 ? 'casilla sin marcar' : 'casillas sin marcar'} en clases ya dictadas. Las cuentas quedan incompletas hasta marcarlas con 1 o 0.` : '',
  ].filter(Boolean).map((x) => `<p class="alerta" role="alert">${ic('warning')}<span>${x}</span></p>`).join('');
  const reparto = ESTADOS_AYUDA.filter(([e]) => a.porEstado[e]).map(([e, k]) => `<i class="${k}" style="flex:${a.porEstado[e]}" title="${esc(e)}: ${a.porEstado[e]}"></i>`).join('');
  const leyenda = ESTADOS_AYUDA.filter(([e]) => a.porEstado[e]).map(([e, k, ayuda]) => `<li><span class="est-asis ${k}">${esc(e)}</span><strong>${a.porEstado[e]}</strong><small>${esc(ayuda)}</small></li>`).join('');
  const orden = [...a.lista].sort((p, q) => ESTADOS.indexOf(p.estado) - ESTADOS.indexOf(q.estado) || p.n - q.n);
  const celda = (v) => (v === 1 ? `<td class="m si" title="Asistió"><span class="solo-lectores">Asistió</span><i aria-hidden="true"></i></td>` : v === 0 ? `<td class="m no" title="Faltó"><span class="solo-lectores">Faltó</span><i aria-hidden="true"></i></td>` : '<td class="m sin" title="Sin marcar"><span class="solo-lectores">Sin marcar</span></td>');
  const cuerpo = orden.map((x) => `<tr><th scope="row"><span class="mx-nombre">${esc(nombre(x))}</span><small>N.º ${x.n}</small></th>${dictadas.map((c) => celda(x.marcas?.[c.clase] ?? null)).join('')}
      <td class="mx-faltas"><strong>${x.faltas}</strong> <small>de ${a.permitidas}</small></td><td><span class="est-asis ${CLASE_ESTADO[x.estado]}">${esc(x.estado)}</span></td></tr>`).join('');
  const pie = dictadas.map((c) => `<td class="mx-pie" title="Clase ${c.clase}: ${c.asistieron} de ${c.de}">${c.de ? Math.round(100 * c.asistieron / c.de) : 0}<small> %</small></td>`).join('');
  const matriz = dictadas.length ? `<div class="mx-envoltura" tabindex="0" role="region" aria-label="Asistencia de cada estudiante a cada clase dictada"><table class="mx">
      <thead><tr><th scope="col">Estudiante</th>${dictadas.map((c) => `<th scope="col" title="Clase ${c.clase}">${c.clase}</th>`).join('')}<th scope="col">Faltas</th><th scope="col">Estado</th></tr></thead>
      <tbody>${cuerpo}</tbody><tfoot><tr><th scope="row">Asistieron</th>${pie}<td></td><td></td></tr></tfoot></table></div>
    <p class="mx-clave"><span class="cl si"><i></i></span>Asistió <span class="cl no"><i></i></span>Faltó <span class="cl sin"></span>Sin marcar. Los números de arriba son las clases dictadas; el porcentaje de abajo es cuántos asistieron a cada una.</p>` : '<p class="nota">Todavía no se ha marcado la asistencia de ninguna clase.</p>';
  return `<div class="asis-explica"><h4>¿Cómo se lee esto?</h4>
      <p>Para certificar, cada estudiante debe asistir al menos al <strong>80 %</strong> de las clases: <strong>${minimo} de ${a.programadas}</strong>. Eso significa que puede faltar <strong>hasta ${a.permitidas}</strong> ${a.permitidas === 1 ? 'vez' : 'veces'} en todo el curso. El estado de cada persona compara sus faltas con ese límite.</p></div>
    <ul class="asis-kpis"><li><strong>${a.dictadas}<small> de ${a.programadas}</small></strong><span>clases con asistencia marcada</span></li><li><strong>${pct(a.promedio)}</strong><span>promedio de asistencia</span></li><li><strong>${a.estudiantes}</strong><span>estudiantes en la lista</span></li></ul>
    ${avisos}
    <div class="asis-reparto"><h4>Cómo van los ${a.estudiantes} estudiantes</h4><div class="reparto" role="img" aria-label="${ESTADOS_AYUDA.filter(([e]) => a.porEstado[e]).map(([e]) => `${a.porEstado[e]} ${e.toLowerCase()}`).join(', ')}">${reparto}</div><ul class="leyenda">${leyenda}</ul></div>
    <div class="asis-matriz"><h4>Quién asistió a cada clase</h4>${matriz}</div>`;
}

/** Bloque plegable de asistencia que va dentro de la tarjeta de cada curso. */
export function htmlAsistenciaCurso(r, t = ahora()) {
  const a = r.asis;
  if (!a) return '';
  const nivel = nivelAsistencia(r, t);
  const alerta = (a.porEstado['Perdió el mínimo'] || 0) + (a.porEstado['En riesgo'] || 0), atencion = a.porEstado.Atención || 0, por = alerta + atencion;
  return `<details class="curso-asis ${nivel}" data-asis-curso="${esc(r.c.id)}"><summary><span class="asis-punto" title="${NIVEL_TXT[nivel]}" aria-hidden="true"></span>
    <span class="ca-texto"><strong>Asistencia</strong><small>${a.dictadas} de ${a.programadas} clases con asistencia, promedio ${pct(a.promedio)}</small></span>
    ${por ? `<span class="est-asis ${alerta ? 'riesgo' : 'atencion'}">${por} por atender</span>` : nivel === 'verde' ? '<span class="asis-ok-mini">Al día</span>' : '<span class="est-asis atencion">Por revisar</span>'}<span class="asis-abrir" aria-hidden="true"></span></summary>
    <div class="asis-detalle">${detalle(r, t)}${cierre(r) ? htmlCierre(r) : ''}</div></details>`;
}

/** Resultado final del curso según el Excel de asistencia. Solo existe cuando el curso terminó o ya se dictaron todas las clases. */
export function cierre(r) {
  const a = r.asis;
  const completo = !!a && a.programadas > 0 && a.dictadas >= a.programadas;
  if (!a || !(r.estado === 'terminado' || completo)) return null;
  const aprueban = a.lista.filter((x) => x.estado === 'Aprobó');
  const noAprueban = a.lista.filter((x) => x.estado === 'Perdió el mínimo');
  const porDefinir = a.lista.filter((x) => x.estado !== 'Aprobó' && x.estado !== 'Perdió el mínimo');
  return { aprueban, noAprueban, porDefinir, definitivo: !porDefinir.length && completo && !a.sinMarcar };
}

const numeros = (lista) => (lista.length ? lista.slice().sort((p, q) => p.n - q.n).map((x) => `${nombre(x)} (N.º ${x.n})`).join(', ') : 'Nadie');

export function htmlCierre(r) {
  const k = cierre(r);
  const { c, asis: a } = r;
  const aviso = k.definitivo ? '' : `<p class="alerta" role="alert">${ic('warning')}<span>El resultado es provisional: ${a.dictadas < a.programadas ? `faltan por dictar o marcar ${a.programadas - a.dictadas} ${a.programadas - a.dictadas === 1 ? 'clase' : 'clases'} en el Excel de asistencia` : 'hay casillas sin marcar en el Excel de asistencia'}. Cuando estén completas, esta lista se actualiza sola.</span></p>`;
  return `<details class="asis-fila cierre ${k.definitivo ? 'verde' : 'ambar'}" data-curso="${esc(c.id)}"><summary class="asis-resumen-fila"><span class="asis-punto"></span>
    <span class="asis-curso"><strong>${esc(c.programaCorto)}</strong><small>${esc(etiquetaPeriodo(c))}${r.estado === 'terminado' ? ', terminado' : ''}</small></span>
    <span class="asis-avance">${k.aprueban.length} aprueban<small>${k.noAprueban.length} no aprueban</small></span>
    <span class="asis-prom">${k.definitivo ? '<span class="asis-ok-mini">Resultado final</span>' : '<span class="est-asis atencion">Provisional</span>'}</span><span></span><span class="asis-abrir" aria-hidden="true"></span></summary>
    <div class="asis-detalle">${aviso}
      <div class="cierre-cols"><div class="cierre-col aprueba"><h4>Aprueban <span>${k.aprueban.length}</span></h4><p>${numeros(k.aprueban)}</p></div>
        <div class="cierre-col no-aprueba"><h4>No aprueban <span>${k.noAprueban.length}</span></h4><p>${numeros(k.noAprueban)}</p></div>
        ${k.porDefinir.length ? `<div class="cierre-col por-definir"><h4>Por definir <span>${k.porDefinir.length}</span></h4><p>${numeros(k.porDefinir)}</p></div>` : ''}</div>
      <p class="nota">El número es el de la lista en el Excel de asistencia. Para certificar hacen falta ${a.programadas - a.permitidas} de ${a.programadas} clases.</p>
      <p><button class="btn" type="button" data-cierre="${esc(c.id)}">${ic('arrow-up-right')}<span>Descargar para certificación</span></button></p></div></details>`;
}

/** CSV para pasar a certificación: un renglón por estudiante, con número de lista y nombre (sin documento). */
export function filasCierre(r) {
  const k = cierre(r);
  const { c, asis: a } = r;
  const filas = [...k.aprueban.map((x) => [x, 'Aprueba']), ...k.noAprueban.map((x) => [x, 'No aprueba']), ...k.porDefinir.map((x) => [x, 'Por definir'])].sort((p, q) => p[0].n - q[0].n);
  return filas.map(([x, res]) => [c.programaCorto, c.periodo || '', c.cohorte || '', x.n, res, x.asistio, x.faltas, a.programadas, Math.round((100 * x.asistio) / a.programadas) + ' %', k.definitivo ? 'Sí' : 'No', nombre(x)]);
}
export const TITULOS_CIERRE = ['Curso', 'Periodo', 'Cohorte', 'Número de lista', 'Resultado', 'Clases asistidas', 'Faltas', 'Clases programadas', 'Asistencia final', 'Resultado definitivo', 'Nombre'];

/** Resumen de una línea para la portada de la sección. */
export function resumenAsistencia(rs) {
  const con = rs.filter((r) => r.asis);
  const seguir = con.reduce((s, r) => s + urgentesAsistencia(r).length, 0);
  if (!con.length) return '';
  return seguir ? `${seguir} ${seguir === 1 ? 'estudiante está' : 'estudiantes están'} en atención, en riesgo o ya perdieron el mínimo, sumando ${con.length === 1 ? 'el curso con asistencia publicada' : `los ${con.length} cursos con asistencia publicada`}.` : 'Ningún estudiante está cerca de perder el mínimo de asistencia.';
}
