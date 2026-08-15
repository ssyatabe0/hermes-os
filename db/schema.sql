-- Hermes OS — 東京8区 地域サービス・データ事業 DBスキーマ (SQLite)
--
-- 設計原則:
--   1. 実測値と推定値を区別する: 数値系テーブルは data_type('actual'|'estimate') と
--      confidence('high'|'medium'|'low') を必ず持つ。
--   2. 過去データを上書きしない: 計測系テーブル（*_db, *_score, *_demand, *_metrics,
--      *_history, *_log）は INSERT-only。最新値取得は v_* ビューを使う。
--   3. マスタ/台帳系テーブル（wards, towns, service_catalog, license_requirements,
--      asp_programs, partners）は UPDATE してよい（現在の状態を表すため）。
--   4. 全国展開を前提にしたテーブル構造（prefecture列を持つ）だが、初期投入データは
--      東京都8区に限定する。
--
-- 使い方: init_db.py が schema.sql → seed.sql の順で流し込み db/hermes.db を作る。

PRAGMA foreign_keys = ON;

-- =========================================================
-- 1. 地域マスタ・地域分析
-- =========================================================

CREATE TABLE wards (
    ward_id       INTEGER PRIMARY KEY,
    prefecture    TEXT NOT NULL DEFAULT '東京都',
    ward_name     TEXT NOT NULL UNIQUE,
    priority_tier TEXT NOT NULL CHECK (priority_tier IN ('top_priority','priority','future')),
    -- top_priority = 港区・品川区 / priority = 他6区 / future = 全国展開時に追加する区市町村
    notes         TEXT
);

CREATE TABLE towns (
    town_id           INTEGER PRIMARY KEY,
    ward_id           INTEGER NOT NULL REFERENCES wards(ward_id),
    town_name         TEXT NOT NULL,
    characteristic_tags TEXT,   -- 例: '高級住宅街,戸建て,大使館多数'
    affluence_level   TEXT CHECK (affluence_level IN ('very_high','high','medium','mixed','unknown')),
    dominant_housing  TEXT,     -- 例: '戸建て中心' '高級マンション中心' '賃貸マンション多数'
    notes             TEXT,
    source_url        TEXT,
    collected_at      TEXT,     -- ISO date
    UNIQUE(ward_id, town_name)
);

-- 区レベルの各種指標（人口・世帯・持ち家率など）。指標ごとに行を持つEAV形式にして、
-- 指標追加のたびにスキーマ変更しなくてよいようにする。追記専用。
CREATE TABLE region_metrics (
    id            INTEGER PRIMARY KEY,
    ward_id       INTEGER NOT NULL REFERENCES wards(ward_id),
    metric_name   TEXT NOT NULL,   -- 例: population, households, home_ownership_rate, detached_house_ratio ...
    metric_value  TEXT NOT NULL,   -- 数値以外(取得不能の説明等)も入るためTEXT。数値利用時はCASTする
    unit          TEXT,
    period        TEXT,            -- 例: '2025-04', '2023(令和5年住調)'
    data_type     TEXT NOT NULL CHECK (data_type IN ('actual','estimate','not_available')),
    confidence    TEXT NOT NULL CHECK (confidence IN ('high','medium','low')),
    source_url    TEXT,
    collected_at  TEXT NOT NULL
);

CREATE INDEX idx_region_metrics_ward ON region_metrics(ward_id, metric_name);

-- =========================================================
-- 2. サービスマスタ・許認可
-- =========================================================

CREATE TABLE service_catalog (
    service_id        INTEGER PRIMARY KEY,
    service_name       TEXT NOT NULL UNIQUE,
    category           TEXT NOT NULL,  -- リフォーム/庭・屋外/清掃/住宅管理/除雪(将来)/その他
    subcategory         TEXT,
    description         TEXT,
    outsourceable       INTEGER NOT NULL DEFAULT 1,  -- 0/1
    requires_license    INTEGER NOT NULL DEFAULT 0,  -- 0/1 (詳細は license_requirements)
    seasonality_hypothesis TEXT,  -- 例: '夏(6-8月)ピーク仮説'
    affluent_affinity_hypothesis TEXT CHECK (affluent_affinity_hypothesis IN ('very_high','high','medium','low')),
    status              TEXT NOT NULL DEFAULT 'candidate'
                         CHECK (status IN ('candidate','testing','affiliate_active','self_operate','paused','rejected')),
    future_region_only  INTEGER NOT NULL DEFAULT 0, -- 1 = 除雪等、東京8区では現状非対応
    notes               TEXT
);

