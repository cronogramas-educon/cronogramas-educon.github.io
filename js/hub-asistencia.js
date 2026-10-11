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
    ? `<li title="Clase ${c.clase}: ${c.asistieron} de ${c.de}"><i style="height:${c.de ? Math.max(6, Math.round(100 * c.asistieron / c.de)) : 6}%"></i><span>${c.clase}</span></li>`
    : `<li class="vacia" title="Clase ${c.clase}: aún sin marcar"><i></i><span>${c.clase}</span></li>`).join('');
  const peor = mayor.reduce((m, c) => (c.asistieron / c.de < m.asistieron / m.de ? c : m), mayor[0]);
  return `<div class="asis-barras"><p class="asis-sub">Quiénes asistieron a cada clase</p>
    <ol role="img" aria-label="Asistencia por clase. La más baja fue la clase ${peor.clase}, con ${peor.asistieron} de ${peor.de}.">${celdas}</ol></div>`;
}

export function tarjetaAsistencia(r, t = ahora()) {
  const { c, asis: a } = r;
  const titulo = `<header><p class="tipo">${esc(c.periodo ? `Periodo ${c.periodo}${c.cohorte ? `, ${c.cohorte}` : ''}` : c.tipo)}</p></header><h3>${esc(c.programaCorto)}</h3>`;
  if (!a) return `<article class="asis papel" data-curso="${esc(c.id)}">${titulo}<p class="asis-vacio">Este curso aún no tiene asistencia publicada. Aparece al guardar el Excel de asistencia en su carpeta.</p></article>`;
  const minimo = a.programadas - a.permitidas;
  const seguir = urgentesAsistencia(r);
  const pasadas = sinRegistrar(r, t);
  const fichas = ['Perdió el mínimo', 'En riesgo', 'Atención', 'Al día', 'Aprobó'].filter((e) => a.porEstado[e]).map((e) => `<li class="${CLASE_ESTADO[e]}"><strong>${a.porEstado[e]}</strong> ${esc(e.toLowerCase())}</li>`).join('');
  const avisos = [
    pasadas.length ? `${pasadas.length === 1 ? 'La clase' : 'Las clases'} ${pasadas.map((x) => `${x.id} (${fechaLarga(x.fecha)})`).join(', ')} ya ${pasadas.length === 1 ? 'pasó' : 'pasaron'} y no ${pasadas.length === 1 ? 'tiene' : 'tienen'} asistencia marcada. Si se reprogramó, cambia la fecha en el Excel del curso; si se dictó, marca la asistencia.` : '',
    a.sinMarcar ? `Hay ${a.sinMarcar} ${a.sinMarcar === 1 ? 'casilla sin marcar' : 'casillas sin marcar'} en clases ya dictadas. Las cuentas quedan incompletas hasta marcarlas con 1 o 0.` : '',
  ].filter(Boolean).map((x) => `<p class="alerta" role="alert">${ic('warning')}<span>${x}</span></p>`).join('');
  const tabla = seguir.length
    ? `<div class="tabla-envoltura"><table class="tabla-pend tabla-asis"><caption>A quién conviene escribirle, de más a menos urgente</caption>
      <thead><tr><th scope="col">Estudiante</th><th scope="col">Estado</th><th scope="col">Faltas</th><th scope="col">Le quedan</th><th scope="col">Asistencia hasta hoy</th><th scope="col">Puede llegar hasta</th></tr></thead>
      <tbody>${seguir.map((x) => `<tr><th scope="row">Estudiante ${x.n}</th><td><span class="est-asis ${CLASE_ESTADO[x.estado]}">${esc(x.estado)}</span></td><td>${x.faltas}</td><td>${x.quedan < 0 ? '0' : x.quedan}</td><td>${pct(x.porcentaje)}</td><td>${pct(x.puedeLlegar)}</td></tr>`).join('')}</tbody></table></div>
      <p class="nota">El número es el de la lista en el Excel de asistencia, donde está el nombre.</p>`
    : `<p class="ok-nota asis-ok">${ic('check')}<span>${a.dictadas ? 'Nadie está cerca de perder por ahora.' : 'Aún no se ha dictado ninguna clase.'}</span></p>`;
  return `<article class="asis papel" data-curso="${esc(c.id)}">${titulo}
    <p class="asis-linea">Van <strong>${a.dictadas} de ${a.programadas}</strong> clases dictadas. Asistencia promedio: <strong>${pct(a.promedio)}</strong>. Para certificar hay que asistir al menos a ${minimo} clases: se puede faltar hasta ${a.permitidas} ${a.permitidas === 1 ? 'vez' : 'veces'}.</p>
    <ul class="asis-fichas">${fichas}</ul>${avisos}${tabla}${barras(a)}</article>`;
}

/** Resumen de una línea para la portada de la sección. */
export function resumenAsistencia(rs) {
  const con = rs.filter((r) => r.asis);
  const seguir = con.reduce((s, r) => s + urgentesAsistencia(r).length, 0);
  if (!con.length) return '';
  return seguir ? `${seguir} ${seguir === 1 ? 'estudiante está' : 'estudiantes están'} en atención, en riesgo o ya perdieron el mínimo, sumando ${con.length === 1 ? 'el curso con asistencia publicada' : `los ${con.length} cursos con asistencia publicada`}.` : 'Ningún estudiante está cerca de perder el mínimo de asistencia.';
}
