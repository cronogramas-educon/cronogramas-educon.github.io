import { cargarConfig, cargarDatos } from './datos.js';
import { estado, poner, leerURL, hayFiltros, suscribir } from './estado.js';
import { filtrar } from './filtros.js';
import { renderLista, iniciarLista } from './vista-lista.js';
import { renderCalendario, iniciarCalendario, mesesDe } from './vista-calendario.js';
import { renderPanel, tick, proximaDe } from './proxima-clase.js';
import { renderAvisos } from './cambios.js';
import { construirICS, descargar, urlSuscripcion } from './ics.js';
import { prepararHoja } from './pdf.js';
import * as sec from './secciones.js';
import { esc, usarSiglas, legible } from './ui.js';
import { ic } from './iconos.js';
import { ahora, estadoClase, haceCuanto, partes, MESES } from './utils-fecha.js';

const $ = (id) => document.getElementById(id);
let datos, cfg, ultimaCarga = new Date(), desdeCopia = false, guardadoEn = null, firma = '';
const plan = new Set();

const sinDia = (iso) => { const p = partes(iso); return `${p.d} de ${MESES[p.m - 1]} de ${p.y}`; };
const corto = (s, n) => (s.length > n ? s.slice(0, n - 1) + '…' : s);

function contexto() {
  const t = ahora();
  return { meta: datos.meta, cfg, q: estado.q, t, proximaId: proximaDe(datos.clases, t)?.id, mes: estado.mes, sel: estado.sel, foco: estado.foco };
}
const visibles = () => filtrar(datos.clases, estado, ahora());

function resumenFiltros() {
  const o = [];
  if (estado.q) o.push(`búsqueda "${estado.q}"`);
  if (estado.docente) o.push(`docente ${estado.docente}`);
  if (estado.unidad) o.push(`unidad ${legible(datos.unidades.find((u) => u.slug === estado.unidad)?.nombre ?? '')}`);
  if (estado.estado !== 'todas') o.push(estado.estado);
  if (estado.ocultar) o.push('sin realizadas');
  return o.join(', ');
}

const vacio = () => `<div class="vacio"><strong>Ninguna clase coincide con tu búsqueda</strong>Prueba con otras palabras o <button class="enlace-btn" type="button" data-limpiar>limpia los filtros</button> para ver las ${datos.meta.totalClases} clases.</div>`;
const firmaEstados = () => { const t = ahora(); return datos.clases.map((c) => estadoClase(c, t)[0]).join('') + proximaDe(datos.clases, t)?.id; };

function pintar() {
  const ctx = contexto();
  const cs = visibles();
  document.querySelectorAll('[data-vista]').forEach((b) => b.setAttribute('aria-pressed', b.dataset.vista === estado.vista));
  if ($('f-q').value !== estado.q) $('f-q').value = estado.q;
  $('f-docente').value = estado.docente; $('f-unidad').value = estado.unidad; $('f-estado').value = estado.estado;
  $('f-ocultar').checked = estado.ocultar; $('f-temas').checked = estado.temas;
  $('limpiar').hidden = !hayFiltros();
  const activos = [estado.docente, estado.unidad, estado.estado !== 'todas', estado.ocultar].filter(Boolean).length;
  $('cuenta-filtros').hidden = !activos;
  $('cuenta-filtros').textContent = activos;
  $('contador').textContent = cs.length === datos.meta.totalClases ? `${cs.length} clases` : `Mostrando ${cs.length} de ${datos.meta.totalClases} clases`;
  const v = $('vista');
  if (estado.vista === 'lista') {
    v.className = 'vista-lista';
    cs.length ? renderLista(v, cs, ctx) : (v.innerHTML = vacio());
  } else {
    v.className = 'vista-cal';
    renderCalendario(v, cs, ctx);
    if (!cs.length) v.insertAdjacentHTML('afterbegin', vacio());
    if (estado.foco) { v.querySelector(`[data-fecha="${estado.foco}"]`)?.focus(); estado.foco = null; }
  }
  renderAvisos($('avisos'), datos.clases, cfg, ctx.t);
  firma = firmaEstados();
}

