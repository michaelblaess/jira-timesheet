"""Tabelle der Ticket-Ansichten "Meine Tickets" und "Relevante Tickets".

Zeigt ein fertig aufbereitetes Board des Kerns an: Gruppen als Zwischen-
ueberschriften, darunter die Tickets. Das Widget rechnet nichts - es stellt
dar, was ``services.ticket_board`` geliefert hat, und filtert die Anzeige.

Bewusst NICHT sortierbar per Kopfzeilenklick: die Reihenfolge kommt aus dem
Kern und traegt eine Aussage (im Backlog etwa Fehler zuerst, sonst das
Aelteste oben). Eine Sortierung nach Titel wuerde diese Aussage wegwerfen,
ohne dass es auffaellt.
"""

from __future__ import annotations

from typing import Any

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Checkbox, DataTable, Input, Select, Static

from jira_timesheet.i18n import format_number, t
from jira_timesheet.services.ticket_board import Board, Group, Marker, Role, Ticket
from jira_timesheet.widgets.resizable_data_table import ResizableDataTable

# Reihenfolge und i18n-Schluessel der Spalten.
_COLUMNS: tuple[tuple[str, str], ...] = (
    ("key", "board.col.ticket"),
    ("status", "board.col.status"),
    ("priority", "board.col.priority"),
    ("type", "board.col.type"),
    ("idle", "board.col.idle"),
    ("markers", "board.col.markers"),
    ("summary", "board.col.summary"),
)

# Der Titel fuellt die restliche Breite, bis der Benutzer ihn selbst zieht.
_MIN_SUMMARY_WIDTH = 20

# Zeichen vor einer Gruppenueberschrift. Es steht fuer eine aufgeklappte
# Gruppe wie im Baum der Qt-Fassung - hier ist nichts zuklappbar, aber das
# Zeichen macht die Ueberschrift auf einen Blick als solche erkennbar.
_GROUP_MARK = "▼"

# Einrueckung der Ticketzeilen unter ihrer Gruppe. Ohne sie stehen
# Ueberschrift und Tickets buendig untereinander, und die Gliederung ist
# nur noch an der Schriftstaerke zu erkennen.
_TICKET_INDENT = "  "

# Ueberschriften der Gruppen. Bewusst kurz: der Titel steht in der ersten
# Spalte und bestimmt damit deren Breite - eine ausgeschriebene Anweisung wie
# "zurueckgeben, nicht bearbeiten" haette die Ticket-Spalte auf das Dreifache
# aufgeblasen. Die Anweisung steht deshalb daneben in der Titel-Spalte, wo
# ohnehin Platz ist, und geht dadurch nicht verloren.
_GROUP_KEYS: dict[Role, str] = {
    Role.ACTIVE: "board.group.active",
    Role.ACCEPTANCE: "board.group.acceptance",
    Role.BACKLOG: "board.group.backlog",
    Role.HANDBACK: "board.group.handback",
    Role.CLOSING: "board.group.closing",
    Role.UNKNOWN: "board.group.unknown",
}

# Beschriftung der Merkmale. Kurz, damit die Spalte schmal bleibt.
_MARKER_KEYS: dict[Marker, str] = {
    Marker.PILE_OF_SHAME: "board.marker.pile_of_shame",
    Marker.HANDBACK: "board.marker.handback",
    Marker.STALE: "board.marker.stale",
    Marker.HIGH_PRIORITY: "board.marker.high_priority",
    Marker.ACCEPTANCE: "board.marker.acceptance",
    Marker.BLOCKED: "board.marker.blocked",
}

# Merkmale, die auf eine Unterlassung zeigen, werden rot gesetzt. Die
# uebrigen sind Hinweise und bleiben ruhig - faerbt man alles ein, faellt
# nichts mehr auf.
_URGENT_MARKERS = (Marker.PILE_OF_SHAME, Marker.STALE, Marker.HIGH_PRIORITY)

# Wert des Statusfilters fuer "alle". Leer waere mehrdeutig, weil ein Ticket
# tatsaechlich einen leeren Status haben kann.
_ALL_STATUS = "\x00alle"


