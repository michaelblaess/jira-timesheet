"""DataTable mit ziehbaren Spaltenbreiten und einer Flex-Spalte.

Textuals DataTable kennt keine Maus-Interaktion fuer Spaltenbreiten. Diese
Ableitung ergaenzt sie: auf der Trennlinie zwischen zwei Spaltenkoepfen laesst
sich die linke Spalte per Drag breiter oder schmaler ziehen, ein Doppelklick
auf dieselbe Stelle setzt die Spalte auf Auto-Breite zurueck.

Zusaetzlich kann eine Spalte als Flex-Spalte markiert werden - sie fuellt dann
die restliche Tabellenbreite, bis der Benutzer sie selbst zieht.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from textual import events
from textual.geometry import Size
from textual.message import Message
from textual.widgets import DataTable
from textual.widgets.data_table import ColumnKey, RowKey


class ResizableDataTable(DataTable[Any]):
    """DataTable, deren Spaltenbreiten mit der Maus verstellt werden koennen."""

    # Toleranz um die Trennlinie herum, in Zellen. 1 deckt die rechte Polsterung
    # der linken und die linke Polsterung der rechten Spalte ab.
    GRIP_WIDTH = 1
    # Kleinste per Drag erreichbare Spaltenbreite (ohne Polsterung).
    MIN_COLUMN_WIDTH = 3

    class RightClicked(Message):
        """Rechtsklick auf eine Zeile - der Host oeffnet das Kontextmenue.

        ``row_index`` ist -1, wenn der Klick den Spaltenkopf getroffen hat.
        """

        def __init__(self, screen_x: int, screen_y: int, row_index: int) -> None:
            super().__init__()
            self.screen_x = screen_x
            self.screen_y = screen_y
            self.row_index = row_index

    class ColumnResized(Message):
        """Wird gesendet wenn eine Spaltenbreite per Maus geaendert wurde.

        Der Host entscheidet, ob er die Breite persistiert - das Widget selbst
        kennt keine Settings.
        """

        def __init__(self, column_key: ColumnKey, width: int | None) -> None:
            super().__init__()
            self.column_key = column_key
            # None bedeutet: zurueck auf Auto-Breite.
            self.width = width

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Index der Spalte, die gerade gezogen wird (None = kein Drag).
        self._resize_index: int | None = None
        self._resize_start_x: int = 0
        self._resize_start_width: int = 0
        # Spalte, auf deren Trennlinie der letzte Mausklick lag - fuer den
        # Doppelklick-Reset, der erst beim Click-Event ausgewertet wird.
        self._grip_index: int | None = None
        # Spalten, deren Breite der Benutzer selbst gesetzt hat. Der Host kann
        # damit Auto-Layouts unterdruecken, sobald manuell gezogen wurde.
        self._pinned: set[ColumnKey] = set()
        # Spalte, die den Rest der Tabellenbreite fuellt.
        self._flex_key: ColumnKey | None = None
        self._flex_min_width: int = 10

    # --- Public API -------------------------------------------------

    def is_column_pinned(self, column_key: ColumnKey) -> bool:
        """Gibt True zurueck wenn die Spaltenbreite manuell gesetzt wurde."""
        return column_key in self._pinned

    def set_flex_column(self, column_key: ColumnKey, min_width: int = 10) -> None:
        """Legt fest, welche Spalte die restliche Tabellenbreite fuellt.

        Sobald der Benutzer diese Spalte selbst zieht, gilt seine Breite und
        die automatische Anpassung entfaellt.
        """
        self._flex_key = column_key
        self._flex_min_width = min_width
        self._refresh_widths()

    def set_column_width(self, column_key: ColumnKey, width: int, *, pin: bool = True) -> None:
        """Setzt eine feste Spaltenbreite (ohne Polsterung).

        pin=True markiert die Spalte als manuell gesetzt; automatische
        Layout-Anpassungen des Hosts sollen sie dann in Ruhe lassen.
        """
        column = self.columns.get(column_key)
        if column is None:
            return
        column.auto_width = False
        column.width = max(self.MIN_COLUMN_WIDTH, width)
        if pin:
            self._pinned.add(column_key)
        self._refresh_widths()

    def reset_column_width(self, column_key: ColumnKey) -> None:
        """Setzt eine Spalte zurueck auf Auto-Breite (Inhaltsbreite)."""
        column = self.columns.get(column_key)
        if column is None:
            return
        column.auto_width = True
        self._pinned.discard(column_key)
        self._refresh_widths()

    # --- Maus-Interaktion -------------------------------------------

    async def _on_mouse_down(self, event: events.MouseDown) -> None:
        """Startet den Drag, wenn der Klick auf einer Trennlinie im Kopf liegt."""
        index = self._grip_at(event)
        self._grip_index = index
        if index is None:
            return
        column = self.ordered_columns[index]
        self._resize_index = index
        self._resize_start_x = event.screen_x
        self._resize_start_width = column.get_render_width(self) - 2 * self.cell_padding
        self.capture_mouse()
        event.stop()
        event.prevent_default()

    def _on_mouse_move(self, event: events.MouseMove) -> None:
        """Verstellt die Breite waehrend des Drags."""
        if self._resize_index is None:
            return
        column = self.ordered_columns[self._resize_index]
        delta = event.screen_x - self._resize_start_x
        width = max(self.MIN_COLUMN_WIDTH, self._resize_start_width + delta)
        if column.auto_width or column.width != width:
            column.auto_width = False
            column.width = width
            self._pinned.add(column.key)
            self._refresh_widths()
        event.stop()
        event.prevent_default()

    async def _on_mouse_up(self, event: events.MouseUp) -> None:
        """Beendet den Drag und meldet die neue Breite."""
        if self._resize_index is None:
            return
        column = self.ordered_columns[self._resize_index]
        self._resize_index = None
        self.release_mouse()
        self.post_message(self.ColumnResized(column.key, column.width))
        event.stop()
        event.prevent_default()

    async def _on_click(self, event: events.Click) -> None:
        """Faengt Rechtsklicks und den Klick ab, der auf einen Drag folgt.

        Rechtsklick meldet ``RightClicked`` und wird NICHT an die Basisklasse
        durchgereicht: deren ``_on_click`` verschiebt sonst den Cursor und
        postet ``RowSelected``, was den Detail-Dialog ueber das Kontextmenue
        legen wuerde.

        Ohne das Abfangen des Drag-Klicks wuerde jeder Resize zusaetzlich die
        Sortierung umschalten. Ein Doppelklick auf die Trennlinie setzt die
        Spalte auf Auto-Breite.
        """
        if event.button == 3:
            meta = event.style.meta if event.style else {}
            row_index = meta.get("row", -1)
            if isinstance(row_index, int):
                event.stop()
                event.prevent_default()
                self.post_message(self.RightClicked(event.screen_x, event.screen_y, row_index))
                return

        index = self._grip_index
        if index is None:
            return
        self._grip_index = None
        if event.chain >= 2 and index < len(self.ordered_columns):
            column = self.ordered_columns[index]
            self.reset_column_width(column.key)
            self.post_message(self.ColumnResized(column.key, None))
        event.stop()
        event.prevent_default()

    # --- Flex-Spalte ------------------------------------------------

    def _update_dimensions(self, new_rows: Iterable[RowKey]) -> None:
        """Nach jeder Breitenberechnung die Flex-Spalte nachziehen."""
        super()._update_dimensions(new_rows)
        if self._apply_flex_column():
            self._recompute_virtual_size()

    def _on_resize(self, event: events.Resize) -> None:
        """Bei geaenderter Tabellenbreite die Flex-Spalte nachziehen."""
        if self._apply_flex_column():
            self._recompute_virtual_size()

    def _apply_flex_column(self) -> bool:
        """Gibt der Flex-Spalte die Breite, die die anderen Spalten uebrig lassen.

        Gibt True zurueck wenn sich die Breite dadurch geaendert hat.
        """
        key = self._flex_key
        if key is None or key in self._pinned:
            return False
        column = self.columns.get(key)
        if column is None:
            return False
        available = self.scrollable_content_region.width
        if available <= 0:
            return False
        others = sum(other.get_render_width(self) for other_key, other in self.columns.items() if other_key != key)
        width = max(self._flex_min_width, available - others - 2 * self.cell_padding)
        if not column.auto_width and column.width == width:
            return False
        column.auto_width = False
        column.width = width
        return True

    # --- Interna ----------------------------------------------------

    def _grip_at(self, event: events.MouseEvent) -> int | None:
        """Index der Spalte, deren rechte Trennlinie unter der Maus liegt.

        Gibt None zurueck wenn die Maus nicht im Spaltenkopf oder nicht nahe
        genug an einer Trennlinie ist.
        """
        if not self.show_header:
            return None
        content_y = event.y - self.gutter.top
        if not 0 <= content_y < self.header_height:
            return None
        content_x = event.x - self.gutter.left + self.scroll_offset.x
        edge = self._row_label_column_width
        for index, column in enumerate(self.ordered_columns):
            edge += column.get_render_width(self)
            if abs(content_x - edge) <= self.GRIP_WIDTH:
                return index
        return None

    def _refresh_widths(self) -> None:
        """Uebernimmt geaenderte Spaltenbreiten und zieht die Flex-Spalte nach."""
        self._apply_flex_column()
        self._recompute_virtual_size()

    def _recompute_virtual_size(self) -> None:
        """Verwirft die Render-Caches und rechnet die virtuelle Groesse neu.

        Billiger als _update_dimensions(), das alle Zellen neu vermessen wuerde -
        beim Ziehen faellt das pro Mausbewegung an.
        """
        self._clear_caches()
        self._update_count += 1
        data_width = sum(column.get_render_width(self) for column in self.columns.values())
        header_height = self.header_height if self.show_header else 0
        self.virtual_size = Size(
            data_width + self._row_label_column_width,
            self._total_row_height + header_height,
        )
        self.refresh()