function estaticos() {
  const m = datos.meta;
  const nombre = cfg.programaCorto ?? m.programa.split(',')[0];
  $('marca').textContent = cfg.marca ?? `${m.tipo} ${nombre.split(' ')[0]}`;
  $('titulo').innerHTML = nombre.split(' ').map((w) => (w.includes('-') ? `<span class="sin-corte">${esc(w)}</span>` : esc(w))).join(' ');
  // Terminado: el mismo enlace sigue abierto en modo lectura y se aclara de qué periodo es
  const terminado = datos.clases.every((c) => estadoClase(c, ahora()) === 'pasada');
  document.body.classList.toggle('finalizado', terminado);
  $('lead').innerHTML = `<strong>${esc(m.tipo)}${terminado ? ' finalizado' : ''}.</strong> ${terminado && cfg.periodo ? `Periodo ${esc(cfg.periodo)}. ` : ''}${m.totalClases} clases del ${esc(sinDia(m.inicio))} al ${esc(sinDia(m.fin))}. ${esc(m.modalidad)}.`;
  document.title = `${nombre}, cronograma`;
  // Sin unidades en el Excel no hay temario por unidades ni filtro de unidad
  const hayUnidades = datos.unidades.length > 0;
  $('temario').hidden = !hayUnidades;
  $('nav').querySelector('[href="#temario"]').hidden = !hayUnidades;
  $('f-unidad').closest('.campo').hidden = !hayUnidades;
  sec.plan($('plan-lista'), datos, plan);
  sec.docentes($('docentes-lista'), datos);
  sec.apoyo($('apoyo'), datos);
  sec.sobre($('sobre-contenido'), datos, cfg);
  $('pie-nombre').textContent = [cfg.universidad, cfg.facultad].filter(Boolean).join(', ');
  const opt = (v, t, title) => `<option value="${esc(v)}"${title ? ` title="${esc(title)}"` : ''}>${esc(t)}</option>`;
  $('f-docente').innerHTML = opt('', 'Todos') + datos.profesores.map((p) => opt(p, p)).join('');
  $('f-unidad').innerHTML = opt('', 'Todas las unidades') + datos.unidades.map((u) => opt(u.slug, corto(legible(u.nombre), 64), legible(u.nombre))).join('');
  $('suscribir').href = urlSuscripcion();
}

function textoActualizado() {
  $('actualizado').textContent = `Datos actualizados ${haceCuanto(datos.meta.generadoEn)}`;
  const r = $('aviso-red');
  r.hidden = !desdeCopia;
  if (desdeCopia) r.innerHTML = `<div class="dentro">Mostrando la última versión guardada (${esc(haceCuanto(guardadoEn ?? ultimaCarga))}). Revisa tu conexión: seguiremos intentando.</div>`;
}

function aplicar(data) {
  datos = data;
  if (!estado.vista) estado.vista = matchMedia('(max-width: 720px)').matches ? 'lista' : 'calendario';
  const meses = mesesDe(datos.meta);
  if (!meses.includes(estado.mes)) { const p = proximaDe(datos.clases); estado.mes = p ? p.fecha.slice(0, 7) : meses.at(-1); }
  estaticos();
  renderPanel($('panel'), datos.clases, datos.meta, cfg);
  if (hayFiltros() && !estado.q) abrirFiltros(true);
  pintar();
  textoActualizado();
}

async function refrescar() {
  try {
    const r = await cargarDatos();
    ultimaCarga = new Date(); desdeCopia = r.desdeCopia; guardadoEn = r.guardadoEn;
    if (r.data.meta.hash !== datos.meta.hash || r.data.meta.generadoEn !== datos.meta.generadoEn) aplicar(r.data);
  } catch { desdeCopia = true; guardadoEn = guardadoEn ?? ultimaCarga.toISOString(); }
  textoActualizado();
}

function abrirFiltros(abierto) {
  $('filtros').hidden = !abierto;
  $('abrir-filtros').setAttribute('aria-expanded', abierto);
}

function limpiar() { poner({ q: '', docente: '', unidad: '', estado: 'todas', ocultar: false, sel: null }); $('f-q').value = ''; }

