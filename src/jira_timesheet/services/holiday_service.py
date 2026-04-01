"""Feiertagsberechnung fuer deutsche Bundeslaender."""
from __future__ import annotations

from datetime import date

import holidays


# Bundesland-Kuerzel → Anzeigename
FEDERAL_STATES: dict[str, str] = {
    "BW": "Baden-Wuerttemberg",
    "BY": "Bayern",
    "BE": "Berlin",
    "BB": "Brandenburg",
    "HB": "Bremen",
    "HH": "Hamburg",
    "HE": "Hessen",
    "MV": "Mecklenburg-Vorpommern",
    "NI": "Niedersachsen",
    "NW": "Nordrhein-Westfalen",
    "RP": "Rheinland-Pfalz",
    "SL": "Saarland",
    "SN": "Sachsen",
    "ST": "Sachsen-Anhalt",
    "SH": "Schleswig-Holstein",
    "TH": "Thueringen",
}


class HolidayService:
    """Berechnet Feiertage und Arbeitstage fuer ein Bundesland."""

    def __init__(self, federal_state: str = "SN") -> None:
        self._state = federal_state if federal_state in FEDERAL_STATES else "SN"

    def is_holiday(self, d: date) -> bool:
        """Prueft ob ein Datum ein Feiertag ist."""
        h = holidays.Germany(state=self._state, years=d.year)
        return d in h

    def get_holiday_name(self, d: date) -> str:
        """Gibt den Feiertagsnamen zurueck, oder leeren String."""
        h = holidays.Germany(state=self._state, years=d.year)
        return h.get(d, "")

    def is_workday(self, d: date) -> bool:
        """Prueft ob ein Datum ein Arbeitstag ist (kein WE, kein Feiertag)."""
        if d.weekday() >= 5:
            return False
        return not self.is_holiday(d)

    def count_workdays(self, date_from: date, date_to: date) -> int:
        """Zaehlt die Arbeitstage in einem Zeitraum."""
        h = holidays.Germany(state=self._state, years={date_from.year, date_to.year})
        count = 0
        current = date_from
        one_day = __import__("datetime").timedelta(days=1)
        while current <= date_to:
            if current.weekday() < 5 and current not in h:
                count += 1
            current += one_day
        return count

    def get_holidays_in_range(self, date_from: date, date_to: date) -> dict[date, str]:
        """Gibt alle Feiertage in einem Zeitraum zurueck."""
        h = holidays.Germany(state=self._state, years={date_from.year, date_to.year})
        result: dict[date, str] = {}
        for d, name in sorted(h.items()):
            if date_from <= d <= date_to:
                result[d] = name
        return result

    def get_missing_workdays(
        self,
        date_from: date,
        date_to: date,
        worked_dates: set[date],
    ) -> list[tuple[date, str]]:
        """Findet Arbeitstage ohne Worklogs.

        Gibt Liste von (Datum, Grund) zurueck:
        - Feiertag: ("Karfreitag")
        - Luecke: ("— kein Eintrag —")
        """
        h = holidays.Germany(state=self._state, years={date_from.year, date_to.year})
        missing: list[tuple[date, str]] = []
        current = date_from
        one_day = __import__("datetime").timedelta(days=1)

        while current <= date_to:
            if current.weekday() < 5:
                if current in h:
                    if current not in worked_dates:
                        missing.append((current, h[current]))
                elif current not in worked_dates:
                    missing.append((current, "\u2014 kein Eintrag \u2014"))
            current += one_day

        return missing
