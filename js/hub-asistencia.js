// Sección Asistencia del sitio de administración. Los estudiantes son "Estudiante N" (su número de lista en el Excel): nunca se muestran nombres.
import { esc, ic } from './ui.js';
import { ahora, estadoClase, fechaLarga } from './utils-fecha.js';

const pct = (x) => (x == null ? 'Sin datos' : `${Math.round(x * 100)} %`);
const SEGUIR = ['Perdió el mínimo', 'En riesgo', 'Atención']; // a quienes conviene escribirles
const CLASE_ESTADO = { 'Perdió el mínimo': 'perdio', 'En riesgo': 'riesgo', Atención: 'atencion', 'Al día': 'aldia', Aprobó: 'aprobo' };

/** Clases que ya pasaron según el cronograma pero no tienen ninguna marca de asistencia. */
export function sinRegistrar(r, t = ahora()) {
  if (!r.d || !r.asis) return [];
  const dictadas = new Set(r.asis.porClase.filter((x) => x.estado === 'Dictada').map((x) => x.clase));
  return r.d.clases.filter((c) => estadoClase(c, t) === 'pasada' && !dictadas.has(c.id));
}

export const urgentesAsistencia = (r) => (r.asis ? r.asis.lista.filter((x) => SEGUIR.includes(x.estado)) : []);

function barras(a) {
  const mayor = a.porClase.filter((c) => c.estado === 'Dictada');
  if (!mayor.length) return '';
  const celdas = a.porClase.map((c) => c.estado === 'Dictada'
    ? `<li${c.marcadas < c.de ? ' class="incompleta"' : ''} title="Clase ${c.clase}: ${c.asistieron} de ${c.de}${c.marcadas < c.de ? `, faltan por marcar ${c.de - c.marcadas}` : ''}"><i style="height:${c.de ? Math.max(6, Math.round(100 * c.asistieron / c.de)) : 6}%"></i><span>${c.clase}</span></li>`
    : `<li class="vacia" title="Clase ${c.clase}: aún sin marcar"><i></i><span>${c.clase}</span></li>`).join('');
  const completas = mayor.filter((c) => c.marcadas >= c.de);
  const peor = (completas.length ? completas : mayor).reduce((m, c) => (c.asistieron / c.de < m.asistieron / m.de ? c : m), (completas.length ? completas : mayor)[0]);
  return `<div class="asis-barras"><p class="asis-sub">Quiénes asistieron a cada clase</p>
    <ol role="img" aria-label="Asistencia por clase. La más baja fue la clase ${peor.clase}, con ${peor.asistieron} de ${peor.de}.${mayor.length > completas.length ? ' Algunas clases tienen la asistencia sin terminar de marcar.' : ''}">${celdas}</ol></div>`;
}

const etiquetaPeriodo = (c) => (c.periodo ? `Periodo ${c.periodo}${c.cohorte ? `, ${c.cohorte}` : ''}` : c.tipo);

/** Semáforo del curso: rojo si alguien está en riesgo o ya perdió el mínimo, ámbar si hay Atención o asistencia sin marcar, verde si todo va bien. */
export function nivelAsistencia(r, t = ahora()) {
  const a = r.asis;
  if (!a) return 'gris';
  if ((a.porEstado['En riesgo'] || 0) + (a.porEstado['Perdió el mínimo'] || 0)) return 'rojo';
  return a.porEstado.Atención || a.sinMarcar || sinRegistrar(r, t).length ? 'ambar' : 'verde';
}
const ORDEN_NIVEL = { rojo: 0, ambar: 1, verde: 2, gris: 3 };
const NIVEL_TXT = { rojo: 'Requiere atención', ambar: 'Por revisar', verde: 'Todo en orden', gris: 'Sin asistencia publicada' };

/** Estudiantes a quienes conviene escribirles, de todos los cursos, de más a menos urgente. */
export function bandeja(rs) {
  const orden = ['Perdió el mínimo', 'En riesgo', 'Atención'];
  return rs.flatMap((r) => urgentesAsistencia(r).map((x) => ({ ...x, r, id: `${r.c.id}|${x.n}|${x.faltas}` })))
    .sort((p, q) => orden.indexOf(p.estado) - orden.indexOf(q.estado) || p.quedan - q.quedan || p.r.c.programaCorto.localeCompare(q.r.c.programaCorto) || p.n - q.n);
}

