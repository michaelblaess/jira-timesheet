"""DataTable Widget fuer Stundenzettel-Anzeige."""
from __future__ import annotations

from datetime import date

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import DataTable

from jira_timesheet.models.timesheet import Timesheet, WorklogEntry

_WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


class TimesheetTable(Vertical):
    """Zeigt den Stundenzettel als Tabelle mit Tagesgruppen an."""

    class EntrySelected(Message):
        """Wird gesendet wenn Enter auf einer Zeile gedrueckt wird."""

        def __init__(self, entry: WorklogEntry | None) -> None:
            super().__init__()
            self.entry = entry

    DEFAULT_CSS = """
    TimesheetTable {
        height: 1fr;
    }

    TimesheetTable DataTable {
        height: 1fr;
    }
    """

    def __init__(self, hours_per_day: float = 8.0, jira_host: str = "", **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._hours_per_day = hours_per_day
        self._jira_host = jira_host.rstrip("/")
        self._row_entries: dict[str, WorklogEntry] = {}

    def compose(self) -> ComposeResult:
        """Erstellt die DataTable."""
        yield DataTable(id="timesheet-data", cursor_type="row", zebra_stripes=False)

    def on_mount(self) -> None:
        """Initialisiert die Tabellenspalten."""
        table = self.query_one("#timesheet-data", DataTable)
        table.add_columns("KW", "Tag", "Datum", "Ticket", "Beschreibung", "h", "Tages-h")

    def load_timesheet(
        self,
        timesheet: Timesheet,
        missing_days: list[tuple[date, str]] | None = None,
    ) -> None:
        """Laedt einen Timesheet in die Tabelle.

        missing_days: Liste von (Datum, Grund) fuer Luecken/Feiertage.
        """
        table = self.query_one("#timesheet-data", DataTable)
        table.clear()
        self._row_entries.clear()

        all_day_items = self._merge_days_and_gaps(timesheet, missing_days or [])
        row_idx = 0

        for item in all_day_items:
            if isinstance(item, tuple):
                gap_date, gap_reason = item
                kw = str(gap_date.isocalendar()[1])
                weekday = _WEEKDAYS[gap_date.weekday()]
                date_str = f"{gap_date:%d.%m.}"

                style = "dim" if "Feiertag" in gap_reason or "kein Eintrag" not in gap_reason else "red"
                table.add_row(
                    Text(kw, style="dim"),
                    Text(weekday, style="dim"),
                    Text(date_str, style="dim"),
                    Text("", style="dim"),
                    Text(gap_reason, style=style),
                    Text("", style="dim"),
                    Text("0.00", style=style),
                    key=str(row_idx),
                )
                row_idx += 1
            else:
                day = item
                for i, entry in enumerate(day.entries):
                    is_first = i == 0
                    is_last = i == len(day.entries) - 1

                    kw = str(entry.date.isocalendar()[1]) if is_first else ""
                    weekday = _WEEKDAYS[entry.date.weekday()] if is_first else ""
                    date_str = f"{entry.date:%d.%m.}" if is_first else ""
                    hours_str = f"{entry.hours:.2f}"

                    if is_last:
                        total = day.total_hours
                        under_target = total < self._hours_per_day
                        total_style = "bold red" if under_target else "bold"
                        day_total = Text(f"{total:.2f}", style=total_style)
                    else:
                        day_total = Text("")

                    if self._jira_host and entry.ticket:
                        ticket_text = Text(entry.ticket, style=f"link {self._jira_host}/browse/{entry.ticket}")
                    else:
                        ticket_text = Text(entry.ticket)

                    row_key = str(row_idx)
                    self._row_entries[row_key] = entry
                    table.add_row(
                        kw,
                        weekday,
                        date_str,
                        ticket_text,
                        self._truncate(entry.summary, 80),
                        hours_str,
                        day_total,
                        key=row_key,
                    )
                    row_idx += 1

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Enter auf einer Zeile — sendet EntrySelected Message."""
        row_key = str(event.row_key.value) if event.row_key else ""
        entry = self._row_entries.get(row_key)
        self.post_message(self.EntrySelected(entry))

    def clear_table(self) -> None:
        """Leert die Tabelle."""
        table = self.query_one("#timesheet-data", DataTable)
        table.clear()

    @staticmethod
    def _merge_days_and_gaps(
        timesheet: Timesheet,
        missing_days: list[tuple[date, str]],
    ) -> list:
        """Merged Timesheet-Tage und Luecken in chronologischer Reihenfolge."""
        items: list = []
        day_map = {day.date: day for day in timesheet.days}
        gap_map = {d: reason for d, reason in missing_days}

        all_dates = sorted(set(day_map.keys()) | set(gap_map.keys()))

        for d in all_dates:
            if d in day_map:
                items.append(day_map[d])
            elif d in gap_map:
                items.append((d, gap_map[d]))

        return items

    @staticmethod
    def _truncate(text: str, max_len: int) -> str:
        """Kuerzt Text mit Ellipsis."""
        if len(text) <= max_len:
            return text
        return text[: max_len - 1] + "\u2026"
