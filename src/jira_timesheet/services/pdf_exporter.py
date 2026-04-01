"""PDF Export — Stundenzettel als signierbares PDF mit Unicode-Unterstuetzung."""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from fpdf import FPDF

from jira_timesheet.models.timesheet import Timesheet

# Arial TTF Pfade (Windows)
_ARIAL_REGULAR = "C:/Windows/Fonts/arial.ttf"
_ARIAL_BOLD = "C:/Windows/Fonts/arialbd.ttf"
_FONT_NAME = "Arial"

_WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


class PdfExporter:
    """Erzeugt eine PDF-Datei im gleichen Layout wie der Excel-Export."""

    #              KW   Tag  Datum  Ticket  Beschreibung  Aufwand  Tages-h    = 277mm (A4L - 2x10mm)
    COL_WIDTHS = [10,  10,  16,    24,     167,          25,      25]
    HEADERS = ["KW", "Tag", "Datum", "Ticket", "Beschreibung", "Aufwand (h)", "Tages-h"]

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
        """Exportiert den Timesheet als .pdf Datei."""
        if not output_dir:
            output_dir = str(Path.home() / "Desktop")

        from datetime import datetime
        ts_stamp = datetime.now().strftime("%H%M%S")
        filename = (
            f"Stundenzettel_{timesheet.date_from:%Y-%m-%d}"
            f"_{timesheet.date_to:%Y-%m-%d}_{ts_stamp}.pdf"
        )
        filepath = os.path.join(output_dir, filename)

        pdf = FPDF(orientation="L", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_left_margin(10)
        pdf.set_right_margin(10)
        self._register_fonts(pdf)
        pdf.add_page()

        self._add_logo(pdf)
        self._add_header(pdf, timesheet, target_hours)
        self._add_table(pdf, timesheet, missing_days or [])
        self._add_footer(pdf)

        pdf.output(filepath)
        return str(Path(filepath).resolve())

    def _register_fonts(self, pdf: FPDF) -> None:
        """Registriert Arial Unicode-Font fuer Umlaut-Unterstuetzung."""
        if os.path.isfile(_ARIAL_REGULAR):
            pdf.add_font(_FONT_NAME, "", _ARIAL_REGULAR)
        if os.path.isfile(_ARIAL_BOLD):
            pdf.add_font(_FONT_NAME, "B", _ARIAL_BOLD)

    def _font(self, style: str = "", size: int = 10) -> tuple[str, str, int]:
        """Gibt Font-Tupel zurueck, Fallback auf Helvetica."""
        if os.path.isfile(_ARIAL_REGULAR):
            return (_FONT_NAME, style, size)
        return ("Helvetica", style, size)

    def _add_logo(self, pdf: FPDF) -> None:
        """Fuegt das Logo oben links ein."""
        logo = self._find_logo()
        if logo and os.path.isfile(logo):
            try:
                pdf.image(logo, x=10, y=8, w=45)
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

    def _add_header(self, pdf: FPDF, ts: Timesheet, target_hours: float) -> None:
        """Fuegt Titel, Entwickler, Zeitraum hinzu."""
        pdf.set_y(10)
        pdf.set_x(55)
        pdf.set_font(*self._font("B", 16))
        pdf.cell(0, 10, "Stundenzettel", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(4)
        pdf.set_font(*self._font("B", 10))
        pdf.cell(30, 6, "Entwickler:", new_x="END")
        pdf.set_font(*self._font("", 10))
        pdf.cell(0, 6, ts.developer, new_x="LMARGIN", new_y="NEXT")

        pdf.set_font(*self._font("B", 10))
        pdf.cell(30, 6, "Zeitraum:", new_x="END")
        pdf.set_font(*self._font("", 10))
        date_range = f"{ts.date_from:%d.%m.%Y} - {ts.date_to:%d.%m.%Y}"
        pdf.cell(80, 6, date_range, new_x="END")

        pdf.set_font(*self._font("B", 10))
        pdf.cell(25, 6, "Gesamt (h):", new_x="END")
        pdf.cell(20, 6, f"{ts.total_hours:.2f}", new_x="LMARGIN", new_y="NEXT")

        if target_hours > 0:
            pdf.set_font(*self._font("", 9))
            pdf.set_x(145)
            diff = ts.total_hours - target_hours
            diff_sign = "+" if diff >= 0 else ""
            pdf.cell(0, 5, f"Soll: {target_hours:.0f}h  |  Differenz: {diff_sign}{diff:.2f}h", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(4)

    def _add_table(
        self,
        pdf: FPDF,
        ts: Timesheet,
        missing_days: list[tuple[date, str]],
    ) -> None:
        """Fuegt die Daten-Tabelle hinzu."""
        self._add_table_header(pdf)

        day_map = {day.date: day for day in ts.days}
        gap_map = {d: reason for d, reason in missing_days}
        all_dates = sorted(set(day_map.keys()) | set(gap_map.keys()))

        pdf.set_font(*self._font("", 8))
        row_height = 5.5

        for d in all_dates:
            if d in gap_map and d not in day_map:
                if pdf.get_y() + row_height > 190:
                    pdf.add_page()
                    self._add_table_header(pdf)
                    pdf.set_font(*self._font("", 8))

                reason = gap_map[d]
                is_holiday = "\u2014" not in reason

                y_pos = pdf.get_y()
                pdf.set_draw_color(180, 180, 180)
                pdf.line(10, y_pos, 10 + sum(self.COL_WIDTHS), y_pos)

                if is_holiday:
                    pdf.set_text_color(150, 150, 150)
                else:
                    pdf.set_text_color(200, 0, 0)

                pdf.set_draw_color(220, 220, 220)
                pdf.cell(self.COL_WIDTHS[0], row_height, str(d.isocalendar()[1]), border="LR", new_x="END")
                pdf.cell(self.COL_WIDTHS[1], row_height, _WEEKDAYS[d.weekday()], border="LR", new_x="END")
                pdf.cell(self.COL_WIDTHS[2], row_height, f"{d:%d.%m.}", border="LR", new_x="END")
                pdf.cell(self.COL_WIDTHS[3], row_height, "", border="LR", new_x="END")
                pdf.cell(self.COL_WIDTHS[4], row_height, f" {reason}", border="LR", new_x="END")
                pdf.cell(self.COL_WIDTHS[5], row_height, "", border="LR", new_x="END")
                pdf.cell(self.COL_WIDTHS[6], row_height, "0.00", border="LR", align="R", new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(0, 0, 0)
                continue

            if d not in day_map:
                continue

            day = day_map[d]
            needed_height = row_height * len(day.entries) + 2
            if pdf.get_y() + needed_height > 190:
                pdf.add_page()
                self._add_table_header(pdf)
                pdf.set_font(*self._font("", 8))

            for i, entry in enumerate(day.entries):
                is_first = i == 0

                if is_first:
                    y_pos = pdf.get_y()
                    pdf.set_draw_color(0, 0, 0)
                    pdf.line(10, y_pos, 10 + sum(self.COL_WIDTHS), y_pos)

                kw = str(entry.date.isocalendar()[1]) if is_first else ""
                weekday = _WEEKDAYS[entry.date.weekday()] if is_first else ""
                date_str = f"{entry.date:%d.%m.}" if is_first else ""
                day_total = f"{day.total_hours:.2f}" if is_first else ""

                pdf.set_draw_color(220, 220, 220)
                pdf.cell(self.COL_WIDTHS[0], row_height, kw, border="LR", new_x="END")
                pdf.cell(self.COL_WIDTHS[1], row_height, weekday, border="LR", new_x="END")
                pdf.cell(self.COL_WIDTHS[2], row_height, date_str, border="LR", new_x="END")
                pdf.cell(self.COL_WIDTHS[3], row_height, f" {entry.ticket}", border="LR", new_x="END")
                pdf.cell(self.COL_WIDTHS[4], row_height, f" {self._truncate(entry.summary, 100)}", border="LR", new_x="END")
                pdf.cell(self.COL_WIDTHS[5], row_height, f"{entry.hours:.2f} ", border="LR", align="R", new_x="END")

                pdf.set_font(*self._font("B" if day_total else "", 8))
                pdf.cell(self.COL_WIDTHS[6], row_height, f"{day_total} " if day_total else "", border="LR", align="R", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font(*self._font("", 8))

    def _add_table_header(self, pdf: FPDF) -> None:
        """Zeichnet die Header-Zeile der Tabelle."""
        pdf.set_font(*self._font("B", 8))
        pdf.set_fill_color(200, 200, 200)
        pdf.set_draw_color(180, 180, 180)

        for i, header in enumerate(self.HEADERS):
            align = "R" if i >= 5 else "L"
            pdf.cell(self.COL_WIDTHS[i], 6, f" {header}", border=1, fill=True, align=align, new_x="END")
        pdf.ln()

    def _add_footer(self, pdf: FPDF) -> None:
        """Fuegt die Unterschriftszeile hinzu."""
        pdf.ln(10)
        y_pos = pdf.get_y()

        pdf.set_draw_color(0, 0, 0)
        pdf.line(55, y_pos, 250, y_pos)

        pdf.set_font(*self._font("", 9))
        pdf.set_x(55)
        pdf.cell(40, 6, "bestätigt am:", new_x="END")
        pdf.cell(0, 6, "Projektleiter (Blockschrift, Unterschrift)", new_x="LMARGIN", new_y="NEXT")

    @staticmethod
    def _truncate(text: str, max_len: int) -> str:
        """Kuerzt Text mit Ellipsis."""
        if len(text) <= max_len:
            return text
        return text[: max_len - 1] + "\u2026"
