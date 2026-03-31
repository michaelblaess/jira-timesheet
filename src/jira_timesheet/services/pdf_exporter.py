"""PDF Export — Stundenzettel als signierbares PDF."""
from __future__ import annotations

import os
from pathlib import Path

from fpdf import FPDF

from jira_timesheet.models.timesheet import Timesheet


class PdfExporter:
    """Erzeugt eine PDF-Datei im gleichen Layout wie der Excel-Export."""

    COL_WIDTHS = [22, 22, 72, 25, 28, 18, 22]
    HEADERS = ["Datum", "Ticket", "Beschreibung", "Bearbeiter", "Budget", "h", "Tages-h"]

    def __init__(self, logo_path: str = "") -> None:
        self._logo_path = logo_path

    def export(self, timesheet: Timesheet, output_dir: str = "") -> str:
        """Exportiert den Timesheet als .pdf Datei.

        Gibt den absoluten Pfad der erzeugten Datei zurueck.
        """
        if not output_dir:
            output_dir = str(Path.home() / "Desktop")

        filename = (
            f"Stundenzettel_{timesheet.date_from:%Y-%m-%d}"
            f"_{timesheet.date_to:%Y-%m-%d}.pdf"
        )
        filepath = os.path.join(output_dir, filename)

        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        self._add_logo(pdf)
        self._add_header(pdf, timesheet)
        self._add_table(pdf, timesheet)
        self._add_footer(pdf)

        pdf.output(filepath)
        return str(Path(filepath).resolve())

    def _add_logo(self, pdf: FPDF) -> None:
        """Fuegt das Logo oben links ein."""
        logo = self._find_logo()
        if logo and os.path.isfile(logo):
            try:
                pdf.image(logo, x=10, y=8, w=30)
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

    def _add_header(self, pdf: FPDF, ts: Timesheet) -> None:
        """Fuegt Titel, Entwickler, Zeitraum hinzu."""
        pdf.set_y(10)
        pdf.set_x(55)
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Stundenzettel", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(30, 6, "Entwickler:", new_x="END")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, ts.developer, new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(30, 6, "Zeitraum:", new_x="END")
        pdf.set_font("Helvetica", "", 10)
        date_range = f"{ts.date_from:%d.%m.%Y} - {ts.date_to:%d.%m.%Y}"
        pdf.cell(80, 6, date_range, new_x="END")

        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(25, 6, "Gesamt (h):", new_x="END")
        pdf.cell(20, 6, f"{ts.total_hours:.2f}", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(4)

    def _add_table(self, pdf: FPDF, ts: Timesheet) -> None:
        """Fuegt die Daten-Tabelle hinzu."""
        self._add_table_header(pdf)

        pdf.set_font("Helvetica", "", 8)
        row_height = 5.5

        for day in ts.days:
            needed_height = row_height * len(day.entries) + 2
            if pdf.get_y() + needed_height > 270:
                pdf.add_page()
                self._add_table_header(pdf)
                pdf.set_font("Helvetica", "", 8)

            for i, entry in enumerate(day.entries):
                is_first = i == 0
                is_last = i == len(day.entries) - 1

                if is_first:
                    x_start = pdf.get_x()
                    y_pos = pdf.get_y()
                    pdf.set_draw_color(0, 0, 0)
                    pdf.line(x_start, y_pos, x_start + sum(self.COL_WIDTHS), y_pos)

                date_str = f"{entry.date:%d.%m.}" if is_first else ""
                day_total = f"{day.total_hours:.2f}" if is_first else ""

                pdf.cell(self.COL_WIDTHS[0], row_height, date_str, new_x="END")
                pdf.cell(self.COL_WIDTHS[1], row_height, entry.ticket, new_x="END")
                pdf.cell(self.COL_WIDTHS[2], row_height, self._truncate(entry.summary, 55), new_x="END")
                pdf.cell(self.COL_WIDTHS[3], row_height, self._truncate(entry.author, 16), new_x="END")
                pdf.cell(self.COL_WIDTHS[4], row_height, self._truncate(entry.budget, 18), new_x="END")
                pdf.cell(self.COL_WIDTHS[5], row_height, f"{entry.hours:.2f}", align="R", new_x="END")

                pdf.set_font("Helvetica", "B" if day_total else "", 8)
                pdf.cell(self.COL_WIDTHS[6], row_height, day_total, align="R", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 8)

    def _add_table_header(self, pdf: FPDF) -> None:
        """Zeichnet die Header-Zeile der Tabelle."""
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(200, 200, 200)

        for i, header in enumerate(self.HEADERS):
            align = "R" if i >= 5 else "L"
            pdf.cell(self.COL_WIDTHS[i], 6, header, fill=True, align=align, new_x="END")
        pdf.ln()

    def _add_footer(self, pdf: FPDF) -> None:
        """Fuegt die Unterschriftszeile hinzu."""
        pdf.ln(10)
        y_pos = pdf.get_y()

        pdf.set_draw_color(0, 0, 0)
        pdf.line(55, y_pos, 190, y_pos)

        pdf.set_font("Helvetica", "", 9)
        pdf.set_x(55)
        pdf.cell(40, 6, "bestaetigt am:", new_x="END")
        pdf.cell(0, 6, "Projektleiter (Blockschrift, Unterschrift)", new_x="LMARGIN", new_y="NEXT")

    @staticmethod
    def _truncate(text: str, max_len: int) -> str:
        """Kuerzt Text mit Ellipsis (ASCII-kompatibel fuer Helvetica)."""
        if len(text) <= max_len:
            return text
        return text[: max_len - 2] + ".."
