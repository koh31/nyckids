# NYC Kids Go — Stylish Complete

GitHub Pages にそのままアップロードできる静的サイトです。

## Data sources
- New York Public Library (NYPL)
- Children's Museum of Manhattan
- MoMA
- The Metropolitan Museum of Art

## Auto update
GitHub Actions が1日2回 `scripts/update_events.py` を実行します。

## Publish
GitHub repository にこのフォルダの中身をすべてアップロードし、Settings → Pages → Deploy from a branch → main / root を選択します。

## Note
公式サイトのHTML構造が変更されると、そのソースの取得部分を更新する必要がある場合があります。イベント情報は必ず公式ページで最終確認してください。
