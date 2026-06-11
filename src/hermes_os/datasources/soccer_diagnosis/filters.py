"""Display-gating rules for case videos.

A video may be shown publicly only when ALL of the following hold:

* ``visibility == "public"``
* ``consent_status == "approved"`` OR ``consented is True``
* ``youtube_video_id`` is non-empty

These rules mirror the upstream `public_videos` definition so the
client and the WordPress theme agree on what is publicly visible.
"""

from __future__ import annotations

from collections.abc import Iterable

from .models import Video


def is_video_displayable(video: Video) -> bool:
    """Return True when ``video`` satisfies the public-display contract."""
    if video.visibility != "public":
        return False
    if not (video.consent_status == "approved" or video.consented):
        return False
    return bool(video.youtube_video_id)


def displayable_videos(videos: Iterable[Video]) -> list[Video]:
    """Filter an iterable of videos down to the publicly displayable ones."""
    return [v for v in videos if is_video_displayable(v)]
