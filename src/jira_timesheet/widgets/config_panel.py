"""Konfigurations-Header mit Host/Token/Entwickler/Zeitraum."""

from __future__ import annotations

from datetime import date, timedelta

from textual.message import Message
from textual_widgets import InfoHeader, InfoItem

from jira_timesheet.i18n import t
from jira_timesheet.models.settings import Settings

_TOKEN_MASK = "●" * 20


class ConfigPanel(InfoHeader):  # type: ignore[misc]
    """Info-Header mit Jira-Konfiguration und Zeitraum-Navigation.

    Klick auf die Pfeile am Zeitraum sendet ``MonthChanged``, ebenso ein
    Aufruf von :meth:`prev_month` / :meth:`next_month`. Die App fängt die
    Message ab und löst den Worklog-Abruf aus.
    """

    # InfoHeader-Default hat .info-cell / .info-nav als width: 1fr. Bei
    # columns=1 dehnt das den Wert + die Navigations-Pfeile über die volle
    # Panel-Breite. Hier auf "auto" zwingen, damit Werte links direkt nach
    # dem Label stehen und die Pfeile am Wert kleben.
    DEFAULT_CSS = """
    ConfigPanel .info-cell {
        width: auto;
    }
    ConfigPanel .info-value {
        width: auto;
    }
    ConfigPanel .info-nav {
        width: auto;
    }
    ConfigPanel .info-nav-value {
        width: auto;
        padding: 0 1;
    }
    """

    class MonthChanged(Message):
        """Wird gesendet, wenn sich der Zeitraum ändert."""

        def __init__(self, date_from: date, date_to: date) -> None:
            super().__init__()
            self.date_from = date_from
            self.date_to = date_to

    def __init__(self, settings: Settings, **kwargs: object) -> None:
        self._settings = settings

        if settings.last_date_from and settings.last_date_to:
            try:
                self._date_from = date.fromisoformat(settings.last_date_from)
                self._date_to = date.fromisoformat(settings.last_date_to)
            except ValueError:
                self._date_from, self._date_to = self._current_month()
        else:
            self._date_from, self._date_to = self._current_month()

        items = [
            InfoItem(
                key="host",
                label=t("config.host"),
                value=self._format_host(),
                markup=True,
            ),
            InfoItem(key="token", label=t("config.token"), value=self._format_token()),
            InfoItem(key="developer", label=t("config.developer"), value=self._format_email()),
            InfoItem(
                key="period",
                label=t("config.period"),
                value=self._format_date_range(),
                navigable=True,
            ),
        ]
        super().__init__(
            items,
            columns=1,
            label_width=14,
            title=t("config.title"),
            collapsible=True,
            collapsed=bool(settings.config_collapsed),
            **kwargs,
        )

    # --- Public API -------------------------------------------------

    @property
    def date_from(self) -> date:
        """Aktuelles Von-Datum."""
        return self._date_from

    @property
    def date_to(self) -> date:
        """Aktuelles Bis-Datum."""
        return self._date_to

    def prev_month(self) -> None:
        """Wechselt zum vorherigen Monat und postet ``MonthChanged``."""
        first_day = self._date_from.replace(day=1)
        prev_last = first_day - timedelta(days=1)
        self._date_from = prev_last.replace(day=1)
        self._date_to = prev_last
        self._after_month_change()

    def next_month(self) -> None:
        """Wechselt zum nächsten Monat und postet ``MonthChanged``."""
        if self._date_to.month == 12:
            next_first = self._date_to.replace(year=self._date_to.year + 1, month=1, day=1)
        else:
            next_first = self._date_to.replace(month=self._date_to.month + 1, day=1)

        if next_first.month == 12:
            next_last = next_first.replace(day=31)
        else:
            next_last = next_first.replace(month=next_first.month + 1, day=1) - timedelta(days=1)

        self._date_from = next_first
        self._date_to = next_last
        self._after_month_change()

    def refresh_display(self) -> None:
        """Aktualisiert Host/Token/Entwickler nach einer Settings-Änderung."""
        self.set_value("host", self._format_host())
        self.set_value("token", self._format_token())
        self.set_value("developer", self._format_email())

    def on_mount(self) -> None:
        """Setzt den Host-Wert erneut, damit der Link-Markup greift."""
        super().on_mount()
        self.set_value("host", self._format_host())

    def watch_collapsed(self, collapsed: bool) -> None:
        """Persistiert den Collapsed-Zustand."""
        super().watch_collapsed(collapsed)
        if self._settings.config_collapsed == collapsed:
            return
        self._settings.config_collapsed = collapsed
        self._settings.save()

    # --- InfoHeader-Hooks -------------------------------------------

    def on_info_header_navigated(self, event: InfoHeader.Navigated) -> None:
        """Reagiert auf Klick auf die Zeitraum-Pfeile."""
        if event.key != "period":
            return
        event.stop()
        if event.direction == "prev":
            self.prev_month()
        else:
            self.next_month()

    # --- intern ------------------------------------------------------

    def _after_month_change(self) -> None:
        """Aktualisiert die Anzeige und postet ``MonthChanged``."""
        self.set_value("period", self._format_date_range())
        self.post_message(self.MonthChanged(self._date_from, self._date_to))

    def _format_host(self) -> str:
        host = self._settings.jira_host
        if not host:
            # markup=True ist gesetzt → eckige Klammern müssen escaped werden.
            return t("common.not_set").replace("[", r"\[")
        # Klickbarer Link über ClickableLinksMixin der App, sobald gemountet.
        # Während __init__ ist self.app noch nicht erreichbar — dann plain.
        try:
            return self.app.link_markup(host, host)  # type: ignore[attr-defined]
        except Exception:
            return host

    def _format_token(self) -> str:
        return _TOKEN_MASK if self._settings.jira_token else t("common.not_set")

    def _format_email(self) -> str:
        return self._settings.email or t("common.not_set")

    def _format_date_range(self) -> str:
        return f"{self._date_from:%d.%m.%Y} — {self._date_to:%d.%m.%Y}"

    @staticmethod
    def _current_month() -> tuple[date, date]:
        today = date.today()
        first = today.replace(day=1)
        if today.month == 12:
            last = today.replace(day=31)
        else:
            last = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        return first, last
