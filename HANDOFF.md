# Choropleth Map for Japan — 開発引き継ぎ

最終更新: 2026-05-28
リポジトリ: https://github.com/bluegoat21/choropleth-map
公開URL: https://bluegoat21.github.io/choropleth-map/

---

## 1. プロジェクト概要

**「CSVをドラッグ&ドロップするだけで日本地図上の検索ボリュームを可視化する」** ブラウザツール集。完全クライアントサイド処理(CSVデータは外部送信されない)。

> ⚠️ **URL共有機能 (Supabase バックエンド) は 2026-06-14 にコスト削減のため凍結**。復活手順は §14 参照。将来的に会員制サービスサイトへの拡張を見据えた構成は維持。

### ツール構成 (3つの Webツール)

| URL | ツール名 | 対象 | 内部マスタ |
|---|---|---|---|
| `/` | ランディング(ハブページ) | — | — |
| `/area-builder/` | **Area Builder** | 全国市区町村 (1,902自治体) | `japan-cities.geojson` (9.6MB) |
| `/rail-builder/` | **Rail Builder** | 全国駅 (6,658) / 路線 (597) | `stations.json` (656KB) + `japan-rail-lines.geojson` (1MB) |

すべて GitHub Pages にホスティングされ、`.nojekyll` で Jekyll処理を無効化。

---

## 2. 識別コード仕様 (重要)

3ツールは **完全に独立した名前空間** を使用。共通コードはない。

| データ | コード形式 | 採番元 | 例 |
|---|---|---|---|
| エリア (市区町村) | **5桁数字** | JIS X 0402 (公式) | `13103` (港区) |
| 駅 | **`S` + 5桁数字** | 内部採番 (prepare_rail_data.py) | `S03540` (東京駅) |
| 路線 | **`L` + 4桁数字** | 内部採番 (build_rail_atlas.py、辞書順) | `L0267` (山手線), `L0329` (本線・京成) |

「本線」のような同名路線は事業者ごとに別コード(L0329=京成本線、L0337=阪神本線など)。

CSVに駅コードと路線コードが混在しても、各ツールはプレフィックス(S/L) で判別して該当するもののみマッチ。

---

## 3. ファイル構成

```
choropleth-map/
├── index.html                          # ランディング (両ツールへのリンク)
├── area-builder/                       # 🗾 Area Builder
│   ├── index.html                      # Webアプリ本体 (47KB)
│   ├── japan-cities.geojson            # 全国1902自治体ポリゴン (9.6MB)
│   ├── sample.csv                      # 雛形CSV (10エリア)
│   └── README.md
├── rail-builder/                       # 🚉 Rail Builder
│   ├── index.html                      # Webアプリ本体 (61KB)
│   ├── japan-rail-lines.geojson        # 全国597路線GeoJSON (1MB、code属性付き)
│   ├── stations.json                   # 全国6,658駅 (駅コード→{n,lat,lng,lines,op}) (656KB)
│   ├── lines-list.csv                  # 597路線の対応表 (路線コード/路線名/事業者)
│   ├── sample-stations.csv             # 駅サンプル (10駅)
│   └── sample-lines.csv                # 路線サンプル (10路線)
├── builder/                            # ⚠ 旧URL→area-builderへのリダイレクトHTML
│   └── index.html
├── build_atlas.py                      # 市区町村GeoJSON 生成スクリプト
├── build_rail_atlas.py                 # 路線GeoJSON 生成スクリプト (路線コード採番)
├── prepare_rail_data.py                # N02 → stations.csv/lines.csv 生成
├── build_map.py                        # 旧CLI版 (市区町村コロプレス静的HTML生成)
├── stations.csv                        # 全駅マスタ (6,658駅、stations.json元データ)
├── lines.csv                           # 路線マスタ (378路線)
├── n02_cache/                          # 国土数値情報 N02 鉄道データキャッシュ
└── README.md
```

### 中間生成物 (gitignore)

- `geojson_cache/` ... build_atlas.py が市区町村GeoJSONをキャッシュ
- `n02_cache/` ... N02鉄道Zipと展開済みGeoJSON

---

## 4. データフロー (各ツール)

