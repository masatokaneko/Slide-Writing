import os
import openai
import json
import socket
from dotenv import load_dotenv
from pathlib import Path

class SlideGenerator:
    def __init__(self, timeout=60):
        load_dotenv(dotenv_path=Path(__file__).parent.parent / 'config' / '.env')
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.timeout = timeout
        if not self.api_key:
            raise ValueError('OpenAI APIキーが設定されていません。')
        openai.api_key = self.api_key

    def generate_structure(self, content: str) -> dict:
        """
        入力テキストをBCGスタイルのスライド構造(JSON)に変換
        """
        prompt = self._build_prompt(content)
        try:
            # タイムアウト・ネットワークエラー対応
            old_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(self.timeout)
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "あなたはBCGのプロフェッショナルなスライド構成コンサルタントです。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1200,
                request_timeout=self.timeout
            )
            socket.setdefaulttimeout(old_timeout)
            # 文字エンコーディング対応
            result_text = response.choices[0].message['content']
            try:
                result_json = json.loads(result_text)
            except json.JSONDecodeError:
                # JSONパース失敗時のリカバリ
                result_json = json.loads(result_text.encode('utf-8').decode('utf-8', 'ignore'))
            return result_json
        except openai.error.Timeout as e:
            return {"status": "error", "message": f"OpenAIタイムアウト: {str(e)}"}
        except openai.error.APIConnectionError as e:
            return {"status": "error", "message": f"ネットワーク接続エラー: {str(e)}"}
        except Exception as e:
            return {"status": "error", "message": f"AI処理エラー: {str(e)}"}

    def _build_prompt(self, content: str) -> str:
        return f"""
あなたはBCG（ボストン コンサルティング グループ）流のプロフェッショナルなスライド構成コンサルタントです。
以下の日本語ビジネス文書を、BCGスタイルのピラミッド構造・結論ファースト・MECE・1スライド1メッセージ・データドリブンの原則に従い、
JSON形式でスライド構造に変換してください。

【出力JSON形式】
{{
  "title": "プレゼンテーションタイトル",
  "slides": [
    {{
      "slide_number": 1,
      "title": "スライドタイトル",
      "type": "title_slide|content_slide|chart_slide|conclusion_slide",
      "content": {{
        "main_message": "メインメッセージ",
        "supporting_points": ["ポイント1", "ポイント2"],
        "data": {{"key": "value"}}
      }}
    }}
  ]
}}

【注意事項】
- JSON以外の出力は禁止
- スライド数は3〜7枚程度
- 各スライドは1メッセージ
- データや数値があれば必ず反映
- 日本語で出力

【変換対象文書】
{content}
"""

# 追加: main.pyから直接呼び出せる関数

def generate_slide_structure(content: str) -> dict:
    generator = SlideGenerator()
    return generator.generate_structure(content) 