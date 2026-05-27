"""
全国鉄道路線GeoJSON Atlas 生成

国土数値情報 N02 (鉄道) から全国路線ラインを抽出 →
路線名+事業者でmerge → shapelyで頂点間引き → 単一GeoJSONとして
rail-builder/japan-rail-lines.geojson に出力。

このAtlasはWebビルダーに静的バンドルされ、CSVの「路線コード」と
joinできる形式: properties.code (L+4桁ゼロ埋め), 路線名, 事業者, 事業者元 を持つ。
- code は (路線名, 事業者表示名) を辞書順ソートして連番採番。
  路線名の異表記や事業者集約変更があった場合は安定しないため、
  公開後は OUTPUT_ALIAS との互換性を別途検討すること。

実行:
    python3 build_rail_atlas.py
    # 入力: n02_cache/N02-25_RailroadSection.geojson (要事前ダウンロード)
    # 出力: rail-builder/japan-rail-lines.geojson

注: N02 GMLデータ(無料) は事前に https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N02-v3_2.html から
ダウンロード→GeoJSONに変換して n02_cache/ に配置する必要があります。
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

from shapely.geometry import shape, mapping, MultiLineString
from shapely.ops import unary_union

ROOT = Path(__file__).parent
INPUT = ROOT / "n02_cache" / "N02-25_RailroadSection.geojson"
OUTPUT = ROOT / "rail-builder" / "japan-rail-lines.geojson"

# 事業者名の正規化マッピング (N02の表記 → 表示用)
OPERATOR_NORMALIZE = {
    "東日本旅客鉄道": "JR東日本",
    "東海旅客鉄道": "JR東海",
    "西日本旅客鉄道": "JR西日本",
    "北海道旅客鉄道": "JR北海道",
    "九州旅客鉄道": "JR九州",
    "四国旅客鉄道": "JR四国",
    "日本貨物鉄道": "JR貨物",
    "東京地下鉄": "東京メトロ",
    "東京都": "東京都営",
    "大阪市高速電気軌道": "Osaka Metro",
    "横浜市": "横浜市営",
    "名古屋市": "名古屋市営",
    "京都市": "京都市営",
    "神戸市": "神戸市営",
    "札幌市": "札幌市営",
    "仙台市": "仙台市営",
    "福岡市": "福岡市営",
}


def round_coords(coords, ndigits=4):
    if isinstance(coords, (int, float)):
        return round(coords, ndigits)
    return [round_coords(c, ndigits) for c in coords]


def main() -> None:
    if not INPUT.exists():
        sys.exit(
            f"❌ 入力ファイルが見つかりません: {INPUT}\n"
            "  N02 (鉄道) GeoJSON を https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N02-v3_2.html\n"
            "  からダウンロードして n02_cache/ に配置してください。"
        )

    print(f"📍 入力: {INPUT}")
    with INPUT.open(encoding="utf-8") as f:
        data = json.load(f)

    raw_features = data.get("features", [])
    print(f"   生Feature数: {len(raw_features)}")

    # 路線名 + 事業者 でグループ化
    groups: dict[tuple[str, str], list] = defaultdict(list)
    for ft in raw_features:
        p = ft.get("properties", {}) or {}
        name = p.get("N02_003", "")
        op_raw = p.get("N02_004", "")
        if not name or not op_raw:
            continue
        op_display = OPERATOR_NORMALIZE.get(op_raw, op_raw)
        groups[(name, op_display)].append((op_raw, ft.get("geometry")))

    print(f"   路線数(merge前): {sum(len(g) for g in groups.values())}, グループ後: {len(groups)}")

    # 各グループのジオメトリをunion → simplify
    # 路線コード採番のため、(路線名, 事業者表示名) を辞書順ソート
    out_features = []
    failed = 0
    sorted_keys = sorted(groups.keys())
    for idx, (name, op_display) in enumerate(sorted_keys, start=1):
        items = groups[(name, op_display)]
        try:
            shapes = []
            for _, geom in items:
                if not geom:
                    continue
                shapes.append(shape(geom))
            if not shapes:
                continue
            merged = unary_union(shapes)
            # MultiLineString に統一
            if merged.geom_type == "LineString":
                merged = MultiLineString([list(merged.coords)])
            simplified = merged.simplify(0.005, preserve_topology=True)
            if simplified.is_empty:
                continue
            geom_out = mapping(simplified)
            geom_out["coordinates"] = round_coords(geom_out["coordinates"])
            op_original = items[0][0]
            code = f"L{idx:04d}"
            out_features.append({
                "type": "Feature",
                "properties": {
                    "code": code,
                    "路線名": name,
                    "事業者": op_display,
                    "事業者元": op_original,
                },
                "geometry": geom_out,
            })
        except Exception as e:
            failed += 1
            print(f"  ⚠️ {name} ({op_display}): {e}", file=sys.stderr)

    print(f"\n🔧 出力features: {len(out_features)} (失敗: {failed})")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    atlas = {"type": "FeatureCollection", "features": out_features}
    OUTPUT.write_text(
        json.dumps(atlas, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    size_kb = OUTPUT.stat().st_size / 1024
    print(f"\n💾 出力: {OUTPUT} ({size_kb:.0f} KB)")
    print("\n✅ Atlas生成完了")


if __name__ == "__main__":
    main()
