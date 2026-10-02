import { esc, horario, legible } from './ui.js';
import { fechaLargaAnio, cap, estadoClase, cambioVigente, ahora, hoyISO } from './utils-fecha.js';

/** Llena #hoja-impresion con las clases filtradas. El diálogo de impresión permite "Guardar como PDF". */
export function prepararHoja(el, clases, { meta, cfg, estado, resumenFiltros }) {
  const t = ahora();
  const filas = clases.map((c) => {
    const e = estadoClase(c, t);
    const repro = cambioVigente(c, cfg, t);
    const teams = cfg.mostrarLinksTeams && c.linkTeams ? `<a href="${esc(c.linkTeams)}">Teams</a>` : '';
    const f = repro ? `${esc(fechaLargaAnio(c.fecha))}<br><span class="imp-repro">Reprogramada (antes ${esc(fechaLargaAnio(c.cambio.fechaAnterior))})</span>` : esc(fechaLargaAnio(c.fecha));
    return `<tbody class="${e === 'pasada' ? 'imp-pasada' : ''}"><tr>
      <td>${esc(cap(c.clase.toLowerCase()))}</td><td>${f}</td><td>${esc(horario(meta))}</td>
      <td>${esc(legible(c.unidad))}</td><td>${esc(c.profesores.join(' y '))}</td><td>${esc(c.asistentePat)}</td><td>${teams}</td></tr>
      ${estado.temas ? `<tr><td class="temas" colspan="7"><ul>${c.temaPuntos.map((p) => `<li>${esc(p)}</li>`).join('')}</ul></td></tr>` : ''}</tbody>`;
  }).join('');
  el.innerHTML = `<div class="imp-cab"><h1>${esc(meta.programa)}</h1><p>Cohorte ${esc(meta.cohorte)}. Generado el ${esc(fechaLargaAnio(hoyISO(t)))}. Horario en hora de Colombia.</p></div>
    ${resumenFiltros ? `<p class="imp-filtros">Filtros activos: ${esc(resumenFiltros)}. ${clases.length} de ${meta.totalClases} clases.</p>` : ''}
    <table><thead><tr><th>Clase</th><th>Fecha</th><th>Horario</th><th>Unidad</th><th>Docente</th><th>Te acompaña</th><th>Enlace</th></tr></thead>${filas}</table>`;
}
