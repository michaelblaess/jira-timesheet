"""Excel Export — 1:1 Nachbau des bestehenden Stundenzettel-Formats."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XlImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from jira_timesheet.models.timesheet import Timesheet


class ExcelExporter:
    """Erzeugt eine Excel-Datei im Originalformat des Stundenzettels."""

    def __init__(self, logo_path: str = "") -> None:
        self._logo_path = logo_path

    def export(self, timesheet: Timesheet, output_dir: str = "") -> str:
        """Exportiert den Timesheet als .xlsx Datei.

        Gibt den absoluten Pfad der erzeugten Datei zurueck.
        """
        if not output_dir:
            output_dir = str(Path.home() / "Desktop")

        filename = (
            f"Stundenzettel_{timesheet.date_from:%Y-%m-%d}"
            f"_{timesheet.date_to:%Y-%m-%d}.xlsx"
        )
        filepath = os.path.join(output_dir, filename)

        wb = Workbook()
        ws = wb.active
        ws.title = "Stundenzettel"
        ws.sheet_properties.pageSetUpPr = ws.sheet_properties.pageSetUpPr or None

        self._setup_columns(ws)
        self._add_logo(ws)
        self._add_header(ws, timesheet)
        self._add_table_header(ws)
        last_row = self._add_data(ws, timesheet)
        self._add_footer(ws, last_row)
        self._setup_print(ws)

        wb.save(filepath)
        return str(Path(filepath).resolve())

    def _setup_columns(self, ws: object) -> None:
        """Setzt die Spaltenbreiten wie im Original."""
        widths = {
            "A": 10.4, "B": 10.4, "C": 67.5, "D": 14.3,
            "E": 14.7, "F": 10.7, "G": 14.9,
        }
        for col, width in widths.items():
            ws.column_dimensions[col].width = width  # type: ignore[index]

    def _add_logo(self, ws: object) -> None:
        """Fuegt das Logo in A1:B2 ein."""
        logo = self._find_logo()
        if logo and os.path.isfile(logo):
            try:
                img = XlImage(logo)
                img.width = 120
                img.height = 65
                ws.add_image(img, "A1")  # type: ignore[arg-type]
            except Exception:
                pass

    def _find_logo(self) -> str:
        """Sucht das Logo: erst Settings-Pfad, dann assets/logo.png."""
        if self._logo_path and os.path.isfile(self._logo_path):
            return self._logo_path

        here = Path(__file__).resolve().parent.parent.parent.parent
        default_logo = here / "assets" / "logo.png"
        if default_logo.is_file():
            return str(default_logo)

        return ""

    def _add_header(self, ws: object, ts: Timesheet) -> None:
        """Fuegt Titel, Entwickler, Zeitraum und Gesamtstunden hinzu."""
        font_title = Font(name="Arial", size=16, bold=True)
        font_label = Font(name="Arial", size=10, bold=True)
        font_normal = Font(name="Arial", size=10)

        ws.merge_cells("C3:E3")  # type: ignore[attr-defined]
        cell_title = ws["C3"]  # type: ignore[index]
        cell_title.value = "Stundenzettel"
        cell_title.font = font_title

        ws["A5"].value = "Entwickler"  # type: ignore[index]
        ws["A5"].font = font_label  # type: ignore[index]
        ws["C5"].value = ts.developer  # type: ignore[index]
        ws["C5"].font = font_normal  # type: ignore[index]

        ws["A6"].value = "Zeitraum"  # type: ignore[index]
        ws["A6"].font = font_label  # type: ignore[index]
        ws["C6"].value = f"{ts.date_from:%d.%m.%Y} - {ts.date_to:%d.%m.%Y}"  # type: ignore[index]
        ws["C6"].font = font_normal  # type: ignore[index]

        ws["F6"].value = "Gesamt (h)"  # type: ignore[index]
        ws["F6"].font = Font(name="Arial", size=10, bold=True)  # type: ignore[index]
        ws["G6"].value = ts.total_hours  # type: ignore[index]
        ws["G6"].font = Font(name="Arial", size=10, bold=True)  # type: ignore[index]
        ws["G6"].number_format = "0.00"  # type: ignore[index]

    def _add_table_header(self, ws: object) -> None:
        """Fuegt die Tabellenheader-Zeile hinzu (Zeile 8)."""
        headers = ["Datum", "Ticket", "Beschreibung", "Bearbeiter", "Budget", "Aufwand (h)", "Tagessumme (h)"]
        header_fill = PatternFill(start_color="C8C8C8", end_color="C8C8C8", fill_type="solid")
        header_font = Font(name="Arial", size=10)
        header_align = Alignment(horizontal="left", vertical="center")

        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=8, column=col_idx)  # type: ignore[attr-defined]
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_align

    def _add_data(self, ws: object, ts: Timesheet) -> int:
        """Fuegt die Datenzeilen hinzu. Gibt die letzte Zeilennummer zurueck."""
        font_normal = Font(name="Arial", size=10)
        align_left = Alignment(horizontal="left", vertical="center")
        align_right = Alignment(horizontal="right", vertical="center")
        border_day_top = Border(top=Side(style="medium", color="000000"))

        current_row = 9

        for day in ts.days:
            for i, entry in enumerate(day.entries):
                is_first = i == 0
                is_last = i == len(day.entries) - 1

                ws.row_dimensions[current_row].height = 20.1  # type: ignore[index]

                cell_a = ws.cell(row=current_row, column=1)  # type: ignore[attr-defined]
                cell_a.value = entry.date
                cell_a.number_format = "DD.MM.YYYY"
                cell_a.font = font_normal
                cell_a.alignment = align_left

                cell_b = ws.cell(row=current_row, column=2)  # type: ignore[attr-defined]
                cell_b.value = entry.ticket
                cell_b.font = font_normal
                cell_b.alignment = align_left

                cell_c = ws.cell(row=current_row, column=3)  # type: ignore[attr-defined]
                cell_c.value = entry.summary
                cell_c.font = font_normal
                cell_c.alignment = align_left

                cell_d = ws.cell(row=current_row, column=4)  # type: ignore[attr-defined]
                cell_d.value = entry.author
                cell_d.font = font_normal
                cell_d.alignment = align_left

                cell_e = ws.cell(row=current_row, column=5)  # type: ignore[attr-defined]
                cell_e.value = entry.budget
                cell_e.font = font_normal
                cell_e.alignment = align_left

                cell_f = ws.cell(row=current_row, column=6)  # type: ignore[attr-defined]
                cell_f.value = entry.hours
                cell_f.number_format = "0.00"
                cell_f.font = font_normal
                cell_f.alignment = align_right

                cell_g = ws.cell(row=current_row, column=7)  # type: ignore[attr-defined]
                if is_first:
                    cell_g.value = day.total_hours
                    cell_g.number_format = "0.00"
                cell_g.font = font_normal
                cell_g.alignment = align_right

                if is_first:
                    for col in range(1, 8):
                        cell = ws.cell(row=current_row, column=col)  # type: ignore[attr-defined]
                        cell.border = border_day_top

                current_row += 1

        return current_row - 1

    def _add_footer(self, ws: object, last_row: int) -> None:
        """Fuegt die Unterschriftszeile hinzu."""
        footer_row = last_row + 3
        font_normal = Font(name="Arial", size=10)
        border_top = Border(top=Side(style="thin", color="000000"))

        ws.cell(row=footer_row, column=3).value = "bestaetigt am:"  # type: ignore[attr-defined]
        ws.cell(row=footer_row, column=3).font = font_normal  # type: ignore[attr-defined]

        ws.cell(row=footer_row, column=4).value = "Projektleiter (Blockschrift, Unterschrift)"  # type: ignore[attr-defined]
        ws.cell(row=footer_row, column=4).font = font_normal  # type: ignore[attr-defined]

        for col in range(3, 6):
            ws.cell(row=footer_row, column=col).border = border_top  # type: ignore[attr-defined]

    def _setup_print(self, ws: object) -> None:
        """Setzt Druckeinstellungen: A4 Portrait, Fit to Page."""
        try:
            ws.page_setup.paperSize = ws.PAPERSIZE_A4  # type: ignore[attr-defined]
            ws.page_setup.orientation = "portrait"  # type: ignore[attr-defined]
            ws.page_setup.fitToWidth = 1  # type: ignore[attr-defined]
            ws.page_setup.fitToHeight = 0  # type: ignore[attr-defined]
        except Exception:
            pass
