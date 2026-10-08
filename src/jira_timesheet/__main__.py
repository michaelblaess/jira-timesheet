"""CLI Entry Point fuer jira-timesheet."""

from __future__ import annotations

import argparse
import atexit
import contextlib
import faulthandler
import sys
from datetime import datetime
from typing import TextIO

from textual_widgets import reset_terminal_title, set_terminal_title

from jira_timesheet import __version__
from jira_timesheet.i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, load_locale
from jira_timesheet.models.settings import Settings

# Log-Handle offen halten, solange der Prozess laeuft - faulthandler schreibt
# beim fatalen Signal direkt hinein. Ohne Referenz wuerde der GC es schliessen.
_fault_log: TextIO | None = None

BANNER = f"Jira Timesheet v{__version__} — TUI für Jira Stundenzettel"

USAGE_EXAMPLES = """
Beispiele:
  jira-timesheet
  jira-timesheet --lang en
  jira-timesheet --version
  jira-timesheet --new-tickets-json --days 2
"""


def main() -> None:
    """Haupteinstiegspunkt."""
    _enable_faulthandler()
    settings = Settings.load()
    saved_lang = settings.language if settings.language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE

    parser = argparse.ArgumentParser(
        prog="jira-timesheet",
        description=BANNER,
        epilog=USAGE_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--lang",
        default=saved_lang,
        choices=SUPPORTED_LANGUAGES,
        help="Sprache der Oberfläche (Default: gespeicherte Einstellung)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "--new-tickets-json",
        action="store_true",
        help="Gibt die neuen Tickets der Merkliste als JSON aus und beendet sich, ohne die Oberfläche zu starten",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Arbeitstage zurück für --new-tickets-json (Default: der zuletzt gewählte Zeitraum)",
    )

    args = parser.parse_args()

    # Sprache laden, BEVOR die App-Klasse importiert wird - sonst sind
    # t()-Aufrufe auf Modul-Ebene leer.
    load_locale(args.lang)

    if args.new_tickets_json:
        sys.exit(_print_new_tickets(settings, args.days))

    # Per CLI gewaehlte Sprache persistieren.
    if args.lang != saved_lang:
        settings.language = args.lang
        settings.save()

    # Terminal-Tab-Titel setzen - Textual macht das nicht selbst.
    set_terminal_title(f"◷ jira-timesheet v{__version__}")
    try:
        from jira_timesheet.app import JiraTimesheetApp

        app = JiraTimesheetApp()
        app.run()
    finally:
        reset_terminal_title()
        # Nach einem harten Absturz laesst Textuals Windows-Teardown das
        # Maus-Tracking an - danach kippt jede Mausbewegung Steuerzeichen-Muell
        # in die Shell. Hier abschalten, auch bei Crash (finally).
        _reset_mouse_tracking()


def _print_new_tickets(settings: Settings, days: int | None) -> int:
    """Schreibt die neuen Tickets als JSON auf die Standardausgabe.

    Geschrieben wird in Bytes und immer als UTF-8: die Ausgabe liest ein
    anderes Programm, und die Windows-Konsole wuerde Umlaute sonst in ihrer
    eigenen Codepage ausgeben.

    Args:
        settings:
            Zugang, Host und Merkliste.
        days:
            Arbeitstage zurueck, None nimmt den zuletzt gewaehlten Zeitraum.

    Returns:
        Der Rueckgabewert des Prozesses: 0 bei Erfolg, 1 bei einem gescheiterten Abruf.
    """
    import asyncio
    import json

    from jira_timesheet.services.new_tickets_export import default_workdays, export_new_tickets

    workdays = days if days is not None and days > 0 else default_workdays(settings)
    result = asyncio.run(export_new_tickets(settings, workdays))
    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()
    return 1 if "error" in result else 0


def _enable_faulthandler() -> None:
    """Faengt HARTE Abstuerze ab, die an Pythons Exception-Handling UND am
    finally-Block vorbeilaufen: native Access Violation, Stack-Overflow, fataler
    Interpreter-Fehler.

    faulthandler installiert einen Handler fuer fatale Signale (unter Windows
    auch fuer Access Violations) und schreibt beim Absturz den Traceback aller
    Threads in fault.log - separat vom Terminal, das der Maus-Tracking-Muell
    sonst unlesbar macht. Der CrashGuard und _persist_crash greifen nur bei
    normalen Python-Exceptions, dieser Handler bei allem darunter.
    """
    global _fault_log
    with contextlib.suppress(Exception):
        Settings.SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        # Bewusst offen lassen (Prozess-Lebensdauer) - faulthandler schreibt
        # beim fatalen Signal direkt in dieses Handle.
        _fault_log = open(Settings.SETTINGS_DIR / "fault.log", "a", encoding="utf-8")  # noqa: SIM115
        _fault_log.write(f"\n===== Start {datetime.now():%Y-%m-%d %H:%M:%S} - v{__version__} =====\n")
        _fault_log.flush()
        faulthandler.enable(file=_fault_log, all_threads=True)
        # Gegenstueck zur Startzeile - siehe _write_fault_end.
        atexit.register(_write_fault_end)


def _reset_mouse_tracking() -> None:
    """Schaltet alle Maus-Tracking-Modi des Terminals ab (idempotent).

    ?1000/?1002/?1003 = Tracking-Modi, ?1006/?1015 = erweitertes Encoding.
    Sind sie bereits aus, bewirken die Sequenzen nichts.

    Schreibt bewusst nach sys.__stdout__, NICHT sys.stdout: Textual kapert
    sys.stdout zur Laufzeit, ein Reset dorthin landet im Nichts und das Terminal
    bleibt im Maus-Tracking-Modus haengen. sys.__stdout__ ist die echte Konsole.
    Der garantierte Reset passiert ohnehin im Shell-Wrapper run.ps1 (laeuft auch
    nach einem harten Crash) - das hier ist der zusaetzliche In-Prozess-Pfad.
    """
    stream = sys.__stdout__
    if stream is None or not stream.isatty():
        return
    stream.write("\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1006l\x1b[?1015l")
    stream.flush()


def _write_fault_end() -> None:
    """Schreibt die Endzeile der Sitzungsklammer (ueber atexit registriert).

    Erst dieses Gegenstueck zur Startzeile macht die Datei aussagekraeftig:

      Start + Ende            -> sauber beendet
      Start + Traceback       -> Python-Fehler (der Handler hat ihn gesehen)
      Start und sonst nichts  -> Prozess hart abgeraeumt

    Unter Windows hilft ein Signalhandler dabei nicht: ein Abbruch von aussen
    laeuft dort ueber TerminateProcess und liefert dem Ziel kein abfangbares
    Signal. Die FEHLENDE Endzeile ist der einzige Beleg.
    """
    import contextlib
    from datetime import datetime

    if _fault_log is None:
        return
    with contextlib.suppress(Exception):
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _fault_log.write(f"===== Ende {stamp} =====\n")
        _fault_log.flush()


if __name__ == "__main__":
    main()
