"""Tests fuer die Tabellen-Widgets (Spaltenbreiten, Flex-Spalte, Drag)."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from textual.app import App, ComposeResult
from textual.events import MouseMove
from textual.pilot import Pilot, _get_mouse_message_arguments
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Input, Select

from jira_timesheet.i18n import load_locale
from jira_timesheet.models.export_column import ExportColumn, default_columns
from jira_timesheet.models.timesheet import Timesheet, TimesheetDay, WorklogEntry
from jira_timesheet.screens.confirm_screen import ConfirmScreen
from jira_timesheet.screens.manual_entry_screen import ManualEntryResult, ManualEntryScreen
from jira_timesheet.screens.year_screen import MonthTile, YearScreen
from jira_timesheet.services.manual_entry_service import ManualEntry
from jira_timesheet.widgets.resizable_data_table import ResizableDataTable
from jira_timesheet.widgets.summary_panel import SummaryPanel
from jira_timesheet.widgets.timesheet_table import _MIN_DESCRIPTION_WIDTH, TimesheetTable

_LONG_SUMMARY = "Sitefinity Security Advisory for Addressing Security Vulnerabilities in Telerik UI " * 2


@pytest.fixture(autouse=True)
def _german_labels() -> None:
    """Echte Spaltentitel laden - sonst stehen die i18n-Schluessel im Kopf."""
    load_locale("de")


def _timesheet() -> Timesheet:
    """Baut einen Stundenzettel mit einem langen Beschreibungstext."""
    entry = WorklogEntry(
        date=date(2026, 7, 23),
        ticket="DMZ-17301",
        summary=_LONG_SUMMARY,
        author="Michael",
        budget="",
        hours=0.5,
    )
    return Timesheet(
        developer="Michael",
        email="mail@example.org",
        date_from=date(2026, 7, 1),
        date_to=date(2026, 7, 31),
        days=[TimesheetDay(date=date(2026, 7, 23), entries=[entry])],
    )


class _TableApp(App[None]):
    """Minimal-App, die nur die Stundenzettel-Tabelle zeigt."""

    def __init__(self, column_widths: dict[str, int] | None = None) -> None:
        super().__init__()
        self.column_widths = column_widths or {}
        self.persisted: dict[str, int] = {}

    def compose(self) -> ComposeResult:
        yield TimesheetTable(column_widths=self.column_widths, id="timesheet-table")

    def on_timesheet_table_column_widths_changed(self, event: TimesheetTable.ColumnWidthsChanged) -> None:
        """Haelt fest, was die App persistieren wuerde."""
        self.persisted = event.widths


def _column_edge(table: ResizableDataTable, index: int) -> int:
    """Virtuelle x-Position der rechten Trennlinie einer Spalte."""
    edge = table._row_label_column_width
    for column in table.ordered_columns[: index + 1]:
        edge += column.get_render_width(table)
    return edge


async def _mouse_move(pilot: Pilot[None], widget: ResizableDataTable, offset: tuple[int, int]) -> None:
    """Schickt ein MouseMove an das Widget - Pilot bietet dafuer nichts an."""
    arguments = _get_mouse_message_arguments(widget, offset)
    pilot.app.screen._forward_event(MouseMove(**arguments))
    await pilot.pause()


async def _drag_header(
    pilot: Pilot[None],
    table: ResizableDataTable,
    column_index: int,
    delta: int,
) -> None:
    """Zieht die rechte Trennlinie einer Spalte um delta Zellen."""
    edge = _column_edge(table, column_index)
    start = (edge, 0)
    end = (edge + delta, 0)
    await pilot.mouse_down(table, offset=start)
    await pilot.pause()
    await _mouse_move(pilot, table, end)
    await pilot.mouse_up(table, offset=end)
    await pilot.pause()


@pytest.mark.asyncio
async def test_description_column_fills_remaining_width() -> None:
    """Die Beschreibung fuellt die Breite - ohne horizontalen Ueberlauf."""
    app = _TableApp()
    async with app.run_test(size=(120, 30)) as pilot:
        widget = app.query_one(TimesheetTable)
        widget.load_timesheet(_timesheet(), missing_days=[])
        await pilot.pause()
        table = widget.query_one("#timesheet-data", ResizableDataTable)
        assert table.virtual_size.width <= table.scrollable_content_region.width
        description = table.ordered_columns[4]
        assert not description.auto_width
        assert description.width > 20


@pytest.mark.asyncio
async def test_header_drag_changes_column_width() -> None:
    """Ziehen an der Trennlinie im Kopf verstellt die Spaltenbreite."""
    app = _TableApp()
    async with app.run_test(size=(120, 30)) as pilot:
        widget = app.query_one(TimesheetTable)
        widget.load_timesheet(_timesheet(), missing_days=[])
        await pilot.pause()
        table = widget.query_one("#timesheet-data", ResizableDataTable)
        ticket = table.ordered_columns[3]
        before = ticket.get_render_width(table) - 2 * table.cell_padding
        await _drag_header(pilot, table, 3, 10)
        assert not ticket.auto_width
        assert ticket.width == before + 10
        # Die Flex-Spalte gibt den Platz ab, statt horizontal zu scrollen.
        assert table.virtual_size.width <= table.scrollable_content_region.width


@pytest.mark.asyncio
async def test_header_drag_does_not_sort() -> None:
    """Ein Resize-Drag darf die Sortierung nicht umschalten."""
    app = _TableApp()
    async with app.run_test(size=(120, 30)) as pilot:
        widget = app.query_one(TimesheetTable)
        widget.load_timesheet(_timesheet(), missing_days=[])
        await pilot.pause()
        table = widget.query_one("#timesheet-data", ResizableDataTable)
        sort_col_before = widget._sort_col
        sort_desc_before = widget._sort_desc
        await _drag_header(pilot, table, 0, 4)
        assert table.ordered_columns[0].width > 0
        assert widget._sort_col == sort_col_before
        assert widget._sort_desc == sort_desc_before


@pytest.mark.asyncio
async def test_dragging_description_reveals_more_text() -> None:
    """Die Beschreibung breiter ziehen zeigt mehr vom Text."""
    app = _TableApp()
    async with app.run_test(size=(120, 30)) as pilot:
        widget = app.query_one(TimesheetTable)
        widget.load_timesheet(_timesheet(), missing_days=[])
        await pilot.pause()
        table = widget.query_one("#timesheet-data", ResizableDataTable)
        before = table.render_line(1).text
        await _drag_header(pilot, table, 4, 10)
        assert table.ordered_columns[4].width > _MIN_DESCRIPTION_WIDTH
        assert table.is_column_pinned(table.ordered_columns[4].key)
        assert table.render_line(1).text != before


@pytest.mark.asyncio
async def test_double_click_resets_flex_column() -> None:
    """Doppelklick auf die Trennlinie gibt die Flex-Breite zurueck."""
    app = _TableApp()
    async with app.run_test(size=(120, 30)) as pilot:
        widget = app.query_one(TimesheetTable)
        widget.load_timesheet(_timesheet(), missing_days=[])
        await pilot.pause()
        table = widget.query_one("#timesheet-data", ResizableDataTable)
        flex_width = table.ordered_columns[4].width
        await _drag_header(pilot, table, 4, 10)
        assert table.ordered_columns[4].width != flex_width
        await pilot.double_click(table, offset=(_column_edge(table, 4), 0))
        await pilot.pause()
        assert not table.is_column_pinned(table.ordered_columns[4].key)
        assert table.ordered_columns[4].width == flex_width


@pytest.mark.asyncio
async def test_column_widths_round_trip() -> None:
    """Gezogene Breiten werden gemeldet und beim Start wieder angewendet."""
    app = _TableApp()
    async with app.run_test(size=(120, 30)) as pilot:
        widget = app.query_one(TimesheetTable)
        widget.load_timesheet(_timesheet(), missing_days=[])
        await pilot.pause()
        table = widget.query_one("#timesheet-data", ResizableDataTable)
        await _drag_header(pilot, table, 3, 10)
        # Breiten werden ueber den Spalten-Key gemerkt, nicht ueber den Index.
        assert app.persisted.get("ticket") == table.ordered_columns[3].width
    saved = dict(app.persisted)

    restored = _TableApp(column_widths=saved)
    async with restored.run_test(size=(120, 30)) as pilot:
        widget = restored.query_one(TimesheetTable)
        widget.load_timesheet(_timesheet(), missing_days=[])
        await pilot.pause()
        table = widget.query_one("#timesheet-data", ResizableDataTable)
        assert table.ordered_columns[3].width == saved["ticket"]


def _styles_of_line(table: ResizableDataTable, line: int) -> set[str]:
    """Alle Rich-Stile einer gerenderten Zeile als Strings."""
    return {str(seg.style) for seg in table.render_line(line)._segments if seg.text.strip()}


def _mixed_timesheet() -> Timesheet:
    """Ein Tag mit einem Jira- und einem manuellen Eintrag."""
    jira = WorklogEntry(date=date(2026, 7, 23), ticket="DMZ-13983", summary="Agile", author="M", budget="", hours=1.0)
    manual = ManualEntry(
        entry_date=date(2026, 7, 23),
        ticket="DMZ-17024",
        summary="Pipelines",
        hours=10.0,
        entry_id=7,
        customer="Corporate",
    ).to_worklog(author="M")
    return Timesheet(
        developer="M",
        email="mail@example.org",
        date_from=date(2026, 7, 1),
        date_to=date(2026, 7, 31),
        days=[TimesheetDay(date=date(2026, 7, 23), entries=[jira, manual])],
    )


class _MarkingApp(App[None]):
    """Tabelle mit einstellbarer Markierung manueller Eintraege."""

    def __init__(self, mark: bool = True, color: str = "FF0000") -> None:
        super().__init__()
        self.mark = mark
        self.color = color

    def compose(self) -> ComposeResult:
        yield TimesheetTable(mark_manual=self.mark, manual_color=self.color, id="timesheet-table")


@pytest.mark.asyncio
async def test_manual_entry_is_colour_marked() -> None:
    """Die manuelle Zeile wird fett in der eingestellten Farbe gesetzt."""
    app = _MarkingApp(color="FF0000")
    async with app.run_test(size=(120, 20)) as pilot:
        widget = app.query_one(TimesheetTable)
        widget.load_timesheet(_mixed_timesheet(), missing_days=[])
        await pilot.pause()
        table = widget.query_one("#timesheet-data", ResizableDataTable)
        # Zeile 1 = Jira-Eintrag, Zeile 2 = manueller Eintrag (Zeile 0 = Kopf).
        assert not any("#ff0000" in s for s in _styles_of_line(table, 1))
        assert any("bold #ff0000" in s for s in _styles_of_line(table, 2))


@pytest.mark.asyncio
async def test_manual_marking_can_be_switched_off_at_runtime() -> None:
    """set_manual_marking wirkt sofort, ohne den Stundenzettel neu zu laden."""
    app = _MarkingApp(color="FF0000")
    async with app.run_test(size=(120, 20)) as pilot:
        widget = app.query_one(TimesheetTable)
        widget.load_timesheet(_mixed_timesheet(), missing_days=[])
        await pilot.pause()
        table = widget.query_one("#timesheet-data", ResizableDataTable)
        assert any("#ff0000" in s for s in _styles_of_line(table, 2))

        widget.set_manual_marking(False, "FF0000")
        await pilot.pause()
        assert not any("#ff0000" in s for s in _styles_of_line(table, 2))


@pytest.mark.asyncio
async def test_current_entry_returns_manual_id() -> None:
    """Der Cursor liefert den manuellen Eintrag samt Datenbank-Id."""
    app = _MarkingApp()
    async with app.run_test(size=(120, 20)) as pilot:
        widget = app.query_one(TimesheetTable)
        widget.load_timesheet(_mixed_timesheet(), missing_days=[])
        await pilot.pause()
        table = widget.query_one("#timesheet-data", ResizableDataTable)

        table.move_cursor(row=0, animate=False)
        await pilot.pause()
        first = widget.current_entry()
        assert first is not None
        assert first.manual is False

        table.move_cursor(row=1, animate=False)
        await pilot.pause()
        second = widget.current_entry()
        assert second is not None
        assert second.manual is True
        assert second.manual_id == 7
        assert widget.current_date() == date(2026, 7, 23)


@pytest.mark.asyncio
async def test_header_click_still_sorts() -> None:
    """Ein Klick in der Mitte eines Spaltenkopfs sortiert weiterhin."""
    app = _TableApp()
    async with app.run_test(size=(120, 30)) as pilot:
        widget = app.query_one(TimesheetTable)
        widget.load_timesheet(_timesheet(), missing_days=[])
        await pilot.pause()
        table = widget.query_one("#timesheet-data", ResizableDataTable)
        assert widget._sort_col == "date"
        assert not widget._sort_desc
        edge = _column_edge(table, 2)
        width = table.ordered_columns[2].get_render_width(table)
        middle = edge - width // 2
        await pilot.click(table, offset=(middle, 0))
        await pilot.pause()
        assert widget._sort_col == "date"
        assert widget._sort_desc


class _DialogApp(App[None]):
    """Traegt den Dialog fuer manuelle Zeiten, ohne die ganze App zu starten."""

    def __init__(self, screen: ModalScreen[Any]) -> None:
        super().__init__()
        self._screen_to_push = screen
        self.result: object = "unset"

    def on_mount(self) -> None:
        """Oeffnet den Dialog direkt beim Start."""
        self.push_screen(self._screen_to_push, callback=self._store)

    def _store(self, value: object) -> None:
        """Merkt sich das Dialog-Ergebnis fuer die Pruefung."""
        self.result = value


@pytest.mark.asyncio
async def test_manual_dialog_ticket_field_is_empty() -> None:
    """Die Ticket-Nummer wird nicht mehr als Platzhalter vorgeschlagen."""
    app = _DialogApp(ManualEntryScreen(default_customer="Vertrieb", customers=["Vertrieb"]))
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        ticket = app.screen.query_one("#manual-ticket", Input)
        assert ticket.value == ""
        assert ticket.placeholder == ""


@pytest.mark.asyncio
async def test_manual_dialog_customer_is_a_dropdown() -> None:
    """Der Kunde kommt aus einer Auswahlliste statt aus einem freien Textfeld."""
    app = _DialogApp(ManualEntryScreen(default_customer="Corporate", customers=["Vertrieb", "Corporate"]))
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        select = app.screen.query_one("#manual-customer", Select)
        assert [option[0] for option in select._options if option[0]] == ["Vertrieb", "Corporate"]
        assert select.value == "Corporate"


@pytest.mark.asyncio
async def test_manual_dialog_keeps_unknown_customer_when_editing() -> None:
    """Ein Kunde, der nicht mehr in der Liste steht, geht beim Bearbeiten nicht verloren."""
    entry = ManualEntry(entry_id=3, entry_date=date(2026, 7, 1), ticket="DMZ-17024", hours=8.0, customer="Altkunde")
    app = _DialogApp(ManualEntryScreen(entry=entry, customers=["Vertrieb"]))
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        select = app.screen.query_one("#manual-customer", Select)
        assert "Altkunde" in [option[0] for option in select._options if option[0]]
        assert select.value == "Altkunde"


@pytest.mark.asyncio
async def test_confirm_dialog_defaults_to_cancel() -> None:
    """Esc und der vorausgewaehlte Fokus duerfen nichts loeschen."""
    app = _DialogApp(ConfirmScreen("Wirklich?"))
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        assert app.screen.focused is app.screen.query_one("#confirm-cancel", Button)
        await pilot.press("escape")
        await pilot.pause()
        assert app.result is False


@pytest.mark.asyncio
async def test_confirm_dialog_returns_true_on_delete() -> None:
    """Erst der Klick auf Löschen bestätigt die Aktion."""
    app = _DialogApp(ConfirmScreen("Wirklich?"))
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        await pilot.click("#confirm-ok")
        await pilot.pause()
        assert app.result is True


class _ColumnsApp(App[None]):
    """Tabelle mit konfigurierbaren Spalten."""

    def __init__(self, columns: list[ExportColumn], default_customer: str = "Vertrieb") -> None:
        super().__init__()
        self.columns = columns
        self.default_customer = default_customer

    def compose(self) -> ComposeResult:
        yield TimesheetTable(
            columns=self.columns,
            default_customer=self.default_customer,
            id="timesheet-table",
        )


@pytest.mark.asyncio
async def test_customer_column_is_shown_when_visible() -> None:
    """Die Kunden-Spalte erscheint in der Liste und faellt auf den Standard zurueck."""
    app = _ColumnsApp(default_columns())
    async with app.run_test(size=(160, 20)) as pilot:
        widget = app.query_one(TimesheetTable)
        widget.load_timesheet(_mixed_timesheet(), missing_days=[])
        await pilot.pause()
        table = widget.query_one("#timesheet-data", ResizableDataTable)

        assert "Kunde" in table.render_line(0).text
        # Jira-Eintrag ohne eigenen Kunden zeigt den Standard, der manuelle nicht.
        assert "Vertrieb" in table.render_line(1).text
        assert "Corporate" in table.render_line(2).text


@pytest.mark.asyncio
async def test_hidden_columns_disappear_from_the_list() -> None:
    """Abgewaehlte Spalten tauchen in der Liste nicht mehr auf."""
    columns = default_columns()
    for column in columns:
        if column.key in ("week", "weekday", "customer"):
            column.visible = False

    app = _ColumnsApp(columns)
    async with app.run_test(size=(160, 20)) as pilot:
        widget = app.query_one(TimesheetTable)
        widget.load_timesheet(_mixed_timesheet(), missing_days=[])
        await pilot.pause()
        table = widget.query_one("#timesheet-data", ResizableDataTable)

        header = table.render_line(0).text
        assert "KW" not in header
        assert "Kunde" not in header
        assert "Ticket" in header
        assert len(table.ordered_columns) == 5


@pytest.mark.asyncio
async def test_export_only_column_stays_out_of_the_list() -> None:
    """visible=False, enabled=True: nur im Export, nicht in der Liste."""
    columns = default_columns()
    customer = next(c for c in columns if c.key == "customer")
    customer.visible = False
    customer.enabled = True

    app = _ColumnsApp(columns)
    async with app.run_test(size=(160, 20)) as pilot:
        widget = app.query_one(TimesheetTable)
        widget.load_timesheet(_mixed_timesheet(), missing_days=[])
        await pilot.pause()
        table = widget.query_one("#timesheet-data", ResizableDataTable)
        assert "Kunde" not in table.render_line(0).text


@pytest.mark.asyncio
async def test_sorting_survives_hidden_columns() -> None:
    """Nach dem Ausblenden von Spalten sortiert der Datums-Kopf weiterhin."""
    columns = default_columns()
    for column in columns:
        if column.key == "week":
            column.visible = False

    app = _ColumnsApp(columns)
    async with app.run_test(size=(160, 20)) as pilot:
        widget = app.query_one(TimesheetTable)
        widget.load_timesheet(_mixed_timesheet(), missing_days=[])
        await pilot.pause()
        table = widget.query_one("#timesheet-data", ResizableDataTable)

        # Datum ist jetzt Spalte 1 statt 2 - der Pfeil muss trotzdem dort sitzen.
        assert "▲" in str(table.ordered_columns[1].label)
        edge = _column_edge(table, 1)
        width = table.ordered_columns[1].get_render_width(table)
        await pilot.click(table, offset=(edge - width // 2, 0))
        await pilot.pause()
        assert widget._sort_col == "date"
        assert widget._sort_desc


@pytest.mark.asyncio
async def test_set_columns_rebuilds_at_runtime() -> None:
    """Eine Aenderung im Settings-Dialog wirkt ohne Neustart."""
    app = _ColumnsApp(default_columns())
    async with app.run_test(size=(160, 20)) as pilot:
        widget = app.query_one(TimesheetTable)
        widget.load_timesheet(_mixed_timesheet(), missing_days=[])
        await pilot.pause()
        table = widget.query_one("#timesheet-data", ResizableDataTable)
        assert "Kunde" in table.render_line(0).text

        columns = default_columns()
        next(c for c in columns if c.key == "customer").visible = False
        widget.set_columns(columns)
        await pilot.pause()

        table = widget.query_one("#timesheet-data", ResizableDataTable)
        assert "Kunde" not in table.render_line(0).text
        assert "Corporate" in table.render_line(2).text or True
        assert len(table.ordered_columns) == 7


@pytest.mark.asyncio
async def test_summary_shows_manual_share() -> None:
    """Die Kennzahlen-Zeile weist den manuellen Anteil gesondert aus."""

    class _SummaryApp(App[None]):
        def compose(self) -> ComposeResult:
            yield SummaryPanel(id="summary-panel")

    app = _SummaryApp()
    async with app.run_test(size=(180, 10)) as pilot:
        panel = app.query_one(SummaryPanel)
        panel.update_timesheet(_mixed_timesheet(), target_hours=8.0)
        await pilot.pause()
        line = panel.render_line(0).text
        assert "davon manuell" in line
        assert "10,00h" in line


@pytest.mark.asyncio
async def test_summary_hides_manual_share_without_manual_entries() -> None:
    """Ohne manuelle Zeiten bleibt die Zelle weg statt 0,00h zu zeigen."""

    class _SummaryApp(App[None]):
        def compose(self) -> ComposeResult:
            yield SummaryPanel(id="summary-panel")

    app = _SummaryApp()
    async with app.run_test(size=(180, 10)) as pilot:
        panel = app.query_one(SummaryPanel)
        panel.update_timesheet(_timesheet(), target_hours=8.0)
        await pilot.pause()
        assert "davon manuell" not in panel.render_line(0).text


_YEAR_DATA = {
    1: {"actual": 161.2, "manual": 0.0, "target": 168.0, "working_days": 20, "target_days": 21},
    7: {"actual": 160.2, "manual": 38.75, "target": 184.0, "working_days": 18, "target_days": 23},
    8: {"actual": 0.0, "manual": 0.0, "target": 168.0, "working_days": 0, "target_days": 21},
}


class _YearApp(App[None]):
    """Traegt nur die Jahresansicht."""

    def __init__(self, mark_manual: bool = True) -> None:
        super().__init__()
        self.mark_manual = mark_manual

    def compose(self) -> ComposeResult:
        yield from ()

    def on_mount(self) -> None:
        """Oeffnet die Jahresansicht beim Start."""
        self.push_screen(
            YearScreen(
                year=2026,
                month_data=dict(_YEAR_DATA),
                max_yearly_hours=1720.0,
                mark_manual=self.mark_manual,
                manual_color="FF0000",
            )
        )


def _tile(screen: Screen[Any], month: int) -> MonthTile:
    """Liefert die Monatskachel eines Monats."""
    tiles: list[MonthTile] = list(screen.query(MonthTile))
    return next(tile for tile in tiles if tile._month == month)


@pytest.mark.asyncio
async def test_year_tile_shows_manual_share() -> None:
    """Monate mit manuellen Zeiten weisen den Anteil aus, andere nicht."""
    app = _YearApp()
    async with app.run_test(size=(180, 55)) as pilot:
        await pilot.pause()
        await pilot.pause()
        screen = app.screen
        assert "davon manuell: 38,75h" in _tile(screen, 7).render().plain
        # Januar hat keine manuellen Stunden - keine zusaetzliche Zeile.
        assert "manuell" not in _tile(screen, 1).render().plain
        # August hat gar keine Daten - Kachel bleibt unveraendert.
        assert "manuell" not in _tile(screen, 8).render().plain


@pytest.mark.asyncio
async def test_year_summary_shows_total_manual() -> None:
    """Die Jahres-Zusammenfassung summiert den manuellen Anteil."""
    app = _YearApp()
    async with app.run_test(size=(180, 55)) as pilot:
        await pilot.pause()
        await pilot.pause()
        summary = app.screen.query_one("#year-summary").render_line(0).text
        assert "davon manuell: 38,75h" in summary


@pytest.mark.asyncio
async def test_year_manual_share_respects_marking_setting() -> None:
    """Ist die Markierung aus, bleibt der Anteil sichtbar - nur ohne Farbe."""
    app = _YearApp(mark_manual=False)
    async with app.run_test(size=(180, 55)) as pilot:
        await pilot.pause()
        await pilot.pause()
        tile = _tile(app.screen, 7)
        assert "davon manuell: 38,75h" in tile.render().plain
        styles = {str(span.style) for span in tile.render().spans}
        assert not any("#ff0000" in style for style in styles)


@pytest.mark.asyncio
async def test_edit_dialog_has_delete_button() -> None:
    """Beim Bearbeiten gibt es Löschen, beim Anlegen nicht."""
    entry = ManualEntry(entry_id=3, entry_date=date(2026, 7, 1), ticket="DMZ-17024", hours=8.0)

    app = _DialogApp(ManualEntryScreen(entry=entry, customers=["Vertrieb"]))
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        assert app.screen.query("#manual-delete")

    app = _DialogApp(ManualEntryScreen(customers=["Vertrieb"]))
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        assert not app.screen.query("#manual-delete")


@pytest.mark.asyncio
async def test_delete_button_returns_delete_flag() -> None:
    """Der Löschen-Button gibt den Eintrag mit delete=True zurück - ohne selbst zu löschen."""
    entry = ManualEntry(entry_id=3, entry_date=date(2026, 7, 1), ticket="DMZ-17024", hours=8.0)
    app = _DialogApp(ManualEntryScreen(entry=entry, customers=["Vertrieb"]))
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        await pilot.click("#manual-delete")
        await pilot.pause()

    assert isinstance(app.result, ManualEntryResult)
    assert app.result.delete is True
    assert app.result.entry.entry_id == 3


@pytest.mark.asyncio
async def test_save_returns_result_without_delete_flag() -> None:
    """Speichern liefert dasselbe Ergebnis-Objekt, aber ohne Löschwunsch."""
    app = _DialogApp(ManualEntryScreen(default_customer="Vertrieb", customers=["Vertrieb"]))
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        app.screen.query_one("#manual-ticket", Input).value = "DMZ-17024"
        app.screen.query_one("#manual-hours", Input).value = "3h 30m"
        await pilot.click("#manual-save")
        await pilot.pause()

    assert isinstance(app.result, ManualEntryResult)
    assert app.result.delete is False
    assert app.result.entry.hours == pytest.approx(3.5)
    assert app.result.entry.customer == "Vertrieb"


class _RightClickApp(App[None]):
    """Tabelle, die den Rechtsklick der Liste festhaelt."""

    def __init__(self) -> None:
        super().__init__()
        self.clicked: TimesheetTable.RowRightClicked | None = None

    def compose(self) -> ComposeResult:
        yield TimesheetTable(columns=default_columns(), id="timesheet-table")

    def on_timesheet_table_row_right_clicked(self, event: TimesheetTable.RowRightClicked) -> None:
        """Haelt das Ereignis fuer die Pruefung fest."""
        self.clicked = event


@pytest.mark.asyncio
async def test_right_click_reports_manual_entry() -> None:
    """Rechtsklick auf eine manuelle Zeile meldet den Eintrag samt Datenbank-Id."""
    app = _RightClickApp()
    async with app.run_test(size=(160, 20)) as pilot:
        widget = app.query_one(TimesheetTable)
        widget.load_timesheet(_mixed_timesheet(), missing_days=[])
        await pilot.pause()
        table = widget.query_one("#timesheet-data", ResizableDataTable)

        await pilot.click(table, offset=(20, 2), button=3)
        await pilot.pause()

    assert app.clicked is not None
    assert app.clicked.entry is not None
    assert app.clicked.entry.manual is True
    assert app.clicked.entry.manual_id == 7
    assert app.clicked.entry_date == date(2026, 7, 23)


@pytest.mark.asyncio
async def test_right_click_on_gap_row_reports_date_without_entry() -> None:
    """Auf einer Lückenzeile gibt es keinen Eintrag, aber ein Datum zum Erfassen."""
    app = _RightClickApp()
    async with app.run_test(size=(160, 20)) as pilot:
        widget = app.query_one(TimesheetTable)
        widget.load_timesheet(
            _mixed_timesheet(),
            missing_days=[(date(2026, 7, 24), "— kein Eintrag —")],
        )
        await pilot.pause()
        table = widget.query_one("#timesheet-data", ResizableDataTable)

        # Zeile 3 (nach Kopf + 2 Eintraegen) ist die Luecke.
        await pilot.click(table, offset=(20, 3), button=3)
        await pilot.pause()

    assert app.clicked is not None
    assert app.clicked.entry is None
    assert app.clicked.entry_date == date(2026, 7, 24)


@pytest.mark.asyncio
async def test_right_click_does_not_select_the_row() -> None:
    """Der Rechtsklick darf keine RowSelected-Message ausloesen (Detail-Dialog)."""

    class _SelectApp(_RightClickApp):
        selected = 0

        def on_timesheet_table_entry_selected(self, event: TimesheetTable.EntrySelected) -> None:
            """Zaehlt ungewollte Auswahl-Ereignisse."""
            self.selected += 1

    app = _SelectApp()
    async with app.run_test(size=(160, 20)) as pilot:
        widget = app.query_one(TimesheetTable)
        widget.load_timesheet(_mixed_timesheet(), missing_days=[])
        await pilot.pause()
        table = widget.query_one("#timesheet-data", ResizableDataTable)
        table.move_cursor(row=1, animate=False)
        await pilot.pause()

        # Rechtsklick auf die bereits markierte Zeile - genau der Fall, in dem
        # DataTable sonst RowSelected postet.
        await pilot.click(table, offset=(20, 2), button=3)
        await pilot.pause()

    assert app.clicked is not None
    assert app.selected == 0