### Area Builder
```
ユーザーCSV (市区町村コード + 数値列)
      ↓ ドロップ
列マッピング (codeCol/nameCol/kwCols 自動推定+手動修正)
      ↓
Atlas (japan-cities.geojson) と code でJOIN
      ↓ (政令市親コードは区コードに展開)
state.features = matched FeatureCollection
      ↓
Leaflet で choropleth描画 (ヒート/差分マップ切替)
```

### Rail Builder (駅データ)
```
ユーザーCSV (駅コード S\d+ + 数値列)
      ↓ ドロップ → 駅コード自動検出 (列名 or 値パターン)
列マッピング (codeCol/kwCols)
      ↓
stations.json (起動時プリロード) と駅コードでJOIN
      ↓ マッチ件数を即時表示 (✓N件 / ⚠M件未マッチ)
state.features = [{lat, lng, properties}]
      ↓
L.circleMarker で 比例シンボル描画 (ヒート/差分)
```

### Rail Builder (路線データ)
```
ユーザーCSV (路線コード L\d{4} + 数値列)
      ↓
japan-rail-lines.geojson (起動時プリロード) とJOIN
      ↓
L.geoJSON で線として描画 (太さ=Vol、色濃度=Vol)
```

---

## 5. 主要機能一覧 (実装済み)

### 両ツール共通
- ✅ CSV ドラッグ&ドロップ
- ✅ 列マッピング画面 (自動検出 + 手動修正)
- ✅ ヒートマップ表示 (Vol合計に比例)
- ✅ **差分マップ** (2列の比率対比、赤(A優勢)→白(拮抗)→青(B優勢))
- ✅ 最小値フィルタ
- ✅ キーワード個別選択 / プリセット (Area Builder) / 全選択・全解除
- ✅ PNG画像エクスポート (dom-to-image)
- ✅ **HTMLとして保存** (自己完結HTMLとしてダウンロード)
- ✅ 設定リンクをコピー (`?mode=...&kw=...&filter=...&title=...` を含むURLをクリップボードへ)
- 🧊 ~~URLで共有 (Supabase経由の短縮URL)~~ — コスト削減のため 2026-06-14 凍結 (復活手順 §14)
- ✅ コントロールパネル・凡例の最小化
- ✅ タイトル編集

### Rail Builder のみ
- ✅ データ種別切替 (駅 / 路線)
- ✅ 駅コードベースJOIN (緯度経度はマスタから自動解決)
- ✅ 路線コードベースJOIN (同名路線も事業者で区別)
- ✅ 駅マスタとAtlas のページ起動時プリロード
- ✅ マッチ件数のリアルタイム表示
- ✅ Vol=0 の路線/駅を灰色で薄く描画 (データなしを可視化)
- ✅ ツールチップに 駅名/路線名/事業者/路線リスト/全キーワード値
- ✅ 路線コード一覧CSV (`lines-list.csv`) ダウンロードボタン

### 共有HTML (exportHTMLで保存されたファイル) 閲覧専用UI
- ✅ 開いた時に自動で map-screen に遷移 (アップロード画面スキップ)
- ✅ ヘッダー (ホーム/最初に戻るリンク) を非表示
- ✅ 保存・共有ボタンを非表示
- ✅ map高さを 100vh に拡張 (ヘッダー分回収)
- ✅ Atlas/stations を内包 or features直接埋込で自己完結 (Area Builder は 170KB、Rail Builderは660KB〜1MB)
- ✅ 共通の `applySnapshot(snap, { viewOnly: true })` 関数を経由 (DRY、Supabase復活時に流用可)

---

## 6. 重要な実装パターン (開発者向け)

### exportHTML の仕組み (3ツール共通)

