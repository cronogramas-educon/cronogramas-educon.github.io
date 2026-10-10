#!/usr/bin/env python3
"""Genera el Excel "Registro de cursos" a partir de config/cursos.json: python scripts/generar_registro_xlsx.py SALIDA.xlsx
Las dos hojas son para personas sin conocimientos técnicos: Instrucciones (con secciones y colores) y Registro (una fila por curso)."""
import sys
from pathlib import Path
from urllib.parse import quote

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.properties import PageSetupProperties
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableFormula, TableStyleInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cursos as cu

AZUL, AZUL_CLARO, ROJO, ROSA, GRIS = "1F3864", "9DB7DB", "B60205", "FDE9E7", "F2F2F2"
TENANT = "aca51631-00fe-490d-91ab-163ef87260ee"
FUENTE = "Calibri"

# (nombre, ancho, obligatoria, qué escribir, ejemplo, ayuda corta al seleccionar la celda)
COLS = [
    ("Periodo", 11, "Sí", "El semestre o ciclo del curso, con año, guion y número.", "2026-2", "Año, guion y número. Ejemplo: 2026-2"),
    ("Carpeta del periodo", 24, "Sí", "El nombre exacto de la carpeta del periodo en SharePoint, tal como se ve.", "EDU CONTINUA 2026", "Nombre exacto de la carpeta del periodo en SharePoint"),
    ("Cohorte", 14, "Recomendada", "Cuál apertura del periodo es. Un mismo periodo puede abrir los mismos cursos varias veces (por ejemplo al inicio y dos meses después): cada apertura es una cohorte, una carpeta dentro del periodo.", "Cohorte 1", "Apertura dentro del periodo. Ejemplo: Cohorte 1, Cohorte 2"),
    ("Carpeta del curso", 44, "Sí", "El nombre exacto de la carpeta del curso. Si está dentro de otra carpeta, escribe las dos separadas por una barra.", "Dip en Derecho Laboral", "Nombre exacto de la carpeta del curso. Si hay una carpeta dentro de otra, sepáralas con una barra /"),
    ("Tipo", 13, "Recomendada", "Elige Diplomado o Curso en la lista. Se antepone solo al nombre en todo el sitio, así que no lo escribas dentro del nombre.", "Diplomado", "Elige Diplomado o Curso en la lista"),
    ("Nombre del curso", 44, "Sí", "El nombre corto que verán los estudiantes como título. Sin la palabra Diplomado ni Curso.", "Derecho Laboral", "Nombre corto, sin la palabra Diplomado ni Curso"),
    ("Nombre completo", 70, "Opcional", "El nombre oficial del programa. Si lo dejas vacío se usa el nombre del curso.", "Diplomado en Derecho Laboral", "Nombre oficial. Vacío = se usa el nombre del curso"),
    ("Modalidad", 26, "Opcional", "Cómo se dicta. Si lo dejas vacío aparece Por confirmar.", "Remota (Microsoft Teams)", "Por ejemplo: Remota (Microsoft Teams)"),
    ("Hora de inicio", 14, "Sí", "A qué hora empiezan las clases, con dos puntos.", "18:00", "Hora con dos puntos. Ejemplo: 18:00"),
    ("Hora de fin", 13, "Opcional", "A qué hora terminan. Si lo dejas vacío, cada clase termina según las horas de su Excel del curso.", "21:00", "Hora con dos puntos. Vacío = según las horas del Excel del curso"),
    ("Inicio del sábado", 17, "Opcional", "Solo si los sábados empiezan a otra hora y dejaste vacía la Hora de fin.", "08:00", "Solo si los sábados empiezan a otra hora (y la Hora de fin está vacía)"),
    ("Página oficial", 60, "Opcional", "La dirección de la página del programa en unisabana.edu.co.", "https://www.unisabana.edu.co/programas/...", "Dirección completa, empieza por https://"),
    ("Grupo de Teams", 50, "Opcional", "El enlace del grupo de Teams del curso, para avisar a los estudiantes de los cambios de fecha. En Teams: los tres puntos del equipo, Obtener vínculo al equipo.", "https://teams.microsoft.com/l/team/...", "Enlace de Obtener vínculo al equipo, en Teams"),
    ("Clave", 30, "Automático", "Identifica la fila para que el sistema escriba el Estado. Se calcula sola con las carpetas. No la edites.", "EduContinua 2026-2/Cohorte 1/Dip en Derecho Laboral", "Se calcula sola, no la edites"),
    ("Estado", 34, "Automático", "Lo escribe el sistema cuando prepara la carpeta y el Excel del curso. No lo edites.", "Listo: carpeta y Excel creados", "Lo escribe el sistema, no lo edites"),
]
OBLIGATORIAS = {"Periodo", "Carpeta del periodo", "Carpeta del curso", "Nombre del curso", "Hora de inicio"}
TIPOS_ENCABEZADO = {"Sí": "Obligatoria", "Recomendada": "Recomendada", "Opcional": "Opcional", "Automático": "Automática"}
N = len(COLS)
IDX = {c[0]: i for i, c in enumerate(COLS, 1)}
L = lambda nombre: chr(64 + IDX[nombre])  # letra de columna de un encabezado


