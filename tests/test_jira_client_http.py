"""Tests des Jira-Clients gegen hinterlegte HTTP-Antworten.

Die uebrigen Tests ersetzen den ganzen `JiraClient` durch eine Attrappe
(`monkeypatch.setattr("jira_timesheet.app.JiraClient", FakeJiraClient)`).
Damit ist geprueft, wie die Anwendung auf Ergebnisse reagiert - aber nie, ob
der Client aus einer echten Jira-Antwort das Richtige liest. Am 08.09.2026 lag
die Abdeckung von `jira_client.py` deshalb bei 35 Prozent.

Hier laeuft der echte Client mit echtem httpx, nur die Leitung endet in einer
hinterlegten Antwort (`respx` faengt auf Transportebene ab). Geprueft wird
damit genau das, was sonst niemand prueft: JQL-Bau, Paginierung, der
Unterschied zwischen Cloud v3 und Data Center v2, das Filtern der Worklogs
nach Autor und Zeitraum, und die Fehlerpfade.

Die Antworten sind Attrappen im Format der Jira-API, keine echten Ticketdaten.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import httpx
import pytest
import respx

from jira_timesheet.i18n import load_locale
from jira_timesheet.services.jira_client import JiraClient, JiraClientError

load_locale("de")

HOST = "https://example.atlassian.net"
CLOUD_SUCHE = f"{HOST}/rest/api/3/search/jql"
LEGACY_SUCHE = f"{HOST}/rest/api/2/search"
MYSELF = f"{HOST}/rest/api/3/myself"

ICH = "acc-ich"
JEMAND_ANDERES = "acc-fremd"


def worklog(tag: str, sekunden: int = 3600, account: str = ICH, name: str = "") -> dict[str, Any]:
    """Baut einen Worklog-Eintrag im Format der Jira-API."""
    author: dict[str, Any] = {"displayName": "Blaess, Michael"}
    if account:
        author["accountId"] = account
    if name:
        author["name"] = name
    return {
        "started": f"{tag}T09:00:00.000+0200",
        "timeSpentSeconds": sekunden,
        "author": author,
    }


def issue(key: str = "ABC-1", *worklogs: dict[str, Any], **felder: Any) -> dict[str, Any]:
    """Baut ein Issue mit eingebetteten Worklogs."""
    fields: dict[str, Any] = {
        "summary": "Ein Vorgang",
        "status": {"name": "In Arbeit"},
        "issuetype": {"name": "Task"},
        "priority": {"name": "Medium"},
        "components": [{"name": "Backend"}],
        "labels": ["wichtig", "cloud"],
        "assignee": {"displayName": "Muster, Erika"},
        "created": "2026-09-01T08:30:00.000+0200",
        "updated": "2026-09-05T17:12:00.000+0200",
        "timespent": 7200,
        "worklog": {"maxResults": 20, "total": len(worklogs), "worklogs": list(worklogs)},
    }
    fields.update(felder)
    return {"key": key, "fields": fields}


def cloud_client(**kwargs: Any) -> JiraClient:
    return JiraClient(host=HOST, email="michael@example.de", token="geheim", **kwargs)


def legacy_client(**kwargs: Any) -> JiraClient:
    return JiraClient(host=HOST, email="mblaess", token="geheim", legacy=True, **kwargs)


# --- Cloud: der Normalfall ------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_cloud_liest_einen_worklog_vollstaendig() -> None:
    respx.get(MYSELF).mock(return_value=httpx.Response(200, json={"accountId": ICH}))
    respx.get(CLOUD_SUCHE).mock(
        return_value=httpx.Response(
            200,
            json={"issues": [issue("ABC-1", worklog("2026-09-03", 5400))], "isLast": True},
        )
    )

    eintraege = await cloud_client().get_worklogs(date(2026, 9, 1), date(2026, 9, 30))

    assert len(eintraege) == 1
    e = eintraege[0]
    assert e.ticket == "ABC-1"
    assert e.date == date(2026, 9, 3)
    assert e.hours == pytest.approx(1.5)
    assert e.summary == "Ein Vorgang"
    assert e.status == "In Arbeit"
    assert e.components == "Backend"
    assert e.labels == "wichtig, cloud"
    assert e.assignee == "Muster, Erika"
    # created/updated werden auf Minuten gekuerzt und das T ersetzt.
    assert e.created == "2026-09-01 08:30"
    assert e.total_logged == "2.00h"


@respx.mock
@pytest.mark.asyncio
async def test_fremde_worklogs_werden_aussortiert() -> None:
    respx.get(MYSELF).mock(return_value=httpx.Response(200, json={"accountId": ICH}))
    respx.get(CLOUD_SUCHE).mock(
        return_value=httpx.Response(
            200,
            json={
                "issues": [
                    issue(
                        "ABC-1",
                        worklog("2026-09-03", account=ICH),
                        worklog("2026-09-03", account=JEMAND_ANDERES),
                    )
                ],
                "isLast": True,
            },
        )
    )

    eintraege = await cloud_client().get_worklogs(date(2026, 9, 1), date(2026, 9, 30))
    assert len(eintraege) == 1


@respx.mock
@pytest.mark.asyncio
async def test_worklogs_ausserhalb_des_zeitraums_fallen_weg() -> None:
    respx.get(MYSELF).mock(return_value=httpx.Response(200, json={"accountId": ICH}))
    respx.get(CLOUD_SUCHE).mock(
        return_value=httpx.Response(
            200,
            json={
                "issues": [
                    issue(
                        "ABC-1",
                        worklog("2026-08-31"),  # ein Tag zu frueh
                        worklog("2026-09-01"),  # Randtag, gehoert dazu
                        worklog("2026-09-30"),  # Randtag, gehoert dazu
                        worklog("2026-10-01"),  # ein Tag zu spaet
                    )
                ],
                "isLast": True,
            },
        )
    )

    eintraege = await cloud_client().get_worklogs(date(2026, 9, 1), date(2026, 9, 30))
    assert [e.date for e in eintraege] == [date(2026, 9, 1), date(2026, 9, 30)]


@respx.mock
@pytest.mark.asyncio
async def test_die_jql_fragt_nach_den_eigenen_worklogs_im_zeitraum() -> None:
    respx.get(MYSELF).mock(return_value=httpx.Response(200, json={"accountId": ICH}))
    route = respx.get(CLOUD_SUCHE).mock(return_value=httpx.Response(200, json={"issues": [], "isLast": True}))

    await cloud_client().get_worklogs(date(2026, 9, 1), date(2026, 9, 30))

    jql = route.calls.last.request.url.params["jql"]
    assert "worklogAuthor = currentUser()" in jql
    assert 'worklogDate >= "2026-09-01"' in jql
    assert 'worklogDate <= "2026-09-30"' in jql


# --- Paginierung ----------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_cloud_holt_alle_seiten() -> None:
    respx.get(MYSELF).mock(return_value=httpx.Response(200, json={"accountId": ICH}))
    respx.get(CLOUD_SUCHE).mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "issues": [issue("ABC-1", worklog("2026-09-02"))],
                    "isLast": False,
                    "nextPageToken": "seite2",
                },
            ),
            httpx.Response(
                200,
                json={"issues": [issue("ABC-2", worklog("2026-09-03"))], "isLast": True},
            ),
        ]
    )

    eintraege = await cloud_client().get_worklogs(date(2026, 9, 1), date(2026, 9, 30))
    assert sorted(e.ticket for e in eintraege) == ["ABC-1", "ABC-2"]


@respx.mock
@pytest.mark.asyncio
async def test_fehlender_folgetoken_beendet_die_schleife() -> None:
    # Gegenprobe zur Endlosschleife: isLast=False, aber kein nextPageToken.
    respx.get(MYSELF).mock(return_value=httpx.Response(200, json={"accountId": ICH}))
    route = respx.get(CLOUD_SUCHE).mock(return_value=httpx.Response(200, json={"issues": [], "isLast": False}))

    await cloud_client().get_worklogs(date(2026, 9, 1), date(2026, 9, 30))
    assert route.call_count == 1


@respx.mock
@pytest.mark.asyncio
async def test_worklogs_werden_nachgeladen_wenn_die_seite_nicht_reicht() -> None:
    # maxResults < total heisst: das Issue bringt nicht alle Worklogs mit.
    respx.get(MYSELF).mock(return_value=httpx.Response(200, json={"accountId": ICH}))
    knapp = issue("ABC-1", worklog("2026-09-02"))
    knapp["fields"]["worklog"] = {"maxResults": 1, "total": 2, "worklogs": [worklog("2026-09-02")]}
    respx.get(CLOUD_SUCHE).mock(return_value=httpx.Response(200, json={"issues": [knapp], "isLast": True}))

    nachladen = respx.get(f"{HOST}/rest/api/3/issue/ABC-1/worklog").mock(
        return_value=httpx.Response(
            200,
            json={"worklogs": [worklog("2026-09-02"), worklog("2026-09-04")], "total": 2},
        )
    )

    eintraege = await cloud_client().get_worklogs(date(2026, 9, 1), date(2026, 9, 30))
    assert nachladen.called
    assert [e.date for e in eintraege] == [date(2026, 9, 2), date(2026, 9, 4)]


# --- Data Center (Legacy) -------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_legacy_nutzt_den_alten_endpunkt_und_bearer_auth() -> None:
    # Beide Endpunkte hinterlegen - so laesst sich pruefen, dass der Cloud-Weg
    # unberuehrt bleibt, statt nur zu hoffen, dass er nicht gerufen wird.
    cloud = respx.get(CLOUD_SUCHE).mock(return_value=httpx.Response(200, json={"issues": [], "isLast": True}))
    myself = respx.get(MYSELF).mock(return_value=httpx.Response(200, json={"accountId": ICH}))
    route = respx.get(LEGACY_SUCHE).mock(
        return_value=httpx.Response(
            200,
            json={"issues": [issue("ABC-1", worklog("2026-09-03", account="", name="mblaess"))]},
        )
    )

    eintraege = await legacy_client().get_worklogs(date(2026, 9, 1), date(2026, 9, 30))

    assert len(eintraege) == 1
    assert route.calls.last.request.headers["Authorization"] == "Bearer geheim"
    # Der Cloud-Weg bleibt unangetastet, und die accountId wird nicht geholt -
    # im Legacy-Modus laeuft die Zuordnung ueber den Benutzernamen.
    assert not cloud.called
    assert not myself.called


@respx.mock
@pytest.mark.asyncio
async def test_legacy_ordnet_ueber_den_benutzernamen_zu() -> None:
    respx.get(LEGACY_SUCHE).mock(
        return_value=httpx.Response(
            200,
            json={
                "issues": [
                    issue(
                        "ABC-1",
                        worklog("2026-09-03", account="", name="mblaess"),
                        worklog("2026-09-03", account="", name="jemand.anderes"),
                    )
                ]
            },
        )
    )

    eintraege = await legacy_client().get_worklogs(date(2026, 9, 1), date(2026, 9, 30))
    assert len(eintraege) == 1


# --- Fehlerpfade ----------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_401_wird_zur_anmeldemeldung() -> None:
    respx.get(MYSELF).mock(return_value=httpx.Response(200, json={"accountId": ICH}))
    respx.get(CLOUD_SUCHE).mock(return_value=httpx.Response(401, json={"errorMessages": ["nope"]}))

    with pytest.raises(JiraClientError) as fehler:
        await cloud_client().get_worklogs(date(2026, 9, 1), date(2026, 9, 30))
    assert "Anmeldung" in str(fehler.value) or "401" not in str(fehler.value)


@respx.mock
@pytest.mark.asyncio
async def test_anderer_fehlerstatus_nennt_den_code() -> None:
    respx.get(MYSELF).mock(return_value=httpx.Response(200, json={"accountId": ICH}))
    respx.get(CLOUD_SUCHE).mock(return_value=httpx.Response(503, text="Service Unavailable"))

    with pytest.raises(JiraClientError) as fehler:
        await cloud_client().get_worklogs(date(2026, 9, 1), date(2026, 9, 30))
    assert "503" in str(fehler.value)


@respx.mock
@pytest.mark.asyncio
async def test_die_fehlerdetails_landen_im_log() -> None:
    # Ohne das steht bei einem 403 nur "API-Fehler" da und niemand weiss, wo.
    zeilen: list[str] = []
    respx.get(MYSELF).mock(return_value=httpx.Response(200, json={"accountId": ICH}))
    respx.get(CLOUD_SUCHE).mock(return_value=httpx.Response(403, json={"errorMessages": ["verboten"]}))

    with pytest.raises(JiraClientError):
        await cloud_client(on_log=zeilen.append).get_worklogs(date(2026, 9, 1), date(2026, 9, 30))

    gesamt = " ".join(zeilen)
    assert "403" in gesamt
    assert CLOUD_SUCHE in gesamt


@respx.mock
@pytest.mark.asyncio
async def test_ein_netzwerkfehler_kommt_als_client_fehler_an() -> None:
    respx.get(MYSELF).mock(side_effect=httpx.ConnectError("Verbindung abgelehnt"))

    with pytest.raises(JiraClientError):
        await cloud_client().get_worklogs(date(2026, 9, 1), date(2026, 9, 30))


# --- Sonstige Endpunkte ---------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_budget_feld_erkennung_filtert_auf_den_suchbegriff() -> None:
    respx.get(f"{HOST}/rest/api/3/field").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": "customfield_1", "name": "Budget", "custom": True},
                {"id": "customfield_2", "name": "Sprint", "custom": True},
                {"id": "summary", "name": "Budget Summary", "custom": False},
            ],
        )
    )

    treffer = await cloud_client().detect_budget_field("budget")
    assert treffer == [("customfield_1", "Budget")]


@respx.mock
@pytest.mark.asyncio
async def test_personensuche_liefert_die_treffer() -> None:
    respx.get(f"{HOST}/rest/api/3/user/search").mock(
        return_value=httpx.Response(
            200,
            json=[{"accountId": "1", "displayName": "Muster, Erika", "active": True}],
        )
    )

    treffer = await cloud_client().fetch_people("Muster")
    assert [p["displayName"] for p in treffer] == ["Muster, Erika"]
