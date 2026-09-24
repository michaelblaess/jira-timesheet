"""Reiter "Neue Tickets": was die Team-Mitglieder zuletzt angelegt haben.

Das Widget haelt die geladene Liste und filtert sie lokal nach Person und
Zeitraum - ein Wechsel fragt Jira nicht erneut. Abruf und Aufbereitung liegen
in services.new_tickets und im Loader.

Auswahl und Rechtsklick meldet es ueber die Nachrichten der Ticketlisten
(TicketBoardTable.TicketSelected / TicketRightClicked). So oeffnet die App
Ticket und Kontextmenue auf demselben Weg wie ueberall sonst.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable, Sequence
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, DataTable, Select, Static

from jira_timesheet.i18n import t
from jira_timesheet.services.new_tickets import (
    ALL_MEMBERS,
    DEFAULT_WINDOW,
    WINDOWS,
    created_label,
    visible_tickets,
    window_start,
)
from jira_timesheet.services.ticket_board import Ticket
from jira_timesheet.widgets.resizable_data_table import ResizableDataTable
from jira_timesheet.widgets.ticket_board_table import TicketBoardTable

# Wert des Eintrags "alle Mitglieder" im Auswahlfeld. Select verlangt einen
# nicht leeren Wert, im Kern heisst "alle" dagegen: kein Name.
_ALL = "__alle__"

_COLUMNS: tuple[str, ...] = (
    "new.col.key",
    "new.col.summary",
    "new.col.type",
    "new.col.priority",
    "new.col.status",
    "new.col.reporter",
    "new.col.created",
    "new.col.assignee",
)
_MIN_SUMMARY_WIDTH = 30


def _weekday(day: dt.date) -> bool:
    """Mo-Fr - bis die App den Feiertagskalender hereinreicht."""
    return day.weekday() < 5


class NewTicketsPanel(Vertical):
    """Liste der neuen Tickets mit Personen- und Zeitraumfilter."""

    class WindowChanged(Message):
        """Der Zeitraum wurde gewechselt - die App merkt ihn sich."""

        def __init__(self, kind: str) -> None:
            super().__init__()
            self.kind = kind

    class CountChanged(Message):
        """Die angezeigte Anzahl hat sich geaendert (Reitertitel). -1 = nichts geladen."""

        def __init__(self, count: int) -> None:
            super().__init__()
            self.count = count

    DEFAULT_CSS = """
    NewTicketsPanel .new-filter-bar {
        height: auto;
        padding: 0 1;
    }

    NewTicketsPanel .new-filter-label {
        width: auto;
        padding: 1 1 0 0;
    }

    NewTicketsPanel Select {
        width: 32;
    }

    NewTicketsPanel .new-window {
        width: auto;
        min-width: 6;
        margin: 0 0 0 1;
    }

    NewTicketsPanel .new-window.-active {
        background: $accent;
        color: $text;
        text-style: bold;
    }

    NewTicketsPanel .new-range {
        width: auto;
        padding: 1 0 0 2;
        text-style: bold;
    }

    NewTicketsPanel .new-count {
        width: 1fr;
        padding: 1 0 0 2;
        color: $text-muted;
    }

    NewTicketsPanel .new-hint {
        height: auto;
        padding: 0 1;
        color: $text-muted;
    }

    NewTicketsPanel DataTable {
        height: 1fr;
    }
    """

    def __init__(self, members: Sequence[str] = (), window: str = DEFAULT_WINDOW, **kwargs: Any) -> None:
        """Baut die Ansicht.

        Args:
            members:
                Namen der Merkliste "Mein Team".
            window:
                Der zuletzt gewaehlte Zeitraum, z.B. "1T".
        """
        super().__init__(**kwargs)
        self._members = list(members)
        self._window = window if window in WINDOWS else DEFAULT_WINDOW
        self._member = ALL_MEMBERS
        self._tickets: list[Ticket] | None = None
        self._row_tickets: dict[str, Ticket] = {}
        self._is_workday: Callable[[dt.date], bool] = _weekday
        self._today: Callable[[], dt.date] = dt.date.today
        # Anzeige-Umformung (Screenshot-Modus). Gefiltert wird immer auf den
        # echten Daten, sonst passt kein erfundener Name zur Personenauswahl.
        self._display: Callable[[list[Ticket]], list[Ticket]] | None = None
        self._message = t("new.not_loaded")

    # --- Aufbau ---------------------------------------------------------

    def compose(self) -> ComposeResult:
        """Filterleiste, Hinweiszeile und Tabelle."""
        with Horizontal(classes="new-filter-bar"):
            yield Static(t("new.filter.member"), classes="new-filter-label")
            yield Select[str](
                self._member_options(),
                value=_ALL,
                allow_blank=False,
                id="new-member",
            )
            for kind, days in WINDOWS.items():
                button = Button(kind, id=f"new-window-{kind}", classes="new-window")
                button.tooltip = t("new.window.one") if days == 1 else t("new.window.many", days=days)
                if kind == self._window:
                    button.add_class("-active")
                yield button
            yield Static("", classes="new-range", id="new-range")
            yield Static("", classes="new-count", id="new-count")
        yield Static("", classes="new-hint", id="new-hint")
        yield ResizableDataTable(id="new-data", cursor_type="row", zebra_stripes=False)

    def on_mount(self) -> None:
        """Legt die Spalten an."""
        table = self.query_one("#new-data", ResizableDataTable)
        keys = table.add_columns(*(t(key) for key in _COLUMNS))
        table.set_flex_column(keys[_COLUMNS.index("new.col.summary")], min_width=_MIN_SUMMARY_WIDTH)
        self._refresh()

    def _member_options(self) -> list[tuple[str, str]]:
        return [(t("new.filter.all"), _ALL), *((name, name) for name in self._members)]

    # --- Einstellungen von aussen ---------------------------------------

    def set_workday_check(self, is_workday: Callable[[dt.date], bool]) -> None:
        """Uebernimmt den Feiertagskalender - nach Ostermontag zaehlt 1T ab Donnerstag."""
        self._is_workday = is_workday
        self._refresh()

    def set_clock(self, today: Callable[[], dt.date]) -> None:
        """Ersetzt die Uhr - fuer Tests."""
        self._today = today
        self._refresh()

    def set_display(self, display: Callable[[list[Ticket]], list[Ticket]] | None) -> None:
        """Setzt die Anzeige-Umformung fuer den Screenshot-Modus, None = unveraendert."""
        self._display = display
        self._refresh()

    def set_members(self, names: Sequence[str]) -> None:
        """Fuellt die Personenauswahl, "Alle" bleibt vorn. Die Auswahl bleibt, solange es sie gibt."""
        self._members = list(names)
        if self._member not in self._members:
            self._member = ALL_MEMBERS
        if self.is_mounted:
            select = self.query_one("#new-member", Select)
            with select.prevent(Select.Changed):
                select.set_options(self._member_options())
                select.value = self._member or _ALL
        self._refresh()

    # --- Auswahl --------------------------------------------------------

    @property
    def member(self) -> str:
        """Name aus der Merkliste, leer fuer alle."""
        return self._member

    def select_member(self, name: str) -> None:
        """Waehlt eine Person, leer = alle."""
        if name and name not in self._members:
            return
        self._member = name
        if self.is_mounted:
            select = self.query_one("#new-member", Select)
            with select.prevent(Select.Changed):
                select.value = name or _ALL
        self._refresh()

    @property
    def window(self) -> str:
        """Das Kuerzel des gewaehlten Zeitraums."""
        return self._window

    def set_window(self, kind: str) -> None:
        """Setzt den Zeitraum, ohne ihn zu melden."""
        if kind not in WINDOWS:
            return
        self._window = kind
        if self.is_mounted:
            for other in WINDOWS:
                self.query_one(f"#new-window-{other}", Button).set_class(other == kind, "-active")
        self._refresh()

    def since(self) -> dt.date:
        """Erster Tag des gewaehlten Zeitraums."""
        return window_start(self._today(), WINDOWS[self._window], self._is_workday)

    def since_longest(self) -> dt.date:
        """Erster Tag des laengsten Zeitraums - so weit reicht der Abruf."""
        return window_start(self._today(), max(WINDOWS.values()), self._is_workday)

    def on_select_changed(self, event: Select.Changed) -> None:
        """Personenauswahl: filtert lokal."""
        event.stop()
        value = str(event.value) if event.value is not None else _ALL
        self._member = ALL_MEMBERS if value == _ALL else value
        self._refresh()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Zeitraum-Knopf: filtert lokal und meldet den Wechsel."""
        event.stop()
        kind = str(event.button.label)
        if kind in WINDOWS:
            self.set_window(kind)
            self.post_message(self.WindowChanged(kind))

    # --- Inhalt ---------------------------------------------------------

    @property
    def tickets(self) -> list[Ticket] | None:
        """Die geladene Liste, None vor dem ersten Abruf."""
        return self._tickets

    def set_tickets(self, tickets: Sequence[Ticket]) -> None:
        """Uebernimmt eine frisch geladene Liste."""
        self._tickets = list(tickets)
        self._refresh()

    def show_message(self, message: str) -> None:
        """Zeigt einen Hinweis statt der Liste und verwirft die geladenen Tickets."""
        self._tickets = None
        self._message = message
        self._refresh()

    def filtered(self) -> list[Ticket]:
        """Die Tickets, die Person und Zeitraum gerade zeigen - echte Daten."""
        if self._tickets is None:
            return []
        return visible_tickets(self._tickets, self._member, self.since())

    def displayed(self) -> list[Ticket]:
        """Die Zeilen, wie sie in der Tabelle stehen - im Screenshot-Modus umgeformt."""
        tickets = self.filtered()
        return self._display(tickets) if self._display is not None else tickets

    def _refresh(self) -> None:
        """Baut Kopfzeile und Tabelle neu auf."""
        if not self.is_mounted:
            return
        start = self.since()
        weekday = t(f"new.weekday.{start.weekday()}")
        self.query_one("#new-range", Static).update(t("new.range", weekday=weekday, date=f"{start:%d.%m.%Y}"))

        table = self.query_one("#new-data", DataTable)
        table.clear()
        self._row_tickets.clear()
        count = self.query_one("#new-count", Static)
        hint = self.query_one("#new-hint", Static)
        if self._tickets is None:
            count.update("")
            hint.update(self._message)
            hint.display = True
            self.post_message(self.CountChanged(-1))
            return

        tickets = self.displayed()
        today = self._today()
        for index, ticket in enumerate(tickets):
            row_key = f"{index}:{ticket.key}"
            self._row_tickets[row_key] = ticket
            table.add_row(
                ticket.key,
                ticket.summary,
                ticket.issue_type,
                ticket.priority,
                ticket.status,
                ticket.reporter,
                created_label(ticket.created, today),
                ticket.assignee or "-",
                key=row_key,
            )
        if len(tickets) == 1:
            count.update(t("new.count.one"))
        elif tickets:
            count.update(t("new.count.many", count=len(tickets)))
        else:
            count.update(t("new.count.none"))
        hint.update("" if tickets else t("new.empty"))
        hint.display = not tickets
        self.post_message(self.CountChanged(len(tickets)))

    # --- Ereignisse der Tabelle -----------------------------------------

    def current_ticket(self) -> Ticket | None:
        """Das Ticket unter dem Zeilenzeiger."""
        try:
            table = self.query_one("#new-data", DataTable)
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        except Exception:  # noqa: BLE001 - leere Tabelle
            return None
        return self._row_tickets.get(str(row_key.value))

    def _ticket_at(self, row_index: int) -> Ticket | None:
        try:
            table = self.query_one("#new-data", DataTable)
            row_key = table.ordered_rows[row_index].key
        except (IndexError, AttributeError):
            return None
        return self._row_tickets.get(str(row_key.value))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Enter auf einer Zeile oeffnet das Ticket, wie in den Ticketlisten."""
        event.stop()
        self.post_message(TicketBoardTable.TicketSelected(self._row_tickets.get(str(event.row_key.value))))

    def on_resizable_data_table_cell_clicked(self, event: ResizableDataTable.CellClicked) -> None:
        """Klick auf die Ticketnummer oeffnet - schon beim ersten Mal, wie in den Ticketlisten."""
        event.stop()
        ticket = self._ticket_at(event.row_index)
        if ticket is not None and event.column_index == 0:
            self.post_message(TicketBoardTable.TicketSelected(ticket))

    def on_resizable_data_table_right_clicked(self, event: ResizableDataTable.RightClicked) -> None:
        """Reicht den Rechtsklick mit dem Ticket der Zeile weiter."""
        event.stop()
        ticket = self._ticket_at(event.row_index) if event.row_index >= 0 else None
        self.post_message(TicketBoardTable.TicketRightClicked(event.screen_x, event.screen_y, ticket))
