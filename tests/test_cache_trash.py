"""Cache zuruecksetzen (Taste R): Rueckfrage, dann Papierkorb statt Loeschen.

Anlass: Der Cache haelt Buchungen auf Tickets, die Jira inzwischen archiviert
hat. Vor v1.27.0 loeschte R den Ordner ohne Rueckfrage per rmtree - damit
waren diese Stunden endgueltig weg.
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any

from jira_timesheet.app import JiraTimesheetApp
from jira_timesheet.services import cache_service
from jira_timesheet.services.cache_service import TRASH_KEEP, move_cache_to_trash, trash_dir


def _cache_mit(*namen: str) -> None:
    cache_service.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for name in namen:
        (cache_service.CACHE_DIR / name).write_text("[]", encoding="utf-8")


class TestPapierkorb:
    def test_der_cache_wandert_in_den_papierkorb(self) -> None:
        _cache_mit("2026-01_a.json", "2026-02_a.json")
        ergebnis = move_cache_to_trash(datetime(2026, 10, 23, 15, 0, 0))
        assert ergebnis is not None
        assert ergebnis.count == 2
        assert not cache_service.CACHE_DIR.exists()
        assert sorted(p.name for p in ergebnis.target.iterdir()) == ["2026-01_a.json", "2026-02_a.json"]
        assert ergebnis.target.parent == trash_dir()

    def test_ohne_cache_passiert_nichts(self) -> None:
        assert move_cache_to_trash() is None

    def test_gleicher_zeitpunkt_ueberschreibt_nichts(self) -> None:
        jetzt = datetime(2026, 10, 23, 15, 0, 0)
        _cache_mit("2026-01_a.json")
        erstes = move_cache_to_trash(jetzt)
        _cache_mit("2026-02_a.json")
        zweites = move_cache_to_trash(jetzt)
        assert erstes is not None and zweites is not None
        assert erstes.target != zweites.target
        assert (erstes.target / "2026-01_a.json").is_file()

    def test_nur_die_neuesten_bleiben(self) -> None:
        for minute in range(TRASH_KEEP + 2):
            _cache_mit("2026-01_a.json")
            move_cache_to_trash(datetime(2026, 10, 23, 15, minute, 0))
        namen = sorted(p.name for p in trash_dir().iterdir())
        assert len(namen) == TRASH_KEEP
        assert namen[0] == "2026-10-23_15-02-00"


class TestRueckfrage:
    def _app(self) -> tuple[Any, list[str]]:
        log: list[str] = []
        fake = SimpleNamespace(
            _invalidate_year=lambda: log.append("invalidate"),
            _write_log=log.append,
            notify=lambda msg, **_: log.append(msg),
        )
        return fake, log

    def test_abbrechen_laesst_den_cache_stehen(self) -> None:
        _cache_mit("2026-01_a.json")
        fake, log = self._app()
        JiraTimesheetApp._on_reset_cache_confirmed(fake, False)
        assert (cache_service.CACHE_DIR / "2026-01_a.json").is_file()
        assert log == []

    def test_zustimmen_verschiebt_in_den_papierkorb(self) -> None:
        _cache_mit("2026-01_a.json")
        fake, log = self._app()
        JiraTimesheetApp._on_reset_cache_confirmed(fake, True)
        assert not cache_service.CACHE_DIR.exists()
        assert len(list(trash_dir().iterdir())) == 1
        assert log[0] == "invalidate"


def test_der_cache_liegt_im_testordner() -> None:
    """Die Isolierung aus conftest.py - sonst landet der echte Cache im Papierkorb."""
    assert ".jira-timesheet" not in str(cache_service.CACHE_DIR)
