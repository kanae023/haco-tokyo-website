# HACO+ Journal — 設定と使い方

## 仕組み

```
Instagram に #hacojournal を付けて投稿
        ↓（毎朝 自動チェック）
GitHub Actions が記事の下書きを作成 → プルリクエスト
        ↓（スマホのGitHubアプリで確認・マージ）
hacoplus.jp/journal/ に公開
```

- 通常の作品投稿はジャーナルに載りません。**載せたい投稿にだけ `#hacojournal`** を付けてください。
- キャプションには「誰が・何を・どこで」を書くと記事の質が上がります。
  例：`Wataro がヘアモード12月号の表紙ヘアを担当しました。撮影：〇〇 #hacojournal`

## 初回設定（1回だけ）

### 1. Instagram のアクセストークンを取得
1. https://developers.facebook.com で「アプリを作成」→ ユースケース「Instagramでメッセージやコンテンツを管理」
2. 「Instagramログインによる API 設定」で @hacohairnailstokyo を追加し、**アクセストークンを生成**
3. 権限は `instagram_business_basic` のみで OK（投稿の読み取りだけ）

### 2. GitHub にシークレットを登録
リポジトリ → Settings → Secrets and variables → Actions → New repository secret

| 名前 | 内容 | 必須 |
|---|---|---|
| `IG_ACCESS_TOKEN` | 手順1のトークン | 必須 |
| `ANTHROPIC_API_KEY` | キャプションを記事文（日英）に整える | 任意 |
| `GH_PAT` | トークン自動延長の保存用（Fine-grained token、このリポジトリの Secrets: Read and write） | 任意（無いと60日ごとに手順1をやり直し） |

### 3. Actions の権限
Settings → Actions → General → Workflow permissions →
**「Read and write permissions」** と **「Allow GitHub Actions to create and approve pull requests」** をオン

### 4. 動作確認
Actions タブ →「Instagram → Journal」→「Run workflow」

## 記事を手で追加・修正する
`_journal/` の Markdown を GitHub 上で編集して保存すると、自動でページが作り直されます。
非公開にしたい記事は `status: draft` にしてください。

## 設定の変更
`scripts/build_journal.py` の先頭：
- `WORK_EMAIL` … 仕事依頼の窓口
- `RECRUIT_URL` … 採用ページ（新しいリクルートLPができたら差し替え）
- `STAFF` … スタッフの肩書き・写真・予約リンク（新しいスタッフはここに追加）