CREATE TABLE license_requirements (
    license_id         INTEGER PRIMARY KEY,
    service_id          INTEGER NOT NULL REFERENCES service_catalog(service_id),
    license_name         TEXT NOT NULL,
    license_type          TEXT,  -- 国家資格/都道府県登録/市区町村許可/事業者指定 等
    issuing_body           TEXT,
    required_when           TEXT,  -- どのような場合に必要か
    threshold_notes          TEXT, -- 例: '税込500万円未満の工事は建設業許可不要（建築一式は1500万円未満）'
    self_operate_feasible     INTEGER NOT NULL DEFAULT 0, -- 自社取得を現実的に検討できるか(0/1)
    recommended_approach       TEXT, -- 例: '有資格の協力業者へ委託'
    source_url                  TEXT,
    collected_at                 TEXT,
    confidence                    TEXT CHECK (confidence IN ('high','medium','low'))
);

CREATE TABLE asp_programs (
    asp_program_id     INTEGER PRIMARY KEY,
    service_id          INTEGER REFERENCES service_catalog(service_id),
    asp_name             TEXT NOT NULL,   -- 例: A8.net, もしもアフィリエイト, afb
    program_name          TEXT,
    commission_type        TEXT,  -- 成果報酬/固定/クリック課金 等
    commission_amount       TEXT,
    approval_conditions      TEXT,
    cookie_duration_days       INTEGER,
    data_type                  TEXT NOT NULL DEFAULT 'estimate' CHECK (data_type IN ('actual','estimate','not_available')),
    notes                        TEXT,
    source_url                    TEXT,
    collected_at                   TEXT
);

-- =========================================================
-- 3. キーワードDB（追記専用ログ）
-- =========================================================

CREATE TABLE keyword_db (
    id                INTEGER PRIMARY KEY,
    keyword            TEXT NOT NULL,
    prefecture          TEXT NOT NULL DEFAULT '東京都',
    ward                 TEXT,
    area                  TEXT,   -- 町丁目・駅名等、区より細かい単位
    service                TEXT NOT NULL,
    category                TEXT,
    intent                   TEXT NOT NULL,  -- 情報収集/料金/相場/比較/業者探し/緊急/見積/施工依頼/
                                              -- 故障/交換/修理/定期管理/高品質/不在対応/富裕層向け/法人
    estimated_volume          INTEGER,
    competition                 TEXT,   -- low/medium/high
    estimated_cpc                 INTEGER,
    current_rank                    INTEGER,
    impressions                      INTEGER,
    clicks                             INTEGER,
    ctr                                  REAL,
    cta_clicks                            INTEGER,
    leads                                   INTEGER,
    affiliate_outbound                       INTEGER,
    conversions                                INTEGER,
    revenue                                      INTEGER,
    data_type                                     TEXT NOT NULL DEFAULT 'estimate'
                                                   CHECK (data_type IN ('actual','estimate','not_available')),
    data_source                                     TEXT NOT NULL, -- 'GSC' 'GA4' 'ASP' 'hypothesis' 等
    confidence                                       TEXT NOT NULL CHECK (confidence IN ('high','medium','low')),
    collected_at                                       TEXT NOT NULL
);

CREATE INDEX idx_keyword_db_lookup ON keyword_db(ward, service, collected_at);

-- 常に最新スナップショットだけを見るビュー
CREATE VIEW v_keyword_latest AS
SELECT k.*
FROM keyword_db k
JOIN (
    SELECT keyword, ward, service, MAX(collected_at) AS max_collected_at
    FROM keyword_db
    GROUP BY keyword, ward, service
) latest
ON k.keyword = latest.keyword AND IFNULL(k.ward,'') = IFNULL(latest.ward,'')
   AND k.service = latest.service AND k.collected_at = latest.max_collected_at;

-- =========================================================
-- 4. 記事DB（追記専用ログ）
-- =========================================================

CREATE TABLE article_db (
    id                  INTEGER PRIMARY KEY,
    content_id            TEXT NOT NULL,  -- 記事固有ID（プラットフォーム移行しても不変のID）
    url                     TEXT,
    title                     TEXT,
    region                      TEXT,
    service                       TEXT,
    main_keyword                    TEXT,
    related_keywords                  TEXT,  -- カンマ区切り
    search_intent                       TEXT,
    publish_date                          TEXT,
    update_date                             TEXT,
    impressions                               INTEGER,
    clicks                                      INTEGER,
    ctr                                           REAL,
    average_position                                REAL,
    cta_clicks                                        INTEGER,
    affiliate_outbound                                  INTEGER,
    leads                                                 INTEGER,
    conversions                                             INTEGER,
    revenue                                                   INTEGER,
    data_type                                                   TEXT NOT NULL DEFAULT 'estimate'
                                                                 CHECK (data_type IN ('actual','estimate','not_available')),
    data_source                                                   TEXT NOT NULL,
    collected_at                                                    TEXT NOT NULL
);

