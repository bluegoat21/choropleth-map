"""
住まいサーフィン｜検索キーワード地図可視化 (CLI版)

CSVの市区町村コード列を使って、「建売」vs「戸建て」検索ボリュームの差分を
日本地図上にコロプレスマップとして描画する。

使い方:
    python3 build_map.py \\
        --csv "戸建て物件キーワード調査 - 市区町村.csv" \\
        --out output/233areas.html \\
        --title "全国233エリア v2"

CSVに必要な列:
    必須: 市区町村コード, エリア名, 戸建て, 建売
    推奨: エリア区分, 一戸建て, 一軒家, 合計
    任意: 分譲住宅, 分譲戸建て, 分譲一戸建て, 新築戸建て, 新築一戸建て, 新築一軒家, 新築建売
"""
import argparse
import json
import sys
from pathlib import Path

import requests
import folium
from folium.features import GeoJsonTooltip
import pandas as pd
from shapely.geometry import shape, mapping

ROOT = Path(__file__).parent
GEOJSON_CACHE = ROOT / "geojson_cache"
GEOJSON_CACHE.mkdir(exist_ok=True)

GEOJSON_BASE = "https://raw.githubusercontent.com/niiyz/JapanCityGeoJson/master/geojson"

# キーワード名 → propertiesキー名 (英数の方がJSで扱いやすい)
KEYWORD_PROP_MAP: dict[str, str] = {
    "戸建て": "v_kodate",
    "一戸建て": "v_ikkodate",
    "一軒家": "v_ikkenya",
    "建売": "v_tatemai",
    "分譲住宅": "v_bunjo_jutaku",
    "分譲戸建て": "v_bunjo_kodate",
    "分譲一戸建て": "v_bunjo_ikkodate",
    "新築戸建て": "v_shinchiku_kodate",
    "新築一戸建て": "v_shinchiku_ikkodate",
    "新築一軒家": "v_shinchiku_ikkenya",
    "新築建売": "v_shinchiku_tatemai",
}

# ヒートマップ用プリセット (キーの並び順がそのままボタン配置になる)
PRESETS: dict[str, list[str]] = {
    "戸建て系": ["戸建て", "一戸建て", "一軒家"],
    "建売系": ["建売", "分譲住宅", "分譲戸建て", "分譲一戸建て"],
    "新築系": ["新築戸建て", "新築一戸建て", "新築一軒家", "新築建売"],
    "全選択": list(KEYWORD_PROP_MAP.keys()),
    "全解除": [],
}

# 政令指定都市の親市コード → 区コードレンジ
# (CSV側で親コード xx100 などを書いた場合、対応する区ポリゴンを全部集めて束ねる)
DESIGNATED_WARD_RANGES: dict[str, list[range]] = {
    "01100": [range(1101, 1111)],
    "04100": [range(4101, 4106)],
    "11100": [range(11101, 11111)],
    "12100": [range(12101, 12107)],
    "14100": [range(14101, 14119)],
    "14130": [range(14131, 14138)],
    "14150": [range(14151, 14154)],
    "15100": [range(15101, 15109)],
    "22100": [range(22101, 22104)],
    "22130": [range(22131, 22138)],
    "23100": [range(23101, 23117)],
    "26100": [range(26101, 26112)],
    "27100": [range(27101, 27129)],
    "27140": [range(27141, 27148)],
    "28100": [range(28101, 28111)],
    "33100": [range(33101, 33105)],
    "34100": [range(34101, 34109)],
    "40100": [range(40101, 40110)],
    "40130": [range(40131, 40138)],
    "43100": [range(43101, 43106)],
}


def download_geojson(code: str) -> dict | None:
    """指定したコード(5桁)のGeoJSONを取得。キャッシュ優先、404はNone。"""
    cache_path = GEOJSON_CACHE / f"{code}.json"
    if cache_path.exists():
        with cache_path.open(encoding="utf-8") as f:
            return json.load(f)
    pref = code[:2]
    url = f"{GEOJSON_BASE}/{pref}/{code}.json"
    resp = requests.get(url, timeout=30)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    cache_path.write_bytes(resp.content)
    return json.loads(resp.content.decode("utf-8"))


