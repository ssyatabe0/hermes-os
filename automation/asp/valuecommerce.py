"""バリューコマース 案件調査モジュール(read-only想定)。構成はa8net.pyと同様。

`base.TOS_REGISTRY["バリューコマース"].automation_allowed == "unknown"` のため、
人間が利用規約(https://www.valuecommerce.ne.jp/st_affiliate/terms.html)を確認し
レジストリを更新するまで、`search_programs` は例外を送出し実行されない。
"""

from __future__ import annotations

from automation.asp.base import AspProgramRecord, require_readonly_allowed
from automation.browser.engine import BrowserSession

ASP_NAME = "バリューコマース"
LOGIN_URL = "https://www.valuecommerce.ne.jp/"
SEARCH_URL = "https://pub.valuecommerce.ne.jp/mypage/ad/search"  # 実URLは要確認、プレースホルダ


def open_and_wait_login() -> None:
    with BrowserSession(profile_name="valuecommerce", headless=False) as session:
        session.goto(LOGIN_URL)
        session.wait_for_manual_step("バリューコマースへログインしてください。")
        session.screenshot("after_manual_login")


def search_programs(keyword: str, *, service_name: str | None = None) -> list[AspProgramRecord]:
    require_readonly_allowed(ASP_NAME)

    records: list[AspProgramRecord] = []
    with BrowserSession(profile_name="valuecommerce", headless=True, allow_write=False) as session:
        page = session.goto(SEARCH_URL)
        # TODO: 実際の検索画面のセレクタに合わせて実装する(プレースホルダ)。
        session.fill("keyword search box", lambda: page.get_by_placeholder("キーワード"), keyword)
        session.click_navigate("search button", lambda: page.get_by_role("button", name="検索"))
        rows_data = session.extract_table(
            "program results", lambda: page.locator("table.ad-list tr").all()
        )
        session.screenshot(f"search_{keyword}")
        for row in rows_data[1:]:
            if not row:
                continue
            records.append(
                AspProgramRecord(
                    asp_name=ASP_NAME,
                    program_name=row[0] if len(row) > 0 else "unknown",
                    service_name=service_name,
                    commission_amount=row[1] if len(row) > 1 else None,
                    source_url=page.url,
                    notes="バリューコマース検索結果からの自動取得(セレクタ未検証、要人間レビュー)",
                )
            )
    return records