CREATE INDEX idx_article_db_lookup ON article_db(content_id, collected_at);

CREATE VIEW v_article_latest AS
SELECT a.*
FROM article_db a
JOIN (
    SELECT content_id, MAX(collected_at) AS max_collected_at
    FROM article_db
    GROUP BY content_id
) latest
ON a.content_id = latest.content_id AND a.collected_at = latest.max_collected_at;

-- =========================================================
-- 5. 季節需要（追記専用ログ、月次粒度）
-- =========================================================

CREATE TABLE seasonal_demand (
    id                INTEGER PRIMARY KEY,
    service             TEXT NOT NULL,
    region                TEXT NOT NULL,
    year                    INTEGER NOT NULL,
    month                     INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    season                      TEXT,  -- 春/夏/秋/冬
    estimated_demand              TEXT,  -- very_high/high/medium/low
    impressions                     INTEGER,
    clicks                            INTEGER,
    leads                               INTEGER,
    conversions                          INTEGER,
    revenue                                INTEGER,
    data_type                                TEXT NOT NULL DEFAULT 'estimate'
                                              CHECK (data_type IN ('actual','estimate','not_available')),
    confidence                                 TEXT NOT NULL CHECK (confidence IN ('high','medium','low')),
    notes                                         TEXT,
    collected_at                                    TEXT NOT NULL
);

CREATE INDEX idx_seasonal_demand_lookup ON seasonal_demand(service, region, year, month);

-- =========================================================
-- 6. 地域×サービス スコアリング（追記専用ログ、再評価のたびに新規行）
-- =========================================================

CREATE TABLE region_service_score (
    id                    INTEGER PRIMARY KEY,
    ward                    TEXT NOT NULL,
    service                   TEXT NOT NULL,
    month                       INTEGER,  -- NULL可（地域×サービスのみの評価の場合）
    search_demand                 INTEGER CHECK (search_demand BETWEEN 1 AND 5),
    demand_growth                   INTEGER CHECK (demand_growth BETWEEN 1 AND 5),
    seo_difficulty                    INTEGER CHECK (seo_difficulty BETWEEN 1 AND 5), -- 1=易しい 5=難しい
    competitor_strength                 INTEGER CHECK (competitor_strength BETWEEN 1 AND 5),
    ad_competition                        INTEGER CHECK (ad_competition BETWEEN 1 AND 5),
    inquiry_intent                          INTEGER CHECK (inquiry_intent BETWEEN 1 AND 5),
    cta_rate_score                            INTEGER CHECK (cta_rate_score BETWEEN 1 AND 5),
    cv_rate_score                               INTEGER CHECK (cv_rate_score BETWEEN 1 AND 5),
    estimated_cpa                                 INTEGER,  -- 円
    avg_order_value                                 INTEGER, -- 円
    asp_commission                                    INTEGER, -- 円
    estimated_gross_margin                              INTEGER, -- 円
    outsourceability                                      INTEGER CHECK (outsourceability BETWEEN 1 AND 5),
    partner_sourcing_difficulty                             INTEGER CHECK (partner_sourcing_difficulty BETWEEN 1 AND 5),
    travel_efficiency                                         INTEGER CHECK (travel_efficiency BETWEEN 1 AND 5),
    repeatability                                                INTEGER CHECK (repeatability BETWEEN 1 AND 5),
    annual_contract_potential                                      INTEGER CHECK (annual_contract_potential BETWEEN 1 AND 5),
    affluent_affinity                                                INTEGER CHECK (affluent_affinity BETWEEN 1 AND 5),
    btob_potential                                                     INTEGER CHECK (btob_potential BETWEEN 1 AND 5),
    license_difficulty                                                   INTEGER CHECK (license_difficulty BETWEEN 1 AND 5), -- 1=不要 5=非常に難しい
    star_rating                                                            INTEGER NOT NULL CHECK (star_rating BETWEEN 1 AND 5),
    star_label                                                               TEXT, -- 積極投資/有望/継続観察/優先度低/撤退候補
    data_type                                                                  TEXT NOT NULL DEFAULT 'estimate'
                                                                                CHECK (data_type IN ('actual','estimate')),
    rationale                                                                    TEXT,
    evaluated_at                                                                   TEXT NOT NULL
);