def _link_teams(c):
    t = c.get("teams")
    return f"https://teams.microsoft.com/l/team/{quote(t['canal'])}/conversations?groupId={t['equipo']}&tenantId={TENANT}" if t else ""


YA_EXISTIA = "Ya existía antes del sitio EduContinua"


def _hoja_registro(wb, reg, con_teams=True):
    ws = wb.active
    ws.title = "Registro"
    borde = Border(bottom=Side(style="thin", color="BFBFBF"))
    for j, (t, w, obl, _q, _e, ayuda) in enumerate(COLS, 1):
        c = ws.cell(1, j, t)
        pide = t in OBLIGATORIAS
        auto = obl == "Automático"
        c.font = Font(bold=True, name=FUENTE, size=11, color="FFFFFF" if pide else ("595959" if auto else AZUL))
        c.fill = PatternFill("solid", fgColor=AZUL if pide else ("D9D9D9" if auto else AZUL_CLARO))
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[c.column_letter].width = w
        nota = Comment(f"{TIPOS_ENCABEZADO[obl]}. {ayuda}.", "Registro")
        nota.width, nota.height = 260, 90
        c.comment = nota
    ws.row_dimensions[1].height = 30
    for i, c in enumerate(reg["cursos"], 2):
        per, cur = c["carpeta"].split("/", 1)
        coh = c.get("cohorte", "")
        if coh and cur.startswith(coh + "/"):
            cur = cur[len(coh) + 1:]
        h = c["horario"]
        fila = [c["periodo"], per, coh, cur, c["tipo"], c["programaCorto"], c["programa"], c["modalidad"], h["inicio"], h.get("fin", ""),
                h.get("porDia", {}).get("Sábado", ""), c.get("urlPaginaOficial", ""), _link_teams(c) if con_teams else "", None, YA_EXISTIA]
        for j, v in enumerate(fila, 1):
            x = ws.cell(i, j, v)
            x.alignment = Alignment(vertical="center", wrap_text=True)
            x.font = Font(name=FUENTE, size=11)
            x.border = borde
        ws.row_dimensions[i].height = 32
    n = len(reg["cursos"]) + 1
    for col in (L("Hora de inicio"), L("Hora de fin"), L("Inicio del sábado")):  # las horas son texto (18:00) también en las filas que se agreguen
        for r in range(2, 200):
            ws[f"{col}{r}"].number_format = "@"
    clave = f'={L("Carpeta del periodo")}{{r}}&"/"&IF({L("Cohorte")}{{r}}="","",{L("Cohorte")}{{r}}&"/")&{L("Carpeta del curso")}{{r}}'
    for r in range(2, n + 1):
        ws[f"{L('Clave')}{r}"] = clave.format(r=r)
    t = Table(displayName="Table1", ref=f"A1:{L('Estado')}{n}")
    t.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=True)
    t._initialise_columns()
    for col, (nombre, *_r) in zip(t.tableColumns, COLS):  # la clave se calcula sola también en las filas que se agreguen
        col.name = nombre
        if nombre == "Clave":
            col.calculatedColumnFormula = TableFormula(attr_text='Table1[[#This Row],[Carpeta del periodo]]&"/"&IF(Table1[[#This Row],[Cohorte]]="","",Table1[[#This Row],[Cohorte]]&"/")&Table1[[#This Row],[Carpeta del curso]]')
    ws.add_table(t)

    def regla(rango, tipo, **kw):
        dv = DataValidation(type=tipo, allow_blank=True, showErrorMessage=True, showInputMessage=True, **kw)
        ws.add_data_validation(dv)
        dv.add(rango)
        return dv

    for j, (nombre, _w, _o, _q, _e, ayuda) in enumerate(COLS, 1):  # ayuda al seleccionar cada celda
        col = ws.cell(1, j).column_letter
        if nombre == "Tipo":
            dv = regla(f"{col}2:{col}200", "list", formula1='"Diplomado,Curso"')
            dv.error, dv.errorTitle = "Elige Diplomado o Curso de la lista.", "Tipo"
        elif nombre in ("Hora de inicio", "Hora de fin", "Inicio del sábado"):
            dv = regla(f"{col}2:{col}200", "custom", formula1=f'AND(LEN({col}2)=5,MID({col}2,3,1)=":",ISNUMBER(--LEFT({col}2,2)),ISNUMBER(--RIGHT({col}2,2)))', errorStyle="warning")
            dv.error, dv.errorTitle = "Escribe la hora con dos puntos, por ejemplo 18:00. Si continúas, el sistema intentará entenderla.", "Hora"
        elif nombre == "Periodo":
            dv = regla(f"{col}2:{col}200", "custom", formula1=f'AND(LEN({col}2)=6,MID({col}2,5,1)="-")', errorStyle="warning")
            dv.error, dv.errorTitle = "Escribe el periodo como 2026-2 (año, guion y número).", "Periodo"
        elif nombre == "Página oficial":
            dv = regla(f"{col}2:{col}200", "custom", formula1=f'LEFT({col}2,8)="https://"', errorStyle="warning")
            dv.error, dv.errorTitle = "La dirección debe empezar por https://", "Página oficial"
        else:
            dv = regla(f"{col}2:{col}200", None)
        dv.promptTitle, dv.prompt = nombre[:32], ayuda
    ULT = L("Grupo de Teams")
    rosa = PatternFill("solid", bgColor=ROSA, fgColor=ROSA)
    for j, (nombre, *_r) in enumerate(COLS, 1):  # una celda obligatoria vacía en una fila que ya tiene datos se pinta de rosa
        if nombre in OBLIGATORIAS:
            col = ws.cell(1, j).column_letter
            ws.conditional_formatting.add(f"{col}2:{col}200", FormulaRule(formula=[f'AND(COUNTA($A2:${ULT}2)>0,LEN({col}2)=0)'], fill=rosa))
    ws.freeze_panes = "A2"
    return ws


