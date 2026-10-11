#!/usr/bin/env python3
"""Genera el Excel de asistencia de un curso: python scripts/generar_asistencia_xlsx.py DATOS.json SALIDA.xlsx
DATOS.json: {"curso": "...", "minimo": 0.8, "horas": 3, "clases": [{"fecha": "2026-10-01", "situacion": "", "nueva": ""}, ...],
             "estudiantes": [{"documento": "", "nombre": "...", "marcas": [1, 0, null, ...]}, ...]}
Los datos de estudiantes no viven en el repositorio (es público): el JSON se escribe fuera de él.
Hojas: Instrucciones, Asistencia (una Table1 con una columna por clase), Resumen (reglas y cuentas) y Cronograma (fechas y situación de cada clase).
Las cuentas son fórmulas: el sitio también las recalcula desde las marcas crudas (scripts/asistencia.py)."""
import json, sys
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as colletra
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.properties import PageSetupProperties
from openpyxl.worksheet.table import Table, TableFormula, TableStyleInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generar_registro_xlsx import AZUL, AZUL_CLARO, FUENTE, GRIS, ROJO, ROSA, _paso, _seccion, _texto

PRIMERA = 7          # primera fila de estudiantes (el encabezado de la tabla es la 6)
HOLGURA = 200        # filas que las cuentas y las reglas cubren, para poder agregar estudiantes
COL0 = 4             # la clase 1 está en la columna D
CALCULADAS = ["Asistió", "Faltas", "Sin marcar", "Faltas que le quedan", "% hasta hoy", "Puede llegar hasta", "Estado", "Clases programadas"]
ESTADOS = {"Al día": ("E2F0D9", "375623"), "Atención": ("FFF2CC", "7F6000"), "En riesgo": ("FBE0D6", "C00000"),
           "Perdió el mínimo": ("C00000", "FFFFFF"), "Aprobó": ("DDEBF7", "1F3864")}
DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
R = {"minimo": 4, "horas": 5, "atencion": 6, "riesgo": 7, "programadas": 10, "dictadas": 11, "pendientes": 12, "mimas": 13, "permitidas": 14,
     "horas_curso": 15, "estudiantes": 16, "promedio": 17, "sinmarcar": 25}
RES = lambda k: f"Resumen!$C${R[k]}"


def _celda(ws, ref, valor, **kw):
    c = ws[ref]
    c.value = valor
    c.font = Font(name=FUENTE, size=kw.pop("size", 11), bold=kw.pop("bold", False), color=kw.pop("color", "000000"))
    if kw.get("fill"):
        c.fill = PatternFill("solid", fgColor=kw["fill"])
    kw.pop("fill", None)
    c.alignment = Alignment(horizontal=kw.pop("h", None), vertical="center", wrap_text=kw.pop("wrap", False), indent=kw.pop("indent", 0))
    if kw.get("fmt"):
        c.number_format = kw["fmt"]
    return c


def _banner(ws, titulo, hasta):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=hasta)
    _celda(ws, "A1", titulo, size=20, bold=True, color="FFFFFF", indent=1)
    for col in range(1, hasta + 1):
        ws.cell(1, col).fill = PatternFill("solid", fgColor=AZUL)
        ws.cell(2, col).fill = PatternFill("solid", fgColor=ROJO)
    ws.row_dimensions[1].height = 40
    ws.row_dimensions[2].height = 5


