# BCG スライドジェネレーター

## 概要
自然言語での入力から、BCGレベルの高品質なプレゼンテーションスライドを自動生成するシステムです。
GPT-4を活用して、プロフェッショナルなスライド構造を生成し、python-pptxを使用してPowerPointファイルを作成します。

## 必要な環境
- Windows 10/11
- Python 3.8以上
- インターネット接続
- OpenAI APIキー

## インストール手順

### 1. リポジトリのダウンロード
```cmd
# プロジェクトフォルダに移動
cd "C:\Users\masat\Desktop\Slide Writing"
```

### 2. 自動セットアップ
```cmd
# setup.batをダブルクリック、または
setup.bat
```

セットアップスクリプトは以下の処理を自動的に実行します：
- Python仮想環境の作成
- 必要なパッケージのインストール
- 設定ファイルの初期化

### 3. OpenAI APIキーの設定
1. `config\.env`ファイルを開く
2. `OPENAI_API_KEY=your_openai_api_key_here`の行を編集
3. 実際のAPIキーを入力して保存

### 4. アプリケーション起動
```cmd
# run.batをダブルクリック、または
run.bat
```

### 5. ブラウザでアクセス
http://localhost:5000

## 使用方法

1. テキストエリアに作成したいプレゼンテーションの内容を自然文で入力
2. 「スライドを生成」ボタンをクリック
3. 2-5分待機
4. 生成されたPowerPointファイルをダウンロード

### 入力例
```
BCGの成長率・市場シェアマトリクスについて説明するスライドを作成してください。
以下の内容を含めてください：
- マトリクスの4つの象限の説明
- 各象限における企業の戦略
- 実際の企業事例
- マトリクスの限界と注意点
```

## トラブルシューティング

### よくある問題と解決方法

1. Pythonが見つからない
   - Python 3.8以上をインストール
   - 環境変数PATHの設定確認

2. OpenAI APIエラー
   - APIキーの確認
   - API使用量の確認
   - インターネット接続の確認

3. ファイル生成エラー
   - `data\generated`フォルダの権限確認
   - ディスク容量の確認

### ログファイルの確認
- アプリケーションログ: `app_YYYYMMDD_HHMMSS.log`
- エラー詳細の確認方法：
  1. ログファイルをテキストエディタで開く
  2. エラーメッセージを確認
  3. タイムスタンプと関連する操作を特定

## 技術仕様
- フレームワーク: Flask
- AI: OpenAI GPT-4
- ファイル生成: python-pptx
- 対応ブラウザ: Chrome, Edge

## Windows環境特有の注意点

### パス処理
```python
# 良い例 (Windows対応)
from pathlib import Path
base_dir = Path(__file__).parent
data_dir = base_dir / "data" / "generated"

# 避けるべき例
data_dir = os.path.join(os.getcwd(), "data\\generated")
```

### 文字エンコーディング
```python
# ファイル読み書き時は必ずエンコーディング指定
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
```

### バッチファイルの活用
- `setup.bat`: 環境構築の自動化
- `run.bat`: アプリケーション起動の簡単化

### その他の注意点
- パスにスペースが含まれる場合の処理
- 日本語ファイル名の対応
- Windows Defenderの除外設定（必要に応じて）

## ライセンス
このプロジェクトはMITライセンスの下で公開されています。

## サポート
問題や質問がある場合は、GitHubのIssueを作成してください。