function enlazar() {
  document.querySelectorAll('[data-ic]').forEach((e) => { e.outerHTML = ic(e.dataset.ic); });
  const dponer = (k) => (e) => poner({ [k]: e.target.value, sel: null });
  let to;
  $('f-q').addEventListener('input', (e) => { clearTimeout(to); to = setTimeout(() => poner({ q: e.target.value.trim(), sel: null }), 120); });
  $('f-docente').onchange = dponer('docente'); $('f-unidad').onchange = dponer('unidad'); $('f-estado').onchange = dponer('estado');
  $('f-ocultar').onchange = (e) => poner({ ocultar: e.target.checked, sel: null });
  $('f-temas').onchange = (e) => { estado.temas = e.target.checked; };
  $('abrir-filtros').onclick = () => abrirFiltros($('filtros').hidden);
  document.querySelectorAll('[data-vista]').forEach((b) => (b.onclick = () => poner({ vista: b.dataset.vista, sel: null })));
  $('limpiar').onclick = limpiar;
  $('vista').addEventListener('click', (e) => { if (e.target.closest('[data-limpiar]')) limpiar(); });
  document.addEventListener('click', (e) => {
    const i = e.target.closest('[data-ics]');
    if (i) { const c = datos.clases.find((x) => x.id === +i.dataset.ics); descargar(`clase-${String(c.id).padStart(2, '0')}.ics`, construirICS([c], datos.meta, cfg)); }
    if (e.target.closest('[data-ics-visibles]')) { descargar('clases-visibles.ics', construirICS(visibles(), datos.meta, cfg)); $('menu-ics').open = false; }
    if (e.target.closest('[data-ics-todas]')) { descargar('cronograma.ics', construirICS(datos.clases, datos.meta, cfg)); $('menu-ics').open = false; }
    if (e.target.closest('[data-pdf]')) { e.preventDefault(); window.print(); }
    const d = e.target.closest('[data-docente]');
    if (d) { abrirFiltros(true); poner({ docente: d.dataset.docente, sel: null }); $('cronograma').scrollIntoView(); }
    if (!e.target.closest('#menu-ics')) $('menu-ics').open = false;
  });
  $('plan-lista').addEventListener('toggle', (e) => { const s = e.target.dataset?.slug; if (s) e.target.open ? plan.add(s) : plan.delete(s); }, true);
  const mb = document.querySelector('.menu-btn');
  mb.onclick = () => { const a = $('nav').classList.toggle('abierto'); mb.setAttribute('aria-expanded', a); };
  $('nav').addEventListener('click', (e) => { if (e.target.closest('a')) { $('nav').classList.remove('abierto'); mb.setAttribute('aria-expanded', false); } });
  window.addEventListener('beforeprint', () => prepararHoja($('hoja-impresion'), visibles(), { meta: datos.meta, cfg, estado, resumenFiltros: resumenFiltros() }));
  iniciarLista($('vista'));
  iniciarCalendario($('vista'), { poner, estado, mesesActual: () => mesesDe(datos.meta) });
  suscribir(pintar);
}

async function arrancar() {
  cfg = await cargarConfig();
  usarSiglas(cfg.siglas);
  leerURL();
  try {
    const r = await cargarDatos();
    desdeCopia = r.desdeCopia; guardadoEn = r.guardadoEn;
    enlazar();
    aplicar(r.data);
  } catch (e) {
    $('titulo').textContent = cfg.programaCorto ?? 'Cronograma';
    $('vista').innerHTML = e.sinDatos
      ? `<div class="vacio"><strong>El cronograma de este curso se publicará pronto</strong>Vuelve a revisar esta página en unas horas.</div>`
      : `<div class="vacio"><strong>No pudimos cargar el cronograma</strong>Revisa tu conexión e inténtalo de nuevo. <button class="enlace-btn" type="button" onclick="location.reload()">Reintentar</button></div>`;
    return;
  }
  setInterval(() => { if (document.visibilityState === 'visible') tick(); }, 1000);
  setInterval(() => { if (document.visibilityState !== 'visible') return; if (firmaEstados() !== firma) { renderPanel($('panel'), datos.clases, datos.meta, cfg); pintar(); } textoActualizado(); }, 30000);
  setInterval(() => { if (document.visibilityState === 'visible') refrescar(); }, 60000);
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') { refrescar(); tick(); if (firmaEstados() !== firma) pintar(); } });
}
arrancar();
