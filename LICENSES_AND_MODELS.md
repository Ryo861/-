# 依存関係・フォント・モデルの確認事項

フェーズAではAIモデルを利用・配布しません。外部APIの追加課金もありません。以下は採用版の配布物メタデータと同梱許諾文の確認結果で、商用製品としての最終的な法務審査ではありません。

| 採用物 | 版 | 確認した許諾 | 対応・確認事項 |
|---|---|---|---|
| Python / Tkinter | Windows想定3.11、クラウド3.13.5 | PSF / Tcl/Tkの許諾 | 開発版は利用者が公式インストーラーで導入。将来同梱するときはPSFとTcl/Tkの通知を含める |
| pypdf | 6.1.1 | BSD-3-Clause | 著作権・免責・条件を保持 |
| pypdfium2 | 4.30.0 | Apache-2.0 OR BSD-3-Clause ＋ PDFium第三者ライセンス | バインディング以外にPDFiumとその同梱物の通知が必要。Windows wheelの内容も別途確認 |
| ReportLab | 4.4.4 | BSD | 著作権・免責を保持。製品同梱時は追加フォントの許諾も確認 |
| Pillow | 11.3.0 | MIT-CMU | ライセンスとリンクする画像処理ライブラリの通知を確認 |
| charset-normalizer | 3.5.2 | MIT | ReportLabの依存。著作権・許諾文を保持 |
| BIZ UDゴシック | 取得済みRegular TTF | SIL Open Font License 1.1 | フォント単体の販売不可、Reserved Font Name等を遵守。PDF埋込み可。元のフォントを変更せずOFLを同梱 |

検証に使用したPythonパッケージの通知文は `third_party/licenses/` にコピーしました。Windowsのバイナリ配布を作る際は、その実際のwheelから第三者通知を取り直してください。Linux検証用XvfbはDebianの署名付きAPT配布から取得し、Windows配布ZIPには入れません。

BIZ UDゴシックの取得元：
- https://github.com/googlefonts/morisawa-biz-ud-gothic
- https://raw.githubusercontent.com/googlefonts/morisawa-biz-ud-gothic/main/fonts/ttf/BIZUDGothic-Regular.ttf
- 許諾文：`assets/fonts/OFL.txt`
- 取得時のTTF SHA-256：`7d2b48d84ef4e65c9f85bcf65fb1fb41c92b134be641fab6a7141d597c9a92b0`

ソースコードとTTFを一緒に配布するので、起動時にフォントをダウンロードすることはありません。フォントにない文字（例えば一部の絵文字）を含むコメントは、黙って文字化けさせず保存を止めて修正を求めます。

一次参照：
- pypdf：https://github.com/py-pdf/pypdf
- pypdfium2：https://github.com/pypdfium2-team/pypdfium2
- PDFium：https://pdfium.googlesource.com/pdfium/
- ReportLab：https://www.reportlab.com/
- Pillow：https://github.com/python-pillow/Pillow
- charset-normalizer：https://github.com/jawah/charset_normalizer

PyMuPDFは採用していません。PaddleOCR・Ollama・Gemma等はフェーズB以降で適合性とモデル規約を確認してから検討します。手書き認識の精度・速度・商用再配布の条件は今回確認していません。

この新規アプリ自身にOSSライセンスは指定していません。第三者の許諾文は保持します。公開・有償配布前にアプリ自身の配布条件を決めてください。
