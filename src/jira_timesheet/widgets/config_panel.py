"""Eingabebereich fuer Jira-Konfiguration und Zeitraum."""
from __future__ import annotations

from datetime import date

from rich.text import Text
from textual.app import ComposeResult, RenderResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Static

from jira_timesheet.models.settings import Settings


class ConfigPanel(Vertical):
    """Kompakter Eingabebereich mit Token, E-Mail und Zeitraum."""

    DEFAULT_CSS = """
    ConfigPanel {
        height: auto;
        padding: 0 1;
        background: $surface;
        border: solid $accent;
    }

    ConfigPanel .config-label {
        width: 14;
        color: $text-muted;
    }

    ConfigPanel .config-row {
        height: 1;
        layout: horizontal;
    }

    ConfigPanel .config-value {
        color: $text;
    }

    ConfigPanel #date-range {
        color: $text;
    }

    ConfigPanel .nav-hint {
        color: $text-muted;
    }
    """

    class MonthChanged(Message):
        """Wird gesendet wenn der Monat gewechselt wird."""

        def __init__(self, date_from: date, date_to: date) -> None:
            super().__init__()
            self.date_from = date_from
            self.date_to = date_to

    def __init__(self, settings: Settings, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._settings = settings

        if settings.last_date_from and settings.last_date_to:
            try:
                self._date_from = date.fromisoformat(settings.last_date_from)
                self._date_to = date.fromisoformat(settings.last_date_to)
            except ValueError:
                self._date_from, self._date_to = self._current_month()
        else:
            self._date_from, self._date_to = self._current_month()

    @property
    def date_from(self) -> date:
        """Aktuelles Von-Datum."""
        return self._date_from

    @property
    def date_to(self) -> date:
        """Aktuelles Bis-Datum."""
        return self._date_to

    def compose(self) -> ComposeResult:
        """Erstellt das Layout."""
        token_display = "●" * 20 if self._settings.jira_token else "[nicht gesetzt]"
        host_display = self._settings.jira_host or "[nicht gesetzt]"
        email_display = self._settings.email or "[nicht gesetzt]"

        with Horizontal(classes="config-row"):
            yield Static("  Jira Host:   ", classes="config-label")
            yield Static(host_display, classes="config-value")

        with Horizontal(classes="config-row"):
            yield Static("  Token:       ", classes="config-label")
            yield Static(token_display, classes="config-value", id="token-display")

        with Horizontal(classes="config-row"):
            yield Static("  Entwickler:  ", classes="config-label")
            yield Static(email_display, classes="config-value")

        with Horizontal(classes="config-row"):
            yield Static("  Zeitraum:    ", classes="config-label")
            yield Static(self._format_date_range(), id="date-range")
            yield Static("   [◄] Prev  [►] Next", classes="nav-hint")

    def prev_month(self) -> None:
        """Wechselt zum vorherigen Monat."""
        first_day = self._date_from.replace(day=1)
        prev_last = first_day - __import__("datetime").timedelta(days=1)
        self._date_from = prev_last.replace(day=1)
        self._date_to = prev_last
        self._update_display()

    def next_month(self) -> None:
        """Wechselt zum naechsten Monat."""
        if self._date_to.month == 12:
            next_first = self._date_to.replace(year=self._date_to.year + 1, month=1, day=1)
        else:
            next_first = self._date_to.replace(month=self._date_to.month + 1, day=1)

        if next_first.month == 12:
            next_last = next_first.replace(day=31)
        else:
            next_last = next_first.replace(month=next_first.month + 1, day=1) - __import__("datetime").timedelta(days=1)

        self._date_from = next_first
        self._date_to = next_last
        self._update_display()

    def refresh_display(self) -> None:
        """Aktualisiert die Anzeige nach Settings-Aenderung."""
        try:
            token_widget = self.query_one("#token-display", Static)
            token_display = "●" * 20 if self._settings.jira_token else "[nicht gesetzt]"
            token_widget.update(token_display)
        except Exception:
            pass

    def _update_display(self) -> None:
        """Aktualisiert die Datumsanzeige und sendet Message."""
        try:
            date_widget = self.query_one("#date-range", Static)
            date_widget.update(self._format_date_range())
        except Exception:
            pass
        self.post_message(self.MonthChanged(self._date_from, self._date_to))

    def _format_date_range(self) -> str:
        """Formatiert den Zeitraum fuer die Anzeige."""
        return f"{self._date_from:%d.%m.%Y} — {self._date_to:%d.%m.%Y}"

    @staticmethod
    def _current_month() -> tuple[date, date]:
        """Gibt Anfang und Ende des aktuellen Monats zurueck."""
        today = date.today()
        first = today.replace(day=1)
        if today.month == 12:
            last = today.replace(day=31)
        else:
            last = today.replace(month=today.month + 1, day=1) - __import__("datetime").timedelta(days=1)
        return first, last
