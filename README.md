# Choropleth Map for Japan

エリア別・路線別の検索ボリュームを日本地図に可視化するWebツール集。

🔗 **公開URL**: https://bluegoat21.github.io/choropleth-map/

---

## 📦 ツール

### 🗾 [市区町村ツール](builder/)
全国1700自治体のコロプレスマップ。
- ヒートマップ + 差分マップ(2列対比)
- 最小値フィルタ、URL状態保存、PNG出力
- CSV ドラッグ&ドロップで即可視化

### 🚉 [駅・路線ツール](rail-builder/)
駅は比例シンボル、路線はライン太さで検索ボリュームを表現。
- 駅CSV(緯度経度入り) → CircleMarkerで自動配置
- 路線CSV → 全国378路線ラインAtlas(国土数値情報N02)と結合
- データ種別自動判定、最小値フィルタ、URL状態保存、PNG出力

---

## 🚀 ローカルで試す

```bash
cd choropleth-map
python3 -m http.server 8000
# ブラウザで http://localhost:8000/ を開く
```

---

## 🛠 CLI版(オプション)

Webツール以外に、Python CLI で静的HTMLを生成する方法もあります。

```bash
python3 build_map.py --csv your-data.csv --out output/map.html --title "タイトル"
```

詳細は [`builder/README.md`](builder/README.md) を参照。

---

## 🔧 Atlas データ再生成

GeoJSONは事前バンドルしていますが、再生成したい場合:

```bash
# 全国市区町村Atlas (builder/japan-cities.geojson)
python3 build_atlas.py

# 全国路線Atlas (rail-builder/japan-rail-lines.geojson)
# 事前にN02 GeoJSONを n02_cache/N02-25_RailroadSection.geojson に配置
python3 build_rail_atlas.py
```

依存: `pip install requests shapely`

---

## 📁 構成

```
choropleth-map/
├── index.html                    # ハブページ (ツール選択画面)
├── builder/                      # 🗾 市区町村ツール
│   ├── index.html
│   ├── japan-cities.geojson      # 全国1902自治体ポリゴン
│   └── sample.csv
├── rail-builder/                 # 🚉 駅・路線ツール
│   ├── index.html
│   ├── japan-rail-lines.geojson  # 全国378路線ライン
│   ├── sample-stations.csv       # 駅サンプル(10駅)
│   └── sample-lines.csv          # 路線サンプル(10路線)
├── build_map.py                  # CLI版 (市区町村)
├── build_atlas.py                # 市区町村GeoJSON Atlasジェネレータ
└── build_rail_atlas.py           # 路線GeoJSON Atlasジェネレータ
```

---

## 📜 ライセンス

- コード: MIT
- 市区町村GeoJSON: [niiyz/JapanCityGeoJson](https://github.com/niiyz/JapanCityGeoJson) (CC BY 4.0)
- 鉄道GeoJSON: [国土数値情報 N02](https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N02-v3_2.html)
- 地図タイル: [CARTO](https://carto.com/), [© OpenStreetMap contributors](https://www.openstreetmap.org/copyright)
