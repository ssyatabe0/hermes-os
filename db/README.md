# db/ — Hermes OS データベース

SQLite（`hermes.db`）を使用。理由: 無料・低コスト・単一ファイルでバックアップ容易・
将来PostgreSQL等へ移行する場合もスキーマがほぼそのまま流用できる（指示40に準拠）。

## ファイル

- `schema.sql` — 全テーブル・ビュー定義
- `init_db.py` — schema.sql適用＋初期調査データ(seed)投入スクリプト
- `hermes.db` — 実データベース本体（git管理下。バックアップ方針は下記）

## 再構築方法

```
python3 db/init_db.py
```

**注意:** このスクリプトは実行のたびに `hermes.db` を削除して作り直す。
実測データ（GSC取り込み等）が入った後に無闇に再実行すると、追記専用ログ以外の
データも失われる。運用開始後は、以下のいずれかに切り替えること。

1. `init_db.py` を「初回構築専用」とし、以降のデータ投入は別スクリプト
   （例: `import_gsc.py`, `import_asp.py`）でINSERTのみ行う
2. 再実行前に必ず `cp hermes.db hermes.db.bak.$(date +%Y%m%d)` でバックアップする

## テーブル構成の考え方

| 種別 | テーブル | 更新方法 |
|---|---|---|
| マスタ・台帳 | wards, towns, service_catalog, license_requirements, asp_programs, partners | UPDATE可 |
| 計測ログ（追記専用） | region_metrics, keyword_db, article_db, seasonal_demand, region_service_score, customer_orders, partner_performance_log | INSERT-only。UPDATEしない |
| 現在値ビュー | v_keyword_latest, v_article_latest, v_region_service_score_latest, v_customer_summary | 追記専用ログから最新値だけを取得 |
| 補助 | research_notes | 調査サマリと出典の一元管理 |

すべての計測系テーブルは `data_type`（actual/estimate/not_available）と
`confidence`（high/medium/low）を持つ。**このプロジェクトの初期データはほぼ全て
estimate**（一般知識・WebSearchでの定性情報からの仮説）であり、記事公開後の
実測データ（GSC/GA4/ASP/自社CTA）で徐々に置き換えていく方針（`STATUS.md`参照）。

## バックアップ方針（指示41対応）

- `hermes.db` は git 管理下に置き、コミットのたびに世代管理される
  （= GitHubへのpushそのものがオフサイトバックアップになる）
- 追記専用ログ設計のため、誤ってUPDATEやDELETEをしても大半のテーブルは
  過去のcollected_at時点のスナップショットが残り続ける
- 将来、記事・サイトが停止しても「市場調査・キーワード・SEO実測・売上・問い合わせ・
  顧客・パートナー」のデータは`hermes.db`単体から復元できる

## サンプルクエリ

```sql
-- 現時点のTOP候補(自社化優先度が高い順)
SELECT ward, service, star_rating, star_label, rationale
FROM v_region_service_score_latest
ORDER BY star_rating DESC;

-- 特定サービスの季節性仮説
SELECT month, season, estimated_demand
FROM seasonal_demand
WHERE service = 'エアコンクリーニング'
ORDER BY month;

-- 許認可が必要なサービス一覧
SELECT s.service_name, l.license_name, l.recommended_approach
FROM service_catalog s
JOIN license_requirements l ON l.service_id = s.service_id;
```
