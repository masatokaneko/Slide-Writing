@echo off
echo BCG Slide Generator 起動中...

REM 仮想環境有効化
call venv\Scripts\activate

REM アプリケーション起動
python -m app.main

pause 