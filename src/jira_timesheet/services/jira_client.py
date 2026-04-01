"""Jira REST API Client fuer Worklog-Abfragen."""
from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, datetime, timedelta

import httpx

from jira_timesheet.models.timesheet import WorklogEntry

logger = logging.getLogger(__name__)


class JiraClientError(Exception):
    """Fehler bei der Jira-Kommunikation."""


class JiraClient:
    """Async Client fuer Jira REST API v2."""

    def __init__(
        self,
        host: str,
        token: str,
        budget_field: str = "customfield_36461",
        on_log: Callable[[str], None] | None = None,
    ) -> None:
        self._host = host.rstrip("/")
        self._token = token
        self._budget_field = budget_field
        self._log = on_log or (lambda _: None)

    async def get_worklogs(
        self,
        email: str,
        date_from: date,
        date_to: date,
    ) -> list[WorklogEntry]:
        """Holt alle Worklogs fuer einen Benutzer in einem Zeitraum.

        Entspricht der VBA-Logik:
        - JQL sucht mit workLogged "after" (date_from - 1 Tag)
        - Filtert dann Ergebnisse nach exaktem Zeitraum + Assignee
        """
        search_from = date_from - timedelta(days=1)
        jql = (
            f'issueFunction in workLogged('
            f'"after {search_from:%Y/%m/%d} by {email}")'
        )
        fields = f"worklog,summary,status,issuetype,components,labels,priority,resolution,assignee,created,updated,timespent,{self._budget_field}"

        self._log(f"JQL: {jql}")
        self._log(f"Verbinde mit {self._host}...")

        entries: list[WorklogEntry] = []

        async with httpx.AsyncClient(
            verify=False,
            timeout=60.0,
            follow_redirects=True,
        ) as client:
            issues = await self._search_issues(client, jql, fields)
            self._log(f"{len(issues)} Issues gefunden")

            for issue in issues:
                issue_entries = await self._extract_worklogs(
                    client, issue, email, date_from, date_to,
                )
                entries.extend(issue_entries)

        self._log(f"{len(entries)} Worklogs im Zeitraum gefunden")
        entries.sort(key=lambda e: (e.date, e.ticket))
        return entries

    async def _search_issues(
        self,
        client: httpx.AsyncClient,
        jql: str,
        fields: str,
    ) -> list[dict]:
        """Fuehrt die JQL-Suche aus und gibt Issues zurueck."""
        url = f"{self._host}/rest/api/2/search"
        params = {"jql": jql, "fields": fields, "maxResults": 200}

        response = await client.get(
            url,
            params=params,
            headers=self._headers(),
        )

        if response.status_code == 401:
            raise JiraClientError(
                "Jira Login fehlgeschlagen. Bitte Token pruefen."
            )

        if response.status_code != 200:
            raise JiraClientError(
                f"Jira API Fehler: HTTP {response.status_code}"
            )

        data = response.json()
        return data.get("issues", [])

    async def _extract_worklogs(
        self,
        client: httpx.AsyncClient,
        issue: dict,
        email: str,
        date_from: date,
        date_to: date,
    ) -> list[WorklogEntry]:
        """Extrahiert Worklogs aus einem Issue, holt ggf. paginierte Daten."""
        issue_key = issue.get("key", "")
        fields = issue.get("fields", {})
        summary = fields.get("summary", "")

        budget_data = fields.get(self._budget_field)
        if budget_data and isinstance(budget_data, dict):
            budget = budget_data.get("value", "nicht zugeordnet")
        else:
            budget = "nicht zugeordnet"

        status_obj = fields.get("status", {})
        issue_status = status_obj.get("name", "") if isinstance(status_obj, dict) else ""

        type_obj = fields.get("issuetype", {})
        issue_type = type_obj.get("name", "") if isinstance(type_obj, dict) else ""

        priority_obj = fields.get("priority", {})
        issue_priority = priority_obj.get("name", "") if isinstance(priority_obj, dict) else ""

        comp_list = fields.get("components", [])
        issue_components = ", ".join(c.get("name", "") for c in comp_list if isinstance(c, dict))

        label_list = fields.get("labels", [])
        issue_labels = ", ".join(label_list) if isinstance(label_list, list) else ""

        resolution_obj = fields.get("resolution", {})
        issue_resolution = resolution_obj.get("name", "") if isinstance(resolution_obj, dict) else ""

        assignee_obj = fields.get("assignee", {})
        issue_assignee = assignee_obj.get("displayName", "") if isinstance(assignee_obj, dict) else ""

        issue_created = fields.get("created", "")[:16].replace("T", " ") if fields.get("created") else ""
        issue_updated = fields.get("updated", "")[:16].replace("T", " ") if fields.get("updated") else ""

        timespent_sec = fields.get("timespent", 0) or 0
        total_logged_h = timespent_sec / 3600.0
        issue_total_logged = f"{total_logged_h:.2f}h" if timespent_sec > 0 else ""

        worklog_node = fields.get("worklog", {})
        max_results = worklog_node.get("maxResults", 0)
        total = worklog_node.get("total", 0)

        if max_results < total:
            worklogs = await self._fetch_all_worklogs(client, issue_key)
        else:
            worklogs = worklog_node.get("worklogs", [])

        entries: list[WorklogEntry] = []

        for wl in worklogs:
            author = wl.get("author", {})
            author_name = author.get("name", "")
            author_display = author.get("displayName", author_name)

            started_str = wl.get("started", "")[:10]
            try:
                started = datetime.strptime(started_str, "%Y-%m-%d").date()
            except ValueError:
                continue

            if author_name != email:
                continue
            if started < date_from or started > date_to:
                continue

            seconds = wl.get("timeSpentSeconds", 0)
            hours = seconds / 3600.0

            entries.append(WorklogEntry(
                date=started,
                ticket=issue_key,
                summary=summary,
                author=author_display,
                budget=budget,
                hours=hours,
                status=issue_status,
                issuetype=issue_type,
                epic="",
                components=issue_components,
                labels=issue_labels,
                priority=issue_priority,
                resolution=issue_resolution,
                assignee=issue_assignee,
                created=issue_created,
                updated=issue_updated,
                total_logged=issue_total_logged,
            ))

        return entries

    async def _fetch_all_worklogs(
        self,
        client: httpx.AsyncClient,
        issue_key: str,
    ) -> list[dict]:
        """Holt alle Worklogs eines Issues (bei Pagination)."""
        url = f"{self._host}/rest/api/2/issue/{issue_key}/worklog"
        response = await client.get(url, headers=self._headers())

        if response.status_code != 200:
            logger.warning("Worklog-Abruf fuer %s fehlgeschlagen", issue_key)
            return []

        data = response.json()
        return data.get("worklogs", [])

    def _headers(self) -> dict[str, str]:
        """HTTP Headers fuer Jira API Requests."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Atlassian-Token": "no-check",
            "Authorization": f"Bearer {self._token}",
        }
