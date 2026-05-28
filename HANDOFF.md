# Choropleth Map for Japan — 開発引き継ぎ

最終更新: 2026-05-28
リポジトリ: https://github.com/bluegoat21/choropleth-map
公開URL: https://bluegoat21.github.io/choropleth-map/

---

## 1. プロジェクト概要

**「CSVをドラッグ&ドロップするだけで日本地図上の検索ボリュームを可視化する」** ブラウザツール集。基本は完全クライアントサイド処理だが、**URL共有機能のみ Supabase バックエンドを使用** (詳細は §14)。将来的に会員制サービスサイトへの拡張を見据えた構成。

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
- ✅ **URLで共有** (Supabase 経由、`?s=xxxxxxxx` の短縮URL発行、3ヶ月保持)
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

### 共有HTML / 共有URL 共通 (閲覧専用UI)
- ✅ 開いた時に自動で map-screen に遷移 (アップロード画面スキップ)
- ✅ ヘッダー (ホーム/最初に戻るリンク) を非表示 → 閲覧専用UI
- ✅ 保存・共有ボタンを非表示
- ✅ map高さを 100vh に拡張 (ヘッダー分回収)
- ✅ 共通の `applySnapshot(snap, { viewOnly: true })` 関数を経由 (DRY)

### 共有HTML (exportHTMLで保存されたファイル) 固有
- ✅ Atlas/stations を内包 or features直接埋込で自己完結 (Area Builder は 170KB、Rail Builderは660KB〜1MB)

### 共有URL (Supabase) 固有
- ✅ snapshot は Supabase の `shared_maps` テーブルに JSONB で保存
- ✅ Rail Builder は atlas/stations を含めない (閲覧側で再fetch、Supabase容量節約)
- ✅ Area Builder は features (JOIN後の軽量データ) を含める (Atlas 9.6MB 再fetch回避)
- ✅ view_count を Supabase RPC でインクリメント
- ✅ 3ヶ月で自動削除 (pg_cron で毎日 `0 3 * * *`)

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

### URL共有 (Supabase) の仕組み (両ツール共通パターン)

```js
// CDN から SDK
// <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
const sb = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// 共有ID: 紛らわしい文字を除いた alphanum 8文字 (例: a3f9b2c1)
function genShareId() {
  const chars = 'abcdefghjkmnpqrstuvwxyz23456789';
  let id = '';
  for (let i = 0; i < 8; i++) id += chars[Math.floor(Math.random() * chars.length)];
  return id;
}

// 共有URLを発行
async function shareURL() {
  const id = genShareId();
  const snapshot = { csv, mapping, mode, selectedKws, diffCols, minFilter, title, ... };
  const { error } = await sb.from('shared_maps').insert({
    id, tool: 'area-builder',  // or 'rail-builder'
    snapshot, title,
  });
  const url = `${location.origin}${location.pathname}?s=${id}`;
  await navigator.clipboard.writeText(url);
}

// ?s=xxxxxxxx で復元
async function loadSharedSnapshot() {
  const id = new URLSearchParams(location.search).get('s');
  if (!id) return false;
  const { data, error } = await sb
    .from('shared_maps')
    .select('snapshot, title, tool')
    .eq('id', id)
    .maybeSingle();
  if (!data || data.tool !== 'area-builder') return false;
  sb.rpc('increment_view_count', { map_id: id });  // fire and forget
  await applySnapshot(data.snapshot, { viewOnly: true });
  return true;
}
```

**重要**: `applySnapshot` は exportHTML 経由の `loadEmbeddedSnapshot` と Supabase 経由の `loadSharedSnapshot` で共通化。両者の差は「snapshot をどこから取ってくるか」だけ。

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

### Supabase anon key の運用
- anon key は両ツールの HTML に直書きしているが、RLS (Row Level Security) で保護されているので公開しても問題ない
- 万一漏洩しても、できることは「INSERT (snapshot 追加)」と「SELECT (snapshot 取得)」のみ。他人のデータ書き換え/削除は不可
- ⚠ `service_role` キーは絶対にクライアントに置かない (RLSバイパス全権)
- 将来 abuse 対策が必要なら: Cloudflare Turnstile 等を挟む、レート制限、Supabase Edge Function 経由化など

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
- [ ] **共有URL の管理UI**: 自分が作った共有URLの一覧/削除 (会員機能の入り口)