def _hoja_cronograma(wb, clases):
    ws = wb.create_sheet("Cronograma")
    ws.sheet_view.showGridLines = False
    _banner(ws, "Cronograma de clases", 6)
    for col, w in zip("ABCDEF", (12, 14, 14, 18, 16, 54)):
        ws.column_dimensions[col].width = w
    _celda(ws, "A3", "Solo cambia la Situación cuando una clase se reprograma o se cancela. Lo demás se calcula con las marcas de la hoja Asistencia.", color="595959")
    for j, h in enumerate(("Clase", "Fecha", "Día", "Situación", "Nueva fecha", "Nota"), 1):
        _celda(ws, f"{colletra(j)}5", h, bold=True, color="FFFFFF", fill=AZUL, h="center")
    ws.row_dimensions[5].height = 24
    for i, c in enumerate(clases, 1):
        r = 5 + i
        _celda(ws, f"A{r}", f"Clase {i}", bold=True)
        _celda(ws, f"B{r}", date.fromisoformat(c["fecha"]), fmt="dd/mm/yyyy", h="center")
        _celda(ws, f"C{r}", f'=IF(B{r}="","",CHOOSE(WEEKDAY(B{r},2),"lunes","martes","miércoles","jueves","viernes","sábado","domingo"))', h="center")
        _celda(ws, f"D{r}", c.get("situacion") or None, h="center")
        _celda(ws, f"E{r}", date.fromisoformat(c["nueva"]) if c.get("nueva") else None, fmt="dd/mm/yyyy", h="center")
        _celda(ws, f"F{r}", c.get("nota") or None)
        for col in "ABCDEF":
            ws[f"{col}{r}"].border = Border(bottom=Side(style="thin", color="BFBFBF"))
    ult = 5 + len(clases)
    dv = DataValidation(type="list", formula1='"Reprogramada,Cancelada"', allow_blank=True, showErrorMessage=True, showInputMessage=True)
    dv.promptTitle, dv.prompt = "Situación", "Déjala vacía si la clase sigue igual. Elige Reprogramada o Cancelada."
    dv.error, dv.errorTitle = "Elige Reprogramada o Cancelada, o deja la celda vacía.", "Situación"
    ws.add_data_validation(dv)
    dv.add(f"D6:D{ult}")
    ws.freeze_panes = "A6"
    return ult


def _hoja_resumen(wb, curso, n, ult_asist, hoja_asist="Asistencia"):
    ws = wb.create_sheet("Resumen")
    ws.sheet_view.showGridLines = False
    _banner(ws, "Resumen de asistencia", 4)
    for col, w in zip("ABCD", (2, 52, 16, 70)):
        ws.column_dimensions[col].width = w
    ult = colletra(COL0 + n - 1)
    est = f"{hoja_asist}!$D$4:${ult}$4"
    col = {nombre: colletra(COL0 + n + k) for k, nombre in enumerate(CALCULADAS)}
    rango = lambda nombre: f"{hoja_asist}!${col[nombre]}${PRIMERA}:${col[nombre]}${PRIMERA + HOLGURA}"

    def fila(k, etiqueta, valor, nota="", fmt=None, editable=False):
        r = R[k]
        _celda(ws, f"B{r}", etiqueta, indent=1)
        c = _celda(ws, f"C{r}", valor, bold=True, h="center", fill="FFF2CC" if editable else GRIS, color=AZUL, fmt=fmt)
        _celda(ws, f"D{r}", nota, color="595959", wrap=True)
        ws.row_dimensions[r].height = 30 if len(nota) > 80 else 22
        return c

    def seccion(r, texto):
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)
        _celda(ws, f"B{r}", texto, bold=True, size=13, color=AZUL)
        for cc in range(2, 5):
            ws.cell(r, cc).border = Border(bottom=Side(style="medium", color=ROJO))
        ws.row_dimensions[r].height = 26

    seccion(3, "Reglas (las celdas amarillas se pueden cambiar)")
    fila("minimo", "Asistencia mínima para certificar", 0.8, "", "0%", True)
    fila("horas", "Horas por sesión", 3, "", "General", True)
    fila("atencion", "Marcar Atención cuando use este % de las faltas permitidas", 0.5, "Con 7 faltas permitidas, Atención empieza en la falta 4.", "0%", True)
    fila("riesgo", "Marcar En riesgo cuando use este % de las faltas permitidas", 0.8, "Con 7 faltas permitidas, En riesgo empieza en la falta 6 (queda una).", "0%", True)
    seccion(9, "Cuentas automáticas (no se editan)")
    fila("programadas", "Sesiones programadas", f'=COUNTIF({est},"<>Cancelada")', "No cuenta las canceladas.")
    fila("dictadas", "Sesiones dictadas", f'=COUNTIF({est},"Dictada")', "Una clase cuenta como dictada cuando tiene alguna marca en la hoja Asistencia.")
    fila("pendientes", "Sesiones por dictar", f"=C{R['programadas']}-C{R['dictadas']}")
    fila("mimas", "Asistencias mínimas para certificar", f"=ROUNDUP(ROUND(C{R['programadas']}*C{R['minimo']},6),0)", "Se redondea hacia arriba.")
    fila("permitidas", "Faltas permitidas", f"=C{R['programadas']}-C{R['mimas']}", "Con más faltas que estas ya no se llega al mínimo.")
    fila("horas_curso", "Horas del curso", f"=C{R['programadas']}*C{R['horas']}")
    fila("estudiantes", "Estudiantes", f'=COUNTA({hoja_asist}!$C${PRIMERA}:$C${PRIMERA + HOLGURA})')
    fila("promedio", "Asistencia promedio hasta hoy", f'=IFERROR(SUM({rango("Asistió")})/(SUM({rango("Asistió")})+SUM({rango("Faltas")})),"")', "", "0.0%")
    seccion(19, "Estudiantes por estado")
    for k, (nombre, (fondo, letra)) in enumerate(ESTADOS.items()):
        r = 20 + k
        _celda(ws, f"B{r}", nombre, bold=True, color=letra, fill=fondo, indent=1)
        _celda(ws, f"C{r}", f'=COUNTIF({rango("Estado")},"{nombre}")', bold=True, h="center", color=AZUL, fill=GRIS)
    _celda(ws, f"B{R['sinmarcar']}", "Casillas sin marcar en clases ya dictadas", indent=1)
    _celda(ws, f"C{R['sinmarcar']}", f'=SUM({rango("Sin marcar")})', bold=True, h="center", color=AZUL, fill=GRIS)
    _celda(ws, f"D{R['sinmarcar']}", "Debería ser 0: si no, falta marcar 1 o 0 a alguien.", color="595959")
    return ws


