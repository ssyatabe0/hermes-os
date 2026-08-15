"""A8.net 案件調査モジュール(read-only想定)。

現状 `base.TOS_REGISTRY["A8.net"].automation_allowed == "unknown"` のため、
このモジュールの検索関数を呼ぶと `require_readonly_allowed` が例外を送出し、
自動情報取得は実行されない。

使える状態にするまでの手順:
  1. 人間がA8.netの会員規約・禁止事項ページを読み、自動アクセス/スクレイピングの
     可否を確認する（既に禁止事項ページのURLは `base.TOS_REGISTRY` に記録済み）
  2. 許可される場合、`base.TOS_REGISTRY["A8.net"].automation_allowed` を
     "allowed_readonly" に更新する
  3. `open_and_wait_login()` をローカル(headless=False)で実行し、専用プロファイルで
     人間が一度だけA8.netへログインする
  4. 以後 `search_programs()` を呼べば、ログイン状態を保持したままカテゴリ・キーワード
     検索結果を取得できる(セレクタは実際のページを見て調整が必要。下記はプレースホルダ)

提携申請(`apply_partnership`)は常に allow_write=True かつ人間の最終確認を要求する
設計にしており、既定では絶対に自動実行されない。
"""

from __future__ import annotations

from automation.asp.base import AspProgramRecord, require_readonly_allowed
from automation.browser.engine import BrowserSession

ASP_NAME = "A8.net"
LOGIN_URL = "https://www.a8.net/"
SEARCH_URL = "https://pub.a8.net/a8v2/asp/programSearch"  # 実URLは要確認、プレースホルダ


def open_and_wait_login() -> None:
    """専用プロファイルでA8.netを開き、人間の手動ログインを待つ。ローカルで
    headless=Falseで実行すること。"""
    with BrowserSession(profile_name="a8net", headless=False) as session:
        session.goto(LOGIN_URL)
        session.wait_for_manual_step(
            "A8.netへログインしてください（2段階認証・CAPTCHA等が出た場合もここで対応）。"
        )
        session.screenshot("after_manual_login")


def search_programs(keyword: str, *, service_name: str | None = None) -> list[AspProgramRecord]:
    """キーワードで案件検索し、AspProgramRecordのリストを返す(DB保存は呼び出し側で)。"""
    require_readonly_allowed(ASP_NAME)  # 規約確認が済むまでここで例外になる

    records: list[AspProgramRecord] = []
    with BrowserSession(profile_name="a8net", headless=True, allow_write=False) as session:
        page = session.goto(SEARCH_URL)
        # TODO: 実際のA8.net検索画面のセレクタに合わせて実装する。
        # role/label/text等の安定したロケータを優先すること（固定XPath禁止）。
        session.fill("keyword search box", lambda: page.get_by_placeholder("キーワード"), keyword)
        session.click_navigate("search button", lambda: page.get_by_role("button", name="検索"))
        # 結果テーブルの取得例(プレースホルダ、実セレクタ要調整):
        rows_data = session.extract_table(
            "program results", lambda: page.locator("table.program-list tr").all()
        )
        session.screenshot(f"search_{keyword}")
        for row in rows_data[1:]:  # 先頭行はヘッダ想定
            if not row:
                continue
            records.append(
                AspProgramRecord(
                    asp_name=ASP_NAME,
                    program_name=row[0] if len(row) > 0 else "unknown",
                    service_name=service_name,
                    commission_amount=row[1] if len(row) > 1 else None,
                    source_url=page.url,
                    notes="A8.net検索結果からの自動取得(セレクタ未検証、要人間レビュー)",
                )
            )
    return records
