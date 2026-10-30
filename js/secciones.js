// Secciones que dependen solo de los datos: unidades, docentes, acompañamiento y sobre el programa.
import { esc, horario, legible, ic } from './ui.js';
import { fechaCorta, fechaLarga, cap } from './utils-fecha.js';

const nombreClase = (c) => cap(c.clase.toLowerCase());

export function plan(el, d, abiertas) {
  const porId = new Map(d.clases.map((c) => [c.id, c]));
  el.innerHTML = d.unidades.map((u) => {
    const cs = u.clases.map((id) => porId.get(id));
    return `<details class="unidad" data-slug="${esc(u.slug)}"${abiertas.has(u.slug) ? ' open' : ''}>
      <summary>${esc(legible(u.nombre))}${ic('caret-down')}</summary>
      <div class="unidad-cuerpo">${cs.map((c) => `<div class="unidad-clase">
        <h4>${esc(nombreClase(c))} <span>${esc(fechaLarga(c.fecha))}</span></h4>
        <ul>${c.temaPuntos.map((p) => `<li>${esc(p)}</li>`).join('')}</ul></div>`).join('')}</div></details>`;
  }).join('');
}

/** Cada docente es un botón: al pulsarlo se filtra el cronograma por su nombre. */
export function docentes(el, d) {
  const faltan = d.clases.some((c) => !c.profesores.length);
  el.innerHTML = (d.profesores.length ? '' : `<p class="pendiente-nota">Los docentes se publicarán pronto.</p>`) + d.profesores.map((p) => {
    const n = d.clases.filter((c) => c.profesores.includes(p)).length;
    return `<button class="chip-docente" type="button" data-docente="${esc(p)}" title="Ver las clases de ${esc(p)}">${esc(p)}<small>${n}</small></button>`;
  }).join('') + (faltan && d.profesores.length ? `<p class="pendiente-nota">Algunas clases tienen docente por confirmar.</p>` : '');
}

export function apoyo(el, d) {
  const n = d.asistentesPat;
  el.innerHTML = n.length ? `En las sesiones de Teams te acompañan <strong>${esc(n.join(' y '))}</strong>.` : 'Quién te acompaña en las sesiones de Teams está por confirmar.';
}

/** Lo que un estudiante necesita saber del curso. El texto es el mismo de la bienvenida; un curso puede cambiarlo con `infoCurso` (lista de {titulo, texto}) en su configuración. */
export const INFO_CURSO = [
  { titulo: 'Asistencia', texto: 'Se exige una asistencia mínima del 80 % de las clases programadas para optar al certificado. Si superas el 20 % de inasistencias, no se expide la certificación.' },
  { titulo: 'Certificado', texto: 'El certificado en PDF se envía al correo electrónico registrado en un plazo máximo de 40 días hábiles después de terminar el curso.' },
  { titulo: 'Grabaciones', texto: 'Las sesiones se graban solo para control interno de la Universidad; por políticas institucionales no se comparten con los estudiantes.' },
  { titulo: 'Material de apoyo', texto: 'Oportunamente se compartirá un enlace a la carpeta compartida. Que haya diapositivas o guías depende del criterio de cada docente.' },
  { titulo: 'Conexión', texto: 'Conéctate 5 minutos antes y revisa tu conexión a internet. El enlace de cada clase está en esta página.' },
  { titulo: 'Cambios y trámites', texto: 'La Universidad puede modificar la programación o a los docentes por fuerza mayor, con aviso previo. Los aplazamientos, devoluciones o cancelaciones se rigen por el Reglamento de Estudiantes.' },
  { titulo: 'Ayuda', texto: 'Si no puedes entrar a una clase o tienes una duda logística, escríbenos por el grupo del curso.' },
];

export function infoCurso(el, cfg) {
  const lista = cfg.infoCurso ?? INFO_CURSO;
  el.innerHTML = lista.map((x) => `<div class="tarjeta"><h3>${esc(x.titulo)}</h3><p>${esc(x.texto)}</p></div>`).join('');
}

export function sobre(el, d, cfg) {
  const link = cfg.urlPaginaOficial
    ? `<a class="btn" href="${esc(cfg.urlPaginaOficial)}" target="_blank" rel="noopener noreferrer">Inscripción y valores${ic('arrow-up-right')}</a>` : '';
  el.innerHTML = `<p>La Universidad puede ajustar el cronograma. Esta página siempre muestra la versión vigente.</p>${link}`;
}