def _hoja_asistencia(wb, curso, clases, estudiantes):
    ws = wb.active
    ws.title = "Asistencia"
    n = len(clases)
    hay = len(estudiantes) + 6                    # filas con fórmulas: los estudiantes y seis libres
    ult = PRIMERA + hay - 1
    ucl = colletra(COL0 + n - 1)                  # última columna de clases
    col = {nombre: colletra(COL0 + n + k) for k, nombre in enumerate(CALCULADAS)}
    total_cols = COL0 + n + len(CALCULADAS) - 1
    _banner(ws, f"Asistencia: {curso}", min(total_cols, 14))
    _celda(ws, "A3", "Marca 1 si asistió y 0 si faltó. Una clase sin marcas todavía no se dictó. Detalle en la hoja Instrucciones.", color="595959")
    _celda(ws, "C4", "Estado de la sesión", bold=True, h="right", color=AZUL)
    _celda(ws, "C5", "Fecha", bold=True, h="right", color=AZUL)
    ws.row_dimensions[4].height = 20
    # encabezados de la tabla
    cab = ["N°", "Documento", "Nombre del estudiante"] + [f"Clase {i}" for i in range(1, n + 1)] + CALCULADAS
    for j, h in enumerate(cab, 1):
        c = _celda(ws, f"{colletra(j)}6", h, bold=True, h="center", wrap=True,
                   color="FFFFFF" if j <= COL0 + n - 1 else "595959", fill=AZUL if j <= COL0 + n - 1 else "D9D9D9")
        ws.column_dimensions[colletra(j)].width = 6 if j == 1 else (16 if j == 2 else (42 if j == 3 else (9 if j < COL0 + n else 14)))
    ws.row_dimensions[6].height = 34
    ws.column_dimensions[col["Estado"]].width = 18
    # estado y fecha de cada clase, tomados del cronograma
    for i in range(1, n + 1):
        L, rc = colletra(COL0 + i - 1), 5 + i
        _celda(ws, f"{L}4", f'=IF(Cronograma!$D${rc}="Cancelada","Cancelada",IF(COUNT({L}{PRIMERA}:{L}{PRIMERA + HOLGURA})>0,"Dictada",IF(Cronograma!$D${rc}="Reprogramada","Reprogramada","Pendiente")))',
               size=9, bold=True, h="center", wrap=True)
        _celda(ws, f"{L}5", f'=IF(Cronograma!$E${rc}<>"",Cronograma!$E${rc},Cronograma!$B${rc})', size=10, h="center", fmt="dd/mm/yy")
    ws.row_dimensions[4].height = 28
    # filas de estudiantes
    estr = f"${colletra(COL0)}$4:${ucl}$4"
    for k in range(hay):
        r = PRIMERA + k
        e = estudiantes[k] if k < len(estudiantes) else None
        _celda(ws, f"A{r}", (k + 1) if e else None, h="center", color="595959")
        _celda(ws, f"B{r}", (e or {}).get("documento") or None, h="center", fmt="@")
        _celda(ws, f"C{r}", (e or {}).get("nombre"), bold=bool(e))
        marcas = (e or {}).get("marcas", [])
        for i in range(n):
            v = marcas[i] if i < len(marcas) else None
            _celda(ws, f"{colletra(COL0 + i)}{r}", v, h="center")
        fila = f"{colletra(COL0)}{r}:{ucl}{r}"
        a, f_, sm, q = (f"{col[x]}{r}" for x in ("Asistió", "Faltas", "Sin marcar", "Faltas que le quedan"))
        nom = f"$C{r}"
        F = {
            "Asistió": f'=IF({nom}="","",SUMPRODUCT(({estr}="Dictada")*({fila}=1)))',
            "Faltas": f'=IF({nom}="","",SUMPRODUCT(({estr}="Dictada")*({fila}=0)*({fila}<>"")))',
            "Sin marcar": f'=IF({nom}="","",{RES("dictadas")}-{a}-{f_})',
            "Faltas que le quedan": f'=IF({nom}="","",{RES("permitidas")}-{f_})',
            "% hasta hoy": f'=IF({nom}="","",IF({a}+{f_}=0,"",{a}/({a}+{f_})))',
            "Puede llegar hasta": f'=IF({nom}="","",({RES("programadas")}-{f_})/{RES("programadas")})',
            "Clases programadas": f'=IF({nom}="","",{RES("programadas")})',
        }
        uso = f'IF({RES("permitidas")}=0,0,ROUND({f_}/{RES("permitidas")},6))'
        F["Estado"] = (f'=IF({nom}="","",IF({f_}>{RES("permitidas")},"Perdió el mínimo",IF({RES("pendientes")}=0,"Aprobó",'
                       f'IF({uso}>={RES("riesgo")},"En riesgo",IF({uso}>={RES("atencion")},"Atención","Al día")))))')
        for nombre in CALCULADAS:
            _celda(ws, f"{col[nombre]}{r}", F[nombre], h="center", fmt="0%" if nombre in ("% hasta hoy", "Puede llegar hasta") else None,
                   fill=GRIS if nombre != "Estado" else None, bold=nombre == "Estado")
        for j in range(1, total_cols + 1):
            ws.cell(r, j).border = Border(bottom=Side(style="thin", color="D9D9D9"))
    # tabla: las cuentas se llenan solas en las filas que se agreguen
    t = Table(displayName="Table1", ref=f"A6:{colletra(total_cols)}{ult}")
    t.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=False)
    t._initialise_columns()
    fila_t = f"Table1[[#This Row],[Clase 1]:[Clase {n}]]"
    est_t = f"Asistencia!${colletra(COL0)}$4:${ucl}$4"
    nom_t = "Table1[[#This Row],[Nombre del estudiante]]"
    a_t, f_t = "Table1[[#This Row],[Asistió]]", "Table1[[#This Row],[Faltas]]"
    uso_t = f'IF({RES("permitidas")}=0,0,ROUND({f_t}/{RES("permitidas")},6))'
    FT = {
        "Asistió": f'IF({nom_t}="","",SUMPRODUCT(({est_t}="Dictada")*({fila_t}=1)))',
        "Faltas": f'IF({nom_t}="","",SUMPRODUCT(({est_t}="Dictada")*({fila_t}=0)*({fila_t}<>"")))',
        "Sin marcar": f'IF({nom_t}="","",{RES("dictadas")}-{a_t}-{f_t})',
        "Faltas que le quedan": f'IF({nom_t}="","",{RES("permitidas")}-{f_t})',
        "% hasta hoy": f'IF({nom_t}="","",IF({a_t}+{f_t}=0,"",{a_t}/({a_t}+{f_t})))',
        "Puede llegar hasta": f'IF({nom_t}="","",({RES("programadas")}-{f_t})/{RES("programadas")})',
        "Clases programadas": f'IF({nom_t}="","",{RES("programadas")})',
        "Estado": (f'IF({nom_t}="","",IF({f_t}>{RES("permitidas")},"Perdió el mínimo",IF({RES("pendientes")}=0,"Aprobó",'
                   f'IF({uso_t}>={RES("riesgo")},"En riesgo",IF({uso_t}>={RES("atencion")},"Atención","Al día")))))'),
    }
    for c, nombre in zip(t.tableColumns, cab):
        c.name = nombre
        if nombre in FT:
            c.calculatedColumnFormula = TableFormula(attr_text=FT[nombre])
    ws.add_table(t)
    # solo 1 o 0 en las marcas
    dv = DataValidation(type="list", formula1='"1,0"', allow_blank=True, showErrorMessage=True, showInputMessage=True)
    dv.error, dv.errorTitle = "Escribe 1 si asistió, 0 si faltó, o deja la casilla vacía.", "Asistencia"
    dv.promptTitle, dv.prompt = "Asistencia", "1 = asistió, 0 = faltó. Vacía = aún no se marca."
    ws.add_data_validation(dv)
    dv.add(f"{colletra(COL0)}{PRIMERA}:{ucl}{PRIMERA + HOLGURA}")
    # colores: faltas en rosa, asistencias en verde suave, clases por estado, estado del estudiante
    rango_marcas = f"{colletra(COL0)}{PRIMERA}:{ucl}{PRIMERA + HOLGURA}"
    ws.conditional_formatting.add(rango_marcas, FormulaRule(formula=[f'AND({colletra(COL0)}{PRIMERA}<>"",{colletra(COL0)}{PRIMERA}=0)'], fill=PatternFill("solid", bgColor="F8CBAD", fgColor="F8CBAD"), font=Font(color="9C0006", bold=True)))
    ws.conditional_formatting.add(rango_marcas, FormulaRule(formula=[f'{colletra(COL0)}{PRIMERA}=1'], fill=PatternFill("solid", bgColor="E2F0D9", fgColor="E2F0D9")))
    for nombre, (fondo, letra) in {"Dictada": ("E2F0D9", "375623"), "Pendiente": ("F2F2F2", "7F7F7F"), "Reprogramada": ("FFF2CC", "7F6000"), "Cancelada": ("F8CBAD", "9C0006")}.items():
        ws.conditional_formatting.add(f"{colletra(COL0)}4:{ucl}4", FormulaRule(formula=[f'{colletra(COL0)}4="{nombre}"'], fill=PatternFill("solid", bgColor=fondo, fgColor=fondo), font=Font(color=letra, bold=True, size=9)))
    cE = col["Estado"]
    for nombre, (fondo, letra) in ESTADOS.items():
        ws.conditional_formatting.add(f"{cE}{PRIMERA}:{cE}{PRIMERA + HOLGURA}", FormulaRule(formula=[f'{cE}{PRIMERA}="{nombre}"'], fill=PatternFill("solid", bgColor=fondo, fgColor=fondo), font=Font(color=letra, bold=True)))
    ws.freeze_panes = f"{colletra(COL0)}{PRIMERA}"
    ws["C6"].comment = Comment("Escribe aquí el nombre completo. El resto de la fila se calcula solo.", "Asistencia", width=240, height=70)
    return n, ult


