"""HTTP client for the Soccer Diagnosis REST API (``sdc/v1``).

The API is public and read-only (all ``GET``, no auth). Example::

    from hermes_os.datasources.soccer_diagnosis import SoccerDiagnosisClient

    client = SoccerDiagnosisClient()
    health = client.health()
    cases = client.cases()
    detail = client.case_detail("case-pass-not-coming-001")
    videos = client.public_videos(detail)

Network note: reaching the production host requires it to be present in
the execution environment's network allowlist. The client itself is
transport-agnostic — pass any ``requests.Session``-compatible object to
``session`` for testing or proxying.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import requests

from .filters import displayable_videos
from .models import Case, CaseDetail, Health, Video

DEFAULT_BASE_URL = "https://soccer-kateikyousi.com/diagnosis/wp-json/sdc/v1"
DEFAULT_TIMEOUT = 20.0


class SoccerDiagnosisError(RuntimeError):
    """Raised when the API returns an error or an unexpected payload."""


class SoccerDiagnosisClient:
    """Thin, typed client over the ``sdc/v1`` endpoints."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        session: requests.Session | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = session or requests.Session()

    # -- low-level ---------------------------------------------------------

    def _get(self, path: str) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            response = self._session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:  # network / HTTP errors
            raise SoccerDiagnosisError(f"GET {url} failed: {exc}") from exc
        except ValueError as exc:  # invalid JSON
            raise SoccerDiagnosisError(f"GET {url} returned invalid JSON: {exc}") from exc

    # -- endpoints ---------------------------------------------------------

    def health(self) -> Health:
        """``GET /health`` — counts, integrity checks, fixed-page URLs."""
        return Health.from_dict(self._get("health"))

    def cases(self) -> list[Case]:
        """``GET /cases`` — the full case list."""
        data = self._get("cases")
        items = data.get("cases", data) if isinstance(data, dict) else data
        if not isinstance(items, list):
            raise SoccerDiagnosisError("Unexpected /cases payload shape")
        return [Case.from_dict(item) for item in items]

    def case_detail(self, case_id: str) -> CaseDetail:
        """``GET /case-detail/{case_id}`` — full detail incl. media."""
        if not case_id:
            raise ValueError("case_id is required")
        return CaseDetail.from_dict(self._get(f"case-detail/{quote(case_id, safe='')}"))

    # -- convenience -------------------------------------------------------

    @staticmethod
    def public_videos(detail: CaseDetail) -> list[Video]:
        """Videos from ``detail`` that satisfy the public-display contract."""
        return displayable_videos(detail.videos)