/** Texto listo para pegar. No lleva nombre: quien lo envía lo escribe donde dice [nombre]. */
export function mensajeSeguimiento(x) {
  const q = Math.max(x.quedan, 0);
  const cierre = x.estado === 'Perdió el mínimo'
    ? 'Con las clases que llevamos ya no se alcanza el mínimo de asistencia para certificar, y quisiera que hablemos de cómo seguir.'
    : `Te ${q === 1 ? 'queda 1 falta' : `quedan ${q} faltas`} antes de no alcanzar el mínimo de asistencia para certificar.`;
  return `Hola [nombre], te escribo del ${x.r.c.programaCorto}. Llevas ${x.faltas} ${x.faltas === 1 ? 'falta' : 'faltas'} en las clases. ${cierre} ¿Todo bien? Cuéntame si pasó algo y miramos cómo te podemos apoyar.`;
}

export function htmlBandeja(lista, hechos = new Set()) {
  if (!lista.length) return `<p class="ok-nota asis-ok">${ic('check')}<span>Nadie está cerca de perder el mínimo de asistencia por ahora.</span></p>`;
  const pendientes = lista.filter((x) => !hechos.has(x.id)).length;
  return `<div class="tabla-envoltura"><table class="tabla-pend tabla-asis"><caption>${pendientes} por contactar${lista.length > pendientes ? `, ${lista.length - pendientes} ya ${lista.length - pendientes === 1 ? 'contactado' : 'contactados'}` : ''}. De más a menos urgente.</caption>
    <thead><tr><th scope="col">Estudiante</th><th scope="col">Curso</th><th scope="col">Faltas</th><th scope="col">Le quedan</th><th scope="col">Seguimiento</th></tr></thead>
    <tbody>${lista.map((x) => `<tr${hechos.has(x.id) ? ' class="hecho"' : ''}><th scope="row"><span class="est-asis ${CLASE_ESTADO[x.estado]}">${esc(x.estado)}</span> N.º ${x.n}</th><td>${esc(x.r.c.programaCorto)}<small>${esc(etiquetaPeriodo(x.r.c))}</small></td><td>${x.faltas}</td><td>${Math.max(x.quedan, 0)}</td>
      <td><div class="acciones-asis"><button class="btn" type="button" data-copiar="${esc(mensajeSeguimiento(x))}">${ic('link-simple')}<span>Copiar mensaje</span></button>
      <label class="contactado"><input type="checkbox" data-contactado="${esc(x.id)}"${hechos.has(x.id) ? ' checked' : ''}> Contactado</label></div></td></tr>`).join('')}</tbody></table></div>
    <p class="nota">El número es el de la lista en el Excel de asistencia, donde está el nombre. La marca Contactado se guarda en este navegador y se reinicia si el estudiante vuelve a faltar.</p>`;
}

function detalle(r, t) {
  const a = r.asis;
  const minimo = a.programadas - a.permitidas;
  const pasadas = sinRegistrar(r, t);
  const fichas = ['Perdió el mínimo', 'En riesgo', 'Atención', 'Al día', 'Aprobó'].filter((e) => a.porEstado[e]).map((e) => `<li class="${CLASE_ESTADO[e]}"><strong>${a.porEstado[e]}</strong> ${esc(e.toLowerCase())}</li>`).join('');
  const avisos = [
    pasadas.length ? `${pasadas.length === 1 ? 'La clase' : 'Las clases'} ${pasadas.map((x) => `${x.id} (${fechaLarga(x.fecha)})`).join(', ')} ya ${pasadas.length === 1 ? 'pasó' : 'pasaron'} y no ${pasadas.length === 1 ? 'tiene' : 'tienen'} asistencia marcada. Si se reprogramó, cambia la fecha en el Excel del curso; si se dictó, marca la asistencia.` : '',
    a.sinMarcar ? `Hay ${a.sinMarcar} ${a.sinMarcar === 1 ? 'casilla sin marcar' : 'casillas sin marcar'} en clases ya dictadas. Las cuentas quedan incompletas hasta marcarlas con 1 o 0.` : '',
  ].filter(Boolean).map((x) => `<p class="alerta" role="alert">${ic('warning')}<span>${x}</span></p>`).join('');
  return `<p class="asis-linea">Para certificar hay que asistir al menos a <strong>${minimo}</strong> de ${a.programadas} clases: se puede faltar hasta <strong>${a.permitidas}</strong> ${a.permitidas === 1 ? 'vez' : 'veces'}. Van ${a.dictadas} clases dictadas, con ${a.estudiantes} estudiantes.</p>
    <ul class="asis-fichas">${fichas}</ul>${avisos}${barras(a)}`;
}

