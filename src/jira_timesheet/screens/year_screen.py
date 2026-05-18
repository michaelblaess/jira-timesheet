"""Jahresansicht als Modal-Screen mit 12 Monatskacheln."""

from __future__ import annotations

from datetime import date

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, Static

from jira_timesheet.i18n import t

_QUARTER_NAMES = ["Q1", "Q2", "Q3", "Q4"]


class MonthTile(Widget):
    """Einzelne Monatskachel."""

    DEFAULT_CSS = """
    MonthTile {
        width: 1fr;
        height: 100%;
        min-height: 6;
        padding: 0 1;
        border: solid $surface-lighten-2;
    }

    MonthTile.current {
        border: solid $accent;
    }
    """

    def __init__(
        self,
        month: int,
        year: int,
        actual_hours: float = 0.0,
        target_hours: float = 0.0,
        working_days: int = 0,
        target_days: int = 0,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self._month = month
        self._year = year
        self._actual = actual_hours
        self._target = target_hours
        self._working_days = working_days
        self._target_days = target_days

    def on_mount(self) -> None:
        """CSS-Klassen setzen."""
        today = date.today()
        if self._month == today.month and self._year == today.year:
            self.add_class("current")

    def render(self) -> Text:
        """Rendert die Monatskachel mit Mini-Progressbar."""
        text = Text()
        name = t(f"month.{self._month}")

        if self._actual > 0 and self._target > 0:
            pct = min(self._actual / self._target * 100, 100)
            if pct >= 95:
                bar_style = "green"
                pct_style = "bold green"
            elif pct >= 70:
                bar_style = "yellow"
                pct_style = "bold yellow"
            else:
                bar_style = "red"
                pct_style = "bold red"

            text.append(f"{name}", style="bold")
            text.append(f"  {pct:.0f}%\n", style=pct_style)

            # Mini-Progressbar
            bar_len = 18
            filled = int(pct / 100 * bar_len)
            text.append("\u2588" * filled, style=bar_style)
            text.append("\u2591" * (bar_len - filled), style="dim")
            text.append("\n")

            text.append(f"{self._actual:.1f}h", style=pct_style)
            text.append(f" / {self._target:.0f}h\n", style="dim")

            days = t("year.month_days", days=self._working_days, target=self._target_days)
            text.append(f"\u25b8 {days}", style="dim")

        elif self._actual > 0:
            text.append(f"{name}\n", style="bold")
            text.append(f"{self._actual:.1f}h\n", style="bold yellow")
            text.append(f"\u25b8 {t('year.month_days_single', days=self._working_days)}", style="dim")

        elif self._target > 0:
            text.append(f"{name}\n", style="dim")
            text.append("\u2591" * 18 + "\n", style="dim")
            text.append(f"{t('year.month_target', hours=f'{self._target:.0f}')}\n", style="dim")
            text.append(f"\u25b8 {t('year.month_days_single', days=self._target_days)}", style="dim")

        else:
            text.append(f"{name}\n", style="dim")
            text.append("\u2014", style="dim")

        return text


class QuarterRow(Horizontal):
    """Quartalsreihe mit Label + 3 Monatskacheln."""

    DEFAULT_CSS = """
    QuarterRow {
        width: 100%;
        height: 1fr;
        min-height: 6;
    }

    QuarterRow .quarter-label {
        width: 4;
        height: 100%;
        padding: 1 0;
        text-style: bold;
        color: $text-muted;
    }
    """


class YearScreen(ModalScreen):
    """Modal-Screen fuer die Jahresansicht."""

    DEFAULT_CSS = """
    YearScreen {
        align: center middle;
    }

    YearScreen > Vertical {
        width: 90%;
        height: 90%;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }

    YearScreen #year-title {
        text-style: bold;
        text-align: center;
        height: 1;
        margin-bottom: 1;
    }

    YearScreen #year-grid {
        height: 1fr;
    }

    YearScreen #year-summary {
        height: auto;
        min-height: 2;
        margin-top: 1;
        padding: 0 1;
    }

    YearScreen #year-footer {
        height: auto;
        margin-top: 1;
        align: center middle;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "ESC"),
        Binding("q,Q", "close", "Q", show=False),
        Binding("j,J", "close", "J", show=False),
    ]

    def __init__(
        self,
        year: int,
        month_data: dict[int, dict],
        max_yearly_hours: float = 1720.0,
        hourly_rate: float = 0.0,
        vacation_days: int = 30,
        hours_per_day: float = 8.0,
        federal_state: str = "SN",
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self._year = year
        self._month_data = month_data
        self._max_yearly = max_yearly_hours
        self._hourly_rate = hourly_rate
        self._vacation_days = vacation_days
        self._hours_per_day = hours_per_day
        self._federal_state = federal_state

    def compose(self) -> ComposeResult:
        """Baut die Jahresansicht auf."""
        with Vertical():
            yield Static(t("year.title", year=self._year), id="year-title")

            with Vertical(id="year-grid"):
                for q in range(4):
                    with QuarterRow():
                        yield Static(_QUARTER_NAMES[q], classes="quarter-label")
                        for m_offset in range(3):
                            month = q * 3 + m_offset + 1
                            data = self._month_data.get(month, {})
                            yield MonthTile(
                                month=month,
                                year=self._year,
                                actual_hours=data.get("actual", 0.0),
                                target_hours=data.get("target", 0.0),
                                working_days=data.get("working_days", 0),
                                target_days=data.get("target_days", 0),
                            )

            yield Static(self._build_summary(), id="year-summary")
            with Center(id="year-footer"):
                # can_focus aus: sonst zieht der Button beim Oeffnen den Fokus
                # und zeigt einen unschoenen Focus-Rahmen. ESC/Klick reichen.
                close_button = Button(t("common.close_button"), variant="primary", id="year-close")
                close_button.can_focus = False
                yield close_button

    def _build_summary(self) -> Text:
        """Erzeugt die Jahres-Zusammenfassung."""
        text = Text()

        total_actual = sum(d.get("actual", 0.0) for d in self._month_data.values())
        sum(d.get("target", 0.0) for d in self._month_data.values())
        total_days = sum(d.get("working_days", 0) for d in self._month_data.values())

        text.append(t("year.total", year=self._year), style="bold")
        text.append(f"{total_actual:.1f}h", style="bold")

        if self._max_yearly > 0:
            remaining = self._max_yearly - total_actual
            pct = total_actual / self._max_yearly * 100

            text.append(f" / {self._max_yearly:.0f}h", style="dim")

            bar_len = 20
            filled = min(int(pct / 100 * bar_len), bar_len)
            bar_style = "bold green" if pct < 80 else ("bold yellow" if pct < 95 else "bold red")
            text.append("  [", style="dim")
            text.append("\u2588" * filled, style=bar_style)
            text.append("\u2591" * (bar_len - filled), style="dim")
            text.append("]", style="dim")
            text.append(f" {pct:.1f}%", style=bar_style)

            text.append("  |  ", style="dim")
            if remaining > 0:
                text.append(t("year.remaining", hours=f"{remaining:.1f}"), style="bold green")
            else:
                text.append(t("year.exceeded", hours=f"{abs(remaining):.1f}"), style="bold red")

        text.append("  |  ", style="dim")
        text.append(t("year.workdays", days=total_days), style="dim")

        if self._hourly_rate > 0:
            netto = total_actual * self._hourly_rate
            brutto = netto * 1.19
            text.append("\n")
            text.append(f"  {t('year.net')}: {netto:,.2f}\u20ac", style="bold")
            text.append("  |  ", style="dim")
            text.append(f"{t('year.gross')}: {brutto:,.2f}\u20ac", style="bold")

        # Forecast
        text.append("\n")
        text.append(self._build_forecast(total_actual, total_days))

        return text

    def _build_forecast(self, total_actual: float, total_worked_days: int) -> Text:
        """Berechnet den Jahres-Forecast."""
        text = Text()

        import holidays as _holidays

        h = _holidays.Germany(subdiv=self._federal_state, years=self._year)

        from datetime import timedelta

        total_workdays_year = 0
        current = date(self._year, 1, 1)
        end = date(self._year, 12, 31)
        one_day = timedelta(days=1)
        while current <= end:
            if current.weekday() < 5 and current not in h:
                total_workdays_year += 1
            current += one_day

        available_days = total_workdays_year - self._vacation_days
        forecast_hours = available_days * self._hours_per_day

        text.append(f"{t('year.forecast_header')}\n", style="dim")
        text.append(t("year.forecast_workdays", year=self._year), style="dim")
        text.append(f"{total_workdays_year}", style="bold")
        text.append(t("year.forecast_vacation", days=self._vacation_days), style="dim")
        text.append("  = ", style="dim")
        text.append(f"{t('year.forecast_available', days=available_days)}\n", style="bold")

        text.append(t("year.forecast_hours_label"), style="dim")
        text.append(
            t("year.forecast_hours_calc", days=available_days, per_day=f"{self._hours_per_day:.0f}"),
            style="dim",
        )
        text.append(f"{forecast_hours:.0f}h\n", style="bold")

        if self._hourly_rate > 0:
            forecast_netto = forecast_hours * self._hourly_rate
            forecast_brutto = forecast_netto * 1.19
            text.append(t("year.forecast_revenue_label"), style="dim")
            text.append(f"{t('year.net')}: {forecast_netto:,.2f}\u20ac", style="bold green")
            text.append("  |  ", style="dim")
            text.append(f"{t('year.gross')}: {forecast_brutto:,.2f}\u20ac", style="bold green")

        return text

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Schliesst die Jahresansicht beim Klick auf den Close-Button."""
        self.dismiss()

    def action_close(self) -> None:
        """Schliesst die Jahresansicht."""
        self.dismiss()
