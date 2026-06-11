"""Typed models for the Soccer Diagnosis REST API (sdc/v1).

The upstream API returns plain JSON. These dataclasses give us typed,
tolerant access: unknown fields are ignored and missing fields fall back
to sensible defaults, so a minor API addition never breaks ingestion.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any


def _filter_known(cls: type, data: dict[str, Any]) -> dict[str, Any]:
    """Keep only keys that map to a dataclass field on ``cls``."""
    known = {f.name for f in fields(cls)}
    return {k: v for k, v in data.items() if k in known}


@dataclass(frozen=True)
class Health:
    """Response of ``GET /health``."""

    version: str = ""
    cases: int = 0
    videos: int = 0
    reviews: int = 0
    parent_feedback: int = 0
    public_videos: int = 0
    duplicate_case_ids: int = 0
    missing_video_case_refs: int = 0
    public_videos_missing_id: int = 0
    pages: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Health":
        return cls(**_filter_known(cls, data), raw=data)

    @property
    def is_consistent(self) -> bool:
        """True when all integrity counters report no problems."""
        return (
            self.duplicate_case_ids == 0
            and self.missing_video_case_refs == 0
            and self.public_videos_missing_id == 0
        )


@dataclass(frozen=True)
class Case:
    """A single case summary from ``GET /cases``."""

    case_id: str = ""
    title: str = ""
    age_group: str = ""
    age_label: str = ""
    position_group: str = ""
    position_label: str = ""
    problem: str = ""
    cause_summary: str = ""
    improvement_summary: str = ""
    public_summary: str = ""
    symptom_tags: list[str] = field(default_factory=list)
    cause_categories: list[str] = field(default_factory=list)
    result_types: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    video_ids: list[str] = field(default_factory=list)
    review_ids: list[str] = field(default_factory=list)
    parent_feedback_ids: list[str] = field(default_factory=list)
    has_video: bool = False
    has_review: bool = False
    has_parent_feedback: bool = False
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Case":
        return cls(**_filter_known(cls, data), raw=data)


@dataclass(frozen=True)
class Video:
    """A case video. Display gating is handled in ``filters.py``."""

    youtube_video_id: str = ""
    visibility: str = ""
    consent_status: str = ""
    consented: bool = False
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Video":
        return cls(**_filter_known(cls, data), raw=data)


@dataclass(frozen=True)
class Review:
    """A coach/expert review attached to a case."""

    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Review":
        return cls(raw=data)


@dataclass(frozen=True)
class ParentFeedback:
    """A parent/guardian comment attached to a case."""

    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ParentFeedback":
        return cls(raw=data)


@dataclass(frozen=True)
class CTA:
    """Call-to-action links returned with a case detail."""

    line_url: str = ""
    paid_diagnosis_url: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CTA":
        return cls(**_filter_known(cls, data), raw=data)


@dataclass(frozen=True)
class CaseDetail:
    """Response of ``GET /case-detail/{case_id}``."""

    case: Case
    videos: list[Video] = field(default_factory=list)
    reviews: list[Review] = field(default_factory=list)
    parent_feedback: list[ParentFeedback] = field(default_factory=list)
    cta: CTA = field(default_factory=CTA)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CaseDetail":
        return cls(
            case=Case.from_dict(data.get("case") or {}),
            videos=[Video.from_dict(v) for v in data.get("videos") or []],
            reviews=[Review.from_dict(r) for r in data.get("reviews") or []],
            parent_feedback=[
                ParentFeedback.from_dict(p) for p in data.get("parent_feedback") or []
            ],
            cta=CTA.from_dict(data.get("cta") or {}),
            raw=data,
        )
