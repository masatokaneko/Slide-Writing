import openai
import json
import os
from datetime import datetime

class ContentGenerator:
    def __init__(self):
        openai.api_key = os.getenv('OPENAI_API_KEY')
        self.model = "gpt-4o"
        self.max_tokens = 4000
        self.temperature = 0.2
    
    def generate_structure(self, natural_input):
        """自然言語からスライド構造を生成"""
        
        prompt = self.create_structure_prompt(natural_input)
        
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            content = response.choices[0].message.content
            structure = json.loads(content)
            
            # 基本的な検証
            validated_structure = self.validate_structure(structure)
            return validated_structure
            
        except Exception as e:
            print(f"Error in content generation: {e}")
            return self.create_fallback_structure(natural_input)
    
    def create_structure_prompt(self, natural_input):
        """構造化プロンプトを作成"""
        return f"""
あなたはBCGのプレゼンテーション専門家です。以下の自然言語の内容を、論理的で説得力のあるスライド構造に変換してください。

【入力内容】
{natural_input}

【出力形式】
以下のJSON形式で出力してください：

{{
    "title": "プレゼンテーションのタイトル",
    "objective": "プレゼンテーションの目的",
    "target_audience": "想定聴衆",
    "slides": [
        {{
            "slide_number": 1,
            "title": "スライドタイトル",
            "type": "title_slide",
            "content": {{
                "main_message": "メインメッセージ",
                "subtitle": "サブタイトル（あれば）"
            }}
        }},
        {{
            "slide_number": 2,
            "title": "現状分析",
            "type": "content_slide",
            "content": {{
                "main_message": "現状の課題や機会",
                "supporting_points": [
                    "ポイント1",
                    "ポイント2", 
                    "ポイント3"
                ],
                "data": {{"market_size": "1000億円", "growth_rate": "5%"}}
            }}
        }},
        {{
            "slide_number": 3,
            "title": "解決策・提案",
            "type": "solution_slide",
            "content": {{
                "main_message": "提案内容",
                "solution_points": [
                    "解決策1",
                    "解決策2"
                ],
                "benefits": [
                    "便益1",
                    "便益2"
                ]
            }}
        }},
        {{
            "slide_number": 4,
            "title": "実行計画",
            "type": "chart_slide",
            "content": {{
                "main_message": "実行のロードマップ",
                "timeline": [
                    {{"phase": "Phase 1", "duration": "3ヶ月", "activities": ["活動1", "活動2"]}},
                    {{"phase": "Phase 2", "duration": "6ヶ月", "activities": ["活動3", "活動4"]}}
                ],
                "chart_type": "timeline"
            }}
        }},
        {{
            "slide_number": 5,
            "title": "期待効果・ROI",
            "type": "financial_slide",
            "content": {{
                "main_message": "投資効果の見込み",
                "financial_data": {{
                    "investment": "初期投資額",
                    "revenue_projection": [
                        {{"year": 1, "amount": "100万円"}},
                        {{"year": 2, "amount": "500万円"}},
                        {{"year": 3, "amount": "1億円"}}
                    ],
                    "roi": "投資回収期間"
                }},
                "chart_type": "bar_chart"
            }}
        }},
        {{
            "slide_number": 6,
            "title": "次のステップ",
            "type": "conclusion_slide",
            "content": {{
                "main_message": "今後のアクション",
                "action_items": [
                    "アクション1",
                    "アクション2",
                    "アクション3"
                ],
                "timeline": "実行タイムライン",
                "contact_info": "連絡先情報"
            }}
        }}
    ]
}}

【重要な原則】
1. BCGのピラミッド原則に従い、結論ファーストで構成
2. MECE（漏れなく重複なく）の観点で論理構造を整理
3. データと事実に基づく説得力のある構成
4. 聴衆のアクションを促す明確な提案
5. スライド数は5-8枚程度に調整

JSON形式のみを出力し、他の説明文は含めないでください。
"""
    
    def validate_structure(self, structure):
        """生成された構造の検証・補正"""
        
        # 必須フィールドの確認
        if 'title' not in structure:
            structure['title'] = 'プレゼンテーション'
        
        if 'slides' not in structure:
            structure['slides'] = []
        
        # スライド番号の正規化
        for i, slide in enumerate(structure['slides']):
            slide['slide_number'] = i + 1
            
            # 必須フィールドの補完
            if 'title' not in slide:
                slide['title'] = f'スライド {i + 1}'
            
            if 'type' not in slide:
                slide['type'] = 'content_slide'
            
            if 'content' not in slide:
                slide['content'] = {'main_message': 'コンテンツを確認してください'}
        
        return structure
    
    def create_fallback_structure(self, natural_input):
        """API呼び出し失敗時のフォールバック構造"""
        return {
            "title": "プレゼンテーション",
            "objective": "情報共有",
            "slides": [
                {
                    "slide_number": 1,
                    "title": "タイトル",
                    "type": "title_slide",
                    "content": {
                        "main_message": "プレゼンテーション",
                        "subtitle": "自動生成された資料"
                    }
                },
                {
                    "slide_number": 2,
                    "title": "内容",
                    "type": "content_slide",
                    "content": {
                        "main_message": natural_input[:200] + "..." if len(natural_input) > 200 else natural_input,
                        "supporting_points": [
                            "詳細な分析が必要",
                            "追加検討事項の整理",
                            "次のステップの明確化"
                        ]
                    }
                }
            ]
        } 