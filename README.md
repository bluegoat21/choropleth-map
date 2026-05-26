# Choropleth Map for Japan

エリア別の検索ボリュームを日本地図に可視化するツール群。

## 📦 構成

| ディレクトリ / ファイル | 用途 |
|---|---|
| **[`builder/`](builder/)** | **Webアプリ版**(ブラウザでCSVをアップロード → 可視化)。GitHub Pages 公開対象 |
| [`build_map.py`](build_map.py) | CLI版。`python3 build_map.py --csv ... --out ...` で静的HTML生成 |
| [`build_atlas.py`](build_atlas.py) | 全国市区町村GeoJSONを一括取得して `builder/japan-cities.geojson` を生成 |

## 🚀 クイックスタート

### Webアプリ版を試す(推奨)
```bash
python3 -m http.server 8000
# ブラウザで http://localhost:8000/builder/ を開く
# CSVをドラッグ&ドロップするだけ
```

詳細は [`builder/README.md`](builder/README.md) を参照。GitHub Pages デプロイ手順も同README内。

### CLI版で生成
```bash
python3 build_map.py \
  --csv your-data.csv \
  --out output/map.html \
  --title "あなたのタイトル"
```

## 🎨 機能ハイライト

- **ヒートマップ** + **差分マップ(2列対比)** の2モード
- 列名は柔軟、CSVの中身に応じて自動マッピング
- 政令指定都市の親市コードから区ポリゴンを自動展開
- 最小値フィルタ、URL状態保存、PNG/HTMLエクスポート

## 📜 ライセンス

- コード: MIT
- GeoJSON: [niiyz/JapanCityGeoJson](https://github.com/niiyz/JapanCityGeoJson) (CC BY 4.0)
- 地図タイル: [CARTO](https://carto.com/), [© OpenStreetMap contributors](https://www.openstreetmap.org/copyright)
