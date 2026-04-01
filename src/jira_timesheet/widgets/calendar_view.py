"""Kalenderansicht — Monatskalender mit Tages-Kacheln."""
from __future__ import annotations

import calendar
from datetime import date, timedelta

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widget import Widget
from textual.widgets import Static

from jira_timesheet.models.timesheet import Timesheet, TimesheetDay

_WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


class DayTile(Widget):
    """Einzelne Tages-Kachel im Kalender."""

    DEFAULT_CSS = """
    DayTile {
        width: 1fr;
        height: 100%;
        min-height: 6;
        padding: 0 1;
        border: solid $surface-lighten-2;
    }

    DayTile.weekend {
        background: $surface-darken-1;
    }

    DayTile.holiday {
        background: $surface-darken-1;
    }

    DayTile.gap {
        border: solid $error;
    }

    DayTile.today {
        border: solid $accent;
    }

    DayTile.outside {
        background: $surface-darken-2;
    }
    """

    def __init__(
        self,
        day_date: date,
        day_data: TimesheetDay | None = None,
        holiday_name: str = "",
        is_gap: bool = False,
        is_outside: bool = False,
        hours_per_day: float = 8.0,
        jira_host: str = "",
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self._date = day_date
        self._day_data = day_data
        self._holiday_name = holiday_name
        self._is_gap = is_gap
        self._is_outside = is_outside
        self._hours_per_day = hours_per_day
        self._jira_host = jira_host

    def on_mount(self) -> None:
        """Setzt CSS-Klassen basierend auf dem Tag-Typ."""
        if self._is_outside:
            self.add_class("outside")
        elif self._date.weekday() >= 5:
            self.add_class("weekend")
        elif self._holiday_name:
            self.add_class("holiday")
        elif self._is_gap:
            self.add_class("gap")

        if self._date == date.today():
            self.add_class("today")

    def render(self) -> Text:
        """Rendert den Inhalt der Kachel."""
        text = Text()

        day_num = str(self._date.day)
        weekday = _WEEKDAYS[self._date.weekday()]

        if self._is_outside:
            text.append(f"{day_num} {weekday}", style="dim")
            return text

        if self._day_data and self._day_data.entries:
            total = self._day_data.total_hours
            if total >= self._hours_per_day:
                hour_style = "bold green"
            else:
                hour_style = "bold yellow"

            text.append(f"{day_num} {weekday} ", style="bold")
            text.append(f"{total:.1f}h", style=hour_style)
            text.append("\n")

            for entry in self._day_data.entries:
                ticket_line = f"{entry.ticket} {entry.hours:.1f}h"
                text.append(ticket_line[:20], style="dim")
                text.append("\n")

        elif self._holiday_name:
            text.append(f"{day_num} {weekday}", style="dim")
            text.append("\n")
            text.append(self._holiday_name[:18], style="dim italic")

        elif self._date.weekday() >= 5:
            text.append(f"{day_num} {weekday}", style="dim")

        elif self._is_gap:
            text.append(f"{day_num} {weekday} ", style="bold")
            text.append("0.0h", style="bold red")
            text.append("\n")
            text.append("kein Eintrag", style="red")

        else:
            text.append(f"{day_num} {weekday}", style="dim")

        return text


class WeekRow(Horizontal):
    """Eine Wochenreihe mit 7 Tages-Kacheln."""

    DEFAULT_CSS = """
    WeekRow {
        width: 100%;
        height: auto;
        min-height: 6;
        max-height: 12;
    }
    """


class CalendarView(VerticalScroll):
    """Monatskalender-Ansicht mit Wochen-Reihen und Tages-Kacheln."""

    DEFAULT_CSS = """
    CalendarView #cal-header {
        height: 1;
        width: 100%;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        hours_per_day: float = 8.0,
        jira_host: str = "",
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self._hours_per_day = hours_per_day
        self._jira_host = jira_host

    def compose(self) -> ComposeResult:
        """Erzeugt den Header mit Wochentagnamen."""
        header_text = Text()
        col_width = 14
        for wd in _WEEKDAYS:
            header_text.append(f" {wd:<{col_width - 1}}", style="bold")
        yield Static(header_text, id="cal-header")

    def load_timesheet(
        self,
        timesheet: Timesheet,
        missing_days: list[tuple[date, str]] | None = None,
    ) -> None:
        """Baut den Kalender aus Timesheet-Daten auf."""
        for widget in self.query("WeekRow"):
            widget.remove()

        day_map = {day.date: day for day in timesheet.days}
        gap_map = {d: reason for d, reason in (missing_days or [])}
        holiday_map = {d: reason for d, reason in (missing_days or []) if "\u2014" not in reason}

        weeks = self._build_weeks(timesheet.date_from, timesheet.date_to)

        for week in weeks:
            row = WeekRow()
            self.mount(row)

            for d in week:
                is_outside = d.month != timesheet.date_from.month
                day_data = day_map.get(d)
                holiday_name = holiday_map.get(d, "")
                is_gap = d in gap_map and "\u2014" in gap_map.get(d, "")

                tile = DayTile(
                    day_date=d,
                    day_data=day_data if not is_outside else None,
                    holiday_name=holiday_name if not is_outside else "",
                    is_gap=is_gap and not is_outside,
                    is_outside=is_outside,
                    hours_per_day=self._hours_per_day,
                    jira_host=self._jira_host,
                )
                row.mount(tile)

    def clear_calendar(self) -> None:
        """Leert den Kalender."""
        for widget in self.query("WeekRow"):
            widget.remove()

    @staticmethod
    def _build_weeks(date_from: date, date_to: date) -> list[list[date]]:
        """Baut Wochen-Listen auf (Mo-So), mit Padding-Tagen am Anfang/Ende."""
        first_day = date_from.replace(day=1)
        last_day = date_to

        start = first_day - timedelta(days=first_day.weekday())

        if last_day.weekday() < 6:
            end = last_day + timedelta(days=6 - last_day.weekday())
        else:
            end = last_day

        weeks: list[list[date]] = []
        current = start
        while current <= end:
            week: list[date] = []
            for _ in range(7):
                week.append(current)
                current += timedelta(days=1)
            weeks.append(week)

        return weeks