```js
function exportHTML() {
  if (!state.csv || !state.mapping) { alert('まずCSV読み込み'); return; }
  showLoading('HTML生成中...');
  setTimeout(doExportHTML, 50);   // 重要: requestAnimationFrame NG (preview無効化される)
}

function doExportHTML() {
  try {
    // 1. outerHTML取得前にloadingをhide (HTML生成中...が保存先に残る問題対策)
    const loadingEl = document.getElementById('loading');
    const wasShown = !loadingEl.classList.contains('hide');
    loadingEl.classList.add('hide');

    const html = document.documentElement.outerHTML;
    if (wasShown) loadingEl.classList.remove('hide');

    // 2. snapshot を JSON化して <script id="*-snapshot"> に埋め込む
    const snapshot = { csv, mapping, mode, selectedKws, diffCols, minFilter, title,
                       /* Atlas/stations or features */ };
    const script = `<script id="rb-snapshot" type="application/json">${
      JSON.stringify(snapshot).replace(/<\/script>/g, '<\\/script>')
    }<\/script>`;

    // 3. </head>直前に挿入
    const out = html.replace(/<\/head>/i, script + '\n</head>');
    const blob = new Blob(['<!DOCTYPE html>\n' + out], { type: 'text/html;charset=utf-8' });
    
    // 4. document.body にattachしてからclick (Firefox対策)
    const link = document.createElement('a');
    link.download = filename;
    link.href = URL.createObjectURL(blob);
    document.body.appendChild(link);
    link.click();
    setTimeout(() => { document.body.removeChild(link); URL.revokeObjectURL(link.href); }, 1500);
  } catch(e) {
    alert('HTML保存失敗: ' + e.message);
  } finally {
    hideLoading();
  }
}
```

### loadEmbeddedSnapshot (保存HTML開いた時の自動復元)

```js
function loadEmbeddedSnapshot() {
  const el = document.getElementById('rb-snapshot');  // or 'ab-snapshot'
  if (!el) return false;
  const snap = JSON.parse(el.textContent);
  
  // state復元
  Object.assign(state, { csv: snap.csv, mapping: snap.mapping, mode: snap.mode, ... });
  
  // 画面遷移
  document.getElementById('upload-screen').style.display = 'none';
  document.getElementById('mapping-screen').style.display = 'none';
  document.getElementById('map-screen').style.display = 'block';
  
  // 共有HTMLは閲覧専用UIに (ヘッダー/保存ボタン非表示、map高さ100vh)
  document.querySelector('.app-header').style.display = 'none';
  document.getElementById('export-floating').style.display = 'none';
  document.getElementById('map').style.height = '100vh';
  
  // ★ 重要: 保存時のLeaflet DOM を完全削除してからinitMap (二重pane回避)
  const mapDiv = document.getElementById('map');
  mapDiv.innerHTML = '';
  delete mapDiv._leaflet_id;
  
  // ★ 重要: state.features を再構築 (rail-builder) or 直接復元 (area-builder)
  buildFeatures();  // rail-builder のみ
  
  initMap();
  buildControlPanel();
  restyle();
}
document.addEventListener('DOMContentLoaded', loadEmbeddedSnapshot);
```

### 差分マップの計算

```js
function colorDiff(score) {  // score: -1 〜 +1
  if (score == null) return '#cccccc';
  const t = (score + 1) / 2;
  // 赤(#d73027) → 白(#f7f7f7) → 青(#2166ac) の3色補間
  ...
}
function computeDiffScores() {
  const { a, b } = state.diffCols;
  state.features.forEach(f => {
    const va = f.properties['v_' + a] || 0;
    const vb = f.properties['v_' + b] || 0;
    if (va + vb < 1) { scores[id] = null; return; }
    scores[id] = (vb - va) / (va + vb);
  });
}
```

### 🧊 URL共有 (Supabase) の仕組み — 2026-06-14 凍結

> コード上は削除済み。コミット履歴 (35f7a42, 9840200) と §14 に詳細な復活手順あり。
> `applySnapshot(snap, { viewOnly: true })` 共通関数は残してあるので、復活時はそのまま流用可。

---

## 7. 既知の制約・注意点

### ファイル/Bash権限
- macOSのプライバシー保護で `~/Downloads` にアクセス不可な場合がある
- 解決: システム設定→プライバシーとセキュリティ→ファイルとフォルダで対応ターミナルに Downloads を許可
- 一時的にはユーザーに `cp ~/Downloads/file.csv ~/claude-code/choropleth-map/` してもらう

### MCP keyword-volume APIの文字化け
- `軒` (U+8ED2) が稀に `軍` (U+8ECD) に化けることがある
- 検索Vol取得時に「一軒家」系で発生しやすい
- 対策: 1回のバッチを 195件以下に抑え、`軒` で明示的にエスケープ

### CSVの混在データ
- 「戸建て物件キーワード調査」のスプレッドシートは、駅(S\d+) と路線(L\d{4}) が同じCSVに混在する場合がある (6,418行など)
- Builderは自動で該当しないコードをスキップ。マッピング画面で「⚠ N件未マッチ」を表示する仕様