/** Personas de la Facultad a quienes escribir por temas logísticos o administrativos. Cada una: nombre, cargo y correo institucional. */
export function contactos(el, lista) {
  el.innerHTML = lista.map((p) => `<div class="contacto"><strong>${esc(p.nombre)}</strong><span>${esc(p.cargo)}</span>`
    + `<a href="mailto:${esc(p.correo)}">${esc(p.correo)}</a></div>`).join('');
}

/** "Mi asistencia": el estudiante busca su nombre (Nombre + primer apellido) o su número de lista y ve su fila. Sin asistencia publicada, la sección queda oculta. */
export async function miAsistencia(seccion, nav, entrada, salida) {
  let a;
  try { const r = await fetch(`asistencia.json?m=${Math.floor(Date.now() / 60000)}`, { cache: 'no-store' }); if (!r.ok) return; a = await r.json(); } catch { return; }
  seccion.hidden = nav.hidden = false;
  const plano = (t) => String(t ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
  const NIVEL = { 'Aprobó': 'ok', 'Al día': 'ok', Atención: 'atencion', 'En riesgo': 'riesgo', 'Perdió el mínimo': 'riesgo' };
  const ficha = (x) => {
    const marcas = Object.keys(x.marcas).map(Number).sort((p, q) => p - q);
    const q = Math.max(x.quedan ?? 0, 0), total = x.faltas + q;
    const tramos = Array.from({ length: Math.min(total, 24) }, (_, k) => `<i class="${k < x.faltas ? 'gasto' : ''}"></i>`).join('');
    const frase = x.estado === 'Perdió el mínimo' ? 'Con las clases que llevamos ya no se alcanza el 80 % exigido para certificar.'
      : q === 0 ? 'No te quedan faltas: otra inasistencia haría que no alcances el 80 % exigido.' : `Puedes faltar a ${q === 1 ? '1 clase más' : `${q} clases más`} y aún alcanzar el 80 % exigido para certificar.`;
    return `<article class="asis-ficha nivel-${NIVEL[x.estado] || 'ok'}">
      <header><h3>${esc(x.etiqueta || `N.º ${x.n}`)}</h3><span class="asis-sello">${esc(x.estado)}</span></header>
      <dl class="asis-cifras"><div><dt>Asististe</dt><dd>${x.asistio}</dd></div><div><dt>Faltaste</dt><dd>${x.faltas}</dd></div><div><dt>Te quedan</dt><dd>${q}</dd></div></dl>
      <div class="asis-medidor" role="img" aria-label="Has usado ${x.faltas} de ${total} faltas permitidas"><div class="asis-tramos">${tramos}</div><p>Faltas usadas: ${x.faltas} de ${total} permitidas</p></div>
      <p class="asis-frase">${frase}</p>
      <ol class="asis-clases" aria-label="Asistencia clase por clase">${marcas.map((k) => `<li class="${x.marcas[k] === 1 ? 'si' : 'no'}" title="Clase ${k}: ${x.marcas[k] === 1 ? 'asististe' : 'faltaste'}"><b>${k}</b><span>${x.marcas[k] === 1 ? 'Asistí' : 'Falté'}</span></li>`).join('')}</ol>
      <p class="asis-fecha">Actualizado el ${esc((a.actualizado || '').slice(0, 10))}${a.dictadas ? `, con ${a.dictadas} clases dictadas` : ''}.</p></article>`;
  };
  const ver = () => {
    const t = plano(entrada.value);
    if (!t) { salida.innerHTML = ''; return; }
    if (t.length < 3 && !/^\d+$/.test(t)) { salida.innerHTML = '<p class="asis-vacio">Escribe al menos 3 letras de tu nombre, o tu número de lista.</p>'; return; }
    const hallados = a.lista.filter((x) => String(x.n) === t || plano(x.etiqueta).includes(t));
    salida.innerHTML = hallados.length ? hallados.slice(0, 8).map(ficha).join('') : '<p class="asis-vacio">No encontramos ese nombre o número. Escríbelo como Nombre y primer apellido, o consulta tu número con la coordinación del curso.</p>';
  };
  entrada.addEventListener('input', ver);
}
