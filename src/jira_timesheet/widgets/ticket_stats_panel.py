"""Auswertung ueber der Ticket-Liste, als Balken aus Blockzeichen.

Drei Fragen, drei Zeilen: waechst der Bestand oder schrumpft er (Zulauf
gegen Abgang), wie steht er kumuliert, und wie alt ist das Offene.

Warum Blockzeichen und kein Diagramm: im Terminal ist eine Zeile aus
Achtelbloecken sofort lesbar, braucht keine Grafikbibliothek und bleibt in
jedem Terminal gleich. Die genauen Zahlen stehen daneben - die Balken
zeigen den Verlauf, nicht den Wert.
"""

from __future__ import annotations

from typing import Any

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Collapsible, Static

from jira_timesheet.i18n import format_number, t
from jira_timesheet.services.ticket_board import Statistics

# Achtelbloecke von leer bis voll. Das erste Zeichen ist ein Leerzeichen:
# ein echter Nullwert soll leer bleiben und nicht wie ein kleiner Wert
# aussehen.
_BLOCKS = " ▁▂▃▄▅▆▇█"

# Breite der Balken in der Altersverteilung, in Zeichen.
_BAR_WIDTH = 24

# Beschriftungsbreite, damit die Zeilen untereinander fluchten. Muss die
# laengste Beschriftung fassen ("Bestand kumuliert"), sonst schiebt genau
# diese Zeile ihre Balken aus der Flucht.
_LABEL_WIDTH = 19


def sparkline(values: list[float], scale: float | None = None) -> str:
    """Baut eine Zeile aus Achtelbloecken.

    Args:
        values:
            Die Werte in zeitlicher Reihenfolge.
        scale:
            Bezugswert fuer die volle Hoehe. None nimmt das Maximum der
            eigenen Reihe. Zwei Reihen, die verglichen werden sollen,
            MUESSEN denselben Bezugswert bekommen - sonst sehen ein Zulauf
            von drei und ein Abgang von dreissig gleich hoch aus.

    Returns:
        Eine Zeichenkette mit einem Zeichen je Wert.
    """
    if not values:
        return ""
    top = scale if scale is not None else max(values)
    if top <= 0:
        return " " * len(values)
    result = []
    for value in values:
        share = max(0.0, min(1.0, value / top))
        index = 0 if value <= 0 else max(1, round(share * (len(_BLOCKS) - 1)))
        result.append(_BLOCKS[index])
    return "".join(result)


def bar(value: int, top: int, width: int = _BAR_WIDTH) -> str:
    """Baut einen waagerechten Balken fester Breite."""
    if top <= 0 or value <= 0:
        return ""
    filled = max(1, round(width * value / top))
    return "█" * filled


class TicketStatsPanel(Vertical):
    """Zeigt die Auswertung des Kerns als Textbalken."""

    class Requested(Message):
        """Der Bereich wurde aufgeklappt und hat noch keine Zahlen.

        Der Host holt daraufhin die Historie. Das Widget selbst kennt weder
        Jira noch die Einstellungen.
        """

    DEFAULT_CSS = """
    TicketStatsPanel {
        height: auto;
        max-height: 16;
    }

    TicketStatsPanel Collapsible {
        height: auto;
        border-top: solid $panel;
    }

    TicketStatsPanel Static {
        height: auto;
    }

    TicketStatsPanel .stats-footnote {
        color: $text-muted;
    }
    """

    def __init__(self, mode: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._mode = mode
        self._stats: Statistics | None = None

    def compose(self) -> ComposeResult:
        """Balken und Fussnote in einem zuklappbaren Bereich.

        Zugeklappt als Vorgabe, aus zwei Gruenden: die Auswertung kostet im
        Terminal elf Zeilen, die der Tabelle darueber fehlen - und sie kostet
        einen eigenen Abruf ueber die gesamte Ticket-Historie. Ein Abruf, den
        niemand sehen will, muss auch nicht laufen. Geholt wird deshalb erst
        beim Aufklappen.
        """
        with Collapsible(title=t("board.stats.title"), collapsed=True):
            yield Static("", id=f"stats-body-{self._mode}")
            yield Static(t("board.stats.footnote"), classes="stats-footnote")

    def on_collapsible_toggled(self, event: Collapsible.Toggled) -> None:
        """Fordert die Zahlen an, sobald der Bereich zum ersten Mal aufgeht."""
        event.stop()
        if not event.collapsible.collapsed and self._stats is None:
            self.post_message(self.Requested())

    def set_statistics(self, stats: Statistics | None) -> None:
        """Uebernimmt die Auswertung und zeichnet sie neu."""
        self._stats = stats
        self._refresh()

    def show_message(self, message: str) -> None:
        """Zeigt einen Zwischenstand statt der Balken."""
        self._stats = None
        self._write(Text(message, style="dim"))

    def _write(self, content: Text) -> None:
        """Schreibt in den Hauptbereich."""
        try:
            self.query_one(f"#stats-body-{self._mode}", Static).update(content)
        except Exception:
            return

    def _refresh(self) -> None:
        """Baut die Darstellung aus der gespeicherten Auswertung."""
        stats = self._stats
        if stats is None:
            self._write(Text(""))
            return
        self._write(self.render_text(stats))

    @staticmethod
    def render_text(stats: Statistics) -> Text:
        """Setzt die vollstaendige Darstellung zusammen.

        Bewusst eine reine Funktion auf dem Ergebnis des Kerns: so laesst
        sich die Darstellung ohne laufende Oberflaeche pruefen.

        Args:
            stats:
                Die Auswertung.

        Returns:
            Der fertige Text mit Kopfzeile, drei Reihen und der
            Altersverteilung.
        """
        text = Text()
        text.append(f"{stats.open_count} {t('board.stats.open')}", style="bold")
        text.append(f" · {stats.resolved_recent} {t('board.stats.resolved_recent')}")
        median = t("board.stats.workdays", value=format_number(stats.lead_time_median, decimals=0))
        text.append(f" · {t('board.stats.lead_time')} {median}\n\n")

        months = stats.months
        if months:
            # Zulauf und Abgang teilen sich den Bezugswert - nur so laesst
            # sich aus den beiden Zeilen ablesen, welcher groesser war.
            inflow = [float(m.inflow) for m in months]
            outflow = [float(m.outflow) for m in months]
            top = max([*inflow, *outflow, 1.0])
            span = f"{months[0].month} - {months[-1].month}"
            text.append(f"{t('board.stats.flow')}  ", style="bold")
            text.append(f"{span}\n", style="dim")
            text.append(f"  {'+':<{_LABEL_WIDTH}}{sparkline(inflow, top)}  {stats.inflow_total}\n")
            text.append(f"  {'-':<{_LABEL_WIDTH}}{sparkline(outflow, top)}  {stats.outflow_total}\n")
            cumulative = [float(m.cumulative) for m in months]
            text.append(f"  {t('board.stats.cumulative'):<{_LABEL_WIDTH}}")
            text.append(f"{sparkline(cumulative)}  {months[-1].cumulative}\n")

        buckets = stats.buckets
        if buckets:
            text.append(f"\n{t('board.stats.ages')}\n", style="bold")
            top_count = max([b.count for b in buckets] + [1])
            for bucket in buckets:
                text.append(f"  {bucket.label:<{_LABEL_WIDTH}}")
                text.append(bar(bucket.count, top_count))
                text.append(f" {bucket.count}\n")

        return text
