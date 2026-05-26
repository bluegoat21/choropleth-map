# Choropleth Builder

> エリア別の検索ボリュームを日本地図に可視化するブラウザだけで動くツール

CSV をドラッグ&ドロップするだけで、市区町村別の検索ボリュームをコロプレスマップ(ヒートマップ + 差分マップ)として表示します。検索キーワードを差し替えれば、不動産・医療・教育・観光、どんなテーマでも使えます。

完全クライアントサイド処理なので、**CSVデータが外部サーバーに送信されることはありません**。

---

## 🚀 デモ・利用方法

### ローカルで使う(最速)

```bash
cd choropleth-map
python3 -m http.server 8000
# ブラウザで http://localhost:8000/builder/ を開く
```

### CSVを用意する

最低限以下の列が必要です:

| 列名(例) | 必須 | 例 |
|---|---|---|
| `市区町村コード` | ✅ | `13103` (JIS X 0402 5桁) |
| `エリア名` | ✅ | `港区` |
| `エリア区分` | 任意 | `都心(23区)` |
| 数値列(1個以上) | ✅ | `不妊治療=320`, `妊活=720` |

**列名は柔軟です** — 「コード」「city_code」など類似名でも自動認識します。マッピング画面で手動上書きも可能。

サンプル: [`sample.csv`](sample.csv) をダウンロードして雛形に。

---

## 🎨 機能

### ヒートマップモード
- 任意のキーワード列(1個以上)を選択 → 合計値を白〜深紫のグラデーションで着色
- 「全選択」「全解除」ボタンでワンクリック操作
- 個別チェックは折りたたみ可能なアコーディオン式

### 差分マップモード
- 2列を選んで赤(マイナス側) ⇔ 青(プラス側)で対比
- 例: 「不妊治療 vs 妊活」「戸建て vs 建売」
- 拮抗は白、データなしはグレー

### 最小値フィルタ
- 「合計検索Vol が N 以上のエリアだけ着色」
- 未満エリアは薄グレーで残す(存在は分かる)
- ヒート時は **フィルタ後の最大値で正規化** するのでコントラスト最適化

### エクスポート
- **🔗 リンク取得**: 現在のモード/選択キーワード/フィルタ/タイトルをURLに保存。共有可能
- **🖼 PNG保存**: マップ+凡例をPNG画像でダウンロード
- **📄 HTML保存**: ページをブラウザ機能で保存(設定はURLに含まれる)

### URL状態保存
URLパラメータ例:
```
?mode=heat&kw=不妊治療,妊活&filter=500&title=不妊治療検索Vol分布
```
ブックマーク / 社内共有 / レポート貼付に便利。

---

## 🛠 GitHub Pages デプロイ手順

社内外で **URLでアクセスできるように公開** する場合:

### 1. リポジトリ作成

```bash
cd choropleth-map
git init
git add builder/ build_atlas.py build_map.py README.md
git commit -m "Initial commit"
```

GitHub.com で新規リポジトリを作成(例: `choropleth-map`)し、リモート追加:

```bash
git remote add origin https://github.com/YOUR_USERNAME/choropleth-map.git
git branch -M main
git push -u origin main
```

### 2. GitHub Pages 有効化

1. リポジトリのページで **Settings** タブ
2. 左メニューの **Pages**
3. **Source** で `main` ブランチ、フォルダは `/ (root)` を選択
4. **Save**
5. 1〜2分待つと公開URL発行: `https://YOUR_USERNAME.github.io/choropleth-map/builder/`

### 3. 確認

ブラウザで上記URLを開いて、ローカルと同じ画面が出ればOK。
初回ロード時に `japan-cities.geojson` (9MB、gzip後 ~3MB) を取得します。

---

## 🔧 GeoJSON Atlas の再生成

`japan-cities.geojson` は全国1900自治体を含む静的ファイルです。市町村合併や境界変更で更新が必要な場合:

```bash
python3 build_atlas.py
```

niiyz/JapanCityGeoJson から最新データを取得し、shapelyで簡略化して `builder/japan-cities.geojson` を上書きします。
依存: `pip install requests shapely`

---

## 📁 ファイル構成

```
builder/
├── index.html              # Webアプリ本体 (単一HTML)
├── japan-cities.geojson    # 全国1902自治体のmerged + simplified GeoJSON (9MB)
├── sample.csv              # 雛形CSV (10エリア)
└── README.md               # このファイル
```

依存:
- [Leaflet](https://leafletjs.com/) (CDN) — 地図ライブラリ
- [PapaParse](https://www.papaparse.com/) (CDN) — CSV パーサー
- [dom-to-image](https://github.com/tsayen/dom-to-image) (CDN) — PNG保存

---

## ⚠️ 既知の制約

- **`market.csv` の市区町村コードは5桁ゼロ埋め** が必須です。Google Sheets で頭ゼロが消える場合、列を「書式なしテキスト」に設定するか、`'01100` とシングルクォート付き入力してください。
- **政令指定都市は親市コード**(例: 横浜市=`14100`)を記入してください。区ポリゴンを自動集約します。
- **GeoJSON Atlas は2017年版ベース** — 一部の新設市(岩出市など)が未収録の可能性。`build_atlas.py` で再取得しても変わらない場合は CSV のコードを変更するか、隣接市で代替表示してください。
- **同名市町村は名前ではなくコードで識別** されるので、府中市(東京13206/広島34208)のような同名市も正しく区別されます。
- ブラウザの「CSV → PNG画像保存」フローには `domtoimage` を使っており、フォント描画でブラウザ間の僅かな差が出ることがあります。

---

## 📜 ライセンス

- このコード: MIT
- GeoJSON データ: [niiyz/JapanCityGeoJson](https://github.com/niiyz/JapanCityGeoJson) (CC BY 4.0)
- 地図タイル: [CARTO](https://carto.com/), [© OpenStreetMap contributors](https://www.openstreetmap.org/copyright)