/** Una fila por curso, de más a menos urgente. Al abrirla se despliega el detalle. */
export function htmlTablero(rs, t = ahora()) {
  const filas = rs.map((r) => ({ r, nivel: nivelAsistencia(r, t) })).sort((p, q) => ORDEN_NIVEL[p.nivel] - ORDEN_NIVEL[q.nivel] || p.r.c.programaCorto.localeCompare(q.r.c.programaCorto));
  return `<div class="asis-tablero">${filas.map(({ r, nivel }) => {
    const { c, asis: a } = r;
    if (!a) return `<div class="asis-fila gris"><div class="asis-resumen-fila"><span class="asis-punto"></span><span class="asis-curso"><strong>${esc(c.programaCorto)}</strong><small>${esc(etiquetaPeriodo(c))}</small></span><span class="asis-nota-fila">Sin asistencia publicada. Aparece al guardar el Excel de asistencia en su carpeta.</span></div></div>`;
    const alerta = (a.porEstado['Perdió el mínimo'] || 0) + (a.porEstado['En riesgo'] || 0);
    const atencion = a.porEstado.Atención || 0;
    return `<details class="asis-fila ${nivel}" data-curso="${esc(c.id)}"><summary class="asis-resumen-fila"><span class="asis-punto" title="${NIVEL_TXT[nivel]}"></span>
      <span class="asis-curso"><strong>${esc(c.programaCorto)}</strong><small>${esc(etiquetaPeriodo(c))}</small></span>
      <span class="asis-avance">${a.dictadas} de ${a.programadas}<small>clases</small></span>
      <span class="asis-prom"><span class="barra" role="img" aria-label="Asistencia promedio ${pct(a.promedio)}"><i style="width:${Math.round((a.promedio || 0) * 100)}%"></i></span>${pct(a.promedio)}</span>
      <span class="asis-pills">${alerta ? `<span class="est-asis riesgo" title="En riesgo o perdieron el mínimo">${alerta}</span>` : ''}${atencion ? `<span class="est-asis atencion" title="En atención">${atencion}</span>` : ''}${!alerta && !atencion ? '<span class="asis-ok-mini">Al día</span>' : ''}</span>
      <span class="asis-abrir" aria-hidden="true"></span></summary>
      <div class="asis-detalle">${detalle(r, t)}</div></details>`;
  }).join('')}</div>`;
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

const numeros = (lista) => (lista.length ? lista.map((x) => x.n).sort((p, q) => p - q).join(', ') : 'Nadie');

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
      <p class="nota">Los números son los de la lista en el Excel de asistencia, donde están los nombres. Para certificar hacen falta ${a.programadas - a.permitidas} de ${a.programadas} clases.</p>
      <p><button class="btn" type="button" data-cierre="${esc(c.id)}">${ic('arrow-up-right')}<span>Descargar para certificación</span></button></p></div></details>`;
}

/** CSV para pasar a certificación: un renglón por número de lista, sin nombres. */
export function filasCierre(r) {
  const k = cierre(r);
  const { c, asis: a } = r;
  const filas = [...k.aprueban.map((x) => [x, 'Aprueba']), ...k.noAprueban.map((x) => [x, 'No aprueba']), ...k.porDefinir.map((x) => [x, 'Por definir'])].sort((p, q) => p[0].n - q[0].n);
  return filas.map(([x, res]) => [c.programaCorto, c.periodo || '', c.cohorte || '', x.n, res, x.asistio, x.faltas, a.programadas, Math.round((100 * x.asistio) / a.programadas) + ' %', k.definitivo ? 'Sí' : 'No']);
}
export const TITULOS_CIERRE = ['Curso', 'Periodo', 'Cohorte', 'Número de lista', 'Resultado', 'Clases asistidas', 'Faltas', 'Clases programadas', 'Asistencia final', 'Resultado definitivo'];

/** Resumen de una línea para la portada de la sección. */
export function resumenAsistencia(rs) {
  const con = rs.filter((r) => r.asis);
  const seguir = con.reduce((s, r) => s + urgentesAsistencia(r).length, 0);
  if (!con.length) return '';
  return seguir ? `${seguir} ${seguir === 1 ? 'estudiante está' : 'estudiantes están'} en atención, en riesgo o ya perdieron el mínimo, sumando ${con.length === 1 ? 'el curso con asistencia publicada' : `los ${con.length} cursos con asistencia publicada`}.` : 'Ningún estudiante está cerca de perder el mínimo de asistencia.';
}
