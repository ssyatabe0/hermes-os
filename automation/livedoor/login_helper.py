"""ライブドアブログへ一度だけログインし、Atom Pub用パスワード(APIキー)を取得するための
補助スクリプト。**このスクリプトはこのクラウド実行環境では動かせない**
(automation/README.md参照。ネットワークポリシーによりlivedoor.comへ到達できないため)。
ユーザーのローカルMac等、実際にインターネットへ到達できる環境で実行すること。

認証情報の扱い:
  - ID/パスワードはソースコードに書かない。環境変数(automation/.env)から読む。
  - automation/.env はコミットしない(.gitignore設定済み)。
  - 取得したAPIキーもコンソールに表示はするが、ファイルには手動で
    automation/.env の LIVEDOOR_ATOMPUB_KEY として保存すること(自動保存はしない=
    人間が値を確認してから使う)。

使い方:
  1. automation/.env に LIVEDOOR_BLOG_ID と LIVEDOOR_LOGIN_PASSWORD を設定
     (LIVEDOOR_LOGIN_PASSWORD はAPIキー取得のためだけに一時利用し、その後は
     LIVEDOOR_ATOMPUB_KEY を使うのでこの変数は削除してよい)
  2. `pip install playwright && playwright install chromium`
  3. `python -m automation.livedoor.login_helper`
  4. 表示されたブラウザ(headless=False)でログイン状態を確認し、CAPTCHA等が出たら
     手動で解決してからターミナルでEnterを押す
  5. スクリプトがブログ設定のAtom API画面へ自動遷移を試みる。セレクタが実際の
     ページと違って失敗した場合は、その場でブラウザを操作して手動で
     「ブログ設定」→「Atom API」を開き、画面に表示された値を控える
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

from automation.browser.engine import BrowserSession

LOGIN_URL = "https://member.livedoor.com/login/"
BLOG_CONFIG_URL_TMPL = "https://livedoor.blogcms.jp/blog/{blog_id}/config/api"


def main() -> None:
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
    blog_id = os.environ.get("LIVEDOOR_BLOG_ID")
    password = os.environ.get("LIVEDOOR_LOGIN_PASSWORD")
    if not blog_id or not password:
        raise RuntimeError(
            "LIVEDOOR_BLOG_ID / LIVEDOOR_LOGIN_PASSWORD を automation/.env に設定してください。"
        )

    with BrowserSession(profile_name="livedoor", headless=False) as session:
        page = session.goto(LOGIN_URL)
        try:
            page.get_by_label("ライブドアID").fill(blog_id)
            page.get_by_label("パスワード").fill(password)
            page.get_by_role("button", name="ログイン").click()
        except Exception:
            print("自動入力に失敗しました。ページのフォームが想定と異なる可能性があります。")

        session.wait_for_manual_step(
            "ログイン画面を確認してください。自動入力が効かない場合や2段階認証・CAPTCHAが"
            "出た場合はここで手動ログインを完了させてください。"
        )

        config_page = session.goto(BLOG_CONFIG_URL_TMPL.format(blog_id=blog_id))
        session.screenshot("atom_api_config_page")
        print(
            "\nブラウザで「Atom API」欄の『Atom Pub用パスワード』を確認し、"
            "automation/.env の LIVEDOOR_ATOMPUB_KEY として手動で保存してください。"
            "\n(このスクリプトは値を自動でファイルへ書き込みません — 機密情報を人間が"
            "目視確認してから保存する運用にしています)"
        )
        session.wait_for_manual_step("APIキーを控え終えたらEnterを押してください。")


if __name__ == "__main__":
    main()
