"""
全国市区町村GeoJSON Atlas ジェネレータ

niiyz/JapanCityGeoJson から全1700+自治体を一括取得 →
shapelyで頂点間引き → 座標3桁丸め → 単一GeoJSONとして area-builder/japan-cities.geojson に出力。

このAtlasはWebビルダーに静的バンドルされ、CSVの「市区町村コード」と
joinできる形式: properties.code (5桁), pref, name の3つだけ持つ。

実行:
    python3 build_atlas.py
    (キャッシュ済みなら数秒、初回フルダウンロードで30〜60秒程度)
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from shapely.geometry import shape, mapping

ROOT = Path(__file__).parent
CACHE_DIR = ROOT / "geojson_cache"
CACHE_DIR.mkdir(exist_ok=True)
OUTPUT = ROOT / "area-builder" / "japan-cities.geojson"

GEOJSON_BASE = "https://raw.githubusercontent.com/niiyz/JapanCityGeoJson/master/geojson"
GH_API_BASE = "https://api.github.com/repos/niiyz/JapanCityGeoJson/contents/geojson"

PREF_NAMES = [
    None,
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県",
    "岐阜県", "静岡県", "愛知県", "三重県",
    "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県",
    "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県",
    "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県",
    "沖縄県",
]


def list_codes_for_pref(pref: int) -> list[str]:
    """都道府県の全市区町村コードをGitHub APIで取得"""
    url = f"{GH_API_BASE}/{pref:02d}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    items = resp.json()
    return sorted(
        item["name"].replace(".json", "")
        for item in items
        if item["name"].endswith(".json")
    )


def fetch_geojson(code: str) -> dict | None:
    """個別都市のGeoJSONを取得 (キャッシュ優先、404はNone)"""
    cache_path = CACHE_DIR / f"{code}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    pref = code[:2]
    url = f"{GEOJSON_BASE}/{pref}/{code}.json"
    resp = requests.get(url, timeout=30)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    cache_path.write_bytes(resp.content)
    return json.loads(resp.content.decode("utf-8"))


def round_coords(coords, ndigits=3):
    if isinstance(coords, (int, float)):
        return round(coords, ndigits)
    return [round_coords(c, ndigits) for c in coords]


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    # Step 1: 都道府県ごとに全コードを取得
    print("📍 Step 1/4: 全都道府県の市区町村コード一覧を収集")
    all_codes: list[tuple[int, str]] = []
    for pref in range(1, 48):
        try:
            codes = list_codes_for_pref(pref)
            all_codes.extend([(pref, c) for c in codes])
            print(f"  {pref:02d} {PREF_NAMES[pref]}: {len(codes)}件")
        except Exception as e:
            print(f"  ⚠️ {pref:02d} {PREF_NAMES[pref]}: 失敗 ({e})", file=sys.stderr)
    print(f"   合計: {len(all_codes)}市区町村")

    # Step 2: GeoJSONを並列ダウンロード
    print(f"\n📥 Step 2/4: GeoJSON並列ダウンロード (20並列, キャッシュ優先)")

    def task(item):
        pref, code = item
        try:
            return (pref, code, fetch_geojson(code))
        except Exception as e:
            return (pref, code, None)

    results: list[tuple[int, str, dict | None]] = []
    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = [ex.submit(task, item) for item in all_codes]
        for i, f in enumerate(as_completed(futures), 1):
            results.append(f.result())
            if i % 200 == 0:
                print(f"   {i}/{len(all_codes)}")
    print(f"   完了: {sum(1 for _, _, gj in results if gj)}件取得")

    # Step 3: マージ + シンプル化 + 座標丸め
    print(f"\n🔧 Step 3/4: マージ + simplify (tolerance=0.005) + 座標3桁丸め")
    features: list[dict] = []
    failed = 0
    for pref, code, gj in results:
        if gj is None:
            failed += 1
            continue
        for ft in gj.get("features", []):
            props = ft.get("properties", {}) or {}
            name = props.get("N03_004", "") or ""
            geom = ft.get("geometry")
            if not geom or "coordinates" not in geom:
                continue
            try:
                shp = shape(geom).simplify(0.005, preserve_topology=True)
                if shp.is_empty:
                    continue
                new_geom = mapping(shp)
                new_geom["coordinates"] = round_coords(new_geom["coordinates"])
            except Exception:
                continue
            features.append({
                "type": "Feature",
                "properties": {
                    "code": code,
                    "pref": PREF_NAMES[pref],
                    "name": name,
                },
                "geometry": new_geom,
            })

    print(f"   features: {len(features)}, GeoJSON取得失敗: {failed}件")

    # Step 4: 保存
    print(f"\n💾 Step 4/4: 保存 → {OUTPUT}")
    atlas = {"type": "FeatureCollection", "features": features}
    OUTPUT.write_text(
        json.dumps(atlas, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    size_mb = OUTPUT.stat().st_size / 1024 / 1024
    print(f"   ファイルサイズ: {size_mb:.2f} MB")
    print(f"\n✅ Atlas生成完了")


if __name__ == "__main__":
    main()