def _seccion(ay, fila, texto):
    ay.merge_cells(start_row=fila, start_column=2, end_row=fila, end_column=5)
    c = ay.cell(fila, 2, texto)
    c.font = Font(name=FUENTE, bold=True, size=13, color=AZUL)
    for col in range(2, 6):
        ay.cell(fila, col).border = Border(bottom=Side(style="medium", color=ROJO))
    ay.row_dimensions[fila].height = 26
    return fila + 1


def _texto(ay, fila, c1, c2, texto, alto=None, negrita=False, color="000000", fondo=None):
    ay.merge_cells(start_row=fila, start_column=c1, end_row=fila, end_column=c2)
    c = ay.cell(fila, c1, texto)
    c.alignment = Alignment(wrap_text=True, vertical="center")
    c.font = Font(name=FUENTE, size=11, bold=negrita, color=color)
    if fondo:
        for col in range(c1, c2 + 1):
            ay.cell(fila, col).fill = PatternFill("solid", fgColor=fondo)
    if alto:
        ay.row_dimensions[fila].height = alto


def _paso(ay, fila, numero, texto, alto=34):
    n = ay.cell(fila, 2, numero)
    n.font = Font(name=FUENTE, bold=True, size=14, color="FFFFFF")
    n.fill = PatternFill("solid", fgColor=AZUL)
    n.alignment = Alignment(horizontal="center", vertical="center")
    _texto(ay, fila, 3, 5, texto, alto, fondo=GRIS)
    ay.row_dimensions[fila].height = alto
    return fila + 1


