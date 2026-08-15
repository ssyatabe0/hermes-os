"""ライブドアブログ AtomPub API クライアント(公式API、ブラウザ操作不要)。

認証は「Atom Pub用パスワード(APIキー)」を使う。ログインパスワードとは別物で、
ブログ設定タブ→「Atom API」から取得する(手順は login_helper.py 参照)。

環境変数(automation/.env、コミットしない):
  LIVEDOOR_BLOG_ID       例: ssyatabe2
  LIVEDOOR_ATOMPUB_KEY   ブログ設定画面で発行したAPIキー(ログインパスワードではない)

使い方:
  python -m automation.livedoor.atompub_client --title "..." --body-file draft.html --draft
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import requests
from requests.auth import HTTPBasicAuth

ATOM_ENDPOINT_TMPL = "https://livedoor.blogcms.jp/atom/blog/{blog_id}/article"


@dataclass
class LivedoorCredentials:
    blog_id: str
    atompub_key: str

    @classmethod
    def from_env(cls) -> "LivedoorCredentials":
        blog_id = os.environ.get("LIVEDOOR_BLOG_ID")
        key = os.environ.get("LIVEDOOR_ATOMPUB_KEY")
        if not blog_id or not key:
            raise RuntimeError(
                "LIVEDOOR_BLOG_ID / LIVEDOOR_ATOMPUB_KEY が環境変数に設定されていません。"
                "automation/.env.example を参考に automation/.env を作成してください"
                "(ログインパスワードではなく、ブログ設定のAtom APIキーを使うこと)。"
            )
        return cls(blog_id=blog_id, atompub_key=key)


def _atom_entry_xml(title: str, body_html: str, *, draft: bool) -> str:
    draft_elem = '<app:control xmlns:app="http://purl.org/atom/app#"><app:draft>yes</app:draft></app:control>' if draft else ""
    # XMLエスケープは最小限。実運用では xml.sax.saxutils.escape を使うこと。
    from xml.sax.saxutils import escape

    return f"""<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://www.w3.org/2005/Atom">
  <title>{escape(title)}</title>
  <content type="text/plain">{escape(body_html)}</content>
  {draft_elem}
</entry>"""


def post_article(title: str, body_html: str, *, draft: bool = True,
                  creds: LivedoorCredentials | None = None) -> requests.Response:
    """記事を投稿する。draft=True(既定)なら下書き保存で、ライブ公開はしない。
    実際に公開する場合のみ呼び出し側でdraft=Falseを明示すること(人間の最終確認を推奨)。"""
    creds = creds or LivedoorCredentials.from_env()
    url = ATOM_ENDPOINT_TMPL.format(blog_id=creds.blog_id)
    xml = _atom_entry_xml(title, body_html, draft=draft)
    resp = requests.post(
        url,
        data=xml.encode("utf-8"),
        headers={"Content-Type": "application/atom+xml;type=entry"},
        auth=HTTPBasicAuth(creds.blog_id, creds.atompub_key),
        timeout=30,
    )
    resp.raise_for_status()
    return resp


def list_articles(creds: LivedoorCredentials | None = None) -> requests.Response:
    creds = creds or LivedoorCredentials.from_env()
    url = ATOM_ENDPOINT_TMPL.format(blog_id=creds.blog_id)
    resp = requests.get(url, auth=HTTPBasicAuth(creds.blog_id, creds.atompub_key), timeout=30)
    resp.raise_for_status()
    return resp


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ライブドアブログへAtomPub経由で記事を投稿する")
    parser.add_argument("--title", required=True)
    parser.add_argument("--body-file", required=True, help="本文HTML/テキストファイルのパス")
    parser.add_argument("--publish", action="store_true", help="指定しない場合は下書き保存のみ")
    args = parser.parse_args()

    body = open(args.body_file, encoding="utf-8").read()
    r = post_article(args.title, body, draft=not args.publish)
    print("status:", r.status_code)