def _hoja_instrucciones(wb, curso):
    ay = wb.create_sheet("Instrucciones")
    ay.sheet_view.showGridLines = False
    for c, w in zip("ABCDE", (2, 24, 16, 64, 44)):
        ay.column_dimensions[c].width = w
    ay.merge_cells("B1:E1")
    _celda(ay, "B1", "Control de asistencia", size=22, bold=True, color="FFFFFF", indent=1)
    for c in range(2, 6):
        ay.cell(1, c).fill = PatternFill("solid", fgColor=AZUL)
        ay.cell(2, c).fill = PatternFill("solid", fgColor=ROJO)
    ay.row_dimensions[1].height = 48
    ay.row_dimensions[2].height = 5
    _texto(ay, 3, 2, 5, f"{curso}. Aquí se marca quién asistió a cada clase. Las cuentas, los avisos y el sitio de administración se calculan solos a partir de estas marcas.", 38)
    f = _seccion(ay, 5, "1. Lo esencial en tres pasos")
    f = _paso(ay, f, "1", "Después de cada clase, abre la hoja Asistencia y escribe 1 (asistió) o 0 (faltó) a cada estudiante en la columna de esa clase.")
    f = _paso(ay, f, "2", "Guarda. No hay botón de enviar: el sitio de administración se actualiza solo en unos minutos.")
    f = _paso(ay, f, "3", "Mira la columna Estado de cada estudiante. Quien aparece en Atención o En riesgo es a quien conviene escribirle antes de que pierda.")
    f = _seccion(ay, f + 1, "2. Qué significa cada estado")
    for texto, fondo, color in (("Al día: ha faltado poco, lejos del límite.", "E2F0D9", "375623"),
                                ("Atención: ya usó la mitad o más de las faltas permitidas.", "FFF2CC", "7F6000"),
                                ("En riesgo: le queda una falta o ninguna. Una más y pierde el certificado.", "FBE0D6", "C00000"),
                                ("Perdió el mínimo: ya no puede llegar al porcentaje mínimo, aunque asista a todo lo que queda.", "C00000", "FFFFFF"),
                                ("Aprobó: terminó el curso y cumplió el mínimo.", "DDEBF7", "1F3864")):
        _texto(ay, f, 2, 5, texto, 26, negrita=True, color=color, fondo=fondo)
        f += 1
    _texto(ay, f, 2, 5, "Los avisos se calculan sobre las faltas permitidas del curso, no sobre un número fijo. Así sirven igual para un diplomado de 35 clases que para un curso de 8. Los umbrales se cambian en la hoja Resumen.", 40, color="595959")
    f += 1
    f = _seccion(ay, f + 1, "3. Cómo se leen las cuentas")
    for txt in ("Faltas que le quedan: cuántas veces más puede faltar sin perder el mínimo.",
                "Puede llegar hasta: el mejor porcentaje posible si no falta a nada más.",
                "% hasta hoy: su asistencia solo con las clases ya dictadas.",
                "Sin marcar: clases ya dictadas en las que su casilla está vacía. Debe ser 0: si no, falta marcarla."):
        _texto(ay, f, 2, 5, "•  " + txt, 24)
        f += 1
    f = _seccion(ay, f + 1, "4. Cuando una clase cambia")
    for i, txt in enumerate(("Clase reprogramada: en la hoja Cronograma elige Reprogramada en su Situación y escribe la nueva fecha. Deja sus casillas vacías hasta que se dicte.",
                             "Clase cancelada: en la hoja Cronograma elige Cancelada. Deja de contar en el total, así que cambian las faltas permitidas.",
                             "Una clase pasa a Dictada sola en cuanto tiene alguna marca."), 1):
        f = _paso(ay, f, str(i), txt, 36)
    f = _seccion(ay, f + 1, "5. Estudiantes nuevos o que se retiran")
    for txt in ("Para agregar a alguien, escribe su nombre en la primera fila libre debajo de la lista. La tabla se extiende y las cuentas se llenan solas.",
                "Si alguien se retira, no borres su fila: deja sus marcas. Si hay que quitarlo de las cuentas, borra solo su nombre y las demás casillas quedan guardadas en el historial de versiones de SharePoint.",
                "El documento es opcional, pero ayuda a distinguir a dos personas con nombres parecidos."):
        _texto(ay, f, 2, 5, "•  " + txt, 40)
        f += 1
    f = _seccion(ay, f + 1, "6. Importante")
    for txt in ("No cambies los nombres de las columnas Clase 1, Clase 2, etc. ni los de las columnas grises: el sitio los usa para leer el archivo.",
                "Las columnas grises y la fila Estado de la sesión se calculan solas. No las escribas.",
                "El sitio de administración nunca muestra nombres: solo el número de lista (por ejemplo Estudiante 7). El nombre se consulta aquí, en este archivo."):
        _texto(ay, f, 2, 5, "•  " + txt, 40)
        f += 1
    ay.page_setup.orientation, ay.page_setup.fitToWidth, ay.page_setup.fitToHeight = "portrait", 1, 0
    ay.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)


def main(datos, salida):
    d = json.loads(Path(datos).read_text(encoding="utf-8"))
    wb = Workbook()
    n, ult = _hoja_asistencia(wb, d["curso"], d["clases"], d["estudiantes"])
    _hoja_resumen(wb, d["curso"], n, ult)
    ws = wb["Resumen"]
    ws["C4"], ws["C5"] = d.get("minimo", 0.8), d.get("horas", 3)
    _hoja_cronograma(wb, d["clases"])
    _hoja_instrucciones(wb, d["curso"])
    wb.move_sheet("Instrucciones", offset=-3)
    wb.active = 1
    wb.save(salida)


if __name__ == "__main__":
    main(*sys.argv[1:3])
