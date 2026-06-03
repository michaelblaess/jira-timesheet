"""DataTable Widget fuer Stundenzettel-Anzeige."""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from datetime import date
from typing import Any

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import DataTable, Input, Static
from textual_widgets import SearchInputWithHistory

from jira_timesheet.i18n import format_number, t
from jira_timesheet.models.timesheet import Timesheet, TimesheetDay, WorklogEntry

# Sortier-Indikator-Pfeile (Skill-Konvention).
_ARROW_ASC = " ▲"
_ARROW_DESC = " ▼"


# Ein Eintrag in der gemergten Liste ist entweder ein Tag oder eine Luecke
# (Datum + Grund, z.B. Feiertag oder fehlender Worklog).
_DayItem = TimesheetDay | tuple[date, str]


class TimesheetTable(Vertical):
    """Zeigt den Stundenzettel als Tabelle mit Tagesgruppen an.

    Klick auf einen Spaltenkopf sortiert nach Tagesgruppen (Datum, KW oder
    Tages-h). Ticket/Beschreibung/h pro Eintrag sind bewusst nicht sortierbar,
    weil sie die Tagesgruppierung aufbrechen wuerden.
    """

    class EntrySelected(Message):
        """Wird gesendet wenn Enter auf einer Zeile gedrueckt wird."""

        def __init__(self, entry: WorklogEntry | None) -> None:
            super().__init__()
            self.entry = entry

    class FilterHistoryChanged(Message):
        """Wird gesendet wenn sich der Such-Verlauf aendert.

        Der Host (App) ist fuer die Persistenz zustaendig - das Widget kennt
        die Settings nicht.
        """

        def __init__(self, history: list[str]) -> None:
            super().__init__()
            self.history = history

    DEFAULT_CSS = """
    TimesheetTable {
        height: 1fr;
    }

    TimesheetTable #timesheet-search {
        height: auto;
    }

    TimesheetTable #timesheet-filter-count {
        height: auto;
        padding: 0 1;
        color: $text-muted;
        display: none;
    }

    TimesheetTable #timesheet-filter-count.-visible {
        display: block;
    }

    TimesheetTable DataTable {
        height: 1fr;
    }
    """

    def __init__(
        self,
        hours_per_day: float = 8.0,
        jira_host: str = "",
        search_history: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._hours_per_day = hours_per_day
        self._jira_host = jira_host.rstrip("/")
        self._row_entries: dict[str, WorklogEntry] = {}
        # Sort-Status fuer Klick auf Spaltenkoepfe.
        self._timesheet: Timesheet | None = None
        self._missing_days: list[tuple[date, str]] = []
        # Default-Sortierung: Datum aufsteigend (chronologisch).
        self._sort_col: int = 2
        self._sort_desc: bool = False
        self._col_keys: list[Any] = []
        self._base_column_labels: list[str] = []
        # Such-/Filter-Status.
        self._filter_text: str = ""
        self._search_history: list[str] = list(search_history or [])

    def compose(self) -> ComposeResult:
        """Erstellt Suchleiste, Trefferanzeige und DataTable."""
        yield SearchInputWithHistory(
            placeholder=t("table.filter_placeholder"),
            icon="🔍",
            entries=self._search_history,
            input_id="timesheet-filter-bar",
            dropdown_id="timesheet-filter-dropdown",
            id="timesheet-search",
        )
        yield Static("", id="timesheet-filter-count")
        yield DataTable(id="timesheet-data", cursor_type="row", zebra_stripes=False)

    def on_mount(self) -> None:
        """Initialisiert die Tabellenspalten."""
        table = self.query_one("#timesheet-data", DataTable)
        self._base_column_labels = [
            t("table.col.week"),
            t("table.col.day"),
            t("table.col.date"),
            t("table.col.ticket"),
            t("table.col.description"),
            t("table.col.hours"),
            t("table.col.day_hours"),
        ]
        self._col_keys = table.add_columns(*self._base_column_labels)
        self._update_sort_indicator()
        # Tabelle initial fokussieren - sonst zieht das Such-Input den Start-
        # Fokus und einzelne Buchstaben-Shortcuts (g/s/...) landen im Suchfeld
        # statt eine Aktion auszuloesen.
        self.call_after_refresh(table.focus)

    # --- Public API -------------------------------------------------

    def load_timesheet(
        self,
        timesheet: Timesheet,
        missing_days: list[tuple[date, str]] | None = None,
    ) -> None:
        """Laedt einen Timesheet in die Tabelle.

        missing_days: Liste von (Datum, Grund) fuer Luecken/Feiertage.
        """
        self._timesheet = timesheet
        self._missing_days = list(missing_days or [])
        self._refresh()
        # Cursor auf den heutigen Tag setzen, sofern dieser gebuchte Stunden
        # hat - bei vollen Monaten findet man "heute" sonst nur durch Scrollen.
        # Nach dem Refresh deferren, sonst nutzt move_cursor stale Layout-
        # Dimensionen und scrollt auf Position 0 (clear()+rebuild-Stolperstein).
        self.call_after_refresh(self._focus_today)

    def _focus_today(self) -> None:
        """Setzt den Cursor auf die erste Zeile des heutigen Tages.

        Nur wenn der heutige Tag im Stundenzettel gebuchte Stunden hat - sonst
        bleibt die Default-Position (erste Zeile) erhalten.
        """
        if self._timesheet is None:
            return
        today = date.today()
        if not any(day.date == today for day in self._timesheet.days):
            return
        try:
            table = self.query_one("#timesheet-data", DataTable)
            for idx, row in enumerate(table.ordered_rows):
                entry = self._row_entries.get(str(row.key.value))
                if entry is not None and entry.date == today:
                    table.move_cursor(row=idx, animate=False)
                    return
        except Exception:
            return

    def clear_table(self) -> None:
        """Leert die Tabelle."""
        self._timesheet = None
        self._missing_days = []
        self._row_entries.clear()
        table = self.query_one("#timesheet-data", DataTable)
        table.clear()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Enter auf einer Zeile — sendet EntrySelected Message."""
        row_key = str(event.row_key.value) if event.row_key else ""
        entry = self._row_entries.get(row_key)
        self.post_message(self.EntrySelected(entry))

    # --- Suche / Filter ---------------------------------------------

    def focus_search(self) -> None:
        """Fokussiert das Suchfeld (fuer den /-Shortcut der App)."""
        with contextlib.suppress(Exception):
            self.query_one("#timesheet-search", SearchInputWithHistory).focus_input()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Live-Filter waehrend des Tippens im Suchfeld."""
        if event.input.id == "timesheet-filter-bar":
            self._filter_text = event.value
            self._refresh()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Enter im Suchfeld — uebernimmt den Begriff in den Verlauf."""
        if event.input.id == "timesheet-filter-bar":
            self._add_history(event.value)

    def on_search_input_with_history_history_entry_delete_requested(
        self,
        event: SearchInputWithHistory.HistoryEntryDeleteRequested,
    ) -> None:
        """Delete auf einem Verlaufseintrag — entfernt ihn dauerhaft."""
        self._remove_history(event.entry)

    def on_key(self, event: events.Key) -> None:
        """Escape im Suchfeld gibt den Fokus zurueck an die Tabelle."""
        if event.key != "escape":
            return
        with contextlib.suppress(Exception):
            inp = self.query_one("#timesheet-filter-bar", Input)
            if self.app.focused is inp:
                event.stop()
                table = self.query_one("#timesheet-data", DataTable)
                self.call_after_refresh(lambda: self.app.set_focus(table))

    def _add_history(self, term: str) -> None:
        """Fuegt einen Suchbegriff vorne in den Verlauf ein (max. 20, unique)."""
        term = term.strip()
        if not term:
            return
        self._search_history = [term] + [h for h in self._search_history if h != term]
        self._search_history = self._search_history[:20]
        self._sync_history()

    def _remove_history(self, term: str) -> None:
        """Entfernt einen Suchbegriff aus dem Verlauf."""
        self._search_history = [h for h in self._search_history if h != term]
        self._sync_history()

    def _sync_history(self) -> None:
        """Aktualisiert das Dropdown und meldet die Aenderung an den Host."""
        with contextlib.suppress(Exception):
            self.query_one("#timesheet-search", SearchInputWithHistory).set_entries(self._search_history)
        self.post_message(self.FilterHistoryChanged(list(self._search_history)))

    # --- Sortierung -------------------------------------------------

    # Sort-Keys pro Spalten-Index. Nur Spalten mit Eintrag hier sind klickbar.
    # Tag-/Ticket-/Beschreibung-/h-Spalten wuerden die Tagesgruppen sprengen.
    _SORT_KEYS: dict[int, Callable[[_DayItem], Any]] = {
        0: lambda item: TimesheetTable._item_date(item).isocalendar()[:2],
        2: lambda item: TimesheetTable._item_date(item),
        6: lambda item: TimesheetTable._item_hours(item),
    }

    @staticmethod
    def _item_date(item: _DayItem) -> date:
        """Datum eines Eintrags (Tag oder Luecke)."""
        return item[0] if isinstance(item, tuple) else item.date

    @staticmethod
    def _item_hours(item: _DayItem) -> float:
        """Tagessumme; Luecken haben per Definition 0 Stunden."""
        return 0.0 if isinstance(item, tuple) else item.total_hours

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """Klick auf Spaltenkopf — toggelt Richtung bzw. wechselt Sortierspalte.

        Erster Klick auf eine neue Spalte: aufsteigend. Zweiter Klick auf
        dieselbe Spalte: absteigend. Klick auf eine nicht sortierbare Spalte
        (Tag/Ticket/Beschreibung/h) wird ignoriert.
        """
        try:
            col_index = self._col_keys.index(event.column_key)
        except ValueError:
            return
        if col_index not in self._SORT_KEYS:
            return
        if col_index == self._sort_col:
            self._sort_desc = not self._sort_desc
        else:
            self._sort_col = col_index
            self._sort_desc = False
        self._refresh()

    # --- Interne Tabellen-Logik -------------------------------------

    def _refresh(self) -> None:
        """Baut die Tabelle aus dem gespeicherten Timesheet neu auf."""
        table = self.query_one("#timesheet-data", DataTable)
        table.clear()
        self._row_entries.clear()
        if self._timesheet is None:
            self._update_sort_indicator()
            self._update_filter_count([])
            return

        items = self._sorted_day_items()
        row_idx = 0
        for item in items:
            if isinstance(item, tuple):
                row_idx = self._render_gap_row(table, item, row_idx)
            else:
                row_idx = self._render_day(table, item, row_idx)
        self._update_sort_indicator()
        self._update_filter_count(items)

    def _sorted_day_items(self) -> list[_DayItem]:
        """Merged Tage und Luecken, filtert und sortiert nach aktueller Spalte."""
        assert self._timesheet is not None
        merged: list[_DayItem] = self._merge_days_and_gaps(self._timesheet, self._missing_days)
        merged = self._filter_items(merged)
        key_fn = self._SORT_KEYS.get(self._sort_col)
        if key_fn is not None:
            merged.sort(key=key_fn, reverse=self._sort_desc)
        return merged

    def _filter_items(self, items: list[_DayItem]) -> list[_DayItem]:
        """Filtert nach Ticket oder Beschreibung (case-insensitive Substring).

        Bei aktivem Filter werden Luecken/Feiertage ausgeblendet (sie haben
        weder Ticket noch Beschreibung) und Tage auf die passenden Eintraege
        reduziert - die Tagessumme spiegelt dann die angezeigten Eintraege.
        """
        query = self._filter_text.strip().lower()
        if not query:
            return items
        result: list[_DayItem] = []
        for item in items:
            if isinstance(item, tuple):
                continue
            matching = [e for e in item.entries if query in e.ticket.lower() or query in e.summary.lower()]
            if matching:
                result.append(TimesheetDay(date=item.date, entries=matching))
        return result

    def _update_filter_count(self, items: list[_DayItem]) -> None:
        """Zeigt die Trefferzahl bzw. einen 'keine Treffer'-Hinweis an."""
        try:
            count_widget = self.query_one("#timesheet-filter-count", Static)
        except Exception:
            return
        query = self._filter_text.strip()
        if not query or self._timesheet is None:
            count_widget.remove_class("-visible")
            count_widget.update("")
            return
        entries = sum(len(it.entries) for it in items if not isinstance(it, tuple))
        if entries == 0:
            count_widget.update(Text(t("table.filter_none", query=query), style="dim"))
        else:
            count_widget.update(t("table.filter_count", count=entries))
        count_widget.add_class("-visible")

    def _render_gap_row(self, table: DataTable[Any], gap: tuple[date, str], row_idx: int) -> int:
        """Rendert eine Luecken-/Feiertags-Zeile. Gibt den naechsten row_idx zurueck."""
        gap_date, gap_reason = gap
        kw = str(gap_date.isocalendar()[1])
        weekday = t(f"weekday.{gap_date.weekday()}")
        date_str = f"{gap_date:%d.%m.}"
        # Em-Dash-Marker: Luecke (rot) vs. Feiertag (dim) - sprachneutral.
        style = "red" if "—" in gap_reason else "dim"
        table.add_row(
            Text(kw, style="dim"),
            Text(weekday, style="dim"),
            Text(date_str, style="dim"),
            Text("", style="dim"),
            Text(gap_reason, style=style),
            Text("", style="dim"),
            Text(format_number(0.0), style=style),
            key=str(row_idx),
        )
        return row_idx + 1

    def _render_day(self, table: DataTable[Any], day: TimesheetDay, row_idx: int) -> int:
        """Rendert alle Eintraege eines Tages. Gibt den naechsten row_idx zurueck."""
        for i, entry in enumerate(day.entries):
            is_first = i == 0
            is_last = i == len(day.entries) - 1

            kw = str(entry.date.isocalendar()[1]) if is_first else ""
            weekday = t(f"weekday.{entry.date.weekday()}") if is_first else ""
            date_str = f"{entry.date:%d.%m.}" if is_first else ""
            hours_str = format_number(entry.hours)

            if is_last:
                total = day.total_hours
                under_target = total < self._hours_per_day
                total_style = "bold red" if under_target else "bold"
                day_total = Text(format_number(total), style=total_style)
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
        return row_idx

    def _update_sort_indicator(self) -> None:
        """Haengt ▲/▼ an den Spaltenkopf der aktiven Sort-Spalte."""
        try:
            table = self.query_one("#timesheet-data", DataTable)
        except Exception:
            return
        arrow = _ARROW_DESC if self._sort_desc else _ARROW_ASC
        for idx, key in enumerate(self._col_keys):
            base = self._base_column_labels[idx]
            label = f"{base}{arrow}" if idx == self._sort_col else base
            column = table.columns.get(key)
            if column is not None:
                column.label = Text(label)
        table.refresh()

    @staticmethod
    def _merge_days_and_gaps(
        timesheet: Timesheet,
        missing_days: list[tuple[date, str]],
    ) -> list[_DayItem]:
        """Merged Timesheet-Tage und Luecken in chronologischer Reihenfolge."""
        items: list[_DayItem] = []
        day_map = {day.date: day for day in timesheet.days}
        gap_map = dict(missing_days)

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
        return text[: max_len - 1] + "…"
