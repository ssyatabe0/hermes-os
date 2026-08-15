"""汎用ブラウザ自動化エンジン(Playwright)。

設計方針:
  - ASP専用コードにしない。競合調査・料金調査・施工会社調査等にも使える汎用モジュール。
  - 既存の本番Chromeプロファイルには一切触れない。専用プロファイル(automation/profiles/<name>)
    をpersistent contextとして開く。
  - デフォルトはread-only。フォーム送信・申請・購入・契約・削除等の「書き込み系」操作は
    `allow_write=True` を明示的に渡さない限り拒否する。
  - 固定XPathに頼らず、role/label/text等の安定したロケータを優先する（Playwrightの
    get_by_role/get_by_label/get_by_text/get_by_placeholder を使う）。
  - すべての操作を automation/logs/ へ構造化ログとして記録する。パスワード・Cookie・
    トークン等の機密情報はログに出さない。
  - このコードは「このMac」ではなく、実行しているマシン上でPlaywrightとネットワーク到達性が
    ある場合にのみ動作する。クラウドのClaude Code環境ではネットワークポリシーにより
    外部サイトへ到達できない場合がある（automation/README.md参照）。

使い方の例は automation/scripts/smoke_test_local.py を参照。
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from playwright.sync_api import BrowserContext, Page, sync_playwright

AUTOMATION_ROOT = Path(__file__).resolve().parent.parent
PROFILES_DIR = AUTOMATION_ROOT / "profiles"
LOGS_DIR = AUTOMATION_ROOT / "logs"
SCREENSHOTS_DIR = AUTOMATION_ROOT / "screenshots"

for d in (PROFILES_DIR, LOGS_DIR, SCREENSHOTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

def _discover_chromium_path() -> Optional[str]:
    """使用するChromium実行ファイルを決定する。

    1. HERMES_CHROMIUM_PATH が設定されていればそれを最優先で使う
    2. PLAYWRIGHT_BROWSERS_PATH配下に "chromium-*/chrome-linux/chrome" があれば
       それを明示的に使う（pip版playwrightが期待するリビジョンと、事前インストール
       済みブラウザのリビジョンがズレている環境があるため、自動選択に頼らず
       確実に存在するフルChromiumバイナリを直接指定する）
    3. どちらもなければ None を返し、Playwrightのデフォルト解決に任せる
       （通常の `playwright install chromium` 済みローカル環境向け）
    """
    override = os.environ.get("HERMES_CHROMIUM_PATH")
    if override:
        return override

    browsers_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if browsers_path and Path(browsers_path).is_dir():
        candidates = sorted(Path(browsers_path).glob("chromium-*/chrome-linux/chrome"))
        if candidates:
            return str(candidates[-1])
    return None


_CHROMIUM_PATH_OVERRIDE = _discover_chromium_path()

_SECRET_KEYS = {"password", "pass", "token", "cookie", "session", "api_key", "apikey", "secret"}


def _redact(obj: Any) -> Any:
    """ログ出力前に機密情報らしきキーをマスクする。"""
    if isinstance(obj, dict):
        return {
            k: ("***redacted***" if any(s in k.lower() for s in _SECRET_KEYS) else _redact(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_redact(v) for v in obj]
    return obj


@dataclass
class ActionLog:
    log_path: Path = field(default_factory=lambda: LOGS_DIR / f"{time.strftime('%Y%m%d')}.jsonl")

    def write(self, *, site: str, action: str, detail: Optional[dict] = None,
              result: str = "ok", error: Optional[str] = None) -> None:
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "site": site,
            "action": action,
            "detail": _redact(detail or {}),
            "result": result,
            "error": error,
        }
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


class WriteActionBlocked(RuntimeError):
    """read-onlyモードで書き込み系操作(送信/申請/購入/契約/設定変更/削除)が呼ばれた場合。"""


class BrowserSession:
    """専用Chromeプロファイルを使うPlaywrightセッション。

    profile_name: automation/profiles/<profile_name> にユーザーデータを保存する。
                  ASPごとに分ける想定（例: "a8net", "valuecommerce", "livedoor"）。
    allow_write:  Falseの場合、submit/click_apply等の書き込み系メソッドは例外を投げる。
                  デフォルトFalse（read-only/dry-run）。
    headless:     Trueだとユーザーが画面を見て手動ログインできない。ローカルで手動ログインが
                  必要な初回はheadless=Falseで起動すること。
    """

    def __init__(self, profile_name: str, *, allow_write: bool = False, headless: bool = True):
        self.profile_name = profile_name
        self.allow_write = allow_write
        self.headless = headless
        self.profile_dir = PROFILES_DIR / profile_name
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.log = ActionLog()
        self._pw = None
        self._context: Optional[BrowserContext] = None

    def __enter__(self) -> "BrowserSession":
        self._pw = sync_playwright().start()
        launch_kwargs = dict(
            user_data_dir=str(self.profile_dir),
            headless=self.headless,
            args=["--no-sandbox"],
            ignore_https_errors=True,  # プロキシ環境でのTLS再終端に対応
        )
        if _CHROMIUM_PATH_OVERRIDE:
            launch_kwargs["executable_path"] = _CHROMIUM_PATH_OVERRIDE
        self._context = self._pw.chromium.launch_persistent_context(**launch_kwargs)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._context:
            self._context.close()
        if self._pw:
            self._pw.stop()

    @property
    def page(self) -> Page:
        pages = self._context.pages
        return pages[0] if pages else self._context.new_page()

    # ---- read-only操作 ----

    def goto(self, url: str, *, timeout: int = 30000) -> Page:
        page = self.page
        try:
            page.goto(url, timeout=timeout)
            self.log.write(site=url, action="goto", detail={"url": url})
        except Exception as e:  # noqa: BLE001
            self.log.write(site=url, action="goto", result="error", error=str(e))
            self._save_error_screenshot(page, "goto_error")
            raise
        return page

    def fill(self, locator_desc: str, get_locator_fn, value: str) -> None:
        """検索フォーム等への入力(書き込みではあるが「探す」ための操作なのでread-only扱い)。
        パスワード等の機密値はログにマスクされるが、呼び出し側でも値そのものをログに
        直接残さないこと。"""
        try:
            get_locator_fn().fill(value)
            self.log.write(site=self.page.url, action="fill",
                            detail={"locator": locator_desc, "value_length": len(value)})
        except Exception as e:  # noqa: BLE001
            self.log.write(site=self.page.url, action="fill", result="error", error=str(e))
            raise

    def click_navigate(self, locator_desc: str, get_locator_fn) -> None:
        """遷移・検索・絞り込みのためのクリック。フォーム送信で申請/購入/契約が
        確定する場合は click_navigate ではなく submit_write を使うこと。"""
        try:
            get_locator_fn().click()
            self.log.write(site=self.page.url, action="click_navigate", detail={"locator": locator_desc})
        except Exception as e:  # noqa: BLE001
            self.log.write(site=self.page.url, action="click_navigate", result="error", error=str(e))
            self._save_error_screenshot(self.page, "click_error")
            raise

    def extract_text(self, get_locator_fn) -> Optional[str]:
        loc = get_locator_fn()
        return loc.inner_text() if loc.count() else None

    def extract_table(self, table_locator_desc: str, get_rows_fn) -> list[list[str]]:
        rows = get_rows_fn()
        data = [r.locator("td,th").all_inner_texts() for r in rows]
        self.log.write(site=self.page.url, action="extract_table",
                        detail={"locator": table_locator_desc, "row_count": len(data)})
        return data

    def extract_links(self, selector: str = "a") -> list[dict]:
        page = self.page
        links = page.eval_on_selector_all(
            selector, "els => els.map(e => ({text: e.textContent.trim(), href: e.href}))"
        )
        self.log.write(site=page.url, action="extract_links", detail={"count": len(links)})
        return links

    def screenshot(self, name: str) -> Path:
        path = SCREENSHOTS_DIR / f"{self.profile_name}_{name}_{int(time.time())}.png"
        self.page.screenshot(path=str(path))
        self.log.write(site=self.page.url, action="screenshot", detail={"path": str(path)})
        return path

    def _save_error_screenshot(self, page: Page, tag: str) -> None:
        try:
            path = SCREENSHOTS_DIR / f"{self.profile_name}_{tag}_{int(time.time())}.png"
            page.screenshot(path=str(path))
        except Exception:  # noqa: BLE001
            pass  # スクリーンショット自体の失敗でエラーハンドリングを止めない

    def wait_for_manual_step(self, message: str, *, check_fn=None, timeout_sec: int = 600) -> bool:
        """CAPTCHA・2段階認証・ログイン等、人間の操作が必要な箇所で使う。
        headless=Falseでローカル実行している前提。check_fnがNoneの場合は
        タイムアウトまでポーリングせず、標準入力でEnter待ちにする(ローカルTTY向け)。"""
        print(f"\n[手動操作が必要です] {message}")
        self.log.write(site=self.page.url, action="wait_for_manual_step",
                        detail={"message": message})
        if check_fn is None:
            try:
                input("完了したらEnterキーを押してください... ")
                return True
            except EOFError:
                # 非対話環境(サーバー実行等)ではポーリングにフォールバック
                pass
        start = time.time()
        while time.time() - start < timeout_sec:
            if check_fn and check_fn():
                return True
            time.sleep(3)
        return False

    # ---- 書き込み系操作(デフォルト禁止) ----

    def submit_write(self, action_name: str, get_locator_fn, *, confirm_message: str) -> None:
        """フォーム送信・提携申請・購入・契約・設定変更・削除等、外部に影響する操作。
        allow_write=Trueで明示的に許可されない限り実行しない。"""
        if not self.allow_write:
            self.log.write(site=self.page.url, action=action_name, result="blocked",
                            error="allow_write=False (read-only mode)")
            raise WriteActionBlocked(
                f"'{action_name}' は書き込み系操作のためread-onlyモードでは実行しません。"
                f"実行するには BrowserSession(allow_write=True) を明示してください。"
                f"確認事項: {confirm_message}"
            )
        get_locator_fn().click()
        self.log.write(site=self.page.url, action=action_name, detail={"confirm_message": confirm_message})
