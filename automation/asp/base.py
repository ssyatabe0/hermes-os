"""ASP共通基盤: 規約確認レジストリ、案件レコードのDB保存。

重要な方針(ユーザー指示に基づく):
  - 各ASPについて、自動操作(ログイン後の情報取得・提携申請)が規約上許可されるかを
    人間が一次規約文書で確認するまでは、`automation_allowed` を "unknown" のままにする。
  - "unknown" または "prohibited" の場合、read-onlyの情報取得すら自動実行しない
    （＝プロファイルを開いて人間が手動ログイン・手動閲覧するところまでしか支援しない）。
  - "allowed_readonly" になったASPのみ、ログイン後の案件検索・情報取得を自動化してよい。
    提携申請(≒契約行為)は別区分 `application_allowed` で管理し、真に規約上明確な場合のみ
    Trueにする。デフォルトはFalse=人間が最終確認して手動申請。
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).resolve().parent.parent.parent / "db" / "hermes.db"


@dataclass
class AspToSStatus:
    asp_name: str
    automation_allowed: str  # "unknown" | "prohibited" | "allowed_readonly"
    application_allowed: bool  # 提携申請の自動化を許可するか(現状すべてFalse固定)
    tos_url: str
    checked_at: Optional[str]
    notes: str


# 2026-08-15時点の調査結果。一次規約文書の該当条項までは未確認のため、
# 全ASPとも automation_allowed="unknown" をデフォルトにしている。
# 人間が規約を読んで判断した場合のみ、このテーブルの値を更新すること。
TOS_REGISTRY: dict[str, AspToSStatus] = {
    "A8.net": AspToSStatus(
        asp_name="A8.net",
        automation_allowed="unknown",
        application_allowed=False,
        tos_url="https://www.a8.net/compliance/prohibited-matter.php",
        checked_at="2026-08-15",
        notes="WebSearchでは自動アクセス/スクレイピング/botに関する明示条項を確認できなかった。"
              "会員規約本文を人間が確認するまでread-only自動化も行わない。",
    ),
    "バリューコマース": AspToSStatus(
        asp_name="バリューコマース",
        automation_allowed="unknown",
        application_allowed=False,
        tos_url="https://www.valuecommerce.ne.jp/st_affiliate/terms.html",
        checked_at="2026-08-15",
        notes="同上。自動アクセスに関する明示条項は未確認。",
    ),
    "もしもアフィリエイト": AspToSStatus(
        asp_name="もしもアフィリエイト", automation_allowed="unknown", application_allowed=False,
        tos_url="https://af.moshimo.com/af/rule", checked_at=None,
        notes="未調査。",
    ),
    "アクセストレード": AspToSStatus(
        asp_name="アクセストレード", automation_allowed="unknown", application_allowed=False,
        tos_url="https://www.accesstrade.ne.jp/", checked_at=None,
        notes="未調査。",
    ),
    "afb": AspToSStatus(
        asp_name="afb", automation_allowed="unknown", application_allowed=False,
        tos_url="https://www.afi-b.com/", checked_at=None,
        notes="未調査。",
    ),
}


def is_readonly_automation_allowed(asp_name: str) -> bool:
    status = TOS_REGISTRY.get(asp_name)
    return bool(status and status.automation_allowed == "allowed_readonly")


def require_readonly_allowed(asp_name: str) -> None:
    if not is_readonly_automation_allowed(asp_name):
        status = TOS_REGISTRY.get(asp_name)
        reason = status.notes if status else "未登録のASP"
        raise PermissionError(
            f"{asp_name} は規約上の自動操作可否が確認できていません({reason})。"
            f"手動ログイン・手動閲覧のみサポートします。"
            f"人間が規約を確認しTOS_REGISTRYを更新してから自動情報取得を有効化してください。"
        )


@dataclass
class AspProgramRecord:
    asp_name: str
    program_name: str
    service_name: Optional[str] = None  # service_catalog.service_name と一致させる
    program_id: Optional[str] = None
    advertiser: Optional[str] = None
    category: Optional[str] = None
    program_url: Optional[str] = None
    commission_type: Optional[str] = None
    commission_amount: Optional[str] = None
    recurring_commission: Optional[str] = None
    conversion_condition: Optional[str] = None
    approval_conditions: Optional[str] = None
    cookie_duration_days: Optional[int] = None
    partnership_status: str = "unknown"
    status: str = "active"
    data_type: str = "actual"  # 実ブラウザから取得した値なのでデフォルトactual
    notes: Optional[str] = None
    source_url: Optional[str] = None


def save_asp_programs(records: list[AspProgramRecord]) -> int:
    """取得したASP案件を db/hermes.db の asp_programs へ追記する(追記専用、UPDATEしない)。"""
    now = time.strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    try:
        n = 0
        for r in records:
            conn.execute(
                """INSERT INTO asp_programs
                   (service_id, asp_name, program_id, advertiser, program_name, category,
                    program_url, commission_type, commission_amount, recurring_commission,
                    conversion_condition, approval_conditions, cookie_duration_days,
                    partnership_status, status, data_type, notes, source_url,
                    last_checked_at, collected_at)
                   VALUES (
                    (SELECT service_id FROM service_catalog WHERE service_name=?),
                    ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    r.service_name, r.asp_name, r.program_id, r.advertiser, r.program_name,
                    r.category, r.program_url, r.commission_type, r.commission_amount,
                    r.recurring_commission, r.conversion_condition, r.approval_conditions,
                    r.cookie_duration_days, r.partnership_status, r.status, r.data_type,
                    r.notes, r.source_url, now, now,
                ),
            )
            n += 1
        conn.commit()
        return n
    finally:
        conn.close()