class TicketBoardTable(Vertical):
    """Zeigt ein Board mit Gruppen, Filterleiste und Ticketzeilen."""

    class TicketSelected(Message):
        """Enter auf einer Ticketzeile."""

        def __init__(self, ticket: Ticket | None) -> None:
            super().__init__()
            self.ticket = ticket

    class TicketRightClicked(Message):
        """Rechtsklick auf eine Zeile - der Host oeffnet das Kontextmenue."""

        def __init__(self, screen_x: int, screen_y: int, ticket: Ticket | None) -> None:
            super().__init__()
            self.screen_x = screen_x
            self.screen_y = screen_y
            self.ticket = ticket

    DEFAULT_CSS = """
    TicketBoardTable {
        height: 1fr;
    }

    TicketBoardTable .board-filter-bar {
        height: auto;
        padding: 0 1;
    }

    TicketBoardTable .board-filter-label {
        width: auto;
        padding: 1 1 0 0;
    }

    TicketBoardTable Select {
        width: 32;
    }

    TicketBoardTable Input {
        width: 1fr;
    }

    TicketBoardTable Checkbox {
        width: auto;
    }

    TicketBoardTable .board-hint {
        height: auto;
        padding: 0 1;
        color: $text-muted;
    }

    TicketBoardTable DataTable {
        height: 1fr;
    }
    """

    def __init__(self, mode: str, jira_host: str = "", **kwargs: Any) -> None:
        """Baut die Ansicht.

        Args:
            mode:
                Kennung der Ansicht, wandert in die Widget-Ids.
            jira_host:
                Basis-URL fuer die Ticket-Verweise.
        """
        super().__init__(**kwargs)
        self._mode = mode
        self._jira_host = jira_host.rstrip("/")
        self._board: Board | None = None
        self._status = _ALL_STATUS
        self._actionable_only = False
        self._filter_text = ""
        # Ticket je Zeilenschluessel; Gruppenzeilen fehlen hier bewusst.
        self._row_tickets: dict[str, Ticket] = {}
        self._col_keys: list[Any] = []

    # --- Aufbau ---------------------------------------------------------

    def compose(self) -> ComposeResult:
        """Filterleiste, Hinweiszeile und Tabelle."""
        with Horizontal(classes="board-filter-bar"):
            yield Static(t("board.filter.status"), classes="board-filter-label")
            yield Select[str](
                [(t("board.filter.all"), _ALL_STATUS)],
                value=_ALL_STATUS,
                allow_blank=False,
                id=f"board-status-{self._mode}",
            )
            yield Checkbox(
                t("board.filter.actionable"),
                value=False,
                id=f"board-actionable-{self._mode}",
            )
            yield Input(
                placeholder=t("board.filter.search"),
                id=f"board-search-{self._mode}",
            )
        yield Static("", classes="board-hint", id=f"board-hint-{self._mode}")
        yield ResizableDataTable(
            id=f"board-data-{self._mode}",
            cursor_type="row",
            zebra_stripes=False,
        )

    def on_mount(self) -> None:
        """Legt die Spalten an."""
        table = self.query_one(f"#board-data-{self._mode}", ResizableDataTable)
        self._col_keys = table.add_columns(*(t(key) for _, key in _COLUMNS))
        summary_index = [key for key, _ in _COLUMNS].index("summary")
        table.set_flex_column(self._col_keys[summary_index], min_width=_MIN_SUMMARY_WIDTH)

    # --- Fuellen --------------------------------------------------------

    @property
    def board(self) -> Board | None:
        """Das zuletzt gesetzte Board, oder None."""
        return self._board

    def set_board(self, board: Board | None) -> None:
        """Uebernimmt ein neues Board und baut die Tabelle neu auf."""
        self._board = board
        self._sync_status_options()
        self._refresh()

    def set_jira_host(self, host: str) -> None:
        """Aendert die Basis-URL der Ticket-Verweise."""
        self._jira_host = host.rstrip("/")
        self._refresh()

    def show_message(self, message: str) -> None:
        """Zeigt einen Hinweis statt einer Tabelle.

        Ein Abruf kann eine Minute dauern. Eine leere Flaeche ohne jedes
        Lebenszeichen sieht in dieser Zeit aus wie ein Absturz.
        """
        self._board = None
        self._row_tickets.clear()
        table = self.query_one(f"#board-data-{self._mode}", DataTable)
        table.clear()
        self._set_hint(message)

    # --- Filter ---------------------------------------------------------

    def _sync_status_options(self) -> None:
        """Fuellt den Statusfilter mit den tatsaechlich vorkommenden Werten.

        Eine feste Liste ginge nicht: welche Status es gibt, weiss erst die
        Antwort. Ein zuvor gewaehlter Status bleibt erhalten, solange er noch
        vorkommt - sonst faellt die Auswahl auf "alle" zurueck.
        """
        select = self.query_one(f"#board-status-{self._mode}", Select)
        names = sorted({ticket.status for ticket in self._tickets() if ticket.status})
        options = [(t("board.filter.all"), _ALL_STATUS)] + [(name, name) for name in names]
        select.set_options(options)
        if self._status not in {value for _label, value in options}:
            self._status = _ALL_STATUS
        select.value = self._status

    def _tickets(self) -> list[Ticket]:
        """Alle Tickets des Boards, ungefiltert."""
        return list(self._board.tickets) if self._board is not None else []

    def _visible_groups(self) -> list[Group]:
        """Die Gruppen nach Anwendung aller Filter, leere fallen weg."""
        if self._board is None:
            return []
        needle = self._filter_text.strip().casefold()
        groups: list[Group] = []
        for group in self._board.groups:
            tickets = [
                ticket
                for ticket in group.tickets
                if self._matches(ticket, needle)
            ]
            if tickets:
                groups.append(Group(role=group.role, tickets=tickets))
        return groups

    def _matches(self, ticket: Ticket, needle: str) -> bool:
        """Prueft ein Ticket gegen alle drei Filter."""
        if self._status != _ALL_STATUS and ticket.status != self._status:
            return False
        if self._actionable_only and not ticket.markers:
            return False
        return not (needle and needle not in f"{ticket.key} {ticket.summary}".casefold())

    def on_select_changed(self, event: Select.Changed) -> None:
        """Statusfilter geaendert."""
        if event.select.id != f"board-status-{self._mode}":
            return
        event.stop()
        self._status = str(event.value)
        self._refresh()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Schalter "nur mit Handlungsbedarf" geaendert."""
        if event.checkbox.id != f"board-actionable-{self._mode}":
            return
        event.stop()
        self._actionable_only = bool(event.value)
        self._refresh()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Suchtext geaendert."""
        if event.input.id != f"board-search-{self._mode}":
            return
        event.stop()
        self._filter_text = event.value
        self._refresh()

    def focus_search(self) -> None:
        """Setzt den Fokus ins Suchfeld."""
        self.query_one(f"#board-search-{self._mode}", Input).focus()

    # --- Zeilen ---------------------------------------------------------

    def _refresh(self) -> None:
        """Baut die Tabelle aus dem gespeicherten Board neu auf."""
        try:
            table = self.query_one(f"#board-data-{self._mode}", DataTable)
        except Exception:
            # Vor dem Einhaengen gibt es noch keine Tabelle - das Board ist
            # gespeichert und wird beim naechsten Aufbau gezeichnet.
            return
        table.clear()
        self._row_tickets.clear()
        if self._board is None:
            return

        groups = self._visible_groups()
        row_index = 0
        for position, group in enumerate(groups):
            row_index = self._render_group(table, group, row_index, first=position == 0)
        self._set_hint(self._hint_text(groups))

    def _render_group(
        self,
        table: DataTable[Any],
        group: Group,
        row_index: int,
        first: bool,
    ) -> int:
        """Schreibt eine Gruppenzeile und ihre Tickets.

        Args:
            table:
                Die zu fuellende Tabelle.
            group:
                Die Gruppe mit ihren bereits gefilterten Tickets.
            row_index:
                Fortlaufender Zeilenzaehler, dient als Zeilenschluessel.
            first:
                True fuer die erste Gruppe - sie bekommt keine Leerzeile
                davor, sonst begaenne die Tabelle mit einer Luecke.

        Returns:
            Der naechste freie Zeilenzaehler.
        """
        # Eine Leerzeile trennt die Gruppen. Ohne sie laufen zwanzig Zeilen
        # Tickets und die naechste Ueberschrift ineinander - im Terminal gibt
        # es keine Linien und keine Einrueckung, die das sonst leisten.
        if not first:
            table.add_row(*(Text("") for _ in _COLUMNS), key=str(row_index))
            row_index += 1

        title = f"{_GROUP_MARK} {t(_GROUP_KEYS[group.role])} ({group.count})"
        hint = t(f"{_GROUP_KEYS[group.role]}_hint")
        cells: list[Any] = [Text(title, style="bold")]
        cells.extend(Text("") for _ in _COLUMNS[1:-1])
        # Ohne no_wrap bricht der Hinweis um und macht die Ueberschrift
        # zweizeilig - dann steht er unter der Gruppe statt neben ihr.
        cells.append(Text(hint, style="dim", no_wrap=True, overflow="ellipsis", end=""))
        table.add_row(*cells, key=str(row_index))
        row_index += 1

        for ticket in group.tickets:
            key = str(row_index)
            self._row_tickets[key] = ticket
            table.add_row(*self._cells(ticket), key=key)
            row_index += 1
        return row_index

    def _cells(self, ticket: Ticket) -> list[Any]:
        """Baut die Zellen einer Ticketzeile."""
        urgent = any(ticket.has(marker) for marker in _URGENT_MARKERS)
        style = "red" if urgent else ""

        # Die Einrueckung gehoert zum Text und nicht zum Stil: eine DataTable
        # kennt keine Ebenen, nur Zellen.
        key_text = Text(_TICKET_INDENT, style=style)
        if self._jira_host and ticket.key:
            key_text.append(
                ticket.key,
                style=f"{style} link {self._jira_host}/browse/{ticket.key}".strip(),
            )
        else:
            key_text.append(ticket.key, style=style)

        return [
            key_text,
            Text(ticket.status, style=style),
            Text(ticket.priority, style=style),
            Text(ticket.issue_type, style=style),
            Text(format_number(ticket.idle_workdays, decimals=0), style=style, justify="right"),
            self._marker_text(ticket),
            Text(ticket.summary, no_wrap=True, overflow="ellipsis", end="", style=style),
        ]

    @staticmethod
    def _marker_text(ticket: Ticket) -> Text:
        """Setzt die Merkmale eines Tickets zusammen."""
        if not ticket.markers:
            return Text("")
        parts = [t(_MARKER_KEYS[marker]) for marker in ticket.markers if marker in _MARKER_KEYS]
        urgent = any(marker in _URGENT_MARKERS for marker in ticket.markers)
        return Text(", ".join(parts), style="red" if urgent else "yellow")

    def _hint_text(self, groups: list[Group]) -> str:
        """Zeile unter der Filterleiste: Trefferzahl bzw. Fehlanzeige."""
        shown = sum(group.count for group in groups)
        total = len(self._tickets())
        if total == 0:
            return t("board.hint.empty")
        if shown == total:
            return t("board.hint.count", count=total)
        return t("board.hint.filtered", shown=shown, total=total)

    def _set_hint(self, text: str) -> None:
        """Schreibt die Hinweiszeile."""
        try:
            self.query_one(f"#board-hint-{self._mode}", Static).update(text)
        except Exception:
            return

    # --- Auswahl --------------------------------------------------------

    def current_ticket(self) -> Ticket | None:
        """Das Ticket unter dem Zeilenzeiger, None auf einer Gruppenzeile."""
        try:
            table = self.query_one(f"#board-data-{self._mode}", DataTable)
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        except Exception:
            return None
        return self._row_tickets.get(str(row_key.value))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Enter auf einer Zeile meldet das Ticket an den Host."""
        event.stop()
        self.post_message(self.TicketSelected(self._row_tickets.get(str(event.row_key.value))))

    def on_resizable_data_table_right_clicked(
        self, event: ResizableDataTable.RightClicked
    ) -> None:
        """Reicht den Rechtsklick mit dem Ticket der Zeile weiter."""
        event.stop()
        ticket = None
        if event.row_index >= 0:
            table = self.query_one(f"#board-data-{self._mode}", DataTable)
            try:
                row_key = table.ordered_rows[event.row_index].key
                ticket = self._row_tickets.get(str(row_key.value))
            except (IndexError, AttributeError):
                ticket = None
        self.post_message(self.TicketRightClicked(event.screen_x, event.screen_y, ticket))
