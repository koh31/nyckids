# NYC Kids Go!

NYCの子ども向けイベント紹介サイトです。静的サイトなので **GitHub Pagesで無料公開**でき、GitHub Actionsが毎日イベント情報を更新します。

## いちばん簡単な公開方法

1. GitHubで新しいリポジトリを作る
2. このZIPの中身をそのままアップロード
3. GitHubの `Settings → Pages`
4. `Deploy from a branch` を選択
5. Branchを `main` / folderを `/ (root)` にして保存
6. 数分後、公開URLが発行されます

## 自動更新

`.github/workflows/update-events.yml` が毎日1回 `scripts/update_events.py` を実行します。

初期ソース:
- Children's Museum of Manhattan
- Brooklyn Public Library / Youth & Family

ソース追加は `scripts/update_events.py` にアダプター関数を増やす方式です。NYPL、NYC Parks、Queens Public Libraryなども同じ方式で追加できます。

## 大事な注意

外部サイトのHTML構造は変更されることがあります。その場合、そのソースの取得処理だけ修正が必要です。
また、各イベントの日時・料金・対象年齢は変更される可能性があるため、サイトでは必ず主催者の公式ページへのリンクを掲載しています。

## ローカル確認

```bash
python -m http.server 8000
```

ブラウザで `http://localhost:8000` を開いてください。

## ファイル構成

- `index.html` — トップページ
- `styles.css` — デザイン
- `app.js` — 絞り込み・表示処理
- `data/events.json` — イベントデータ
- `scripts/update_events.py` — 自動収集
- `.github/workflows/update-events.yml` — 毎日更新の設定
