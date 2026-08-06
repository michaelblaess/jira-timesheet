"""Auswertung ueber der Ticket-Liste: zwei Diagramme im Terminal.

Waechst der Bestand oder schrumpft er (Zulauf gegen Abgang je Monat), und
wie alt ist das Offene (Altersverteilung).

Gezeichnet wird mit plotext ueber das Widget aus textual-plotext - beide
MIT-lizenziert und damit vertraeglich mit Apache 2.0. Der erste Entwurf kam
mit selbstgebauten Achtelbloecken aus: zwoelf Monate auf zwoelf Zeichen
ergaben aber keinen erkennbaren Verlauf, sondern ein Muster. Ein Diagramm
mit Achse, Beschriftung und Legende sagt hier schlicht mehr.

Warum nur zwei und nicht drei wie in der Qt-Fassung: bei 150 Zeichen Breite
blieben je Diagramm 50 - zu wenig fuer zwoelf Monatsbalken, und das dritte
rutschte aus dem Bild. Der kumulierte Bestand ist ohnehin dieselbe Aussage
wie Zulauf gegen Abgang; seine Kernzahl, der Saldo, steht jetzt in der
Kennzahlenzeile darueber.
"""

from __future__ import annotations

from typing import Any

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Collapsible, Static
from textual_plotext import PlotextPlot

from jira_timesheet.i18n import format_number, t
from jira_timesheet.services.ticket_board import Statistics

# Farben der beiden Reihen, an der Qt-Fassung ausgerichtet: Zulauf gedaempft
# gruen, Abgang orange. plotext nimmt Namen aus seiner eigenen Palette.
_COLOR_INFLOW = "green"
_COLOR_OUTFLOW = "orange"

# Hoehe des aufgeklappten Bereichs in Zeilen. Mehr nimmt der Tabelle zu viel,
# weniger macht die Achsenbeschriftung unleserlich.
_PLOT_HEIGHT = 15


