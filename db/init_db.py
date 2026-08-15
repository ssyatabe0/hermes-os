#!/usr/bin/env python3
"""Hermes OS DB初期化スクリプト。

schema.sql を流し込み、東京8区の初期調査データ（seed）を投入して db/hermes.db を作る。
既存の hermes.db は削除して作り直す（本スクリプトはあくまで「初期investigationデータの
再現可能な構築手順」であり、hermes.db 自体がgit管理下の実データ本体になった後は、
このスクリプトを不用意に再実行して実測データを消さないこと。
実測データが入った後の再実行は、必ず事前にバックアップを取ってから行う。

使い方: python3 db/init_db.py
"""

import sqlite3
import pathlib

DB_DIR = pathlib.Path(__file__).parent
SCHEMA_PATH = DB_DIR / "schema.sql"
DB_PATH = DB_DIR / "hermes.db"

TODAY = "2026-08-15"


def main():
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

    seed_wards(conn)
    seed_towns(conn)
    seed_region_metrics(conn)
    seed_service_catalog(conn)
    seed_license_requirements(conn)
    seed_asp_programs(conn)
    seed_keyword_db(conn)
    seed_seasonal_demand(conn)
    seed_region_service_score(conn)
    seed_research_notes(conn)

    conn.commit()
    conn.close()
    print(f"Built {DB_PATH}")


def seed_wards(conn):
    wards = [
        (1, "東京都", "港区", "top_priority", "最優先。富裕層密度・タワマン・法人密度とも突出"),
        (2, "東京都", "品川区", "top_priority", "最優先。湾岸再開発＋伝統的邸宅街(御殿山・島津山・池田山)"),
        (3, "東京都", "渋谷区", "priority", "重点。松濤・広尾・代官山、外国人居住者比率も高い"),
        (4, "東京都", "大田区", "priority", "重点。田園調布、区面積が広く戸建てストック多い"),
        (5, "東京都", "千代田区", "priority", "重点。人口最少クラスだが法人密度・所得水準は最高クラス"),
        (6, "東京都", "世田谷区", "priority", "重点。23区最大人口、戸建て比率高くガーデン系需要の絶対量が期待できる"),
        (7, "東京都", "新宿区", "priority", "重点。単身・賃貸比率高く二極化、エリア限定訴求が必要"),
        (8, "東京都", "目黒区", "priority", "重点。自由が丘・八雲等、住宅地としてのブランドイメージが強い"),
    ]
    conn.executemany(
        "INSERT INTO wards (ward_id, prefecture, ward_name, priority_tier, notes) VALUES (?,?,?,?,?)",
        wards,
    )