### 検索Volデータの地域バイアス
- 「戸建て物件キーワード調査」は関東中心 (71%) で、四国・沖縄は0件
- Vol=0 の路線は灰色で薄く表示される(以前は白で見えなかった)

### GitHub Pages デプロイ
- main branch に push すると自動デプロイ (1〜2分)
- `.nojekyll` で Jekyll処理を無効化済み
- アクセス確認: `curl -sI https://bluegoat21.github.io/choropleth-map/...`

### 🧊 Supabase 運用 (凍結中)
- URL共有機能は 2026-06-14 に凍結されたため、現在 Supabase へのアクセスはなし
- 復活手順は §14 参照

---

## 8. ローカル開発フロー

### 起動
```bash
cd /Users/radiata/claude-code/choropleth-map
python3 -m http.server 8000
# http://localhost:8000/area-builder/
# http://localhost:8000/rail-builder/
```

### 内部マスタの再生成
```bash
# 市区町村Atlas (要 GitHub APIアクセス、~60秒)
python3 build_atlas.py    # → area-builder/japan-cities.geojson

# 鉄道Atlas + 駅マスタ (要 n02_cache/N02-25_RailroadSection.geojson)
python3 build_rail_atlas.py   # → rail-builder/japan-rail-lines.geojson
python3 prepare_rail_data.py  # → stations.csv, lines.csv
# stations.json への変換:
python3 -c "
import csv, json
out = {}
with open('stations.csv') as f:
    for r in csv.DictReader(f):
        try: lat, lon = round(float(r['緯度']),5), round(float(r['経度']),5)
        except: continue
        out[r['駅コード']] = {'n':r['駅名'],'lat':lat,'lng':lon,
                              'lines':r['路線リスト'],'op':r['事業者リスト']}
open('rail-builder/stations.json','w').write(json.dumps(out,ensure_ascii=False,separators=(',',':')))
"
```

### コミット規約 (最近のスタイル)
- 件名: `{area-builder|rail-builder}: {変更概要}` (日本語)
- 本文: 修正理由・実装方針・検証結果を簡潔に
- `Co-Authored-By` 等は付けない (このプロジェクトの既存スタイル)

---

## 9. 関連スプレッドシート

