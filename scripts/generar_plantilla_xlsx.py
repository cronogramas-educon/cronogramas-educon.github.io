#!/usr/bin/env python3
"""Plantilla en blanco del Excel de cada curso, con validaciones: python scripts/generar_plantilla_xlsx.py SALIDA.xlsx"""
import sys
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from construir_datos import COLS, HOJA

ANCHOS = [7, 38, 68, 9, 14, 30, 13, 13, 18, 40]
FILAS = 300  # filas con validación
AYUDA = [
    "PLANTILLA DEL EXCEL DE UN CURSO",
    "",
    "Cómo usarla",
    "1. Haz una copia de este archivo dentro de la carpeta del curso en SharePoint y ponle exactamente el nombre: Cuadro de horas módulos y profesores.xlsx",
    "2. Llena la hoja DISTRIBUCIÓN HORAS: una fila por clase, en orden. Para agregar clases, escribe en la fila de abajo y la tabla crece sola.",
    "3. Guarda. En un par de minutos la página del curso se publica.",
    "",
    "Reglas",
    "No cambies los nombres de los encabezados ni de la hoja. La tabla se llama Table1 y no se debe renombrar.",
    "Si no tienes un dato, déjalo en blanco. La página muestra Por confirmar. No escribas N/A, pendiente ni por definir.",
    "Unidad: el nombre del módulo, repetido en cada clase de ese módulo. Si no hay unidades, déjala en blanco.",
    "Tema: un tema por línea dentro de la celda (Alt + Enter para el salto de línea).",
    "Horas: número entero. Si lo dejas en blanco, la hora de fin se calcula con el horario del curso.",
    "Fecha: una fecha real de Excel. El Día se corrige solo en la página si no coincide.",
    "Link de reunión: la dirección completa de Teams, que empieza por https://",
    "El archivo debe llamarse Cuadro de horas módulos y profesores. No guardes esta plantilla con ese nombre en una carpeta de curso hasta llenarla.",
    "Todo lo de las columnas A a J se publica. No pongas correos, teléfonos ni datos de pago.",
]


def main(salida):
    wb = Workbook()
    ws = wb.active
    ws.title = HOJA
    ws.row_dimensions[1].height = 14.25
    for j, (t, w) in enumerate(zip(COLS, ANCHOS), 1):
        c = ws.cell(2, j, t)
        c.font, c.fill = Font(bold=True, name="Calibri", size=11), PatternFill("solid", fgColor="5B9BD5")
        c.alignment = Alignment(horizontal="left" if j == 10 else "center", vertical="center", wrap_text=True)
        ws.column_dimensions[c.column_letter].width = w
    ws.row_dimensions[2].height = 21.75
    for r in range(3, FILAS + 3):
        for j in range(1, 11):
            ws.cell(r, j).alignment = Alignment(horizontal="left" if j in (3, 6, 10) else "center", vertical="center", wrap_text=True)
        ws.cell(r, 8).number_format = "dd/mm/yyyy"
        ws.cell(r, 5).font = Font(bold=True, name="Calibri", size=11)
    t = Table(displayName="Table1", ref="A2:J3")
    t.tableStyleInfo = TableStyleInfo(name="TableStyleMedium20", showRowStripes=True)
    ws.add_table(t)

    def regla(rango, **kw):
        dv = DataValidation(allow_blank=True, showErrorMessage=True, **kw)
        ws.add_data_validation(dv)
        dv.add(rango)

    ultimo = FILAS + 2
    regla(f"A3:A{ultimo}", type="whole", operator="greaterThan", formula1="0", errorTitle="No.", error="Escribe un número entero mayor que 0 y que no se repita.")
    regla(f"D3:D{ultimo}", type="whole", operator="between", formula1="1", formula2="12", errorTitle="Horas", error="Escribe un número entero de horas, entre 1 y 12.")
    regla(f"G3:G{ultimo}", type="list", formula1='"Lunes,Martes,Miércoles,Jueves,Viernes,Sábado,Domingo"', errorTitle="Día", error="Elige un día de la lista.")
    regla(f"H3:H{ultimo}", type="date", operator="greaterThan", formula1=str((date(2020, 1, 1) - date(1899, 12, 30)).days), errorTitle="Fecha", error="Escribe una fecha real, por ejemplo 15/10/2026.")
    regla(f"J3:J{ultimo}", type="custom", formula1='=LEFT(J3,8)="https://"', errorTitle="Link de reunión", error="El enlace debe empezar por https://")
    ay = wb.create_sheet("Instrucciones")
    ay.column_dimensions["A"].width = 130
    for i, l in enumerate(AYUDA, 1):
        c = ay.cell(i, 1, l)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if l in ("PLANTILLA DEL EXCEL DE UN CURSO", "Cómo usarla", "Reglas"):
            c.font = Font(bold=True, size=14 if i == 1 else 12)
    wb.save(salida)


if __name__ == "__main__":
    main(sys.argv[1])
