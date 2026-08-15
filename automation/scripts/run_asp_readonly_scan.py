"""ASP案件のread-onlyスキャンを実行するCLI。

デフォルトはdry-run（実際のブラウザ操作は行わず、何を実行する予定かを表示するだけ）。
本当に実行するには --execute を明示する。対象ASPが `automation/asp/base.TOS_REGISTRY` で
"allowed_readonly" になっていない場合は、--executeを付けても自動では実行されない
（各ASPモジュール内の `require_readonly_allowed` が例外を送出する）。

使い方:
  python -m automation.scripts.run_asp_readonly_scan --asp a8net --keyword "エアコンクリーニング" --service エアコンクリーニング
  python -m automation.scripts.run_asp_readonly_scan --asp a8net --keyword "..." --execute
"""

from __future__ import annotations

import argparse

from automation.asp import a8net, valuecommerce, save_asp_programs

_MODULES = {"a8net": a8net, "valuecommerce": valuecommerce}


def main():
    parser = argparse.ArgumentParser(description="ASP案件のread-onlyスキャン")
    parser.add_argument("--asp", choices=sorted(_MODULES.keys()), required=True)
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--service", default=None, help="service_catalog.service_name と一致させる")
    parser.add_argument("--execute", action="store_true", help="指定しない場合はdry-run(何もしない)")
    args = parser.parse_args()

    mod = _MODULES[args.asp]

    if not args.execute:
        print(f"[dry-run] {args.asp} で「{args.keyword}」を検索する予定です。")
        print("実行するには --execute を付けてください。")
        print("(対象ASPが規約未確認の場合は --execute を付けても自動実行されません)")
        return

    records = mod.search_programs(args.keyword, service_name=args.service)
    n = save_asp_programs(records)
    print(f"{n}件の案件を db/hermes.db の asp_programs テーブルへ保存しました。")
    for r in records:
        print(f"  - {r.program_name} ({r.commission_amount})")


if __name__ == "__main__":
    main()
