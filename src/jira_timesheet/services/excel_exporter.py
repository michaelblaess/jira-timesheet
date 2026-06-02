"""Excel Export - Stundenzettel mit KW, Wochentag und Luecken-Erkennung."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XlImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.worksheet import Worksheet

from jira_timesheet.models.timesheet import Timesheet

_WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


class ExcelExporter:
    """Erzeugt eine Excel-Datei im Originalformat des Stundenzettels."""

    def __init__(
        self,
        logo_path: str = "",
        jira_host: str = "",
        hours_per_day: float = 8.0,
        show_ticket_links: bool = False,
    ) -> None:
        self._logo_path = logo_path
        self._jira_host = jira_host.rstrip("/")
        self._hours_per_day = hours_per_day
        self._show_ticket_links = show_ticket_links

    @staticmethod
    def suggested_filename(timesheet: Timesheet) -> str:
        """Liefert einen vorgeschlagenen Dateinamen fuer den Speichern-Dialog."""
        from datetime import datetime

        now = datetime.now()
        return (
            f"Stundenzettel_{timesheet.date_from:%Y-%m-%d}_"
            f"{timesheet.date_to:%Y-%m-%d}_{now:%Y%m%d_%H%M%S}.xlsx"
        )

    def export(
        self,
        timesheet: Timesheet,
        missing_days: list[tuple[date, str]] | None = None,
        target_hours: float = 0.0,
        output_dir: str = "",
        output_path: str = "",
    ) -> str:
        """Exportiert den Timesheet als .xlsx Datei.

        Ist ``output_path`` gesetzt, wird genau dieser Pfad verwendet (z.B. aus
        dem Speichern-Dialog). Andernfalls wird ein Name in ``output_dir`` bzw.
        auf dem Desktop erzeugt.
        """
        if output_path:
            filepath = output_path
        else:
            if not output_dir:
                output_dir = str(Path.home() / "Desktop")
            filepath = os.path.join(output_dir, self.suggested_filename(timesheet))

        wb = Workbook()
        ws = wb.active
        if ws is None:
            ws = wb.create_sheet()
        ws.title = "Stundenzettel"

        self._setup_columns(ws)
        self._add_logo(ws)
        self._add_header(ws, timesheet, target_hours)
        self._add_table_header(ws)
        last_row = self._add_data(ws, timesheet, missing_days or [])
        self._add_footer(ws, last_row)
        self._setup_print(ws)

        wb.save(filepath)
        return str(Path(filepath).resolve())

    def _setup_columns(self, ws: Worksheet) -> None:
        """Setzt die Spaltenbreiten."""
        widths = {
            "A": 5.0,
            "B": 5.0,
            "C": 10.4,
            "D": 12.0,
            "E": 60.0,
            "F": 10.7,
            "G": 14.9,
        }
        for col, width in widths.items():
            ws.column_dimensions[col].width = width

    def _add_logo(self, ws: Worksheet) -> None:
        """Fuegt das Logo in A1:B2 ein."""
        logo = self._find_logo()
        if logo and os.path.isfile(logo):
            try:
                img = XlImage(logo)
                # Seitenverhaeltnis beibehalten, max 160px breit
                ratio = img.width / img.height if img.height else 1
                img.width = 160
                img.height = int(160 / ratio)
                ws.add_image(img, "A1")
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

    def _add_header(self, ws: Worksheet, ts: Timesheet, target_hours: float) -> None:
        """Fuegt Titel, Entwickler, Zeitraum und Gesamtstunden hinzu."""
        font_title = Font(name="Arial", size=16, bold=True)
        font_label = Font(name="Arial", size=10, bold=True)
        font_normal = Font(name="Arial", size=10)

        ws.merge_cells("D3:F3")
        cell_title = ws["D3"]
        cell_title.value = "Stundenzettel"
        cell_title.font = font_title

        ws["A5"].value = "Entwickler"
        ws["A5"].font = font_label
        ws["D5"].value = ts.developer
        ws["D5"].font = font_normal

        ws["A6"].value = "Zeitraum"
        ws["A6"].font = font_label
        ws["D6"].value = f"{ts.date_from:%d.%m.%Y} - {ts.date_to:%d.%m.%Y}"
        ws["D6"].font = font_normal

        ws["F6"].value = "Gesamt (h)"
        ws["F6"].font = font_label
        ws["G6"].value = ts.total_hours
        ws["G6"].font = font_label
        ws["G6"].number_format = "0.00"

        if target_hours > 0:
            ws["F7"].value = "Soll (h)"
            ws["F7"].font = font_normal
            ws["G7"].value = target_hours
            ws["G7"].font = font_normal
            ws["G7"].number_format = "0.00"

    def _add_table_header(self, ws: Worksheet) -> None:
        """Fuegt die Tabellenheader-Zeile hinzu (Zeile 9)."""
        headers = ["KW", "Tag", "Datum", "Ticket", "Beschreibung", "Aufwand (h)", "Tagessumme (h)"]
        header_fill = PatternFill(start_color="C8C8C8", end_color="C8C8C8", fill_type="solid")
        header_font = Font(name="Arial", size=10)
        header_align = Alignment(horizontal="left", vertical="center")

        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=9, column=col_idx)
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_align

    def _add_data(
        self,
        ws: Worksheet,
        ts: Timesheet,
        missing_days: list[tuple[date, str]],
    ) -> int:
        """Fuegt die Datenzeilen hinzu. Gibt die letzte Zeilennummer zurueck."""
        font_normal = Font(name="Arial", size=10)
        font_dim = Font(name="Arial", size=10, color="999999")
        font_red = Font(name="Arial", size=10, color="CC0000")
        align_left = Alignment(horizontal="left", vertical="center")
        align_right = Alignment(horizontal="right", vertical="center")
        border_day_top = Border(top=Side(style="medium", color="000000"))

        day_map = {day.date: day for day in ts.days}
        gap_map = dict(missing_days)
        all_dates = sorted(set(day_map.keys()) | set(gap_map.keys()))

        current_row = 10

        for d in all_dates:
            if d in gap_map and d not in day_map:
                ws.row_dimensions[current_row].height = 20.1
                reason = gap_map[d]
                is_holiday = "\u2014" not in reason
                use_font = font_dim if is_holiday else font_red

                ws.cell(row=current_row, column=1).value = d.isocalendar()[1]
                ws.cell(row=current_row, column=1).font = use_font
                ws.cell(row=current_row, column=2).value = _WEEKDAYS[d.weekday()]
                ws.cell(row=current_row, column=2).font = use_font
                ws.cell(row=current_row, column=3).value = d
                ws.cell(row=current_row, column=3).number_format = "DD.MM.YYYY"
                ws.cell(row=current_row, column=3).font = use_font
                ws.cell(row=current_row, column=5).value = reason
                ws.cell(row=current_row, column=5).font = use_font
                ws.cell(row=current_row, column=7).value = 0
                ws.cell(row=current_row, column=7).number_format = "0.00"
                ws.cell(row=current_row, column=7).font = use_font

                for col in range(1, 8):
                    ws.cell(row=current_row, column=col).alignment = align_left
                    ws.cell(row=current_row, column=col).border = border_day_top

                current_row += 1
                continue

            if d not in day_map:
                continue

            day = day_map[d]
            for i, entry in enumerate(day.entries):
                is_first = i == 0

                ws.row_dimensions[current_row].height = 20.1

                ws.cell(row=current_row, column=1).value = entry.date.isocalendar()[1] if is_first else None
                ws.cell(row=current_row, column=1).font = font_normal
                ws.cell(row=current_row, column=1).alignment = align_left

                ws.cell(row=current_row, column=2).value = _WEEKDAYS[entry.date.weekday()] if is_first else None
                ws.cell(row=current_row, column=2).font = font_normal
                ws.cell(row=current_row, column=2).alignment = align_left

                cell_c = ws.cell(row=current_row, column=3)
                cell_c.value = entry.date if is_first else None
                cell_c.number_format = "DD.MM.YYYY"
                cell_c.font = font_normal
                cell_c.alignment = align_left

                cell_d = ws.cell(row=current_row, column=4)
                cell_d.value = entry.ticket
                cell_d.font = font_normal
                cell_d.alignment = align_left
                if self._show_ticket_links and self._jira_host and entry.ticket:
                    cell_d.hyperlink = f"{self._jira_host}/browse/{entry.ticket}"
                    cell_d.font = Font(name="Arial", size=10, color="0563C1", underline="single")

                cell_e = ws.cell(row=current_row, column=5)
                cell_e.value = entry.summary
                cell_e.font = font_normal
                cell_e.alignment = align_left

                cell_f = ws.cell(row=current_row, column=6)
                cell_f.value = entry.hours
                cell_f.number_format = "0.00"
                cell_f.font = font_normal
                cell_f.alignment = align_right

                cell_g = ws.cell(row=current_row, column=7)
                if is_first:
                    cell_g.value = day.total_hours
                    cell_g.number_format = "0.00"
                cell_g.font = font_normal
                cell_g.alignment = align_right

                if is_first:
                    for col in range(1, 8):
                        ws.cell(row=current_row, column=col).border = border_day_top

                current_row += 1

        return current_row - 1

    def _add_footer(self, ws: Worksheet, last_row: int) -> None:
        """Fuegt die Unterschriftszeile hinzu."""
        footer_row = last_row + 3
        font_normal = Font(name="Arial", size=10)
        border_top = Border(top=Side(style="thin", color="000000"))

        ws.cell(row=footer_row, column=4).value = "bestätigt am:"
        ws.cell(row=footer_row, column=4).font = font_normal

        ws.cell(row=footer_row, column=5).value = "Projektleiter (Blockschrift, Unterschrift)"
        ws.cell(row=footer_row, column=5).font = font_normal

        for col in range(4, 7):
            ws.cell(row=footer_row, column=col).border = border_top

    def _setup_print(self, ws: Worksheet) -> None:
        """Setzt Druckeinstellungen: A4 Portrait, Fit to Page."""
        try:
            ws.page_setup.paperSize = ws.PAPERSIZE_A4
            ws.page_setup.orientation = "portrait"
            ws.page_setup.fitToWidth = 1
            ws.page_setup.fitToHeight = 0
        except Exception:
            pass
