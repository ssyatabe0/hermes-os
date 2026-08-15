"""専用Chromeプロファイルの管理ユーティリティ。

重要: このモジュールはユーザーの本番Chromeプロファイル(通常
~/Library/Application Support/Google/Chrome/... 等)には一切触れない。
automation/profiles/<name> 配下に、自動化専用のまっさらなプロファイルを作る。
初回はここへ人間が手動ログインし、以後はセッションを保持して再利用する
（第1候補方式。CDPで既存Chromeへ接続する第2候補、既存プロファイルのコピーを使う
第3候補は、本番プロファイルを壊すリスクがあるため現時点では未実装）。
"""

from __future__ import annotations

import shutil
from pathlib import Path

PROFILES_DIR = Path(__file__).resolve().parent.parent / "profiles"


def profile_path(name: str) -> Path:
    p = PROFILES_DIR / name
    p.mkdir(parents=True, exist_ok=True)
    return p


def list_profiles() -> list[str]:
    if not PROFILES_DIR.exists():
        return []
    return sorted(p.name for p in PROFILES_DIR.iterdir() if p.is_dir())


def profile_exists(name: str) -> bool:
    return (PROFILES_DIR / name).exists()


def reset_profile(name: str) -> None:
    """指定した自動化専用プロファイルだけを削除する（本番Chromeには影響しない）。
    ログイン状態をやり直したい時に使う。実行前に本当に消してよいか確認すること。"""
    path = PROFILES_DIR / name
    if path.exists():
        shutil.rmtree(path)
