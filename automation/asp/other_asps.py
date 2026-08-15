"""もしもアフィリエイト・アクセストレード・afb 用のプレースホルダ。

これら3社はまだ規約すら調査していない(`base.TOS_REGISTRY`参照、checked_at=None)。
a8net.py / valuecommerce.py と同じパターンで実装できるよう関数シグネチャだけ
用意している。使う前に必ず `base.TOS_REGISTRY` の該当エントリを調査・更新すること。
"""

from __future__ import annotations

from automation.asp.base import AspProgramRecord, require_readonly_allowed
from automation.browser.engine import BrowserSession

_CONFIG = {
    "もしもアフィリエイト": {"login_url": "https://af.moshimo.com/af/", "profile": "mosimo"},
    "アクセストレード": {"login_url": "https://www.accesstrade.ne.jp/", "profile": "accesstrade"},
    "afb": {"login_url": "https://www.afi-b.com/", "profile": "afb"},
}


def open_and_wait_login(asp_name: str) -> None:
    cfg = _CONFIG[asp_name]
    with BrowserSession(profile_name=cfg["profile"], headless=False) as session:
        session.goto(cfg["login_url"])
        session.wait_for_manual_step(f"{asp_name}へログインしてください。")
        session.screenshot("after_manual_login")


def search_programs(asp_name: str, keyword: str, *, service_name: str | None = None) -> list[AspProgramRecord]:
    require_readonly_allowed(asp_name)  # 現状すべて未調査のためここで必ず例外になる
    raise NotImplementedError(
        f"{asp_name} は検索画面のセレクタが未実装です。規約確認・ログイン確認後に"
        f"a8net.py / valuecommerce.py と同じパターンで実装してください。"
    )
