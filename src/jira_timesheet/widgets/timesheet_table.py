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
from jira_timesheet.models.export_column import (
    DESCRIPTION_KEY,
    ExportColumn,
    default_columns,
    visible_keys,
)
from jira_timesheet.models.timesheet import Timesheet, TimesheetDay, WorklogEntry
from jira_timesheet.widgets.resizable_data_table import ResizableDataTable

# Sortier-Indikator-Pfeile (Skill-Konvention).
_ARROW_ASC = " ▲"
_ARROW_DESC = " ▼"

# Die Beschreibung fuellt den Rest der Tabellenbreite, solange der Benutzer sie
# nicht selbst gezogen hat.
_MIN_DESCRIPTION_WIDTH = 20

# i18n-Schluessel der Spaltenueberschriften je Spalten-Key. Die Ueberschriften
# der Liste bleiben uebersetzt; die frei vergebene Bezeichnung aus den
# Einstellungen gilt nur fuer die Exporte.
_COLUMN_LABEL_KEYS = {
    "week": "table.col.week",
    "weekday": "table.col.day",
    "date": "table.col.date",
    "ticket": "table.col.ticket",
    DESCRIPTION_KEY: "table.col.description",
    "customer": "table.col.customer",
    "hours": "table.col.hours",
    "day_hours": "table.col.day_hours",
}


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

    class RowRightClicked(Message):
        """Rechtsklick auf eine Zeile - mit dem Kontext fuer das Menue.

        ``entry`` ist None auf einer Luecken-/Feiertagszeile; ``entry_date``
        ist dort trotzdem gesetzt, damit sich fuer den Tag eine Zeit erfassen
        laesst.
        """

        def __init__(
            self,
            screen_x: int,
            screen_y: int,
            entry: WorklogEntry | None,
            entry_date: date | None,
        ) -> None:
            super().__init__()
            self.screen_x = screen_x
            self.screen_y = screen_y
            self.entry = entry
            self.entry_date = entry_date

    class ColumnWidthsChanged(Message):
        """Wird gesendet wenn der Benutzer Spaltenbreiten gezogen hat.

        Wie beim Such-Verlauf ist der Host fuer die Persistenz zustaendig.
        Schluessel ist der Spaltenindex als String.
        """

        def __init__(self, widths: dict[str, int]) -> None:
            super().__init__()
            self.widths = widths

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
        column_widths: dict[str, int] | None = None,
        mark_manual: bool = True,
        manual_color: str = "FF0000",
        columns: list[ExportColumn] | None = None,
        default_customer: str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        # Spaltenbreiten werden ueber den Spalten-Key gemerkt, nicht ueber den
        # Index - der verschiebt sich, sobald eine Spalte ausgeblendet wird.
        self._column_widths: dict[str, int] = dict(column_widths or {})
        self._columns = list(columns) if columns is not None else default_columns()
        self._visible_keys: list[str] = visible_keys(self._columns)
        self._default_customer = default_customer
        self._mark_manual = mark_manual
        self._manual_color = manual_color
        self._hours_per_day = hours_per_day
        self._jira_host = jira_host.rstrip("/")
        self._row_entries: dict[str, WorklogEntry] = {}
        # Datum je Zeile - auch fuer Luecken-Zeilen, die keinen Eintrag haben.
        self._row_dates: dict[str, date] = {}
        # Sort-Status fuer Klick auf Spaltenkoepfe.
        self._timesheet: Timesheet | None = None
        self._missing_days: list[tuple[date, str]] = []
        # Default-Sortierung: Datum aufsteigend (chronologisch).
        self._sort_col: str = "date"
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
        yield ResizableDataTable(id="timesheet-data", cursor_type="row", zebra_stripes=False)

    def on_mount(self) -> None:
        """Initialisiert die Tabellenspalten aus der Spaltenkonfiguration."""
        table = self.query_one("#timesheet-data", ResizableDataTable)
        self._build_columns(table)
        # Tabelle initial fokussieren - sonst zieht das Such-Input den Start-
        # Fokus und einzelne Buchstaben-Shortcuts (g/s/...) landen im Suchfeld
        # statt eine Aktion auszuloesen.
        self.call_after_refresh(table.focus)

    def _build_columns(self, table: ResizableDataTable) -> None:
        """Legt die sichtbaren Spalten an und stellt gemerkte Breiten wieder her."""
        self._base_column_labels = [t(_COLUMN_LABEL_KEYS[key]) for key in self._visible_keys]
        self._col_keys = table.add_columns(*self._base_column_labels)
        self._update_sort_indicator()

        # Die Beschreibung fuellt den Rest der Breite, bis der Benutzer die
        # Spalte selbst zieht. Ist sie ausgeblendet, gibt es keine Flex-Spalte.
        description_index = self._index_of(DESCRIPTION_KEY)
        if description_index >= 0:
            table.set_flex_column(self._col_keys[description_index], min_width=_MIN_DESCRIPTION_WIDTH)
        self._restore_column_widths(table)

    def _index_of(self, column_key: str) -> int:
        """Position einer Spalte in der sichtbaren Liste, -1 wenn ausgeblendet."""
        try:
            return self._visible_keys.index(column_key)
        except ValueError:
            return -1

    def _restore_column_widths(self, table: ResizableDataTable) -> None:
        """Stellt die zuletzt gezogenen Spaltenbreiten wieder her."""
        for column_key, width in self._column_widths.items():
            index = self._index_of(column_key)
            if index >= 0:
                table.set_column_width(self._col_keys[index], width)

    def on_resizable_data_table_right_clicked(self, event: ResizableDataTable.RightClicked) -> None:
        """Reicht den Rechtsklick mit Zeilen-Kontext an den Host weiter."""
        event.stop()
        row_key = ""
        try:
            table = self.query_one("#timesheet-data", ResizableDataTable)
            if 0 <= event.row_index < len(table.ordered_rows):
                row_key = str(table.ordered_rows[event.row_index].key.value)
        except Exception:
            return
        self.post_message(
            self.RowRightClicked(
                event.screen_x,
                event.screen_y,
                self._row_entries.get(row_key),
                self._row_dates.get(row_key),
            )
        )

    def on_resizable_data_table_column_resized(self, event: ResizableDataTable.ColumnResized) -> None:
        """Merkt sich eine gezogene Breite und meldet sie an den Host."""
        event.stop()
        try:
            index = self._col_keys.index(event.column_key)
        except ValueError:
            return
        column_key = self._visible_keys[index]
        if event.width is None:
            self._column_widths.pop(column_key, None)
        else:
            self._column_widths[column_key] = event.width
        self.post_message(self.ColumnWidthsChanged(dict(self._column_widths)))

    def set_columns(self, columns: list[ExportColumn]) -> None:
        """Uebernimmt eine geaenderte Spaltenkonfiguration und baut neu auf."""
        new_visible = visible_keys(columns)
        self._columns = list(columns)
        if new_visible == self._visible_keys:
            return
        self._visible_keys = new_visible
        try:
            table = self.query_one("#timesheet-data", ResizableDataTable)
        except Exception:
            return
        # clear(columns=True) wirft auch die Spalten weg - danach neu anlegen.
        table.clear(columns=True)
        self._build_columns(table)
        if self._timesheet is not None:
            self._refresh()

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

    def set_manual_marking(self, enabled: bool, color: str) -> None:
        """Aendert die Markierung manueller Eintraege und zeichnet neu."""
        if enabled == self._mark_manual and color == self._manual_color:
            return
        self._mark_manual = enabled
        self._manual_color = color
        if self._timesheet is not None:
            self._refresh()

    def set_default_customer(self, customer: str) -> None:
        """Uebernimmt den Standard-Kunden fuer Jira-Eintraege ohne eigenen Wert."""
        if customer == self._default_customer:
            return
        self._default_customer = customer
        if self._timesheet is not None:
            self._refresh()

    def current_entry(self) -> WorklogEntry | None:
        """Der Eintrag unter dem Cursor, None bei Luecken-Zeile oder leerer Tabelle."""
        row_key = self._cursor_row_key()
        return self._row_entries.get(row_key) if row_key else None

    def current_date(self) -> date | None:
        """Das Datum der Zeile unter dem Cursor, auch bei Luecken-Zeilen."""
        row_key = self._cursor_row_key()
        return self._row_dates.get(row_key) if row_key else None

    def _cursor_row_key(self) -> str:
        """Schluessel der Zeile unter dem Cursor, leer wenn es keine gibt."""
        try:
            table = self.query_one("#timesheet-data", ResizableDataTable)
            row_idx = table.cursor_row
            if row_idx is None or row_idx < 0 or row_idx >= len(table.ordered_rows):
                return ""
            return str(table.ordered_rows[row_idx].key.value)
        except Exception:
            return ""

    def clear_table(self) -> None:
        """Leert die Tabelle."""
        self._timesheet = None
        self._missing_days = []
        self._row_entries.clear()
        self._row_dates.clear()
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

    # Sort-Keys pro Spalten-Key. Nur Spalten mit Eintrag hier sind klickbar -
    # Tag-/Ticket-/Beschreibung-/h-Spalten wuerden die Tagesgruppen sprengen.
    _SORT_KEYS: dict[str, Callable[[_DayItem], Any]] = {
        "week": lambda item: TimesheetTable._item_date(item).isocalendar()[:2],
        "date": lambda item: TimesheetTable._item_date(item),
        "day_hours": lambda item: TimesheetTable._item_hours(item),
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
            column_key = self._visible_keys[self._col_keys.index(event.column_key)]
        except (ValueError, IndexError):
            return
        if column_key not in self._SORT_KEYS:
            return
        if column_key == self._sort_col:
            self._sort_desc = not self._sort_desc
        else:
            self._sort_col = column_key
            self._sort_desc = False
        self._refresh()

    # --- Interne Tabellen-Logik -------------------------------------

    def _refresh(self) -> None:
        """Baut die Tabelle aus dem gespeicherten Timesheet neu auf."""
        table = self.query_one("#timesheet-data", DataTable)
        table.clear()
        self._row_entries.clear()
        self._row_dates.clear()
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
        cells = {
            "week": Text(kw, style="dim"),
            "weekday": Text(weekday, style="dim"),
            "date": Text(date_str, style="dim"),
            DESCRIPTION_KEY: Text(gap_reason, style=style),
            "day_hours": Text(format_number(0.0), style=style),
        }
        table.add_row(
            *(cells.get(key, Text("", style="dim")) for key in self._visible_keys),
            key=str(row_idx),
        )
        self._row_dates[str(row_idx)] = gap_date
        return row_idx + 1

    def _render_day(self, table: DataTable[Any], day: TimesheetDay, row_idx: int) -> int:
        """Rendert alle Eintraege eines Tages. Gibt den naechsten row_idx zurueck."""
        for i, entry in enumerate(day.entries):
            is_first = i == 0
            is_last = i == len(day.entries) - 1

            kw = str(entry.date.isocalendar()[1]) if is_first else ""
            weekday = t(f"weekday.{entry.date.weekday()}") if is_first else ""
            date_str = f"{entry.date:%d.%m.}" if is_first else ""
            # Manuelle Eintraege werden in der eingestellten Farbe fett gesetzt.
            manual_style = self._manual_style(entry.manual)
            hours_str = Text(format_number(entry.hours), style=manual_style)

            if is_last:
                total = day.total_hours
                under_target = total < self._hours_per_day
                total_style = "bold red" if under_target else "bold"
                day_total = Text(format_number(total), style=total_style)
            else:
                day_total = Text("")

            if self._jira_host and entry.ticket:
                link_style = f"link {self._jira_host}/browse/{entry.ticket}"
                ticket_text = Text(entry.ticket, style=f"{manual_style} {link_style}".strip())
            else:
                ticket_text = Text(entry.ticket, style=manual_style)

            row_key = str(row_idx)
            self._row_entries[row_key] = entry
            self._row_dates[row_key] = entry.date
            cells: dict[str, Any] = {
                "week": kw,
                "weekday": weekday,
                "date": date_str,
                "ticket": ticket_text,
                DESCRIPTION_KEY: self._description_text(entry.summary, entry.manual),
                "customer": Text(entry.customer or self._default_customer, style=manual_style),
                "hours": hours_str,
                "day_hours": day_total,
            }
            table.add_row(
                *(cells.get(key, "") for key in self._visible_keys),
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
            is_sorted = self._visible_keys[idx] == self._sort_col
            label = f"{base}{arrow}" if is_sorted else base
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

    def _manual_style(self, manual: bool) -> str:
        """Rich-Style fuer manuelle Eintraege, sonst leer."""
        if not manual or not self._mark_manual:
            return ""
        return f"bold #{self._manual_color}"

    def _description_text(self, summary: str, manual: bool = False) -> Text:
        """Beschreibungs-Zelle: nicht umbrechen, bei Bedarf mit … abschneiden.

        Rich kuerzt selbst auf die aktuelle Spaltenbreite - so zeigt eine breiter
        gezogene Spalte sofort mehr Text, ohne dass die Zeilen neu gebaut werden.
        """
        return Text(summary, no_wrap=True, overflow="ellipsis", end="", style=self._manual_style(manual))
