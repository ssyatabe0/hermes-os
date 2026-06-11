# Soccer Diagnosis data source (`sdc/v1`)

Typed Python client for the public, read-only Soccer Diagnosis REST API.

- **Base URL:** `https://soccer-kateikyousi.com/diagnosis/wp-json/sdc/v1`
- **Auth:** none (all `GET`)
- **Production state (reference):** `version 0.5.7`, 105 cases, 9 videos, 3 reviews, 3 parent feedback, 9 public videos.

## Endpoints

| Method | Path | Returns |
| --- | --- | --- |
| `GET` | `/health` | counts, integrity checks, fixed-page URLs |
| `GET` | `/cases` | full case list (105) |
| `GET` | `/case-detail/{case_id}` | case + videos + reviews + parent_feedback + cta |

## Usage

```python
from hermes_os.datasources.soccer_diagnosis import SoccerDiagnosisClient

client = SoccerDiagnosisClient()           # defaults to the production base URL
health = client.health()                   # Health
assert health.is_consistent                # duplicate/missing counters all 0

cases = client.cases()                     # list[Case]
detail = client.case_detail("case-pass-not-coming-001")  # CaseDetail
videos = client.public_videos(detail)      # only publicly displayable videos
```

## Video display contract

A video is publicly displayable only when **all** hold (see `filters.py`):

1. `visibility == "public"`
2. `consent_status == "approved"` **or** `consented is True`
3. `youtube_video_id` is non-empty

This mirrors the upstream `public_videos` count so client and WordPress
theme agree on visibility.

## Network access

The production host must be in the execution environment's **network
allowlist** to be reachable; otherwise requests fail with
`Host not in allowlist`. The client is transport-agnostic — pass any
`requests.Session`-compatible object via `session=` for tests/proxying
(see `tests/test_soccer_diagnosis.py`).

## Tests

```bash
python3 -m pytest tests/test_soccer_diagnosis.py
```

Tests use canned JSON modelled on the v0.5.7 contract — no network required.
```