def collect_features(code: str) -> list[dict]:
    """コードに対応するfeatureのリストを返す。
    政令指定都市の親コードなら全区を集約する。
    """
    if code in DESIGNATED_WARD_RANGES:
        feats: list[dict] = []
        for r in DESIGNATED_WARD_RANGES[code]:
            for ward_code in r:
                gj = download_geojson(f"{ward_code:05d}")
                if gj is None:
                    continue
                feats.extend(gj["features"])
        return feats
    gj = download_geojson(code)
    return list(gj["features"]) if gj else []


def round_coords(coords, ndigits=3):
    if isinstance(coords, (int, float)):
        return round(coords, ndigits)
    return [round_coords(c, ndigits) for c in coords]


def color_for(score: float | None) -> str:
    """差分スコア(-1〜+1) → 赤(戸建て)→白→青(建売) のHEX色。"""
    if score is None:
        return "#cccccc"
    t = (score + 1) / 2  # -1..+1 → 0..1
    if t < 0.5:
        k = t / 0.5
        r = int(215 + (247 - 215) * k)
        g = int(48 + (247 - 48) * k)
        b = int(39 + (247 - 39) * k)
    else:
        k = (t - 0.5) / 0.5
        r = int(247 + (33 - 247) * k)
        g = int(247 + (102 - 247) * k)
        b = int(247 + (172 - 247) * k)
    return f"#{r:02x}{g:02x}{b:02x}"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="住まいサーフィン キーワード地図可視化",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--csv", type=Path, required=True,
        help="入力CSV (市区町村コード列必須)",
    )
    p.add_argument(
        "--out", type=Path, required=True,
        help="出力HTMLパス (親ディレクトリは自動作成)",
    )
    p.add_argument(
        "--title", default=None,
        help="マップタイトル (省略時はエリア数から自動生成)",
    )
    p.add_argument(
        "--min-volume", type=int, default=20,
        help="「データ少」グレー判定の閾値 (戸建て+建売 < この値), default=20",
    )
    p.add_argument(
        "--simplify", type=float, default=0.005,
        help="ポリゴン頂点間引きの度数閾値 (大きいほど軽量・粗), default=0.005",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if not args.csv.exists():
        sys.exit(f"❌ CSVが見つかりません: {args.csv}")

    # CSV読み込み: 市区町村コードは文字列(頭ゼロ保持)、空列(Unnamed:*)を自動除去
    df = pd.read_csv(args.csv, dtype={"市区町村コード": str})
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    df = df.dropna(subset=["市区町村コード"]).copy()
    # 数値として読まれて頭ゼロが消えたケースに備えてzfill
    df["市区町村コード"] = df["市区町村コード"].str.zfill(5)
    print(f"📄 CSV読み込み: {len(df)}行 ({args.csv.name})")

    # 重複市区町村コードの検知 (Sheets側のミス検出)
    dup_mask = df["市区町村コード"].duplicated(keep=False)
    if dup_mask.any():
        print(f"\n⚠️  重複市区町村コードが {dup_mask.sum()} 件あります:", file=sys.stderr)
        dup_df = df[dup_mask].sort_values("市区町村コード")
        for code, group in dup_df.groupby("市区町村コード"):
            names = group["エリア名"].tolist()
            print(f"   - {code}: {names}", file=sys.stderr)
        print("   ※ 同じコードのエリアは最後の1件で描画されます\n", file=sys.stderr)
        df = df.drop_duplicates(subset=["市区町村コード"], keep="last").copy()

    # 差分スコア計算
    def diff_score(row):
        ta = row["建売"]
        ko = row["戸建て"]
        if ta + ko < args.min_volume:
            return None
        return (ta - ko) / (ta + ko)
    df["diff_score"] = df.apply(diff_score, axis=1)

    n_data = df["diff_score"].notna().sum()
    n_low = df["diff_score"].isna().sum()
    print(f"   ├ 色分け対象: {n_data}エリア")
    print(f"   └ データ少(グレー): {n_low}エリア (閾値: 戸建て+建売 < {args.min_volume})")

    # GeoJSON収集
    merged_features: list[dict] = []
    failed: list[str] = []
    for _, row in df.iterrows():
        code = row["市区町村コード"]
        feats = collect_features(code)
        if not feats:
            failed.append(f"{row['エリア名']}({code})")
            continue
        for ft in feats:
            props = ft["properties"]
            props["city_code"] = code
            props["area_name"] = row["エリア名"]
            props["area_kbn"] = row.get("エリア区分", "")
            # 全11キーワードを埋め込み (JS側で動的合算するため)
            for kw, prop_key in KEYWORD_PROP_MAP.items():
                props[prop_key] = int(row[kw]) if kw in row and not pd.isna(row[kw]) else 0
            props["v_total"] = int(row.get("合計", 0))
            d = row["diff_score"]
            props["diff_score"] = None if pd.isna(d) else round(float(d), 3)
            props["diff_label"] = (
                "データ少" if pd.isna(d)
                else ("建売優勢" if d > 0.1 else ("戸建て優勢" if d < -0.1 else "拮抗"))
            )
            merged_features.append(ft)

    if failed:
        print(f"\n⚠️ GeoJSON取得失敗 ({len(failed)}件):", file=sys.stderr)
        for f in failed:
            print(f"   - {f}", file=sys.stderr)

    # ジオメトリ簡略化
    for ft in merged_features:
        geom = ft.get("geometry") or {}
        if not geom or "coordinates" not in geom:
            continue
        try:
            shp = shape(geom).simplify(args.simplify, preserve_topology=True)
            if not shp.is_empty:
                ft["geometry"] = mapping(shp)
        except Exception as e:
            print(f"  ⚠️ simplify失敗: {ft['properties'].get('area_name')}: {e}",
                  file=sys.stderr)
        g = ft["geometry"]
        if "coordinates" in g:
            g["coordinates"] = round_coords(g["coordinates"])

    geojson_obj = {"type": "FeatureCollection", "features": merged_features}

    # ----- Folium 描画 -----
    m = folium.Map(
        location=[37.0, 137.5],
        zoom_start=5,
        tiles="cartodbpositron",
        prefer_canvas=True,
    )

    folium.GeoJson(
        geojson_obj,
        name="建売 vs 戸建て",
        style_function=lambda f: {
            "fillColor": color_for(f["properties"].get("diff_score")),
            "color": "#666", "weight": 0.3, "fillOpacity": 0.78,
        },
        highlight_function=lambda _: {"weight": 2, "color": "#222", "fillOpacity": 0.92},
        tooltip=GeoJsonTooltip(
            fields=[
                "area_name", "area_kbn",
                "v_kodate", "v_tatemai", "v_ikkenya", "v_ikkodate",
                "v_total", "diff_score", "diff_label",
            ],
            aliases=[
                "エリア名", "区分",
                "戸建て", "建売", "一軒家", "一戸建て",
                "合計", "差分スコア(-1〜+1)", "判定",
            ],
            localize=True, sticky=False, labels=True,
        ),
    ).add_to(m)

    # タイトル
    title_text = args.title or (
        f'住まいサーフィン｜検索ボリューム地図 (全国{len(df)}エリア)'
    )
    title_html = f"""
    <div style="position: fixed; top: 16px; left: 50%; transform: translateX(-50%);
                z-index: 9999; background: rgba(255,255,255,0.95);
                padding: 8px 18px; border-radius: 8px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.2);
                font-family: -apple-system, system-ui, sans-serif;
                font-size: 14px; font-weight: 600;">
      {title_text}
    </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    # 動的凡例コンテナ (中身はJSで差し替え)
    legend_shell = """
    <div id="legend" style="position: fixed; bottom: 28px; left: 28px; z-index: 9999;
                background: rgba(255,255,255,0.97); padding: 12px 16px;
                border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.2);
                font-family: -apple-system, system-ui, sans-serif; font-size: 12px;">
      <div id="legend-content"></div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_shell))

    # アコーディオン矢印のスタイル (Folium生成CSSの上書き)
    accordion_style = """
    <style>
      #control-panel details summary {
        list-style: none;
        position: relative;
        padding-left: 18px;
      }
      #control-panel details summary::-webkit-details-marker {
        display: none;
      }
      #control-panel details summary::before {
        content: '▶';
        position: absolute;
        left: 0;
        top: 1px;
        font-size: 10px;
        color: #555;
        transition: transform 0.15s ease;
        display: inline-block;
        transform-origin: center;
      }
      #control-panel details[open] summary::before {
        transform: rotate(90deg);
      }
      #control-panel details summary:hover::before {
        color: #000;
      }
    </style>
    """
    m.get_root().html.add_child(folium.Element(accordion_style))

    # 動的コントロールパネル + ヒートマップ切替JS
    keyword_map_json = json.dumps(KEYWORD_PROP_MAP, ensure_ascii=False)
    presets_json = json.dumps(PRESETS, ensure_ascii=False)
    min_volume = args.min_volume
    panel_script = f"""
    <script>
    (function() {{
      const KEYWORD_PROP_MAP = {keyword_map_json};
      const PRESETS = {presets_json};
      const KEYWORDS = Object.keys(KEYWORD_PROP_MAP);
      const MIN_VOL = {min_volume};

      let currentMode = 'diff';
      let selectedKeywords = PRESETS['戸建て系'].slice();
      let minVolumeFilter = 0;
      let geoJsonLayer = null;
      let mapInstance = null;

      function passesFilter(p) {{
        return (p.v_total || 0) >= minVolumeFilter;
      }}
      function filteredStyle() {{
        return {{ fillColor: '#eeeeee', fillOpacity: 0.12, color: '#bbb', weight: 0.2 }};
      }}

      function findMap() {{
        for (const k in window) {{
          if (k.startsWith('map_') && window[k] instanceof L.Map) return window[k];
        }}
        return null;
      }}
      function findGeoJsonLayer(map) {{
        for (const k in window) {{
          if (k.startsWith('geo_json_') && window[k] instanceof L.GeoJSON) return window[k];
        }}
        let found = null;
        map.eachLayer(l => {{ if (l instanceof L.GeoJSON) found = l; }});
        return found;
      }}

      function colorDiff(score) {{
        if (score == null) return '#cccccc';
        const t = (score + 1) / 2;
        let r, g, b;
        if (t < 0.5) {{
          const k = t / 0.5;
          r = Math.round(215 + (247 - 215) * k);
          g = Math.round(48 + (247 - 48) * k);
          b = Math.round(39 + (247 - 39) * k);
        }} else {{
          const k = (t - 0.5) / 0.5;
          r = Math.round(247 + (33 - 247) * k);
          g = Math.round(247 + (102 - 247) * k);
          b = Math.round(247 + (172 - 247) * k);
        }}
        return 'rgb(' + r + ',' + g + ',' + b + ')';
      }}

      // 白(247,244,249) → 深紫(63,0,113)。√正規化でコントラスト改善
      function colorHeat(value, maxValue) {{
        if (!value || value <= 0 || !maxValue) return '#f7f4f9';
        const t = Math.min(Math.sqrt(value / maxValue), 1);
        const r = Math.round(247 - (247 - 63) * t);
        const g = Math.round(244 - (244 - 0) * t);
        const b = Math.round(249 - (249 - 113) * t);
        return 'rgb(' + r + ',' + g + ',' + b + ')';
      }}

      function computeSums() {{
        const sums = {{}};
        geoJsonLayer.eachLayer(l => {{
          const p = l.feature.properties;
          const code = p.city_code;
          if (sums[code] !== undefined) return;
          let sum = 0;
          selectedKeywords.forEach(kw => {{
            const key = KEYWORD_PROP_MAP[kw];
            sum += (p[key] || 0);
          }});
          sums[code] = sum;
        }});
        return sums;
      }}

      function restyle() {{
        if (!geoJsonLayer) return;
        let baseStyleFn;
        let filterCount = 0;
        if (currentMode === 'diff') {{
          baseStyleFn = f => ({{
            fillColor: colorDiff(f.properties.diff_score),
            color: '#666', weight: 0.3, fillOpacity: 0.78
          }});
          updateLegendDiff();
        }} else {{
          // ヒートマップ: フィルタを通った値だけで最大値を出す(色のコントラスト最適化)
          const sums = computeSums();
          let maxV = 1;
          geoJsonLayer.eachLayer(l => {{
            if (passesFilter(l.feature.properties)) {{
              const v = sums[l.feature.properties.city_code] || 0;
              if (v > maxV) maxV = v;
            }}
          }});
          baseStyleFn = f => ({{
            fillColor: colorHeat(sums[f.properties.city_code], maxV),
            color: '#666', weight: 0.3, fillOpacity: 0.78
          }});
          updateLegendHeat(maxV);
        }}
        // フィルタ未満は薄グレーで残す(視覚的に「ここにエリアがある」は分かる)
        const styleFn = f => {{
          if (!passesFilter(f.properties)) {{
            filterCount++;
            return filteredStyle();
          }}
          return baseStyleFn(f);
        }};
        // setStyle だけでなく options.style も書き換えないと、
        // ホバー解除時の resetStyle で元の差分スタイルに戻ってしまう
        geoJsonLayer.options.style = styleFn;
        geoJsonLayer.setStyle(styleFn);
        // フィルタの状態を表示
        const note = document.getElementById('filter-note');
        if (note) {{
          if (minVolumeFilter > 0) {{
            note.textContent = '※フィルタ適用中 (' + minVolumeFilter.toLocaleString() + '/月 未満は薄グレー)';
            note.style.display = 'block';
          }} else {{
            note.style.display = 'none';
          }}
        }}
      }}

      function updateLegendDiff() {{
        document.getElementById('legend-content').innerHTML =
          '<div style="font-weight: 600; margin-bottom: 6px;">建売 vs 戸建て 検索ボリューム差</div>' +
          '<div style="width: 220px; height: 14px; background: linear-gradient(to right, #d73027, #f7f7f7, #2166ac); border: 1px solid #999;"></div>' +
          '<div style="display: flex; justify-content: space-between; width: 220px; margin-top: 2px; font-size: 11px;">' +
            '<span>← 戸建て優勢</span><span>拮抗</span><span>建売優勢 →</span>' +
          '</div>' +
          '<div style="margin-top: 8px; display: flex; align-items: center; gap: 6px;">' +
            '<div style="width: 14px; height: 14px; background: #cccccc; border: 1px solid #999;"></div>' +
            '<span style="font-size: 11px;">データ少 (戸建て+建売 &lt; ' + MIN_VOL + ')</span>' +
          '</div>';
      }}
      function updateLegendHeat(maxV) {{
        const kwLabel = selectedKeywords.length === 0 ? '(未選択)' :
          (selectedKeywords.length > 3 ? selectedKeywords.length + 'キーワード合算' : selectedKeywords.join(' + '));
        document.getElementById('legend-content').innerHTML =
          '<div style="font-weight: 600; margin-bottom: 6px;">検索Volume ヒートマップ</div>' +
          '<div style="font-size: 11px; color: #666; margin-bottom: 6px;">対象: ' + kwLabel + '</div>' +
          '<div style="width: 220px; height: 14px; background: linear-gradient(to right, #f7f4f9, #3f0071); border: 1px solid #999;"></div>' +
          '<div style="display: flex; justify-content: space-between; width: 220px; margin-top: 2px; font-size: 11px;">' +
            '<span>0/月</span><span>' + maxV.toLocaleString() + '/月 (最大)</span>' +
          '</div>';
      }}

      function buildPanel() {{
        const panel = document.createElement('div');
        panel.id = 'control-panel';
        panel.style.cssText = 'position: fixed; top: 70px; right: 20px; z-index: 9999;' +
          'background: rgba(255,255,255,0.97); padding: 12px 14px; border-radius: 8px;' +
          'box-shadow: 0 2px 8px rgba(0,0,0,0.18);' +
          'font-family: -apple-system, system-ui, sans-serif; font-size: 12px;' +
          'max-width: 240px; max-height: 80vh; overflow-y: auto;';

        let html = '<div style="font-weight: 600; margin-bottom: 6px;">表示モード</div>' +
          '<div style="margin-bottom: 10px;">' +
            '<label style="display:inline-flex; align-items:center; gap:4px; margin-right:10px; cursor:pointer;">' +
              '<input type="radio" name="mode" value="diff" checked> 差分マップ</label>' +
            '<label style="display:inline-flex; align-items:center; gap:4px; cursor:pointer;">' +
              '<input type="radio" name="mode" value="heat"> ヒートマップ</label>' +
          '</div>' +
          // 最小Volフィルタ (両モード共通)
          '<div style="border-top: 1px solid #ddd; padding-top: 8px; margin-bottom: 8px;">' +
            '<div style="font-weight: 600; margin-bottom: 4px;">最小検索Vol (合計)</div>' +
            '<div style="display:flex; align-items:center; gap:6px;">' +
              '<input type="number" id="vol-filter" min="0" step="100" value="0" style="width:80px; padding:3px 6px; border:1px solid #aaa; border-radius:4px; font-size:12px;">' +
              '<span style="font-size:11px; color:#666;">/月以上</span>' +
            '</div>' +
            '<div id="filter-note" style="display:none; margin-top:4px; font-size:10px; color:#888;"></div>' +
          '</div>' +
          // ヒートマップ専用
          '<div id="heat-controls" style="display: none; border-top: 1px solid #ddd; padding-top: 8px;">' +
            '<div style="font-weight: 600; margin-bottom: 4px;">プリセット</div>' +
            '<div style="display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 8px;">';
        Object.keys(PRESETS).forEach(name => {{
          html += '<button data-preset="' + name + '" style="padding:3px 8px; font-size:11px; border:1px solid #999; background:#f9f9f9; border-radius:4px; cursor:pointer;">' + name + '</button>';
        }});
        html += '</div>' +
            // アコーディオン化: details/summary でネイティブ折りたたみ
            '<details style="border-top: 1px dashed #ddd; padding-top: 6px;">' +
              '<summary style="cursor: pointer; font-weight: 600; user-select: none; outline: none;">キーワード個別選択</summary>' +
              '<div id="keyword-checks" style="margin-top: 4px;">';
        KEYWORDS.forEach(kw => {{
          const checked = selectedKeywords.includes(kw) ? 'checked' : '';
          html += '<label style="display: block; padding: 2px 0; cursor:pointer;">' +
            '<input type="checkbox" data-kw="' + kw + '" ' + checked + '> ' + kw + '</label>';
        }});
        html += '</div></details>' +
          '</div>';
        panel.innerHTML = html;
        document.body.appendChild(panel);

        // フィルタ入力のイベントハンドラ
        panel.querySelector('#vol-filter').addEventListener('input', (e) => {{
          minVolumeFilter = parseInt(e.target.value, 10) || 0;
          restyle();
        }});

        panel.addEventListener('change', (e) => {{
          if (e.target.name === 'mode') {{
            currentMode = e.target.value;
            document.getElementById('heat-controls').style.display =
              currentMode === 'heat' ? 'block' : 'none';
            restyle();
          }} else if (e.target.dataset.kw) {{
            const kw = e.target.dataset.kw;
            if (e.target.checked) {{
              if (!selectedKeywords.includes(kw)) selectedKeywords.push(kw);
            }} else {{
              selectedKeywords = selectedKeywords.filter(k => k !== kw);
            }}
            if (currentMode === 'heat') restyle();
          }}
        }});
        panel.addEventListener('click', (e) => {{
          const preset = e.target.dataset.preset;
          if (preset && (preset in PRESETS)) {{
            selectedKeywords = PRESETS[preset].slice();
            panel.querySelectorAll('#keyword-checks input').forEach(cb => {{
              cb.checked = selectedKeywords.includes(cb.dataset.kw);
            }});
            if (currentMode === 'heat') restyle();
          }}
        }});
      }}

      function init() {{
        mapInstance = findMap();
        if (!mapInstance) return;
        geoJsonLayer = findGeoJsonLayer(mapInstance);
        if (!geoJsonLayer) {{
          console.error('GeoJsonレイヤーが見つかりません');
          return;
        }}
        buildPanel();
        updateLegendDiff();
      }}

      function waitInit() {{
        if (typeof L === 'undefined' || !findMap()) {{
          setTimeout(waitInit, 100);
          return;
        }}
        setTimeout(init, 400);
      }}

      if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', waitInit);
      }} else {{
        waitInit();
      }}
    }})();
    </script>
    """
    m.get_root().html.add_child(folium.Element(panel_script))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(args.out))
    size_mb = args.out.stat().st_size / 1024 / 1024
    print(f"\n✅ 出力: {args.out} ({size_mb:.2f} MB)")
    print(f"   features: {len(merged_features)}")


if __name__ == "__main__":
    main()
