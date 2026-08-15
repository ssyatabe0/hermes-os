"""汎用ブラウザ自動化エンジンの動作確認スクリプト。

外部サイトではなく、ローカルで立てた静的HTMLページに対して
起動/遷移/クリック/入力/検索/テーブル取得/リンク取得/スクリーンショットを一通り試す。
このクラウド実行環境ではlivedoor.com等の外部サイトへ到達できないため
(automation/README.md参照)、まずここでエンジンの機構そのものが正しく動くことを
確認してから、到達可能な環境(ローカルMac等)で実サイトに対して使う。

実行結果(2026-08-15、Claude Code on the webのサンドボックス内で確認済み):
  TITLE: Local Test Page
  RESULT TEXT: searched: エアコンクリーニング 港区
  TABLE: [['advertiser', 'commission'], ['Example Reform Co', '15000'], ...]
  LINKS: [{'text': 'Program detail 1', 'href': '.../detail1'}, ...]
  スクリーンショット保存も成功。
"""

from __future__ import annotations

import http.server
import socketserver
import threading
import time
from pathlib import Path

from automation.browser.engine import BrowserSession

TEST_HTML = """<!doctype html>
<html><head><title>Local Test Page</title></head>
<body>
  <h1>Automation Smoke Test</h1>
  <form id="search-form">
    <input type="text" name="q" id="q" placeholder="keyword">
    <button type="submit" id="search-btn">Search</button>
  </form>
  <div id="result"></div>
  <table id="programs">
    <tr><th>advertiser</th><th>commission</th></tr>
    <tr><td>Example Reform Co</td><td>15000</td></tr>
    <tr><td>Example Cleaning Co</td><td>4000</td></tr>
  </table>
  <a href="/detail1">Program detail 1</a>
  <a href="/detail2">Program detail 2</a>
  <script>
    document.getElementById('search-form').addEventListener('submit', function(e){
      e.preventDefault();
      document.getElementById('result').textContent = 'searched: ' + document.getElementById('q').value;
    });
  </script>
</body></html>"""


def _serve(directory: Path, port: int):
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(*a, directory=str(directory), **kw)
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        httpd.serve_forever()


def main():
    tmp_dir = Path("/tmp/hermes_pw_smoke_test")
    tmp_dir.mkdir(exist_ok=True)
    (tmp_dir / "index.html").write_text(TEST_HTML, encoding="utf-8")

    port = 8899
    t = threading.Thread(target=_serve, args=(tmp_dir, port), daemon=True)
    t.start()
    time.sleep(1)

    with BrowserSession(profile_name="smoke_test", headless=True) as session:
        page = session.goto(f"http://127.0.0.1:{port}/")
        print("TITLE:", page.title())

        session.fill("keyword box", lambda: page.get_by_placeholder("keyword"), "エアコンクリーニング 港区")
        session.click_navigate("search button", lambda: page.get_by_role("button", name="Search"))
        print("RESULT TEXT:", session.extract_text(lambda: page.locator("#result")))

        table = session.extract_table("programs table", lambda: page.locator("#programs tr").all())
        print("TABLE:", table)

        print("LINKS:", session.extract_links())

        path = session.screenshot("smoke_test")
        print("SCREENSHOT:", path)


if __name__ == "__main__":
    main()
