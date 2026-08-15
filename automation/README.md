# automation/ — ブラウザ自動化基盤

## 0. 最初に: このコードがどこで動くか

**重要な前提の訂正（2026-08-15）:** Claude Codeとのこのセッションは、ユーザーのMac上ではなく
Anthropicが用意したクラウド上の隔離コンテナ（Claude Code on the web）で動いている。
ユーザーのローカルPC・ローカルChrome・既存ログイン済みセッションには一切アクセスできない。

このクラウド実行環境には、さらに**ネットワークポリシーによる制約**もある。検証の結果、
このコンテナから `livedoor.com` や `a8.net` のような一般の外部サイトへの接続は
プロキシ側で `403 (policy denial)` として拒否されることを確認済み
（`curl -x $HTTPS_PROXY https://example.com` で再現可能。詳細は
`STATUS.md`・`DECISIONS.md` の該当エントリ参照）。npm/PyPI/GitHub/Anthropic等の
限定されたホストへの接続は許可されているため、`pip install playwright` 自体は成功し、
Chromiumも起動できるが、任意の外部サイトへは到達できない。

したがって、このディレクトリのコードは**実際に動かす場所によって次のように整理される**:

| 実行場所 | できること |
|---|---|
| このクラウドセッション(Claude Code on the web) | Playwrightの機構そのものの動作確認（`scripts/smoke_test_local.py`、ローカルに立てたテストページに対してのみ）、コードの作成・レビュー・DB統合、規約リサーチ |
| ユーザーのローカルMac（Claude Code CLIをローカルで起動、または人間が直接実行） | livedoor/A8.net/バリューコマース等、実際の外部サイトへのアクセス。手動ログインが必要な箇所も、ユーザーが自分の画面を見ながら操作できる |

**外部サイトを実際に操作したい場合は、このリポジトリをユーザーのMac上でclone/pullし、
Claude Code CLIをローカルで起動して続きを行うのが最も確実。**
（参考: このクラウド環境自体のネットワークポリシーを変更できる場合は
https://code.claude.com/docs/en/claude-code-on-the-web を参照。ただしポリシーを
開放しても、この環境には画面がなく人間がブラウザを目で見て手動ログインする手段が
ないため、CAPTCHA・2段階認証が絡む操作は結局ローカル実行が必要になる）

## 1. 動作確認済みの事実（2026-08-15、このクラウドセッション内で実施）

- Playwright(Python版)のインストールに成功（`pip install playwright`）
- 事前インストール済みChromium(`/opt/pw-browsers/chromium-1194`)の起動に成功
- ローカルの静的テストページに対して、起動・遷移・フォーム入力・クリック・検索結果表示・
  テーブル抽出・リンク抽出・スクリーンショット保存まで一通り成功
  （`python -m automation.scripts.smoke_test_local` で再現可能）
- read-onlyモードでの書き込み系操作（フォーム送信＝提携申請相当）のブロックを確認
- 規約未確認ASP（A8.net等）に対する自動アクセスのブロックを確認
- 一般的な外部サイト(`example.com`, `www.google.com`, `pypi.org`)への到達は、
  ネットワークポリシー拒否(403)またはボット判定ページ("Client Challenge")により失敗

## 2. アーキテクチャ

```
Claude Code / 人間
      ↓
automation/browser/engine.py   … 汎用Playwrightラッパー(専用プロファイル、read-only既定、
                                   構造化ログ、role/label優先セレクタ、スクリーンショット)
      ↓
automation/asp/base.py         … ASP規約レジストリ(TOS_REGISTRY)、DB保存関数
automation/asp/a8net.py        … A8.net用モジュール(規約確認済みになるまでブロック)
automation/asp/valuecommerce.py… バリューコマース用モジュール(同上)
automation/asp/other_asps.py   … もしも/アクセストレード/afb用プレースホルダ
automation/livedoor/           … ライブドアブログ: AtomPub API(推奨) + ログイン補助
      ↓
db/hermes.db (asp_programs テーブル等) … 既存の地域×サービス需要DBと統合
```

汎用エンジン(`browser/engine.py`)はASP専用ではなく、将来の競合調査・料金調査・
施工会社調査等にも流用できる設計にしている。

## 3. 安全設計（既定でブロックされるもの）

| 操作 | 既定動作 |
|---|---|
| ページ遷移・検索・クリック・テキスト/テーブル/リンク抽出・スクリーンショット | 許可（read-only） |
| フォーム送信・提携申請・購入・契約・設定変更・削除 | **既定で例外を投げてブロック**(`BrowserSession(allow_write=True)`を明示しない限り実行不可) |
| 規約上の自動操作可否が未確認("unknown")のASPへの自動アクセス | **完全にブロック**(read-onlyの情報取得すら不可、手動ログインの補助のみ) |
| CAPTCHA・2段階認証 | 自動で突破しようとせず、`wait_for_manual_step()`で人間の操作待ちに切り替える |
| パスワード・Cookie・トークン | ソースコードへ直接記述しない(`.env`経由)。ログには自動マスクされる |

## 4. ASPごとの規約確認状況（`automation/asp/base.py` の `TOS_REGISTRY` が正）

| ASP | automation_allowed | 備考 |
|---|---|---|
| A8.net | unknown | 禁止事項ページは特定したが自動アクセス条項は未確認。人間の確認待ち |
| バリューコマース | unknown | 同上 |
| もしもアフィリエイト | unknown | 未調査 |
| アクセストレード | unknown | 未調査 |
| afb | unknown | 未調査 |

**現状、どのASPに対しても自動情報取得は実行されない。** 人間が規約を確認して
`TOS_REGISTRY`の値を`"allowed_readonly"`に変更した場合のみ、read-onlyの検索・情報取得が
動く設計。提携申請の自動化(`application_allowed`)はすべて`False`固定とし、常に人間が
最終確認して手動で申請する運用にしている。

## 5. セットアップ（ローカルMac等、実際にインターネットへ到達できる環境向け）

```bash
cd hermes-os
pip install -r automation/requirements.txt
playwright install chromium   # ローカルでは実行してよい(このクラウド環境では不要/使わない)
cp automation/.env.example automation/.env
# automation/.env を編集してライブドアの情報等を入れる(パスワードは一時利用のみ)
```

## 6. 使い方

```bash
# 1. 動作確認(ローカルのテストページのみ、ネットワーク不要)
python -m automation.scripts.smoke_test_local

# 2. ライブドアブログ: AtomPub用APIキーを取得(要ローカル実行、手動ログイン)
python -m automation.livedoor.login_helper

# 3. ライブドアブログへ下書き投稿(APIキー取得後。--publishを付けない限り下書きのみ)
python -m automation.livedoor.atompub_client --title "タイトル" --body-file draft.html

# 4. ASP案件のread-onlyスキャン(現状は規約未確認のためdry-runのみ動く)
python -m automation.scripts.run_asp_readonly_scan --asp a8net --keyword "エアコンクリーニング"
```

## 7. まだ実装していないもの（次のステップ）

- A8.net / バリューコマースの実際の検索画面セレクタ（`a8net.py` / `valuecommerce.py`
  内のTODOコメント参照。実サイトを見ながらローカルで調整が必要）
- もしもアフィリエイト・アクセストレード・afbの規約調査とモジュール実装
- 各ASPの利用規約の人間によるレビューと`TOS_REGISTRY`の更新
- ダッシュボードからの`asp_programs`テーブル閲覧（`TODO.md` P2参照）