def seed_towns(conn):
    src = "https://earnest-arch.jp/column/luxury-residential-area/tokyokokyu/"
    src_meguro = "https://earnest-arch.jp/column/luxury-residential-area/meguro/"
    # (ward_id, town_name, tags, affluence, housing, notes, source_url)
    rows = [
        # 港区
        (1, "麻布・元麻布・南麻布", "邸宅,大使館,外国人居住多い", "very_high", "邸宅・高級マンション混在", None, src),
        (1, "西麻布・六本木", "高級マンション,商業近接,法人利用", "high", "高級マンション中心", None, src),
        (1, "白金・白金台", "邸宅街,閑静,教育環境良好", "very_high", "邸宅中心", None, src),
        (1, "高輪", "邸宅,再開発で価値上昇傾向", "very_high", "邸宅・高級マンション", None, src),
        (1, "赤坂", "高級マンション,法人・政治施設近接", "high", "高級マンション中心", None, src),
        (1, "三田", "大学近接,マンション・邸宅混在", "high", "マンション・邸宅混在", None, src),
        (1, "芝浦・港南", "タワーマンション集積,湾岸,共働きファミリー層", "high", "タワーマンション中心", None, src),
        # 品川区
        (2, "東五反田", "高級マンション激戦区,タワマン,山手線内側", "high", "高級マンション中心", None, src),
        (2, "上大崎", "邸宅・高級マンション混在,目黒駅至近", "high", "邸宅・マンション混在", None, src),
        (2, "北品川", "旧市街と再開発混在,マンション増加中", "medium", "マンション増加中", None, src),
        (2, "御殿山", "大使館・邸宅街,高台の閑静な住宅地", "very_high", "邸宅中心", None, src),
        (2, "島津山・池田山", "旧大名屋敷跡由来の高台,区内最上位の邸宅街", "very_high", "邸宅中心", None, src),
        (2, "大崎", "大規模再開発,オフィス・タワマン混在,法人需要", "high", "オフィス・タワマン混在", None, src),
        (2, "天王洲周辺", "運河沿い再開発,オフィス・高級マンション", "high", "オフィス・高級マンション", None, src),
        # 渋谷区
        (3, "松濤", "伝統的高級住宅街,閑静", "very_high", "邸宅中心", None, src),
        (3, "広尾", "大使館,外国人富裕層,高級マンション", "very_high", "高級マンション・邸宅", None, src),
        (3, "代官山", "ブランドイメージ,おしゃれな高級住宅地", "high", "高級マンション・邸宅", None, src),
        (3, "恵比寿西", "利便性高い,高級マンション", "high", "高級マンション中心", None, src),
        # 大田区
        (4, "田園調布", "最上位ブランド邸宅街,計画都市", "very_high", "邸宅中心", None, src),
        (4, "雪谷", "閑静な住宅地,戸建て中心", "high", "戸建て中心", None, src),
        (4, "久が原", "戸建て住宅地,ファミリー層", "medium", "戸建て中心", None, src),
        (4, "山王", "高台の住宅地,邸宅も多い", "high", "戸建て・邸宅", None, src),
        # 千代田区
        (5, "番町", "最上位クラスの邸宅街,政財界関係者", "very_high", "邸宅・高級マンション", None, src),
        (5, "麹町", "邸宅・高級マンション,オフィス近接", "very_high", "邸宅・高級マンション", None, src),
        # 世田谷区
        (6, "成城", "学園都市として計画発展,ブランド住宅地", "very_high", "邸宅中心", None, src),
        (6, "岡本", "閑静な高級住宅地,国分寺崖線沿い", "high", "戸建て中心", None, src),
        (6, "深沢", "戸建て中心の高級住宅地", "high", "戸建て中心", None, src),
        (6, "奥沢・玉川田園調布", "田園調布に隣接するブランドエリア", "high", "戸建て中心", None, src),
        # 新宿区
        (7, "下落合", "高級マンション,邸宅も点在", "high", "高級マンション・邸宅", None, src),
        (7, "若葉・信濃町周辺", "閑静な住宅地,病院・大学近接", "medium", "マンション・邸宅混在", None, src),
        # 目黒区
        (8, "自由が丘", "高級住宅とブランド商業が近接", "high", "戸建て・高級マンション", None, src_meguro),
        (8, "八雲", "閑静な住宅街,高級マンション・邸宅", "high", "邸宅・マンション混在", None, src_meguro),
        (8, "青葉台", "高級賃貸・邸宅,代官山にも近い", "high", "邸宅・高級賃貸", None, src_meguro),
        (8, "碑文谷", "戸建て中心,ファミリー層に人気", "medium", "戸建て中心", None, src_meguro),
    ]
    conn.executemany(
        """INSERT INTO towns (ward_id, town_name, characteristic_tags, affluence_level,
           dominant_housing, notes, source_url, collected_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        [r + (TODAY,) for r in rows],
    )


def seed_region_metrics(conn):
    rows = []
    # 品川区: 実測
    shinagawa_src = "https://www.city.shinagawa.tokyo.jp/contentshozon2025/202504a.pdf"
    rows.append((2, "population", "414581", "人", "2025-04-01", "actual", "high", shinagawa_src))
    rows.append((2, "households", "240047", "世帯", "2025-04-01", "actual", "high", shinagawa_src))
    # 港区: 出典ページは特定できたが数値は次回転記
    minato_src = "https://www.city.minato.tokyo.jp/toukeichousa/kuse/toke/jinko/index.html"
    rows.append((1, "population", "公式ページに月次データあり、本セッションでは未転記", "-", "2025", "not_available", "low", minato_src))
    rows.append((1, "households", "公式ページに月次データあり、本セッションでは未転記", "-", "2025", "not_available", "low", minato_src))
    # 全区共通: 住宅・土地統計調査への導線（未取得）
    estat_src = "https://www.e-stat.go.jp/stat-search/files?toukei=00200522"
    for ward_id in range(1, 9):
        rows.append((ward_id, "home_ownership_rate", "取得不能(次回e-Statより取得)", "%", "2023", "not_available", "low", estat_src))
        rows.append((ward_id, "detached_house_ratio", "取得不能(次回e-Statより取得)", "%", "2023", "not_available", "low", estat_src))
    # 東京都全体の参考値(実測)
    tokyo_src = "https://statresearch.jp/house/family/family_pref_13.html"
    for ward_id in range(1, 9):
        rows.append((ward_id, "tokyo_pref_home_ownership_rate_reference", "65.5", "%", "2018-2023推計", "actual", "medium", tokyo_src))
        rows.append((ward_id, "tokyo_pref_detached_house_ratio_reference", "38.0", "%", "2018-2023推計", "actual", "medium", tokyo_src))
    # 一般知識ベースの規模感（要検証）
    general_note = "一般知識ベース、本セッションでは個別検証していない。次回、区公式統計で要検証"
    rows.append((6, "population_rank_hint", "23区中最多クラスとされる", "-", "2024頃", "estimate", "low", None))
    rows.append((5, "population_rank_hint", "23区中最少クラスとされる（昼夜間人口差大）", "-", "2024頃", "estimate", "low", None))
    conn.executemany(
        """INSERT INTO region_metrics (ward_id, metric_name, metric_value, unit, period,
           data_type, confidence, source_url, collected_at) VALUES (?,?,?,?,?,?,?,?,?)""",
        [r + (TODAY,) for r in rows],
    )


def seed_service_catalog(conn):
    # (name, category, subcategory, description, outsourceable, requires_license,
    #  seasonality, affluent_affinity, status, future_region_only, notes)
    reform = "リフォーム・住宅設備"
    garden = "庭・屋外"
    clean = "清掃・住宅管理"
    snow = "除雪(将来候補)"

    rows = [
        ("給湯器交換", reform, "水回り設備", "給湯器の故障・交換", 1, 1, "冬(故障増)仮説", "medium", "candidate", 0, "ガス接続部の資格要確認"),
        ("トイレ交換・修理", reform, "水回り設備", None, 1, 1, "通年", "medium", "candidate", 0, None),
        ("キッチンリフォーム", reform, "水回り設備", None, 1, 1, "通年", "high", "candidate", 0, None),
        ("浴室リフォーム", reform, "水回り設備", None, 1, 1, "通年", "high", "candidate", 0, None),
        ("洗面台交換", reform, "水回り設備", None, 1, 1, "通年", "medium", "candidate", 0, None),
        ("水漏れ修理", reform, "水回り", "緊急性が高い", 1, 1, "通年(緊急)", "medium", "candidate", 0, "指定給水装置工事事業者が必要"),
        ("排水管つまり", reform, "水回り", None, 1, 1, "通年(緊急)", "medium", "candidate", 0, "指定給水装置工事事業者が必要な場合あり"),
        ("エアコン交換・工事", reform, "空調", None, 1, 1, "夏前ピーク仮説", "medium", "candidate", 0, "電気工事士資格の要否要確認"),
        ("内窓設置", reform, "断熱", "インプラス等", 1, 0, "冬前ピーク仮説", "high", "candidate", 0, None),
        ("窓交換", reform, "外装", None, 1, 1, "通年", "medium", "candidate", 0, None),
        ("玄関ドア交換", reform, "外装", None, 1, 1, "通年", "medium", "candidate", 0, None),
        ("外壁塗装・補修", reform, "外装", None, 1, 1, "春秋ピーク仮説", "high", "candidate", 0, "金額が大きく建設業許可対象になりやすい"),
        ("屋根塗装・補修", reform, "外装", None, 1, 1, "春秋ピーク仮説", "high", "candidate", 0, "同上"),
        ("防水工事", reform, "外装", None, 1, 1, "春秋ピーク仮説", "medium", "candidate", 0, None),
        ("雨漏り修理", reform, "外装", "緊急性が高い", 1, 1, "梅雨・台風期ピーク仮説", "medium", "candidate", 0, None),
        ("内装・クロス張替", reform, "内装", None, 1, 0, "通年", "medium", "candidate", 0, None),
        ("床リフォーム", reform, "内装", None, 1, 0, "通年", "medium", "candidate", 0, None),
        ("原状回復工事", reform, "内装", "賃貸退去時", 1, 0, "通年", "low", "candidate", 0, "BtoB(賃貸オーナー・管理会社)向け候補"),
        ("中古住宅リフォーム", reform, "総合", None, 1, 1, "通年", "high", "candidate", 0, None),
        ("マンションリフォーム", reform, "総合", None, 1, 1, "通年", "high", "candidate", 0, "管理規約対応が必要"),
        ("戸建てリフォーム", reform, "総合", None, 1, 1, "通年", "high", "candidate", 0, None),

        ("草刈り", garden, None, None, 1, 0, "夏ピーク仮説", "medium", "candidate", 0, None),
        ("草むしり", garden, None, None, 1, 0, "春夏ピーク仮説", "medium", "candidate", 0, None),
        ("芝刈り", garden, None, None, 1, 0, "春夏ピーク仮説", "medium", "candidate", 0, None),
        ("庭掃除", garden, None, None, 1, 0, "通年", "medium", "candidate", 0, None),
        ("庭木剪定", garden, None, None, 1, 0, "秋春ピーク仮説", "high", "candidate", 0, "廃棄物処理は許可要確認"),
        ("伐採", garden, None, None, 1, 0, "秋春ピーク仮説", "high", "candidate", 0, "廃棄物処理は許可要確認"),
        ("抜根", garden, None, None, 1, 0, "秋春ピーク仮説", "medium", "candidate", 0, None),
        ("植木・生垣手入れ", garden, None, None, 1, 0, "春秋ピーク仮説", "high", "candidate", 0, None),
        ("落ち葉清掃", garden, None, None, 1, 0, "秋冬ピーク仮説", "medium", "candidate", 0, None),
        ("防草シート施工", garden, None, None, 1, 0, "春夏ピーク仮説", "medium", "candidate", 0, None),
        ("砂利敷き", garden, None, None, 1, 0, "通年", "low", "candidate", 0, None),
        ("空き地管理", garden, None, "土地オーナー向け", 1, 0, "夏ピーク仮説", "medium", "candidate", 0, "BtoB(不動産オーナー)向け候補"),
        ("空き家の庭管理", garden, None, None, 1, 0, "夏ピーク仮説", "high", "candidate", 0, "不在宅管理と組み合わせ可能"),

        ("ハウスクリーニング", clean, None, None, 1, 0, "春(引越)ピーク仮説", "high", "candidate", 0, None),
        ("エアコンクリーニング", clean, None, None, 1, 0, "夏前ピーク仮説", "high", "candidate", 0, None),
        ("ベランダ清掃", clean, None, None, 1, 0, "通年", "medium", "candidate", 0, None),
        ("窓清掃", clean, None, None, 1, 0, "通年", "medium", "candidate", 0, None),
        ("高圧洗浄", clean, None, None, 1, 0, "通年", "medium", "candidate", 0, "近隣配慮・排水条例要確認"),
        ("排水管清掃", clean, None, None, 1, 0, "通年", "low", "candidate", 0, None),
        ("雨樋清掃", clean, None, None, 1, 0, "秋冬ピーク仮説", "medium", "candidate", 0, None),
        ("外壁洗浄", clean, None, None, 1, 0, "春秋ピーク仮説", "medium", "candidate", 0, None),
        ("空き家管理", clean, None, None, 1, 0, "通年", "high", "candidate", 0, None),
        ("留守宅管理・不在時住宅管理", clean, None, None, 1, 0, "通年", "very_high", "candidate", 0, "月額住宅管理の中核候補"),
        ("定期住宅点検", clean, None, None, 1, 0, "通年", "very_high", "candidate", 0, "月額住宅管理の中核候補"),
        ("住宅設備点検", clean, None, None, 1, 0, "通年", "high", "candidate", 0, None),
        ("小修繕", clean, None, None, 1, 0, "通年", "medium", "candidate", 0, None),
        ("鍵預かり", clean, None, None, 1, 0, "通年", "very_high", "candidate", 0, "コンシェルジュ系サービスの付帯機能"),
        ("業者立ち会い代行", clean, None, None, 1, 0, "通年", "very_high", "candidate", 0, "コンシェルジュ系サービスの付帯機能"),
        ("施工会社手配", clean, None, None, 1, 0, "通年", "very_high", "candidate", 0, "自社の中核機能そのもの"),
        ("緊急時対応窓口", clean, None, None, 1, 0, "通年", "very_high", "candidate", 0, "月額プレミアムプランの核"),
        ("セカンドハウス管理", clean, None, None, 1, 0, "通年", "very_high", "candidate", 0, None),

        ("雪かき", snow, None, None, 1, 0, "冬(積雪地域)", "low", "candidate", 1, "東京8区では非対応、横展開候補として保持"),
        ("除雪", snow, None, None, 1, 0, "冬(積雪地域)", "low", "candidate", 1, "同上"),
        ("屋根雪下ろし", snow, None, None, 1, 1, "冬(積雪地域)", "low", "candidate", 1, "同上、高所作業のため資格要確認"),
        ("駐車場除雪", snow, None, None, 1, 0, "冬(積雪地域)", "low", "candidate", 1, "同上"),
        ("法人向け除雪", snow, None, None, 1, 0, "冬(積雪地域)", "low", "candidate", 1, "同上、BtoB候補"),
        ("排雪", snow, None, None, 1, 0, "冬(積雪地域)", "low", "candidate", 1, "同上"),
        ("雪庇除去", snow, None, None, 1, 1, "冬(積雪地域)", "low", "candidate", 1, "同上、高所作業のため資格要確認"),
        ("凍結対策", snow, None, None, 1, 0, "冬(積雪地域)", "low", "candidate", 1, "同上"),
    ]
    conn.executemany(
        """INSERT INTO service_catalog (service_name, category, subcategory, description,
           outsourceable, requires_license, seasonality_hypothesis, affluent_affinity_hypothesis,
           status, future_region_only, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )


def service_id(conn, name):
    return conn.execute("SELECT service_id FROM service_catalog WHERE service_name=?", (name,)).fetchone()[0]


def seed_license_requirements(conn):
    rows = [
        (
            "戸建てリフォーム", "建設業許可", "都道府県許可(知事許可 or 大臣許可)", "国土交通省/都道府県",
            "税込500万円以上の工事(建築一式は1,500万円以上、または延べ面積150㎡以上の木造住宅工事)",
            "建築一式工事以外は500万円未満、建築一式工事は1,500万円未満(延べ150㎡未満の木造住宅含む)は許可不要",
            0, "500万円未満に収まる工事は自社受付可、超える場合は建設業許可を持つ協力会社へ委託",
            "https://vs-group.jp/gyoseiss/gyosho/500tax/", "high",
        ),
        (
            "水漏れ修理", "指定給水装置工事事業者", "水道事業者(東京都水道局)による指定", "東京都水道局",
            "水道メーターより宅地側の給水管の新設・改造・修繕",
            "事業所ごとに国家資格「給水装置工事主任技術者」の配置等が必要",
            0, "指定給水装置工事事業者の資格を持つ協力会社へ発注する。自社取得は現時点で非現実的",
            "https://www.waterworks.metro.tokyo.lg.jp/kurashi/shitei/ichiran", "high",
        ),
        (
            "庭木剪定", "産業廃棄物収集運搬業(枝葉処分時)", "都道府県許可(自治体差あり)", "都道府県・自治体",
            "剪定・伐採で発生した枝葉等を自社で引き取り・運搬・処分する場合",
            "自治体により一般廃棄物/産業廃棄物の扱いが異なる。剪定・伐採作業自体は建設業許可不要",
            0, "廃棄物の引き取り・処分は許可を持つ協力会社や委託先を経由する",
            "https://sanpai-shuuun.com/zouen/", "medium",
        ),
        (
            "エアコン交換・工事", "電気工事士", "国家資格", "経済産業省",
            "エアコンの電源工事(配線工事)を伴う場合",
            "未調査。取付のみか電気工事を伴うかで要否が変わる可能性がある",
            0, "要調査。判明するまでは電気工事を伴う案件は有資格の協力会社へ委託を前提にする",
            None, "low",
        ),
        (
            "排水管つまり", "指定給水装置工事事業者(排水管の構造による)", "水道事業者による指定", "東京都水道局/各自治体下水道部局",
            "公共下水道に接続する排水設備の新設・改造",
            "未調査。単純な詰まり除去と配管改造で要否が変わる可能性がある",
            0, "要調査。配管の改造を伴う場合は有資格の協力会社へ委託を前提にする",
            None, "low",
        ),
    ]
    conn.executemany(
        """INSERT INTO license_requirements
           (service_id, license_name, license_type, issuing_body, required_when, threshold_notes,
            self_operate_feasible, recommended_approach, source_url, collected_at, confidence)
           VALUES ((SELECT service_id FROM service_catalog WHERE service_name=?), ?,?,?,?,?,?,?,?,?,?)""",
        [(r[0],) + r[1:9] + (TODAY, r[9]) for r in rows],
    )


def seed_asp_programs(conn):
    # (service_name, asp_name, program_name, commission_type, commission_amount,
    #  approval_conditions, cookie_duration_days, partnership_status, notes)
    rows = [
        ("エアコンクリーニング", "A8.net", "生活サービス系(一括見積・比較サイト経由と推定)", "成果報酬", "未確認",
         "未確認", None, "not_applied", "案件名・報酬額とも未検証。read-onlyスキャン結果待ち"),
        ("戸建てリフォーム", "もしもアフィリエイト", "リフォーム一括見積もり系(推定)", "成果報酬", "未確認",
         "未確認", None, "not_applied", "同上"),
        ("庭木剪定", "A8.net", "生活サービスマッチング系(推定)", "成果報酬", "未確認",
         "未確認", None, "not_applied", "同上"),
    ]
    conn.executemany(
        """INSERT INTO asp_programs (service_id, asp_name, program_name, commission_type,
           commission_amount, approval_conditions, cookie_duration_days, partnership_status,
           status, data_type, notes, last_checked_at, collected_at)
           VALUES ((SELECT service_id FROM service_catalog WHERE service_name=?), ?,?,?,?,?,?,?,
                   'unknown','not_available',?,?,?)""",
        [r + (TODAY, TODAY) for r in rows],
    )


def seed_keyword_db(conn):
    # 最初の5テスト市場を中心に、代表キーワードを仮説(estimate)として登録。
    # 実測開始後、GSCのデータで上書き(=新規行として追記)していく。
    combos = [
        ("港区", "エアコンクリーニング", [
            ("港区 エアコンクリーニング 業者", "業者探し"),
            ("港区 エアコンクリーニング 料金", "料金"),
            ("麻布 エアコンクリーニング おすすめ", "比較"),
            ("港区 エアコンクリーニング 即日", "緊急"),
        ]),
        ("港区", "水漏れ修理", [
            ("港区 水漏れ 修理 業者", "緊急"),
            ("港区 排水管つまり 業者", "緊急"),
            ("赤坂 水漏れ 夜間対応", "緊急"),
        ]),
        ("品川区", "給湯器交換", [
            ("品川区 給湯器交換 費用", "料金"),
            ("品川区 給湯器 故障 交換", "故障"),
            ("東五反田 給湯器 交換業者", "業者探し"),
        ]),
        ("世田谷区", "庭木剪定", [
            ("世田谷区 庭木剪定 業者", "業者探し"),
            ("世田谷区 剪定 料金相場", "相場"),
            ("成城 庭木 手入れ 定期", "定期管理"),
        ]),
        ("目黒区", "ハウスクリーニング", [
            ("目黒区 ハウスクリーニング おすすめ", "比較"),
            ("自由が丘 ハウスクリーニング 料金", "料金"),
            ("目黒区 水回り クリーニング 業者", "業者探し"),
        ]),
    ]
    rows = []
    for ward, service, kws in combos:
        for kw, intent in kws:
            rows.append((kw, "東京都", ward, None, service, None, intent,
                         None, "medium", None, None, None, None, None, None,
                         None, None, None, None, "estimate", "hypothesis", "low"))
    conn.executemany(
        """INSERT INTO keyword_db (keyword, prefecture, ward, area, service, category, intent,
           estimated_volume, competition, estimated_cpc, current_rank, impressions, clicks, ctr,
           cta_clicks, leads, affiliate_outbound, conversions, revenue, data_type, data_source,
           confidence, collected_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [r + (TODAY,) for r in rows],
    )


def seed_seasonal_demand(conn):
    # service, region, month, season, estimated_demand
    hypotheses = [
        ("エアコンクリーニング", "東京8区", 5, "春", "high"),
        ("エアコンクリーニング", "東京8区", 6, "夏", "very_high"),
        ("エアコンクリーニング", "東京8区", 7, "夏", "very_high"),
        ("草刈り", "東京8区", 6, "夏", "high"),
        ("草刈り", "東京8区", 7, "夏", "very_high"),
        ("草刈り", "東京8区", 8, "夏", "high"),
        ("庭木剪定", "東京8区", 10, "秋", "high"),
        ("庭木剪定", "東京8区", 11, "秋", "very_high"),
        ("落ち葉清掃", "東京8区", 11, "秋", "high"),
        ("雨樋清掃", "東京8区", 10, "秋", "medium"),
        ("給湯器交換", "東京8区", 12, "冬", "high"),
        ("給湯器交換", "東京8区", 1, "冬", "very_high"),
        ("水漏れ修理", "東京8区", 1, "冬", "high"),
        ("内窓設置", "東京8区", 10, "秋", "medium"),
        ("内窓設置", "東京8区", 11, "秋", "high"),
        ("ハウスクリーニング", "東京8区", 3, "春", "very_high"),
        ("ハウスクリーニング", "東京8区", 12, "冬", "high"),
    ]
    rows = [
        (service, region, 2026, month, season, demand, None, None, None, None, None,
         "estimate", "low", "仮説(季節性の一般知識ベース)。実測データで置き換え予定")
        for service, region, month, season, demand in hypotheses
    ]
    conn.executemany(
        """INSERT INTO seasonal_demand (service, region, year, month, season, estimated_demand,
           impressions, clicks, leads, conversions, revenue, data_type, confidence, notes, collected_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [r + (TODAY,) for r in rows],
    )


STAR_LABEL = {5: "積極投資", 4: "有望", 3: "継続観察", 2: "優先度低", 1: "撤退候補"}


def seed_region_service_score(conn):
    # 各タプル: ward, service, (search_demand, demand_growth, seo_difficulty, competitor_strength,
    #   ad_competition, inquiry_intent, cta_rate_score, cv_rate_score, estimated_cpa, avg_order_value,
    #   asp_commission, estimated_gross_margin, outsourceability, partner_sourcing_difficulty,
    #   travel_efficiency, repeatability, annual_contract_potential, affluent_affinity, btob_potential,
    #   license_difficulty, star_rating), rationale
    rows = [
        ("港区", "エアコンクリーニング",
         (4, 4, 4, 4, 4, 4, 4, 4, 6000, 18000, 4000, 9000, 5, 2, 5, 4, 3, 5, 2, 1, 5),
         "タワマン密集で需要が安定。外注しやすくリピート(年1回)も期待できるため自社化最有力候補"),
        ("品川区", "エアコンクリーニング",
         (4, 4, 3, 4, 3, 4, 4, 4, 5500, 18000, 4000, 9500, 5, 2, 5, 4, 3, 4, 2, 1, 5),
         "東五反田等の高級マンション需要。港区よりSEO競合がやや弱いと仮定"),
        ("港区", "水漏れ修理",
         (5, 3, 4, 4, 3, 5, 4, 5, 7000, 35000, 5000, 12000, 3, 4, 5, 2, 1, 4, 2, 4, 4),
         "緊急検索は転換率が高いが、指定給水装置工事事業者への依存度が高く自社化難度は中程度"),
        ("品川区", "給湯器交換",
         (5, 3, 3, 4, 4, 4, 3, 4, 9000, 220000, 8000, 60000, 4, 3, 4, 1, 1, 3, 2, 3, 4),
         "検索ボリューム・単価とも大きいが低頻度商材。当面はアフィリエイト/提携送客が有利"),
        ("世田谷区", "庭木剪定",
         (3, 3, 2, 3, 2, 4, 4, 4, 5000, 45000, 4500, 18000, 4, 3, 3, 4, 4, 4, 2, 2, 5),
         "戸建てストックが23区最大級で剪定需要の絶対量が期待できる。年間契約化にも向く"),
        ("大田区", "庭木剪定",
         (3, 3, 2, 3, 2, 4, 4, 4, 5000, 42000, 4500, 17000, 4, 3, 2, 4, 4, 3, 2, 2, 4),
         "田園調布等で戸建て比率高いが区が広く移動効率がやや劣る"),
        ("目黒区", "ハウスクリーニング",
         (4, 3, 3, 4, 3, 3, 4, 3, 6500, 45000, 5000, 18000, 5, 2, 4, 3, 3, 4, 2, 1, 4),
         "住宅地としてのブランドイメージが強く、清掃需要との相性が良い"),
        ("世田谷区", "草刈り",
         (3, 4, 2, 3, 2, 4, 4, 4, 4500, 30000, 3500, 12000, 4, 3, 3, 3, 3, 3, 1, 1, 4),
         "夏季に広い庭・空き地の需要が見込める。季節偏重のため他サービスとの組み合わせが必要"),
        ("渋谷区", "ハウスクリーニング",
         (4, 3, 4, 4, 4, 3, 3, 3, 7500, 45000, 5000, 16000, 4, 2, 4, 3, 3, 4, 2, 1, 3),
         "富裕層・外国人居住者の時間短縮ニーズが強いと仮定するが、SEO競合が激しい"),
        ("千代田区", "定期住宅点検・不在宅管理",
         (2, 4, 3, 2, 2, 3, 3, 2, 12000, 100000, None, 40000, 3, 4, 5, 4, 5, 5, 5, 2, 3),
         "検索ボリュームは小さいがBtoB(法人役員邸宅・管理会社)との相性が高く、年間契約化ポテンシャル大"),
        ("渋谷区", "内窓設置",
         (3, 2, 3, 3, 3, 3, 3, 3, 8000, 70000, 5500, 20000, 3, 3, 4, 1, 1, 4, 1, 2, 3),
         "施工品質のばらつきと原価変動リスクがあり、初期は送客中心が無難"),
        ("新宿区", "水漏れ修理",
         (4, 2, 4, 4, 3, 5, 3, 4, 7500, 32000, 5000, 10000, 3, 4, 3, 2, 1, 2, 2, 4, 3),
         "区全体の単身・賃貸比率が高く、法人管理会社経由の需要も一定あると仮定"),
        ("大田区", "外壁塗装・補修",
         (3, 2, 2, 3, 2, 3, 3, 3, 10000, 800000, 15000, 150000, 2, 4, 2, 1, 1, 3, 1, 4, 2),
         "工事金額が大きく施工管理・保証リスクが高いため、初期は自社化せず提携送客に留める"),
        ("港区", "定期住宅点検・不在宅管理",
         (2, 4, 3, 2, 2, 3, 3, 2, 12000, 120000, None, 50000, 3, 4, 5, 4, 5, 5, 3, 2, 4),
         "富裕層LTV最大化候補の筆頭。検索需要が顕在化しておらずSEO単独では初期テストしにくい"),
        ("品川区", "セカンドハウス管理",
         (2, 3, 3, 2, 2, 3, 3, 2, 12000, 90000, None, 35000, 3, 4, 4, 4, 5, 5, 2, 2, 4),
         "御殿山・島津山等の邸宅所有者に潜在ニーズがあると仮定。検索より紹介経由が中心の可能性"),
        ("渋谷区", "留守宅管理・不在時住宅管理",
         (2, 3, 3, 2, 2, 3, 3, 2, 13000, 90000, None, 32000, 3, 4, 4, 4, 4, 5, 2, 2, 4),
         "外国人居住者・セカンドハウス所有者向け。英語対応体制の構築が課題"),
        ("千代田区", "原状回復工事",
         (2, 2, 2, 2, 1, 3, 2, 3, 9000, 150000, None, 45000, 3, 3, 5, 2, 2, 2, 5, 2, 3),
         "オフィスビル・法人賃貸が多く、管理会社経由のBtoB継続受注が期待できる"),
        ("目黒区", "原状回復工事",
         (3, 2, 3, 3, 2, 3, 3, 3, 8500, 130000, None, 38000, 3, 3, 4, 2, 2, 3, 4, 2, 3),
         "賃貸オーナー向けBtoB候補。管理会社との年間契約化余地あり"),
        ("大田区", "住宅設備点検",
         (2, 2, 2, 2, 1, 3, 2, 2, 9500, 60000, None, 20000, 3, 4, 2, 3, 3, 2, 3, 2, 3),
         "不動産管理会社の定期巡回代行としてのBtoB候補。区が広く移動効率に課題"),
    ]
    ins = []
    for ward, service, m, rationale in rows:
        star = m[-1]
        ins.append((ward, service, None, *m[:-1], star, STAR_LABEL[star], "estimate", rationale))
    conn.executemany(
        """INSERT INTO region_service_score
           (ward, service, month, search_demand, demand_growth, seo_difficulty, competitor_strength,
            ad_competition, inquiry_intent, cta_rate_score, cv_rate_score, estimated_cpa,
            avg_order_value, asp_commission, estimated_gross_margin, outsourceability,
            partner_sourcing_difficulty, travel_efficiency, repeatability, annual_contract_potential,
            affluent_affinity, btob_potential, license_difficulty, star_rating, star_label,
            data_type, rationale, evaluated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [r + (TODAY,) for r in ins],
    )


def seed_research_notes(conn):
    rows = [
        ("東京8区 地域分析", "港区・品川区最優先の8区について人口/世帯/富裕エリアを調査。品川区は実測、港区以下は出典特定まで",
         "estimate", "medium", "research/01_region_analysis.md"),
        ("対象サービス・許認可調査", "建設業許可500万円基準、給水装置工事事業者指定、産廃収集運搬業と剪定枝の関係を調査",
         "actual", "high", "research/02_service_catalog_and_licensing.md"),
        ("ASP・アフィリエイト調査", "主要ASPの位置付けまで確認。個社の成果報酬額は未確認(アカウント未開設)",
         "estimate", "low", "research/03_affiliate_asp_landscape.md"),
        ("無料ブログ/CMS比較", "はてなブログを初期採用として選定。note/アメブロは外部ASP制限が理由で不採用",
         "estimate", "medium", "research/04_free_blog_cms_comparison.md"),
        ("受注価格・原価・粗利仮説", "代表8サービスの価格帯・原価・粗利を業界相場感から仮説化。実額は次回検証",
         "estimate", "low", "research/05_pricing_cost_margin.md"),
        ("富裕層特有の需要調査", "価格以外の価値訴求ポイント(業者選定代行・鍵預かり・窓口一本化等)を整理",
         "estimate", "low", "research/06_affluent_demand.md"),
    ]
    conn.executemany(
        """INSERT INTO research_notes (topic, summary, data_type, confidence, source_url, collected_at)
           VALUES (?,?,?,?,?,?)""",
        [r + (TODAY,) for r in rows],
    )


if __name__ == "__main__":
    main()
