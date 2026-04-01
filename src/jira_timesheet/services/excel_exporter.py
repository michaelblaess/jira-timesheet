"""Excel Export — Stundenzettel mit KW, Wochentag und Luecken-Erkennung."""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XlImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from jira_timesheet.models.timesheet import Timesheet

_WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


class ExcelExporter:
    """Erzeugt eine Excel-Datei im Originalformat des Stundenzettels."""

    def __init__(
        self,
        logo_path: str = "",
        jira_host: str = "",
        hours_per_day: float = 8.0,
    ) -> None:
        self._logo_path = logo_path
        self._jira_host = jira_host.rstrip("/")
        self._hours_per_day = hours_per_day

    def export(
        self,
        timesheet: Timesheet,
        missing_days: list[tuple[date, str]] | None = None,
        target_hours: float = 0.0,
        output_dir: str = "",
    ) -> str:
        """Exportiert den Timesheet als .xlsx Datei."""
        if not output_dir:
            output_dir = str(Path.home() / "Desktop")

        from datetime import datetime
        ts_stamp = datetime.now().strftime("%H%M%S")
        filename = (
            f"Stundenzettel_{timesheet.date_from:%Y-%m-%d}"
            f"_{timesheet.date_to:%Y-%m-%d}_{ts_stamp}.xlsx"
        )
        filepath = os.path.join(output_dir, filename)

        wb = Workbook()
        ws = wb.active
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

    def _setup_columns(self, ws: object) -> None:
        """Setzt die Spaltenbreiten."""
        widths = {
            "A": 5.0, "B": 5.0, "C": 10.4, "D": 12.0,
            "E": 60.0, "F": 10.7, "G": 14.9,
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

    def _add_header(self, ws: object, ts: Timesheet, target_hours: float) -> None:
        """Fuegt Titel, Entwickler, Zeitraum und Gesamtstunden hinzu."""
        font_title = Font(name="Arial", size=16, bold=True)
        font_label = Font(name="Arial", size=10, bold=True)
        font_normal = Font(name="Arial", size=10)

        ws.merge_cells("D3:F3")  # type: ignore[attr-defined]
        cell_title = ws["D3"]  # type: ignore[index]
        cell_title.value = "Stundenzettel"
        cell_title.font = font_title

        ws["A5"].value = "Entwickler"  # type: ignore[index]
        ws["A5"].font = font_label  # type: ignore[index]
        ws["D5"].value = ts.developer  # type: ignore[index]
        ws["D5"].font = font_normal  # type: ignore[index]

        ws["A6"].value = "Zeitraum"  # type: ignore[index]
        ws["A6"].font = font_label  # type: ignore[index]
        ws["D6"].value = f"{ts.date_from:%d.%m.%Y} - {ts.date_to:%d.%m.%Y}"  # type: ignore[index]
        ws["D6"].font = font_normal  # type: ignore[index]

        ws["F6"].value = "Gesamt (h)"  # type: ignore[index]
        ws["F6"].font = font_label  # type: ignore[index]
        ws["G6"].value = ts.total_hours  # type: ignore[index]
        ws["G6"].font = font_label  # type: ignore[index]
        ws["G6"].number_format = "0.00"  # type: ignore[index]

        if target_hours > 0:
            ws["F7"].value = "Soll (h)"  # type: ignore[index]
            ws["F7"].font = font_normal  # type: ignore[index]
            ws["G7"].value = target_hours  # type: ignore[index]
            ws["G7"].font = font_normal  # type: ignore[index]
            ws["G7"].number_format = "0.00"  # type: ignore[index]

    def _add_table_header(self, ws: object) -> None:
        """Fuegt die Tabellenheader-Zeile hinzu (Zeile 9)."""
        headers = ["KW", "Tag", "Datum", "Ticket", "Beschreibung", "Aufwand (h)", "Tagessumme (h)"]
        header_fill = PatternFill(start_color="C8C8C8", end_color="C8C8C8", fill_type="solid")
        header_font = Font(name="Arial", size=10)
        header_align = Alignment(horizontal="left", vertical="center")

        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=9, column=col_idx)  # type: ignore[attr-defined]
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_align

    def _add_data(
        self,
        ws: object,
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
        gap_map = {d: reason for d, reason in missing_days}
        all_dates = sorted(set(day_map.keys()) | set(gap_map.keys()))

        current_row = 10

        for d in all_dates:
            if d in gap_map and d not in day_map:
                ws.row_dimensions[current_row].height = 20.1  # type: ignore[index]
                reason = gap_map[d]
                is_holiday = "\u2014" not in reason
                use_font = font_dim if is_holiday else font_red

                ws.cell(row=current_row, column=1).value = d.isocalendar()[1]  # type: ignore[attr-defined]
                ws.cell(row=current_row, column=1).font = use_font  # type: ignore[attr-defined]
                ws.cell(row=current_row, column=2).value = _WEEKDAYS[d.weekday()]  # type: ignore[attr-defined]
                ws.cell(row=current_row, column=2).font = use_font  # type: ignore[attr-defined]
                ws.cell(row=current_row, column=3).value = d  # type: ignore[attr-defined]
                ws.cell(row=current_row, column=3).number_format = "DD.MM.YYYY"  # type: ignore[attr-defined]
                ws.cell(row=current_row, column=3).font = use_font  # type: ignore[attr-defined]
                ws.cell(row=current_row, column=5).value = reason  # type: ignore[attr-defined]
                ws.cell(row=current_row, column=5).font = use_font  # type: ignore[attr-defined]
                ws.cell(row=current_row, column=7).value = 0  # type: ignore[attr-defined]
                ws.cell(row=current_row, column=7).number_format = "0.00"  # type: ignore[attr-defined]
                ws.cell(row=current_row, column=7).font = use_font  # type: ignore[attr-defined]

                for col in range(1, 8):
                    ws.cell(row=current_row, column=col).alignment = align_left  # type: ignore[attr-defined]
                    ws.cell(row=current_row, column=col).border = border_day_top  # type: ignore[attr-defined]

                current_row += 1
                continue

            if d not in day_map:
                continue

            day = day_map[d]
            for i, entry in enumerate(day.entries):
                is_first = i == 0
                is_last = i == len(day.entries) - 1

                ws.row_dimensions[current_row].height = 20.1  # type: ignore[index]

                ws.cell(row=current_row, column=1).value = entry.date.isocalendar()[1] if is_first else None  # type: ignore[attr-defined]
                ws.cell(row=current_row, column=1).font = font_normal  # type: ignore[attr-defined]
                ws.cell(row=current_row, column=1).alignment = align_left  # type: ignore[attr-defined]

                ws.cell(row=current_row, column=2).value = _WEEKDAYS[entry.date.weekday()] if is_first else None  # type: ignore[attr-defined]
                ws.cell(row=current_row, column=2).font = font_normal  # type: ignore[attr-defined]
                ws.cell(row=current_row, column=2).alignment = align_left  # type: ignore[attr-defined]

                cell_c = ws.cell(row=current_row, column=3)  # type: ignore[attr-defined]
                cell_c.value = entry.date if is_first else None
                cell_c.number_format = "DD.MM.YYYY"
                cell_c.font = font_normal
                cell_c.alignment = align_left

                cell_d = ws.cell(row=current_row, column=4)  # type: ignore[attr-defined]
                cell_d.value = entry.ticket
                cell_d.font = font_normal
                cell_d.alignment = align_left
                if self._jira_host and entry.ticket:
                    cell_d.hyperlink = f"{self._jira_host}/browse/{entry.ticket}"
                    cell_d.font = Font(name="Arial", size=10, color="0563C1", underline="single")

                cell_e = ws.cell(row=current_row, column=5)  # type: ignore[attr-defined]
                cell_e.value = entry.summary
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
                        ws.cell(row=current_row, column=col).border = border_day_top  # type: ignore[attr-defined]

                current_row += 1

        return current_row - 1

    def _add_footer(self, ws: object, last_row: int) -> None:
        """Fuegt die Unterschriftszeile hinzu."""
        footer_row = last_row + 3
        font_normal = Font(name="Arial", size=10)
        border_top = Border(top=Side(style="thin", color="000000"))

        ws.cell(row=footer_row, column=4).value = "bestätigt am:"  # type: ignore[attr-defined]
        ws.cell(row=footer_row, column=4).font = font_normal  # type: ignore[attr-defined]

        ws.cell(row=footer_row, column=5).value = "Projektleiter (Blockschrift, Unterschrift)"  # type: ignore[attr-defined]
        ws.cell(row=footer_row, column=5).font = font_normal  # type: ignore[attr-defined]

        for col in range(4, 7):
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