CREATE INDEX idx_region_service_score_lookup ON region_service_score(ward, service, month);

CREATE VIEW v_region_service_score_latest AS
SELECT s.*
FROM region_service_score s
JOIN (
    SELECT ward, service, IFNULL(month,-1) AS m, MAX(evaluated_at) AS max_evaluated_at
    FROM region_service_score
    GROUP BY ward, service, IFNULL(month,-1)
) latest
ON s.ward = latest.ward AND s.service = latest.service
   AND IFNULL(s.month,-1) = latest.m AND s.evaluated_at = latest.max_evaluated_at;

-- =========================================================
-- 7. パートナーDB（台帳、UPDATE可）+ パフォーマンス履歴（追記専用）
-- =========================================================

CREATE TABLE partners (
    partner_id          INTEGER PRIMARY KEY,
    company_or_person      TEXT NOT NULL,
    service                   TEXT NOT NULL,
    coverage_area               TEXT,
    price                          TEXT,
    availability                     TEXT,
    response_speed                     TEXT,
    insurance                            TEXT,
    required_license                       TEXT,
    verified_license                          INTEGER DEFAULT 0, -- 0/1
    notes                                        TEXT,
    status                                          TEXT NOT NULL DEFAULT 'candidate'
                                                     CHECK (status IN ('candidate','active','inactive')),
    created_at                                        TEXT,
    updated_at                                          TEXT
);

CREATE TABLE partner_performance_log (
    id                INTEGER PRIMARY KEY,
    partner_id          INTEGER NOT NULL REFERENCES partners(partner_id),
    completion_rate        REAL,
    customer_rating           REAL,
    complaint_rate               REAL,
    repeat_rate                     REAL,
    period                             TEXT,   -- 集計対象期間
    recorded_at                          TEXT NOT NULL
);

-- =========================================================
-- 8. 顧客・LTV（注文履歴は追記専用、サマリはビューで算出）
-- =========================================================

CREATE TABLE customers (
    customer_id         INTEGER PRIMARY KEY,
    initial_service        TEXT,
    initial_keyword          TEXT,
    initial_region              TEXT,
    property_type                  TEXT, -- 戸建て/マンション/セカンドハウス/賃貸オーナー物件 等
    subscription_status              TEXT NOT NULL DEFAULT 'none'
                                       CHECK (subscription_status IN ('none','light','standard','premium','annual_contract')),
    referral_count                       INTEGER NOT NULL DEFAULT 0,
    created_at                              TEXT,
    notes                                      TEXT
);

CREATE TABLE customer_orders (
    order_id          INTEGER PRIMARY KEY,
    customer_id          INTEGER NOT NULL REFERENCES customers(customer_id),
    service                 TEXT NOT NULL,
    order_date                TEXT NOT NULL,
    channel                     TEXT, -- affiliate/self_operate/referral 等
    revenue                       INTEGER,
    gross_profit                     INTEGER,
    partner_id                          INTEGER REFERENCES partners(partner_id),
    notes                                   TEXT
);

CREATE VIEW v_customer_summary AS
SELECT
    c.customer_id,
    c.initial_service,
    c.initial_keyword,
    c.initial_region,
    c.property_type,
    COUNT(o.order_id)             AS orders_count,
    GROUP_CONCAT(DISTINCT o.service) AS services_used,
    COALESCE(SUM(o.revenue),0)       AS total_revenue,
    COALESCE(SUM(o.gross_profit),0)     AS total_gross_profit,
    MAX(o.order_date)                      AS last_order_date,
    c.subscription_status,
    c.referral_count
FROM customers c
LEFT JOIN customer_orders o ON o.customer_id = c.customer_id
GROUP BY c.customer_id;

-- =========================================================
-- 9. 研究ログ（市場調査メタデータ。出典・取得日・信頼度の一元管理用の補助テーブル）
-- =========================================================

CREATE TABLE research_notes (
    id             INTEGER PRIMARY KEY,
    topic            TEXT NOT NULL,  -- 例: '港区 地域分析' '無料ブログ比較' '建設業許可'
    summary            TEXT NOT NULL,
    data_type            TEXT NOT NULL DEFAULT 'estimate' CHECK (data_type IN ('actual','estimate','not_available')),
    confidence              TEXT NOT NULL CHECK (confidence IN ('high','medium','low')),
    source_url                 TEXT,
    collected_at                  TEXT NOT NULL
);