class TicketStatsPanel(Vertical):
    """Zeigt die Auswertung des Kerns als Diagramme."""

    class Requested(Message):
        """Der Bereich wurde aufgeklappt und hat noch keine Zahlen.

        Der Host holt daraufhin die Historie. Das Widget selbst kennt weder
        Jira noch die Einstellungen.
        """

    DEFAULT_CSS = f"""
    TicketStatsPanel {{
        height: auto;
    }}

    TicketStatsPanel Collapsible {{
        height: auto;
        border-top: solid $panel;
    }}

    TicketStatsPanel .stats-charts {{
        height: {_PLOT_HEIGHT};
    }}

    TicketStatsPanel PlotextPlot {{
        width: 1fr;
    }}

    /* Die Monatsreihe traegt zwoelf Balkenpaare und braucht deshalb den
       doppelten Anteil der Altersverteilung mit ihren vier Balken. Als
       Klasse und nicht als Id: das CSS gehoert der Klasse, die Kennung
       traegt aber den erst im Konstruktor bekannten Ansichtsnamen. */
    TicketStatsPanel .stats-flow {{
        width: 2fr;
    }}

    TicketStatsPanel Static {{
        height: auto;
    }}

    TicketStatsPanel .stats-footnote {{
        color: $text-muted;
    }}
    """

    def __init__(self, mode: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._mode = mode
        self._stats: Statistics | None = None

    def compose(self) -> ComposeResult:
        """Kennzahlen, drei Diagramme und die Fussnote, alles zuklappbar.

        Zugeklappt als Vorgabe, aus zwei Gruenden: die Auswertung kostet im
        Terminal fuenfzehn Zeilen, die der Tabelle darueber fehlen - und sie
        kostet einen eigenen Abruf ueber die gesamte Ticket-Historie. Ein
        Abruf, den niemand sehen will, muss auch nicht laufen. Geholt wird
        deshalb erst beim Aufklappen.
        """
        with Collapsible(title=t("board.stats.title"), collapsed=True):
            yield Static("", id=f"stats-head-{self._mode}")
            with Horizontal(classes="stats-charts", id=f"stats-charts-{self._mode}"):
                yield PlotextPlot(id=f"stats-flow-{self._mode}", classes="stats-flow")
                yield PlotextPlot(id=f"stats-age-{self._mode}")
            yield Static(t("board.stats.footnote"), classes="stats-footnote")

    def on_collapsible_expanded(self, event: Collapsible.Expanded) -> None:
        """Fordert die Zahlen an, sobald der Bereich zum ersten Mal aufgeht.

        NICHT ``on_collapsible_toggled``: Textual postet ausschliesslich die
        Unterklassen ``Expanded`` und ``Collapsed``. Ein Handler auf die
        gemeinsame Oberklasse ``Toggled`` wird nie gerufen - der Bereich ging
        auf und blieb leer (belegt am 06.08.2026, textual 8.2.8,
        _collapsible.py:218).
        """
        event.stop()
        if self._stats is None:
            self.post_message(self.Requested())

    # --- Fuellen --------------------------------------------------------

    @property
    def statistics(self) -> Statistics | None:
        """Die zuletzt gesetzte Auswertung, oder None."""
        return self._stats

    def set_statistics(self, stats: Statistics | None) -> None:
        """Uebernimmt die Auswertung und zeichnet sie neu."""
        self._stats = stats
        if stats is None:
            self._write_head(Text(""))
            return
        self._write_head(self.head_text(stats))
        self._draw(stats)

    def show_message(self, message: str) -> None:
        """Zeigt einen Zwischenstand statt der Diagramme."""
        self._stats = None
        self._write_head(Text(message, style="dim"))

    def _write_head(self, content: Text) -> None:
        """Schreibt die Kennzahlenzeile ueber den Diagrammen."""
        try:
            self.query_one(f"#stats-head-{self._mode}", Static).update(content)
        except Exception:
            return

    @staticmethod
    def head_text(stats: Statistics) -> Text:
        """Baut die Kennzahlenzeile.

        Bewusst eine reine Funktion auf dem Ergebnis des Kerns: so laesst
        sich der Text ohne laufende Oberflaeche pruefen.
        """
        text = Text()
        text.append(f"{stats.open_count} {t('board.stats.open')}", style="bold")
        text.append(f" · {stats.resolved_recent} {t('board.stats.resolved_recent')}")
        median = t("board.stats.workdays", value=format_number(stats.lead_time_median, decimals=0))
        text.append(f" · {t('board.stats.lead_time')} {median}")
        if stats.months:
            saldo = stats.balance_total
            text.append(f" · {stats.inflow_total} / {stats.outflow_total}")
            text.append(
                f" ({saldo:+d})",
                style="bold red" if saldo > 0 else "bold green",
            )
        return text

    def _draw(self, stats: Statistics) -> None:
        """Zeichnet die drei Diagramme neu."""
        try:
            flow = self.query_one(f"#stats-flow-{self._mode}", PlotextPlot)
            ages = self.query_one(f"#stats-age-{self._mode}", PlotextPlot)
        except Exception:
            # Vor dem Einhaengen gibt es noch keine Diagramme - die Zahlen
            # sind gespeichert und werden beim naechsten Aufbau gezeichnet.
            return

        # Kurze Monatsbezeichnung: "2026-08" braucht auf der Achse zu viel
        # Platz, bei zwoelf Monaten ueberlappen die Beschriftungen sonst.
        labels = [month.month[2:] for month in stats.months]

        flow.plt.clear_figure()
        if stats.months:
            # Die Typangaben von textual-plotext widersprechen dem eigenen
            # Code: inspect.signature zeigt "labels" und eine Farbe je Reihe,
            # die Annotation behauptet "label" und eine einzelne Farbe. Die
            # Laufzeit gibt dem Aufruf hier recht - der Test prueft die
            # Legende am gebauten Diagramm.
            flow.plt.multiple_bar(  # type: ignore[call-arg]
                labels,
                [[m.inflow for m in stats.months], [m.outflow for m in stats.months]],
                labels=[t("board.stats.inflow"), t("board.stats.outflow")],
                color=[_COLOR_INFLOW, _COLOR_OUTFLOW],  # type: ignore[arg-type]
            )
        flow.plt.title(t("board.stats.flow"))
        flow.refresh()

        ages.plt.clear_figure()
        if stats.buckets:
            ages.plt.bar(
                [bucket.label for bucket in stats.buckets],
                [bucket.count for bucket in stats.buckets],
                orientation="horizontal",
            )
        ages.plt.title(t("board.stats.ages"))
        ages.refresh()
