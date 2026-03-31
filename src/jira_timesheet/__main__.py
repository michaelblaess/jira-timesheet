"""CLI Entry Point fuer jira-timesheet."""
from __future__ import annotations

import argparse
import sys

from jira_timesheet import __version__
from jira_timesheet.app import JiraTimesheetApp


BANNER = f"Jira Timesheet v{__version__} — TUI fuer Jira Stundenzettel"

USAGE_EXAMPLES = """
Beispiele:
  jira-timesheet
  jira-timesheet --version
"""


def main() -> None:
    """Haupteinstiegspunkt."""
    parser = argparse.ArgumentParser(
        prog="jira-timesheet",
        description=BANNER,
        epilog=USAGE_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.parse_args()

    app = JiraTimesheetApp()
    app.run()


if __name__ == "__main__":
    main()
