HACO+ Tokyo — Website v30

【v29 → v30 変更点】

1. Hero 中央ロゴを白ロゴ・背景なしに変更（前回完了済み）
   ・assets/logo-white.png（透明背景の白ロゴ）
   ・ドロップシャドウで視認性確保

2. フッター住所・営業時間を完全バイリンガル化
   JP版時に〒107-0062・東京都港区南青山・表参道駅より徒歩7分など
   完全に日本語表示

3. Contact リンクを mailto に変更
   旧: Hot Pepper Beauty へのリンク
   新: mailto:info@hacogroup.online
   タップでメール作成画面が直接開く

   変更箇所:
   - index.html フッター Contact
   - nails.html フッター Contact
   - privacy.html フッター Contact + JP/EN問い合わせ文

4. モバイル UI 大幅改善（ハンバーガーメニュー方式）
   旧 v29 の問題:
   - ナビメニューが横に詰まってロゴが見切れていた
   - スタイリストが480px以下で2カラム→大きすぎ

   新 v30:
   - ハンバーガーメニュー実装
     * モバイルでメニューを隠し、3線アイコン表示
     * タップでフルスクリーンメニュー（黒背景, blur）
     * Hair / Nail / Management / Book の4項目
     * アイコンはタップでX印にアニメ
     * メニュー外クリックで自動閉じ
   - Hero 画像が画面の78vhを占める存在感UP
   - Artists は3カラム維持（より小さくコンパクトに）
   - 文字サイズ最適化（名前13px, 役職10px等）

【プレビュー確認方法】
   ローカルで python3 -m http.server 8000 を実行し
   ブラウザの開発者ツール（スマホ表示）で確認可能

© 2026 HACO Group Co Ltd