def _hoja_instrucciones(wb):
    ay = wb.create_sheet("Instrucciones")
    ay.sheet_view.showGridLines = False
    for col, w in zip("ABCDE", (2, 24, 16, 64, 44)):
        ay.column_dimensions[col].width = w
    ay.merge_cells("B1:E1")
    t = ay.cell(1, 2, "Registro de cursos y diplomados")
    t.font, t.alignment = Font(name=FUENTE, bold=True, size=22, color="FFFFFF"), Alignment(vertical="center", indent=1)
    for col in range(2, 6):
        ay.cell(1, col).fill = PatternFill("solid", fgColor=AZUL)
    ay.row_dimensions[1].height = 48
    for col in range(2, 6):
        ay.cell(2, col).fill = PatternFill("solid", fgColor=ROJO)
    ay.row_dimensions[2].height = 5
    _texto(ay, 3, 2, 5, "Aquí se decide qué cursos aparecen en el sitio de cronogramas. Escribes, guardas y listo: no hace falta tocar GitHub ni pedir ayuda.", 38)

    f = _seccion(ay, 5, "1. Lo esencial en tres pasos")
    f = _paso(ay, f, "1", "Abre la hoja Registro. Cada fila es un curso de un periodo. Agrega una fila nueva debajo de la última, o edita la de un curso que ya existe.")
    f = _paso(ay, f, "2", "Guarda el archivo. No hay botón de enviar: al guardar, el sitio se actualiza solo.")
    f = _paso(ay, f, "3", "Espera un par de minutos y revisa el sitio de administración, sección Cursos y periodos. Ahí aparece el curso nuevo con su enlace para estudiantes, o el aviso si algo falló.")

    f = _seccion(ay, f + 1, "2. Qué significan los colores de la hoja Registro")
    for texto, fondo, color in (("Encabezado azul oscuro: dato obligatorio. Sin él, el curso nuevo no se crea.", AZUL, "FFFFFF"),
                                ("Encabezado azul claro: dato opcional o que se completa solo si falta.", AZUL_CLARO, AZUL),
                                ("Celda rosada: falta un dato obligatorio en una fila que ya tiene información. Complétala.", ROSA, ROJO)):
        _texto(ay, f, 2, 5, texto, 26, negrita=True, color=color, fondo=fondo)
        f += 1
    _texto(ay, f, 2, 5, "Al seleccionar una celda de la hoja Registro aparece una ayuda corta de qué escribir.", 24, color="595959")
    f += 1

    f = _seccion(ay, f + 1, "3. Qué escribir en cada columna")
    for j, h in enumerate(("Columna", "¿Obligatoria?", "Qué escribir", "Ejemplo"), 2):
        c = ay.cell(f, j, h)
        c.font, c.fill = Font(name=FUENTE, bold=True, color="FFFFFF"), PatternFill("solid", fgColor=AZUL)
        c.alignment = Alignment(vertical="center", indent=1)
    ay.row_dimensions[f].height = 22
    f += 1
    for k, (nombre, _w, obl, que, ejemplo, _a) in enumerate(COLS):
        fondo = PatternFill("solid", fgColor=GRIS if k % 2 == 0 else "FFFFFF")
        for j, v in enumerate((nombre, obl, que, ejemplo), 2):
            c = ay.cell(f, j, v)
            c.fill = fondo
            c.alignment = Alignment(wrap_text=True, vertical="center", indent=1)
            c.font = Font(name=FUENTE, size=11, bold=j == 2, color=ROJO if (j == 3 and obl == "Sí") else "000000")
        ay.row_dimensions[f].height = 50 if len(que) > 110 else 36
        f += 1

    f = _seccion(ay, f + 1, "4. Cómo se organizan las carpetas")
    _texto(ay, f, 2, 5, "Todo vive en el sitio EduContinua de SharePoint. Cada periodo (semestre) tiene su carpeta, y dentro van las cohortes: una cohorte es cada vez que se abren cursos dentro del mismo periodo. Así, si a mitad del semestre se vuelven a abrir los mismos cursos, van en otra cohorte y no se mezclan.", 52)
    f += 1
    _texto(ay, f, 2, 5, "EduContinua 2026-2  >  Cohorte 1  >  Dip en Derecho Laboral  >  Cuadro de horas módulos y profesores.xlsx", 28, negrita=True, color=AZUL, fondo=GRIS)
    f += 1

    f = _seccion(ay, f + 1, "5. Cómo agregar cursos: lo que haces tú y lo que hace el sistema")
    for i, txt in enumerate(("Escribe una fila por curso en la hoja Registro: periodo, cohorte, nombre del curso y horas. Si prefieres no tocar la tabla, usa el formulario Registrar curso nuevo.",
                             "Guarda. El sistema crea solo la carpeta del periodo, la de la cohorte y la del curso, y copia adentro el Excel Cuadro de horas ya preparado.",
                             "Mira la columna Estado de tu fila: dice Listo cuando todo se creó, o explica qué falló.",
                             "Abre el Excel del curso y llena el cronograma. Al guardarlo, el sitio publica la página del curso."), 1):
        f = _paso(ay, f, str(i), txt, 36)

    f = _seccion(ay, f + 1, "6. Cómo abrir un periodo nuevo o una cohorte nueva")
    for i, txt in enumerate(("Periodo nuevo: copia las filas del periodo anterior, pégalas debajo y cambia el Periodo (por ejemplo 2027-1) y la Carpeta del periodo (por ejemplo EduContinua 2027-1). Deja vacía la columna Estado.",
                             "Cohorte nueva en el mismo periodo: copia las filas de los cursos que se vuelven a abrir y cambia solo la Cohorte (por ejemplo Cohorte 2). Deja vacía la columna Estado.",
                             "Guarda. Cada curso nuevo aparece en el sitio de administración con su propio enlace para estudiantes."), 1):
        f = _paso(ay, f, str(i), txt, 36)

    f = _seccion(ay, f + 1, "7. Importante")
    for txt in ("Un curso se reconoce por Carpeta del periodo, Cohorte y Carpeta del curso. Esas tres columnas no se cambian en un curso que ya existe: si las cambias, el sistema cree que es un curso nuevo.",
                "Nunca borres la fila de un curso que ya se dictó: pasa solo al archivo del sitio y su enlace sigue funcionando en modo lectura. Borrar la fila no daña la página, pero se pierde el rastro de que existió.",
                "Los códigos de las direcciones de los estudiantes los genera el sistema. No se escriben aquí.",
                "Si pegas filas de otro archivo, usa Pegar solo valores para no traer formatos raros."):
        _texto(ay, f, 2, 5, "•  " + txt, 40)
        f += 1

    f = _seccion(ay, f + 1, "8. Si algo no sale como esperabas")
    for txt in ("El curso no aparece: mira si la fila tiene celdas rosadas y completa los datos obligatorios.",
                "El sitio de administración avisa en la sección Cursos y periodos qué fila tiene el problema y por qué (una hora mal escrita, un enlace de Teams que no se entiende, una carpeta repetida). Esa fila no se procesa, las demás sí.",
                "El curso aparece pero sin cronograma: falta guardar el Excel Cuadro de horas de ese curso en su carpeta."):
        _texto(ay, f, 2, 5, "•  " + txt, 40)
        f += 1
    ay.page_setup.orientation, ay.page_setup.fitToWidth, ay.page_setup.fitToHeight = "portrait", 1, 0
    ay.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    return ay


def main(salida, con_teams=True):
    reg = cu.registro()
    wb = Workbook()
    _hoja_registro(wb, reg, con_teams)
    _hoja_instrucciones(wb)
    wb.move_sheet("Instrucciones", offset=-1)
    wb.active = 1
    wb.save(salida)


if __name__ == "__main__":
    main(sys.argv[1], "--sin-teams" not in sys.argv)  # --sin-teams: sin los enlaces de los grupos (para pasarlo por un lugar público)