### 中期 (会員制サイトへの拡張)
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
9840200 rail-builder: Supabase 経由のURL共有機能を実装
35f7a42 area-builder: Supabase 経由のURL共有機能を実装
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

## 14. Supabase バックエンド (URL共有機能)

将来の会員制サービスサイト化を見越して Supabase を選択。現状は URL 共有機能のみで使用。

### 接続情報

| 項目 | 値 |
|---|---|
| Project URL | `https://teqxxdveckinvyomfxoj.supabase.co` |
| anon key | `eyJhbGciOi...` (両ツールの `<script>` 内に直書き) |
| プラン | 有料プラン (詳細はオーナーに確認) |

接続情報は area-builder/index.html と rail-builder/index.html の `SUPABASE_URL`, `SUPABASE_ANON_KEY` 定数に直書き。

### テーブル定義: `shared_maps`

```sql
CREATE TABLE shared_maps (
  id TEXT PRIMARY KEY,           -- 8文字ランダム英数字 (例: 'a3f9b2c1')
  tool TEXT NOT NULL CHECK (tool IN ('area-builder', 'rail-builder')),
  snapshot JSONB NOT NULL,       -- exportHTML 同等のスナップショット
  title TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  view_count INT DEFAULT 0
);
CREATE INDEX idx_shared_maps_created_at ON shared_maps(created_at);
```

### RLS ポリシー

| 操作 | 匿名ユーザー | 備考 |
|---|---|---|
| INSERT | ✅ 許可 | RLSで誰でも INSERT 可 (`anon can insert`) |
| SELECT | ✅ 許可 | RLSで誰でも SELECT 可 (`anon can select`) |
| UPDATE | ❌ 不可 | view_count は RPC (SECURITY DEFINER) 経由でのみ |
| DELETE | ❌ 不可 | pg_cron の自動削除のみ |

### RPC: `increment_view_count`

```sql
CREATE OR REPLACE FUNCTION increment_view_count(map_id TEXT)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  UPDATE shared_maps SET view_count = view_count + 1 WHERE id = map_id;
END;
$$;
```

クライアントから `sb.rpc('increment_view_count', { map_id: id })` で呼ぶ。RLS をバイパスして view_count のみ更新。

### 自動削除 (pg_cron)

```sql
SELECT cron.schedule(
  'delete-old-shared-maps',
  '0 3 * * *',  -- 毎日 03:00 UTC (日本時間 12:00)
  $$DELETE FROM shared_maps WHERE created_at < NOW() - INTERVAL '3 months'$$
);
```

確認: `SELECT * FROM cron.job;` で jobid とスケジュールが見える。

### Snapshot の構造

#### Area Builder
```js
{
  csv: string,                  // CSV 全文
  mapping: { codeCol, nameCol, kwCols },
  features: GeoJSON.Feature[],  // JOIN後の軽量データ (Atlas 9.6MB 再fetch回避)
  mode: 'heat' | 'diff',
  selectedKws: string[],
  diffCols: { a: string, b: string },
  minFilter: number,
  title: string,
}
```

#### Rail Builder
```js
{
  csv: string,
  mapping: { dataType: 'station' | 'line', codeCol, kwCols },
  mode, selectedKws, diffCols, minFilter, title,
  // atlas / stations は含めない (閲覧側で fetch、容量節約)
}
```

### 共有URL の生成・復元フロー

```
[生成]
ユーザー操作 → shareURL() → genShareId() → INSERT → URL生成 → クリップボード

[復元]
ページロード → ?s=xxxxxxxx を検出 → SELECT → applySnapshot(snap, { viewOnly: true })
                                  → increment_view_count RPC (fire & forget)
```

### 将来の会員機能拡張ポイント

1. **`shared_maps` に `user_id UUID REFERENCES auth.users(id)` 列を追加**
2. **RLS ポリシー更新**: 自分の所有マップのみ UPDATE/DELETE 可能に
3. **Supabase Auth** (Email/Google) を追加: Magic Link が UX 軽量で推奨
4. **ダッシュボードページ** `/dashboard/` を追加: 過去マップ一覧、view_count 表示
5. **Stripe 連携**: 有料プランで保持期間延長・件数制限解除

---

(以上)
