@echo off
echo BCG Slide Generator セットアップ開始...

REM 仮想環境作成
python -m venv venv
if %errorlevel% neq 0 (
    echo Pythonが見つかりません。Python 3.8以上をインストールしてください。
    pause
    exit /b 1
)

REM 仮想環境有効化
call venv\Scripts\activate

REM パッケージインストール
pip install -r requirements.txt

REM 設定ファイルコピー
if not exist config\.env (
    copy config\.env.example config\.env
    echo config\.envファイルを作成しました。OpenAI APIキーを設定してください。
)

echo セットアップ完了！
echo config\.envファイルにOpenAI APIキーを設定してから、run.batでアプリを起動してください。
pause 