- [戸建て物件キーワード調査](https://docs.google.com/spreadsheets/d/1hCuu_LsFgRRqU6B9IhkC6T5Onkfh74yb62LJHvWeyn0/)
  - 「市区町村」「市区町村検索Vol」 → Area Builderにアップ
  - 「駅コード」「路線コード」 → Rail Builderにアップ
  - 「路線コード」タブの **D列「検索キーワード」** は、各路線の一般呼称 (例: L0007 御堂筋線、L0267 山手線) を私が生成済み

---

## 10. 次の開発候補 (未実装/改善案)

### 短期(価値高い)
- [ ] **CSV分離ヘルパー**: 6,418行のような混在CSVから「駅のみ」「路線のみ」を抽出する UIまたはスクリプト
- [ ] **lines-list.csv 同等の駅一覧CSV**: 駅コード→駅名→事業者のリファレンスをダウンロード可能に (現在 stations.json は JSONなので人間が見にくい)
- [ ] **キーワード調査の地方拡充**: 四国・沖縄・九州・北海道の検索Volを取得 (mcp__keyword-volume使用、過去履歴参照)
- [ ] **LZ-String URL共有**: Supabaseに依存しない短縮なし共有URL (`#data=` ハッシュに圧縮埋込)。URL長制限はあるが、CSVが小さい案件では Supabase復活より低コスト

### 中期 (会員制サイトへの拡張 — Supabase 復活が前提)
- [ ] **URL共有機能の復活** (§14 の手順)
- [ ] **Supabase Auth 連携**: Email + Magic Link or Google OAuth (URL共有時にユーザー紐付け)
- [ ] **shared_maps に user_id 列追加**: 自分のマップは編集/削除可能に (RLSポリシー更新)
- [ ] **ダッシュボード**: 過去に作ったマップ一覧、view_count 確認
- [ ] **有料プラン分岐 (Stripe)**: 公開マップ件数制限、保持期間延長、独自ドメイン共有URL など

### 中期 (機能拡張)
- [ ] **builderとrail-builderの統合UI**: 1つのページで「エリア/駅/路線」をタブ切替できるよう
- [ ] **複数CSVの重ね合わせ**: エリア+駅+路線を同一マップに重ねて表示
- [ ] **stations.jsonの軽量化**: 駅名以外を別ファイルに分割 (現状656KBは少し重い)
- [ ] **CSVバリデーション強化**: 数値列の負値・桁あふれ等を警告

### 長期
- [ ] **CDN非依存化**: Leaflet等をローカルバンドル (完全オフライン)
- [ ] **PWA化**: オフラインキャッシュ、ホーム画面追加
- [ ] **OGP対応**: 共有URLのプレビュー画像生成 (Supabase Edge Function で Puppeteer 等)

---

## 11. 主要コミット履歴 (最近)

```
(未push) 両ツール: Supabase 依存を全削除 (URL共有機能を凍結)
7ed638e HANDOFF.md: URL共有機能(Supabase) の詳細を追記
9840200 rail-builder: Supabase 経由のURL共有機能を実装 (凍結済み)
35f7a42 area-builder: Supabase 経由のURL共有機能を実装 (凍結済み)
c40e92c area-builder: 「最初に戻る」リンクをランディングページに遷移するよう変更
e34e07e area-builder: ヘッダー右上の「ソース」リンクを削除
c8ec486 area-builder: ツールチップ合計をCSVの合計列ではなく全キーワード合計に修正
940bfe6 共有HTMLを閲覧専用UIに (ヘッダー/保存ボタン非表示)
96b14e9 area-builder: HTML保存機能を実装 (rail-builderから移植)
4c84e1c rail-builder: 保存HTMLでマーカー表示されない問題を修正
65f2134 rail-builder: 保存HTMLの「HTML生成中...」固定表示問題を修正
69d685b rail-builder: Vol=0 の路線/駅を灰色で描画してデータなしを可視化
375e986 rail-builder: Atlas をページロード時にプリロード、マッピング画面で路線コード一致件数を即表示
e53de52 rail-builder: exportHTML 「生成中」固まり問題を修正
291bc0b rail-builder: 路線コード一覧CSV(597路線)を公開
edf925d rail-builder: HTMLとして保存機能を実装
6142cf4 rail-builder: 路線データを路線コードベース化 (Lxxxx形式)
1a10a17 rail-builder: 差分マップ機能を追加 (2列対比、赤白青の3色)
e50f3d8 builder/ を area-builder/ にリネーム
8efa175 rail-builder: 駅データモードを駅コードベース化
ff8a8ce 鉄道版 Web ビルダー(rail-builder)を追加
dae6e59 Initial commit
```

---

## 12. このプロジェクトの設計思想

- **CSVデータを外部送信しない**: 機密性確保 (完全クライアントサイド処理)
- **JIS等の公式コードを優先**: 市区町村は5桁、駅・路線は内部採番だが正規化
- **共有しやすさ**: URL状態保存 + 自己完結HTML 保存で結果を簡単に共有
- **拡張性**: BuilderはCSV列を柔軟に解釈、ユーザーの任意キーワードに対応
- **見やすさ**: 比例シンボル/ヒートマップ/差分マップなど複数の視覚化方法
- **段階的開示**: アップロード → 列マッピング → マップ の3ステップで複雑さを管理

---

## 13. 次のチャットへ渡す指示テンプレート

```
住まいサーフィン SEO戦略用の地図可視化Webツール集 (Choropleth Map for Japan) の開発を継続します。

リポジトリ: https://github.com/bluegoat21/choropleth-map
公開URL: https://bluegoat21.github.io/choropleth-map/
ローカル: /Users/radiata/claude-code/choropleth-map/

3つのツール (area-builder, rail-builder, ランディング) で全機能実装済み。
URL共有機能は Supabase バックエンド (有料プラン) を使用。
詳細仕様・既知制約・次の開発候補は HANDOFF.md を参照してください。

今回のタスク: 【ここに依頼内容】
```

---

## 14. 🧊 URL共有 (Supabase バックエンド) — 凍結中の復活手順

**凍結日**: 2026-06-14
**凍結理由**: 月額利用コスト削減のため、Supabase プロジェクトを廃止
**凍結時点で実装済みだった内容**: 「URLで共有」ボタン → snapshot を `shared_maps` テーブルに INSERT → `?s=xxxxxxxx` の8文字短縮URLを発行 → 閲覧者アクセスで Supabase から SELECT → 閲覧専用UIで表示。3ヶ月で自動削除(pg_cron)。

### 凍結時に削除されたもの

| 種類 | 内容 |
|---|---|
| Supabase プロジェクト | `teqxxdveckinvyomfxoj` (ユーザーが手動削除) |
| `shared_maps` テーブル | プロジェクト削除に伴い消失 (要バックアップ後削除) |
| クライアントコード | Supabase SDK 読み込み、`shareURL` の Supabase 版、`loadSharedSnapshot`、`initFromURL` |

### 凍結時に保持されたもの (復活時に流用可能)

| 種類 | 場所 |
|---|---|
| `applySnapshot(snap, { viewOnly: true })` 共通関数 | area-builder/index.html, rail-builder/index.html |
| 既存の `shareURL()` (旧仕様、URLをクリップボードコピー) | 両ツール、ユーザー操作のエントリポイント維持 |
| メニュー項目 `data-export="url"` | 両ツール、ラベルだけ「設定リンクをコピー」に戻し済み |

### 凍結時に参照すべきコミット

| コミット | 内容 |
|---|---|
| [35f7a42](https://github.com/bluegoat21/choropleth-map/commit/35f7a42) | area-builder: Supabase 経由のURL共有機能を実装 |
| [9840200](https://github.com/bluegoat21/choropleth-map/commit/9840200) | rail-builder: Supabase 経由のURL共有機能を実装 |
| [7ed638e](https://github.com/bluegoat21/choropleth-map/commit/7ed638e) | HANDOFF.md: URL共有機能(Supabase) の詳細を追記 |

復活時はこれらのコミットの diff を参考にすれば、当時の実装にほぼ戻せる。

---

### 📦 復活手順

#### Step 1: 新しい Supabase プロジェクトを作成

1. https://supabase.com/dashboard で「New Project」
2. プロジェクト名・パスワード・リージョン(`Northeast Asia (Tokyo)` 推奨) を入力
3. 作成後、`Settings` → `API` から取得:
   - `Project URL` (例: `https://xxxxxxxxxxxx.supabase.co`)
   - `anon` `public` key (`eyJ...`)
   - ⚠ `service_role` キーは使わない・公開しない

#### Step 2: テーブル + RLS + RPC を作成

Supabase ダッシュボード → `SQL Editor` で実行:

```sql
-- shared_maps テーブル
CREATE TABLE IF NOT EXISTS shared_maps (
  id TEXT PRIMARY KEY,           -- 8文字ランダム英数字 (例: 'a3f9b2c1')
  tool TEXT NOT NULL CHECK (tool IN ('area-builder', 'rail-builder')),
  snapshot JSONB NOT NULL,
  title TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  view_count INT DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_shared_maps_created_at ON shared_maps(created_at);

-- RLS
ALTER TABLE shared_maps ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon can insert" ON shared_maps;
CREATE POLICY "anon can insert" ON shared_maps
  FOR INSERT TO anon WITH CHECK (true);

DROP POLICY IF EXISTS "anon can select" ON shared_maps;
CREATE POLICY "anon can select" ON shared_maps
  FOR SELECT TO anon USING (true);

-- view_count 加算 RPC (SECURITY DEFINER で RLSバイパス)
CREATE OR REPLACE FUNCTION increment_view_count(map_id TEXT)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  UPDATE shared_maps SET view_count = view_count + 1 WHERE id = map_id;
END;
$$;
```

#### Step 3: 自動削除ジョブを登録 (任意)

`Database` → `Extensions` で `pg_cron` を ON にしてから:

```sql
SELECT cron.schedule(
  'delete-old-shared-maps',
  '0 3 * * *',  -- 毎日 03:00 UTC (日本時間 12:00)
  $$DELETE FROM shared_maps WHERE created_at < NOW() - INTERVAL '3 months'$$
);
```

確認: `SELECT * FROM cron.job;`

#### Step 4: クライアントコードに Supabase を再導入

両ツール (`area-builder/index.html`, `rail-builder/index.html`) で:

**1. SDK 読み込み追加** (`<head>` または `<body>` 末尾の他script群と並べる)
```html
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
```

**2. 接続情報と client 初期化を script 先頭付近に追加**
```js
const SUPABASE_URL = '<新プロジェクトのURL>';
const SUPABASE_ANON_KEY = '<新プロジェクトのanon key>';
const sb = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
```

**3. `shareURL()` を Supabase 版に置き換え** (既存の旧版を消す):
```js
function genShareId() {
  const chars = 'abcdefghjkmnpqrstuvwxyz23456789';
  let id = '';
  for (let i = 0; i < 8; i++) id += chars[Math.floor(Math.random() * chars.length)];
  return id;
}
async function shareURL() {
  if (!state.csv || !state.mapping) { alert('まずCSV読み込み'); return; }
  showLoading('共有URL生成中...');
  try {
    const id = genShareId();
    const title = document.getElementById('map-title')?.value || '';
    const snapshot = {
      csv: state.csv, mapping: state.mapping, mode: state.mode,
      selectedKws: state.selectedKws, diffCols: state.diffCols,
      minFilter: state.minFilter, title,
      // area-builder のみ: features: state.features を追加
      // rail-builder は atlas/stations を含めない (閲覧側で fetch)
    };
    const { error } = await sb.from('shared_maps').insert({
      id, tool: 'area-builder',  // rail-builder なら 'rail-builder'
      snapshot, title,
    });
    if (error) throw error;
    const url = `${location.origin}${location.pathname}?s=${id}`;
    await navigator.clipboard.writeText(url);
    alert('共有URLをクリップボードにコピーしました:\n' + url + '\n\n※ 3ヶ月で自動削除されます');
  } catch (e) {
    alert('共有URL生成失敗: ' + (e.message || e));
  } finally { hideLoading(); }
}
```

**4. `loadSharedSnapshot` と `initFromURL` を追加して `loadEmbeddedSnapshot` 直呼びを置き換え**:
```js
async function loadSharedSnapshot() {
  const id = new URLSearchParams(location.search).get('s');
  if (!id) return false;
  showLoading('共有マップ読み込み中...');
  try {
    const { data, error } = await sb
      .from('shared_maps').select('snapshot, title, tool')
      .eq('id', id).maybeSingle();
    if (error) throw error;
    if (!data) throw new Error('共有マップが見つかりません');
    if (data.tool !== 'area-builder') throw new Error('別ツール用URLです');
    sb.rpc('increment_view_count', { map_id: id }).then(() => {}, () => {});
    await applySnapshot(data.snapshot, { viewOnly: true });
    return true;
  } catch (e) {
    alert('読み込み失敗: ' + e.message);
    return false;
  } finally { hideLoading(); }
}
async function initFromURL() {
  if (new URLSearchParams(location.search).get('s')) await loadSharedSnapshot();
  else await loadEmbeddedSnapshot();
}
// DOMContentLoaded のハンドラを initFromURL に差し替え
```

**5. メニュー項目のラベルを「🔗 URLで共有」に変更**:
```html
<button data-export="url">🔗 URLで共有 <span class="sub">(短いリンクで他人と共有・3ヶ月保持)</span></button>
```

#### Step 5: ローカル動作確認 → push

```bash
python3 -m http.server 8000
# http://localhost:8000/area-builder/ で CSV → マップ → 共有URL → 別タブで開く
```

---

### 💾 凍結前のデータバックアップ手順 (ユーザー作業)

Supabase プロジェクトを削除する前に、`shared_maps` の中身を保存しておくと、URLを再発行することなく過去の共有マップを復元できる。

#### A) Table Editor から CSV エクスポート (推奨)
1. ダッシュボード → `Table Editor` → `shared_maps`
2. 右上の `...` メニュー → `Export data to CSV`
3. ダウンロードした CSV を本リポジトリ外の安全な場所に保管

#### B) SQL でJSONダンプ (snapshot をきれいに保持)
SQL Editor で実行 → 結果を `Export` → JSON でダウンロード:
```sql
SELECT id, tool, snapshot, title, created_at, view_count
FROM shared_maps
ORDER BY created_at;
```

#### 復元時
復活後の新プロジェクトに INSERT:
```sql
INSERT INTO shared_maps (id, tool, snapshot, title, created_at, view_count) VALUES
('a3f9b2c1', 'area-builder', '{...}'::jsonb, 'タイトル', '2026-05-28', 0),
...;
```

---

### 🗑 Supabase プロジェクト削除手順 (ユーザー作業)

1. (上記バックアップを取得してから) ダッシュボード → `Settings` → `General`
2. 一番下までスクロール → `Danger Zone` → `Delete Project`
3. プロジェクト名をタイプして確認

---

(以上)
