"""Tests for the Soccer Diagnosis API client.

The production host is not reachable from CI / sandboxed environments,
so these tests use a fake session that returns canned JSON modelled on
the documented API contract (v0.5.7).
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from hermes_os.datasources.soccer_diagnosis import (
    Case,
    CaseDetail,
    SoccerDiagnosisClient,
    SoccerDiagnosisError,
    Video,
    is_video_displayable,
)

# --- fakes ------------------------------------------------------------------


class FakeResponse:
    def __init__(self, payload: Any, status: int = 200) -> None:
        self._payload = payload
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(f"status {self.status_code}")

    def json(self) -> Any:
        if isinstance(self._payload, str):
            return json.loads(self._payload)
        return self._payload


class FakeSession:
    """Maps URL suffixes to canned responses."""

    def __init__(self, routes: dict[str, FakeResponse]) -> None:
        self.routes = routes
        self.calls: list[str] = []

    def get(self, url: str, timeout: float | None = None) -> FakeResponse:
        self.calls.append(url)
        for suffix, response in self.routes.items():
            if url.endswith(suffix):
                return response
        return FakeResponse({}, status=404)


HEALTH_PAYLOAD = {
    "version": "0.5.7",
    "cases": 105,
    "videos": 9,
    "reviews": 3,
    "parent_feedback": 3,
    "public_videos": 9,
    "duplicate_case_ids": 0,
    "missing_video_case_refs": 0,
    "public_videos_missing_id": 0,
}

CASE_PAYLOAD = {
    "case_id": "case-pass-not-coming-001",
    "title": "パスが来ない",
    "age_group": "u12",
    "symptom_tags": ["positioning"],
    "video_ids": ["vid-1"],
    "has_video": True,
}

DETAIL_PAYLOAD = {
    "case": CASE_PAYLOAD,
    "videos": [
        {
            "youtube_video_id": "blMy5M5rFXY",
            "visibility": "public",
            "consent_status": "approved",
            "consented": True,
        }
    ],
    "reviews": [{"id": "rev-1", "body": "good"}],
    "parent_feedback": [{"id": "pf-1", "body": "thanks"}],
    "cta": {"line_url": "https://line", "paid_diagnosis_url": "https://paid"},
}


def make_client(routes: dict[str, FakeResponse]) -> tuple[SoccerDiagnosisClient, FakeSession]:
    session = FakeSession(routes)
    return SoccerDiagnosisClient(session=session), session


# --- endpoint tests ---------------------------------------------------------


def test_health_parses_counts_and_consistency() -> None:
    client, _ = make_client({"/health": FakeResponse(HEALTH_PAYLOAD)})
    health = client.health()
    assert health.version == "0.5.7"
    assert health.cases == 105
    assert health.public_videos == 9
    assert health.is_consistent is True


def test_health_inconsistent_when_duplicates() -> None:
    payload = {**HEALTH_PAYLOAD, "duplicate_case_ids": 2}
    client, _ = make_client({"/health": FakeResponse(payload)})
    assert client.health().is_consistent is False


def test_cases_accepts_bare_list() -> None:
    client, _ = make_client({"/cases": FakeResponse([CASE_PAYLOAD])})
    cases = client.cases()
    assert len(cases) == 1
    assert isinstance(cases[0], Case)
    assert cases[0].case_id == "case-pass-not-coming-001"
    assert cases[0].has_video is True


def test_cases_accepts_wrapped_list() -> None:
    client, _ = make_client({"/cases": FakeResponse({"cases": [CASE_PAYLOAD]})})
    assert client.cases()[0].title == "パスが来ない"


def test_case_detail_parses_nested_structures() -> None:
    client, session = make_client(
        {"/case-detail/case-pass-not-coming-001": FakeResponse(DETAIL_PAYLOAD)}
    )
    detail = client.case_detail("case-pass-not-coming-001")
    assert isinstance(detail, CaseDetail)
    assert detail.case.case_id == "case-pass-not-coming-001"
    assert len(detail.videos) == 1
    assert detail.videos[0].youtube_video_id == "blMy5M5rFXY"
    assert len(detail.reviews) == 1
    assert len(detail.parent_feedback) == 1
    assert detail.cta.line_url == "https://line"
    # case_id is URL-encoded into the path
    assert session.calls[0].endswith("/case-detail/case-pass-not-coming-001")


def test_public_videos_returns_only_displayable() -> None:
    client, _ = make_client(
        {"/case-detail/case-pass-not-coming-001": FakeResponse(DETAIL_PAYLOAD)}
    )
    detail = client.case_detail("case-pass-not-coming-001")
    assert len(client.public_videos(detail)) == 1


def test_case_detail_requires_case_id() -> None:
    client, _ = make_client({})
    with pytest.raises(ValueError):
        client.case_detail("")


def test_http_error_wrapped() -> None:
    client, _ = make_client({"/health": FakeResponse({}, status=500)})
    with pytest.raises(SoccerDiagnosisError):
        client.health()


def test_unexpected_cases_shape_raises() -> None:
    client, _ = make_client({"/cases": FakeResponse({"unexpected": True})})
    with pytest.raises(SoccerDiagnosisError):
        client.cases()


# --- filter tests -----------------------------------------------------------


@pytest.mark.parametrize(
    ("video", "expected"),
    [
        (Video("yt", "public", "approved", False), True),
        (Video("yt", "public", "", True), True),  # consented fallback
        (Video("yt", "public", "pending", False), False),  # not approved/consented
        (Video("", "public", "approved", True), False),  # empty youtube id
        (Video("yt", "private", "approved", True), False),  # not public
    ],
)
def test_is_video_displayable(video: Video, expected: bool) -> None:
    assert is_video_displayable(video) is expected
