// Generador .ics en el navegador (mismo formato que scripts/generar_ics.py).
const VTZ = ['BEGIN:VTIMEZONE', 'TZID:America/Bogota', 'BEGIN:STANDARD', 'DTSTART:19700101T000000', 'TZOFFSETFROM:-0500', 'TZOFFSETTO:-0500', 'TZNAME:-05', 'END:STANDARD', 'END:VTIMEZONE'];
const escapar = (s) => s.replace(/\r\n/g, '\n').replace(/([,;\\])/g, '\\$1').replace(/\n/g, '\\n');
const enc = new TextEncoder();

function plegar(l) {
  if (enc.encode(l).length <= 75) return l;
  const partes = []; let actual = '', n = 0;
  for (const ch of l) {
    const b = enc.encode(ch).length;
    if (n + b > (partes.length ? 74 : 75)) { partes.push(actual); actual = ''; n = 0; }
    actual += ch; n += b;
  }
  partes.push(actual);
  return partes.join('\r\n ');
}

function evento(c, meta, cfg, stamp) {
  const dia = c.fecha.replace(/-/g, '');
  const nombre = c.clase.charAt(0) + c.clase.slice(1).toLowerCase();
  const url = cfg.mostrarLinksTeams && c.linkTeams ? c.linkTeams : '';
  const desc = [...(c.unidad ? [c.unidad, ''] : []), 'Tema:', ...c.temaPuntos.map((p) => `- ${p}`), '', `Docente: ${c.profesor || 'por confirmar'}`];
  if (c.asistentePat) desc.push(`Asistente PAT: ${c.asistentePat}`);
  if (url) desc.push('', `Unirme en Teams: ${url}`);
  const hh = (iso) => iso.slice(11, 16).replace(':', '') + '00';
  return ['BEGIN:VEVENT', `UID:clase-${String(c.id).padStart(2, '0')}@${cfg.uidSufijo}`, `DTSTAMP:${stamp}`, `SEQUENCE:${c.secuencia ?? 0}`,
    `DTSTART;TZID=America/Bogota:${dia}T${hh(c.inicio)}`, `DTEND;TZID=America/Bogota:${dia}T${hh(c.fin)}`,
    `SUMMARY:${escapar(nombre)}: ${escapar(cfg.programaCorto)}`, `DESCRIPTION:${escapar(desc.join('\n'))}`, 'LOCATION:Microsoft Teams',
    ...(url ? [`URL:${url}`] : []),
    'BEGIN:VALARM', 'ACTION:DISPLAY', `DESCRIPTION:${escapar(nombre)} comienza en 30 minutos`, 'TRIGGER:-PT30M', 'END:VALARM', 'END:VEVENT'];
}

export function construirICS(clases, meta, cfg) {
  const stamp = meta.generadoEn.replace(/[-:]/g, '');
  const l = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Cronograma Educacion Continua//ES', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
    `X-WR-CALNAME:${escapar(cfg.programaCorto)}`, 'X-WR-TIMEZONE:America/Bogota', ...VTZ];
  clases.forEach((c) => l.push(...evento(c, meta, cfg, stamp)));
  l.push('END:VCALENDAR');
  return l.map(plegar).join('\r\n') + '\r\n';
}

export function descargar(nombre, texto) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([texto], { type: 'text/calendar;charset=utf-8' }));
  a.download = nombre;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
}

export const urlSuscripcion = () => new URL('cronograma.ics', document.baseURI).href.replace(/^https?:/, 'webcal:');
