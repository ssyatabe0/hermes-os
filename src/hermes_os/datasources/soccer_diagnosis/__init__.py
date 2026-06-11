"""Soccer Diagnosis REST API (``sdc/v1``) data source.

Public, read-only API exposing soccer-skill diagnosis cases, videos,
reviews and parent feedback. See ``client.SoccerDiagnosisClient``.
"""

from .client import (
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT,
    SoccerDiagnosisClient,
    SoccerDiagnosisError,
)
from .filters import displayable_videos, is_video_displayable
from .models import (
    CTA,
    Case,
    CaseDetail,
    Health,
    ParentFeedback,
    Review,
    Video,
)

__all__ = [
    "CTA",
    "DEFAULT_BASE_URL",
    "DEFAULT_TIMEOUT",
    "Case",
    "CaseDetail",
    "Health",
    "ParentFeedback",
    "Review",
    "SoccerDiagnosisClient",
    "SoccerDiagnosisError",
    "Video",
    "displayable_videos",
    "is_video_displayable",
]
