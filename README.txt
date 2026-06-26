HACO+ Tokyo — Website v28

【v27 → v28 変更点】

1. プライバシーポリシー専用ページ作成 (privacy.html)
   - 日本語/英語の両言語対応
   - ヘア&ネイルサロン向けの一般的なポリシー
   - 11セクション構成: 取得 / 種類 / 目的 / 第三者提供 /
     Cookie / SNS連携 / 管理 / 開示・訂正 / 未成年 /
     改定 / お問い合わせ
   - 全ページのフッターから privacy.html へリンク

2. フッター「HACO Group」セクション修正
   旧: <strong>London</strong>
   新: <strong>海外店舗 / Overseas</strong>
   表記は既存サイト準拠:
   - HACO HAIR+NAILS  SHOREDITCH  |  LONDON
   - HACO HAIR+NAILS  HOXTON  |  LONDON

3. Nails 予約セクションを Hair と同じ 4 導線に拡張
   01 First visit / 初めての方 → Hot Pepper Beauty (Nail店舗ID)
   02 Book by nailist / ネイリスト指名 → 各ネイリスト
   03 Returning guest / 再来のお客様 → LINE
   04 International guests / 海外のお客様 → WhatsApp

4. Nails Hero画像をHairと同じワイドサイズに
   旧: 2400x1621 (アスペクト比 3:2)
   新: 2400x1350 (アスペクト比 16:9, Hair画像と同じ)
   中央クロップで処理、画像はそのまま使用

5. 長さ料金表記を英語に統一
   旧: 肩 – 鎖骨 / 鎖骨下 / 胸下 (堅い漢字表記)
   新: Medium / Long / Extra Long (英語表記)
   メニュー名と統一感が出る

6. アシスタント (Moe/Yaya/Kaito) のリンク位置を統一
   問題: モデル募集中の表記でカードの高さが変わり、
        他スタイリストとリンク位置がズレていた
   修正:
   - .artist-info に flex-grow: 1
   - .artist-links に margin-top: auto
   結果: 全スタイリストカードの BOOK/INSTAGRAM ボタンが
        下端揃いに

7. Nails ページの言語混在を解消
   - Reservations are handled... → 多言語化
   - Book via Hot Pepper Beauty → 多言語化
   - All prices tax included... → 多言語化
   - 各 section-intro も多言語化

【現在のファイル構成】
  index.html      ヘアページ
  nails.html      ネイルページ
  privacy.html    プライバシーポリシー (新規)
  assets/
    logo.png, hero-hair.jpg, concept-strip.jpg, instanticon.mp4
    nails/hero-pedicure.jpg (リサイズ済 16:9)
    press/*.jpg (10枚)
    staff/*.jpg (Hair 12名 + Nail Kurumi/Karen)

© 2026 HACO Group Co Ltd
