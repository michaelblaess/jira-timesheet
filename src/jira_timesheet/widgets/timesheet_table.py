"""DataTable Widget fuer Stundenzettel-Anzeige."""
from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Static

from jira_timesheet.models.timesheet import Timesheet, TimesheetDay


class TimesheetTable(Vertical):
    """Zeigt den Stundenzettel als Tabelle mit Tagesgruppen an."""

    DEFAULT_CSS = """
    TimesheetTable {
        height: 1fr;
    }

    TimesheetTable DataTable {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        """Erstellt die DataTable."""
        yield DataTable(id="timesheet-data", cursor_type="row", zebra_stripes=False)

    def on_mount(self) -> None:
        """Initialisiert die Tabellenspalten."""
        table = self.query_one("#timesheet-data", DataTable)
        table.add_columns("Datum", "Ticket", "Beschreibung", "Bearbeiter", "Budget", "h", "Tages-h")

    def load_timesheet(self, timesheet: Timesheet) -> None:
        """Laedt einen Timesheet in die Tabelle."""
        table = self.query_one("#timesheet-data", DataTable)
        table.clear()

        row_idx = 0
        for day in timesheet.days:
            for i, entry in enumerate(day.entries):
                is_last = i == len(day.entries) - 1

                date_str = f"{entry.date:%d.%m.}" if i == 0 else ""
                hours_str = f"{entry.hours:.2f}"

                if is_last:
                    day_total = Text(f"{day.total_hours:.2f}", style="bold")
                else:
                    day_total = Text("")

                table.add_row(
                    date_str,
                    entry.ticket,
                    self._truncate(entry.summary, 40),
                    entry.author,
                    self._truncate(entry.budget, 16),
                    hours_str,
                    day_total,
                    key=str(row_idx),
                )
                row_idx += 1

    def clear_table(self) -> None:
        """Leert die Tabelle."""
        table = self.query_one("#timesheet-data", DataTable)
        table.clear()

    @staticmethod
    def _truncate(text: str, max_len: int) -> str:
        """Kuerzt Text mit Ellipsis."""
        if len(text) <= max_len:
            return text
        return text[: max_len - 1] + "…"
