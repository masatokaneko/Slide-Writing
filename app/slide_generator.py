import os
import openai
import json
import socket
import re
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
        入力テキストをBCGパートナーレベルの詳細なスライド構造(JSON)に変換
        """
        prompt = self._build_prompt(content)
        try:
            old_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(self.timeout)
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "あなたはBCGのパートナーであり、ピラミッドストラクチャ・MECE・結論ファースト・データドリブン・1スライド1メッセージ・ビジネスインパクト明確化の原則を徹底するプロフェッショナルなスライド構成コンサルタントです。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1800,
                timeout=self.timeout
            )
            socket.setdefaulttimeout(old_timeout)
            result_text = response.choices[0].message.content
            print("AIレスポンス:", result_text)
            # コードブロックや説明文を除去してJSON部分のみ抽出
            match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", result_text)
            if match:
                json_str = match.group(1)
            else:
                match = re.search(r"(\{[\s\S]*\})", result_text)
                json_str = match.group(1) if match else result_text
            try:
                result_json = json.loads(json_str)
            except json.JSONDecodeError:
                return {"status": "error", "message": "AIから有効なJSONが返りませんでした。AIレスポンス: " + result_text}
            return result_json
        except Exception as e:
            return {"status": "error", "message": f"AI処理エラー: {str(e)}"}

    def _build_prompt(self, content: str) -> str:
        return f"""
あなたはBCGのパートナーとして、以下の厳格なルールに従い、プロフェッショナルなスライド構造をJSON形式で出力してください。

【厳格な出力ルール】
- ピラミッドストラクチャ、MECE、結論ファーストを徹底
- 各スライドは「1スライド1メッセージ」
- 各スライドに必ず3～5個の具体的な内容項目（supporting_points）を含める
- 各スライドに必ず数値データやファクトを含める（例：市場規模、成長率、コスト削減率、実績数値など）
- 各スライドの主張（main_message）は明確かつインパクトのあるものにする
- 各supporting_pointは根拠や具体例、アクション、ビジネスインパクトを含める
- 聴衆（経営層・現場・顧客など）に応じた適切な詳細レベルで記述
- JSON以外の出力は禁止

【出力JSON形式】
{{
  "title": "プレゼンテーションタイトル",
  "slides": [
    {{
      "slide_number": 1,
      "title": "スライドタイトル",
      "type": "title_slide|content_slide|chart_slide|conclusion_slide",
      "content": {{
        "main_message": "メインメッセージ（結論ファーストで明確に）",
        "supporting_points": [
          "具体的な根拠・データ・アクション・ビジネスインパクト（数値必須）",
          "...（最低3つ、最大5つ）"
        ],
        "data": {{"key": "value"}}
      }}
    }}
  ]
}}

【例】
{{
  "title": "AI経理システム導入による業務効率化",
  "slides": [
    {{
      "slide_number": 1,
      "title": "AI経理システムの導入効果",
      "type": "content_slide",
      "content": {{
        "main_message": "AI経理システム導入で経理業務時間を70%削減",
        "supporting_points": [
          "年間1,200時間の作業削減（従業員50名規模の中小企業の場合）",
          "人件費コストを年間300万円削減",
          "入力ミス率を従来比80%低減",
          "導入企業の満足度92%（2024年4月調査）"
        ],
        "data": {{"作業削減時間": 1200, "コスト削減額": 3000000, "ミス率低減": 80, "満足度": 92}}
      }}
    }}
  ]
}}

【変換対象文書】
{content}
"""

def generate_slide_structure(content: str) -> dict:
    generator = SlideGenerator()
    return generator.generate_structure(content) 