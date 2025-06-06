# BCGスライドジェネレーター 開発手順書

## 開発戦略

### 段階的実装アプローチ
```
MVP1 (Week 1-2) → MVP2 (Week 3-5) → MVP3 (Week 6-7) → 完成版 (Week 8)
     ↓               ↓               ↓               ↓
基本機能検証     コア機能実装     UI/UX改善      最終調整
```

## Phase 1: 基盤構築・検証 (Week 1-2)

### Day 1: プロジェクト環境構築

#### 1.1 開発環境セットアップ
```bash
# プロジェクト作成
mkdir bcg-slide-generator
cd bcg-slide-generator

# Python仮想環境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 基本パッケージインストール
pip install flask python-pptx PyMuPDF pillow openai sqlite3
pip install pytest flask-cors python-dotenv

# プロジェクト構造作成
mkdir -p {app/{static/{css,js,images},templates,api,core,database},data/{design_assets,generated_slides,temp,backups},config,tests,docs}

# 設定ファイル作成
touch config/.env config/settings.json
```

#### 1.2 基本設定ファイル
**config/.env**:
```env
OPENAI_API_KEY=your_openai_api_key_here
FLASK_ENV=development
FLASK_DEBUG=True
DATABASE_PATH=data/database.db
UPLOAD_FOLDER=data/design_assets
OUTPUT_FOLDER=data/generated_slides
MAX_CONTENT_LENGTH=52428800  # 50MB
```

**config/settings.json**:
```json
{
    "app": {
        "name": "BCG Slide Generator",
        "version": "1.0.0",
        "host": "localhost",
        "port": 5000
    },
    "ai": {
        "model": "gpt-4o",
        "max_tokens": 4000,
        "temperature": 0.2
    },
    "file_processing": {
        "allowed_extensions": ["pdf", "png", "jpg", "jpeg", "pptx"],
        "max_file_size_mb": 50,
        "analysis_timeout": 300
    }
}
```

### Day 2: データベース設計・実装

#### 2.1 データベース初期化
**app/database/init_db.py**:
```python
import sqlite3
import os
from datetime import datetime

def create_database(db_path):
    """データベースの初期化"""
    
    # データベース接続
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # テーブル作成
    cursor.executescript('''
        -- デザインアセット管理
        CREATE TABLE IF NOT EXISTS design_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT NOT NULL CHECK(file_type IN ('pdf', 'png', 'jpg', 'jpeg', 'pptx')),
            category TEXT DEFAULT 'general',
            subcategory TEXT,
            quality_rating INTEGER CHECK(quality_rating BETWEEN 1 AND 5) DEFAULT 3,
            file_size INTEGER,
            upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            analysis_status TEXT DEFAULT 'pending' CHECK(analysis_status IN ('pending', 'processing', 'completed', 'failed')),
            extracted_patterns TEXT,
            usage_count INTEGER DEFAULT 0,
            last_used DATETIME
        );
        
        -- デザインパターン保存
        CREATE TABLE IF NOT EXISTS design_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id INTEGER REFERENCES design_assets(id),
            pattern_type TEXT NOT NULL CHECK(pattern_type IN ('layout', 'color', 'typography', 'visual')),
            pattern_name TEXT,
            pattern_data TEXT NOT NULL,
            quality_score REAL CHECK(quality_score BETWEEN 0 AND 1) DEFAULT 0.5,
            usage_frequency INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 生成されたプレゼンテーション履歴
        CREATE TABLE IF NOT EXISTS generated_presentations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            original_input TEXT NOT NULL,
            content_structure TEXT,
            applied_patterns TEXT,
            file_path TEXT,
            creation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            modification_count INTEGER DEFAULT 0,
            last_modified DATETIME,
            revision_history TEXT
        );
        
        -- システム設定
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            description TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        -- インデックス作成
        CREATE INDEX IF NOT EXISTS idx_design_assets_category ON design_assets(category);
        CREATE INDEX IF NOT EXISTS idx_design_patterns_type ON design_patterns(pattern_type);
        CREATE INDEX IF NOT EXISTS idx_presentations_date ON generated_presentations(creation_date);
    ''')
    
    # 初期データ投入
    cursor.execute('''
        INSERT OR IGNORE INTO system_settings (key, value, description) VALUES
        ('app_initialized', 'true', 'アプリケーション初期化フラグ'),
        ('default_design_pattern', 'bcg_standard', 'デフォルトデザインパターン'),
        ('api_cost_limit', '3000', '月間API費用上限（円）'),
        ('quality_threshold', '0.7', 'デザインパターン品質閾値')
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database created at: {db_path}")

if __name__ == "__main__":
    db_path = "../../data/database.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    create_database(db_path)
```

#### 2.2 データベースアクセス層
**app/database/db_manager.py**:
```python
import sqlite3
import json
from datetime import datetime
from contextlib import contextmanager

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
    
    @contextmanager
    def get_connection(self):
        """コンテキストマネージャーでDB接続を管理"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 辞書形式でアクセス可能
        try:
            yield conn
        finally:
            conn.close()
    
    def save_design_asset(self, filename, file_path, file_type, category=None, quality_rating=3):
        """デザインアセットの保存"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO design_assets (filename, file_path, file_type, category, quality_rating, file_size)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (filename, file_path, file_type, category, quality_rating, os.path.getsize(file_path)))
            conn.commit()
            return cursor.lastrowid
    
    def get_design_assets(self, category=None, limit=None):
        """デザインアセット一覧取得"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM design_assets WHERE 1=1"
            params = []
            
            if category:
                query += " AND category = ?"
                params.append(category)
            
            query += " ORDER BY upload_date DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def save_design_pattern(self, asset_id, pattern_type, pattern_data, pattern_name=None):
        """デザインパターンの保存"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO design_patterns (asset_id, pattern_type, pattern_name, pattern_data)
                VALUES (?, ?, ?, ?)
            ''', (asset_id, pattern_type, pattern_name, json.dumps(pattern_data)))
            conn.commit()
            return cursor.lastrowid
    
    def get_best_patterns(self, pattern_type=None, limit=10):
        """品質の高いデザインパターンを取得"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT * FROM design_patterns 
                WHERE quality_score > 0.6
            '''
            params = []
            
            if pattern_type:
                query += " AND pattern_type = ?"
                params.append(pattern_type)
            
            query += " ORDER BY quality_score DESC, usage_frequency DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def save_presentation(self, title, original_input, content_structure, file_path):
        """生成されたプレゼンテーションの保存"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO generated_presentations (title, original_input, content_structure, file_path)
                VALUES (?, ?, ?, ?)
            ''', (title, original_input, json.dumps(content_structure), file_path))
            conn.commit()
            return cursor.lastrowid
```

### Day 3-4: 基本API構造

#### 3.1 Flaskアプリケーション基盤
**app/main.py**:
```python
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import os
import json
from datetime import datetime

from database.db_manager import DatabaseManager
from core.design_analyzer import DesignAnalyzer
from core.content_generator import ContentGenerator
from core.pptx_generator import PPTXGenerator

# アプリケーション初期化
app = Flask(__name__)
CORS(app)

# 設定読み込み
with open('config/settings.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

app.config.update(config['app'])
app.config['MAX_CONTENT_LENGTH'] = config['file_processing']['max_file_size_mb'] * 1024 * 1024

# コンポーネント初期化
db_manager = DatabaseManager('data/database.db')
design_analyzer = DesignAnalyzer()
content_generator = ContentGenerator()
pptx_generator = PPTXGenerator()

@app.route('/')
def index():
    """メインページ"""
    return render_template('index.html')

@app.route('/api/health')
def health_check():
    """ヘルスチェック"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": config['app']['version']
    })

@app.route('/api/upload-design', methods=['POST'])
def upload_design():
    """デザインファイルアップロード"""
    try:
        if 'files' not in request.files:
            return jsonify({"error": "ファイルが選択されていません"}), 400
        
        files = request.files.getlist('files')
        category = request.form.get('category', 'general')
        quality = int(request.form.get('quality', 3))
        
        results = []
        for file in files:
            if file.filename == '':
                continue
            
            # ファイル保存
            filename = secure_filename(file.filename)
            file_path = os.path.join('data/design_assets', filename)
            file.save(file_path)
            
            # データベース保存
            file_type = filename.split('.')[-1].lower()
            asset_id = db_manager.save_design_asset(
                filename, file_path, file_type, category, quality
            )
            
            results.append({
                "filename": filename,
                "asset_id": asset_id,
                "status": "uploaded"
            })
        
        return jsonify({
            "status": "success",
            "uploaded_files": results
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate-slides', methods=['POST'])
def generate_slides():
    """スライド生成"""
    try:
        data = request.get_json()
        content = data.get('content', '')
        design_preference = data.get('design_preference', 'auto')
        
        if not content.strip():
            return jsonify({"error": "コンテンツを入力してください"}), 400
        
        # 1. コンテンツ構造生成
        structure = content_generator.generate_structure(content)
        
        # 2. デザインパターン選択
        if design_preference == 'auto':
            patterns = db_manager.get_best_patterns(limit=5)
        else:
            patterns = db_manager.get_best_patterns(limit=1)
        
        # 3. PowerPoint生成
        output_path = pptx_generator.create_presentation(structure, patterns)
        
        # 4. データベース保存
        presentation_id = db_manager.save_presentation(
            structure.get('title', 'Untitled'),
            content,
            structure,
            output_path
        )
        
        return jsonify({
            "status": "success",
            "presentation_id": presentation_id,
            "download_url": f"/api/download/{presentation_id}",
            "slide_count": len(structure.get('slides', [])),
            "generation_time": 45  # 実際の処理時間に置き換え
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # データベース初期化
    from database.init_db import create_database
    create_database('data/database.db')
    
    # アプリケーション起動
    app.run(
        host=config['app']['host'],
        port=config['app']['port'],
        debug=config['app'].get('debug', False)
    )
```

### Day 5-7: コア機能プロトタイプ

#### 5.1 最小限のデザイン分析機能
**app/core/design_analyzer.py**:
```python
import fitz  # PyMuPDF
from PIL import Image
import json
import colorsys
from collections import Counter

class DesignAnalyzer:
    def __init__(self):
        self.supported_formats = ['pdf', 'png', 'jpg', 'jpeg']
    
    def analyze_file(self, file_path):
        """ファイルからデザインパターンを分析"""
        file_extension = file_path.split('.')[-1].lower()
        
        if file_extension == 'pdf':
            return self.analyze_pdf(file_path)
        elif file_extension in ['png', 'jpg', 'jpeg']:
            return self.analyze_image(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
    
    def analyze_pdf(self, pdf_path):
        """PDFファイルの分析"""
        doc = fitz.open(pdf_path)
        analysis_result = {
            'layout': {},
            'colors': {},
            'typography': {},
            'visual_elements': {}
        }
        
        for page_num in range(min(5, len(doc))):  # 最初の5ページまで分析
            page = doc.load_page(page_num)
            
            # 1. レイアウト分析
            layout = self.extract_layout_from_page(page)
            analysis_result['layout'][f'page_{page_num}'] = layout
            
            # 2. 色彩分析
            colors = self.extract_colors_from_page(page)
            analysis_result['colors'][f'page_{page_num}'] = colors
            
            # 3. テキスト分析
            typography = self.extract_typography_from_page(page)
            analysis_result['typography'][f'page_{page_num}'] = typography
        
        doc.close()
        
        # 全体的なパターンを統合
        integrated_patterns = self.integrate_patterns(analysis_result)
        return integrated_patterns
    
    def extract_layout_from_page(self, page):
        """ページからレイアウトパターンを抽出"""
        blocks = page.get_text("dict")["blocks"]
        
        layout_info = {
            'page_width': page.rect.width,
            'page_height': page.rect.height,
            'text_blocks': [],
            'image_blocks': [],
            'margins': self.calculate_margins(blocks, page.rect)
        }
        
        for block in blocks:
            if "lines" in block:  # テキストブロック
                layout_info['text_blocks'].append({
                    'bbox': block['bbox'],
                    'width': block['bbox'][2] - block['bbox'][0],
                    'height': block['bbox'][3] - block['bbox'][1]
                })
            else:  # 画像ブロック
                layout_info['image_blocks'].append({
                    'bbox': block['bbox'],
                    'width': block['bbox'][2] - block['bbox'][0],
                    'height': block['bbox'][3] - block['bbox'][1]
                })
        
        return layout_info
    
    def extract_colors_from_page(self, page):
        """ページから色彩パターンを抽出"""
        # ページを画像として取得
        mat = fitz.Matrix(2, 2)  # 2倍解像度
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        # Pillowで色彩分析
        img = Image.open(io.BytesIO(img_data))
        colors = img.getcolors(maxcolors=256*256*256)
        
        if colors:
            # 使用頻度の高い色を抽出
            sorted_colors = sorted(colors, key=lambda x: x[0], reverse=True)[:10]
            color_palette = []
            
            for count, color in sorted_colors:
                if len(color) >= 3:  # RGB
                    hex_color = "#{:02x}{:02x}{:02x}".format(color[0], color[1], color[2])
                    color_palette.append({
                        'hex': hex_color,
                        'rgb': color[:3],
                        'frequency': count,
                        'type': self.classify_color(color[:3])
                    })
            
            return {
                'palette': color_palette,
                'dominant_color': color_palette[0] if color_palette else None,
                'color_count': len(color_palette)
            }
        
        return {'palette': [], 'dominant_color': None, 'color_count': 0}
    
    def extract_typography_from_page(self, page):
        """ページからタイポグラフィー情報を抽出"""
        blocks = page.get_text("dict")["blocks"]
        fonts = []
        font_sizes = []
        
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        fonts.append(span.get("font", "Unknown"))
                        font_sizes.append(span.get("size", 0))
        
        font_counter = Counter(fonts)
        size_counter = Counter(font_sizes)
        
        return {
            'primary_font': font_counter.most_common(1)[0][0] if font_counter else None,
            'font_variety': len(font_counter),
            'common_sizes': [size for size, count in size_counter.most_common(5)],
            'size_range': {
                'min': min(font_sizes) if font_sizes else 0,
                'max': max(font_sizes) if font_sizes else 0
            }
        }
    
    def classify_color(self, rgb):
        """色の分類（暖色、寒色、中性色等）"""
        r, g, b = rgb
        h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        
        if v < 0.3:
            return 'dark'
        elif v > 0.8 and s < 0.2:
            return 'light'
        elif h < 0.1 or h > 0.9:
            return 'warm'  # 赤系
        elif 0.3 < h < 0.7:
            return 'cool'  # 青緑系
        else:
            return 'neutral'
    
    def integrate_patterns(self, analysis_result):
        """複数ページの分析結果を統合"""
        # 実装を簡略化：最初のページの結果をベースに使用
        if analysis_result['layout']:
            first_page = list(analysis_result['layout'].keys())[0]
            base_layout = analysis_result['layout'][first_page]
            base_colors = analysis_result['colors'][first_page]
            base_typography = analysis_result['typography'][first_page]
            
            return {
                'layout_pattern': {
                    'grid_type': self.determine_grid_type(base_layout),
                    'margin_ratio': base_layout['margins'],
                    'block_distribution': len(base_layout['text_blocks'])
                },
                'color_pattern': {
                    'palette': base_colors['palette'][:5],
                    'color_harmony': self.analyze_color_harmony(base_colors['palette'])
                },
                'typography_pattern': {
                    'font_hierarchy': base_typography['common_sizes'],
                    'primary_font': base_typography['primary_font']
                }
            }
        
        return {}
    
    def determine_grid_type(self, layout):
        """レイアウトのグリッドタイプを判定"""
        text_blocks = layout['text_blocks']
        if len(text_blocks) <= 2:
            return 'simple'
        elif len(text_blocks) <= 5:
            return 'two_column'
        else:
            return 'complex'
    
    def analyze_color_harmony(self, palette):
        """色の調和パターンを分析"""
        if len(palette) < 2:
            return 'monochrome'
        
        # 簡単な色相分析
        hues = []
        for color_info in palette[:3]:
            rgb = color_info['rgb']
            h, s, v = colorsys.rgb_to_hsv(rgb[0]/255, rgb[1]/255, rgb[2]/255)
            hues.append(h)
        
        hue_diff = max(hues) - min(hues)
        if hue_diff < 0.1:
            return 'monochrome'
        elif hue_diff < 0.3:
            return 'analogous'
        else:
            return 'complementary'
```

## Phase 2: コア機能開発 (Week 3-5)

### Week 3: コンテンツ生成エンジン

#### コンテンツ生成機能
**app/core/content_generator.py**:
```python
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
```

### Week 4: PowerPoint生成エンジン

#### PowerPoint生成機能
**app/core/pptx_generator.py**:
```python
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
import os
from datetime import datetime
import json

class PPTXGenerator:
    def __init__(self):
        self.slide_width = Inches(13.33)  # 16:9 比率
        self.slide_height = Inches(7.5)
        self.default_font = 'Meiryo'  # 日本語対応フォント
        
        # BCGスタイルの色設定
        self.colors = {
            'primary': RGBColor(0, 112, 192),      # BCGブルー
            'secondary': RGBColor(68, 114, 196),   # ライトブルー
            'accent': RGBColor(255, 192, 0),       # オレンジ
            'text': RGBColor(64, 64, 64),          # ダークグレー
            'light_gray': RGBColor(217, 217, 217), # ライトグレー
            'white': RGBColor(255, 255, 255)       # ホワイト
        }
    
    def create_presentation(self, structure, design_patterns=None):
        """スライド構造からPowerPointプレゼンテーションを生成"""
        
        # 新しいプレゼンテーション作成
        prs = Presentation()
        prs.slide_width = self.slide_width
        prs.slide_height = self.slide_height
        
        # デザインパターンの適用
        if design_patterns:
            self.apply_design_patterns(prs, design_patterns)
        
        # スライドの生成
        for slide_data in structure.get('slides', []):
            self.create_slide(prs, slide_data)
        
        # ファイル保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{structure.get('title', 'presentation')}_{timestamp}.pptx"
        output_path = os.path.join('data/generated_slides', filename)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        prs.save(output_path)
        
        return output_path
    
    def create_slide(self, prs, slide_data):
        """個別スライドの作成"""
        slide_type = slide_data.get('type', 'content_slide')
        
        if slide_type == 'title_slide':
            return self.create_title_slide(prs, slide_data)
        elif slide_type == 'content_slide':
            return self.create_content_slide(prs, slide_data)
        elif slide_type == 'chart_slide':
            return self.create_chart_slide(prs, slide_data)
        elif slide_type == 'financial_slide':
            return self.create_financial_slide(prs, slide_data)
        elif slide_type == 'conclusion_slide':
            return self.create_conclusion_slide(prs, slide_data)
        else:
            return self.create_content_slide(prs, slide_data)  # デフォルト
    
    def create_title_slide(self, prs, slide_data):
        """タイトルスライドの作成"""
        slide_layout = prs.slide_layouts[0]  # タイトルレイアウト
        slide = prs.slides.add_slide(slide_layout)
        
        content = slide_data.get('content', {})
        
        # タイトル設定
        title = slide.shapes.title
        title.text = slide_data.get('title', 'タイトル')
        title.text_frame.paragraphs[0].font.size = Pt(44)
        title.text_frame.paragraphs[0].font.color.rgb = self.colors['primary']
        title.text_frame.paragraphs[0].font.name = self.default_font
        title.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        
        # サブタイトル設定
        if content.get('subtitle'):
            subtitle = slide.placeholders[1]
            subtitle.text = content['subtitle']
            subtitle.text_frame.paragraphs[0].font.size = Pt(24)
            subtitle.text_frame.paragraphs[0].font.color.rgb = self.colors['text']
            subtitle.text_frame.paragraphs[0].font.name = self.default_font
            subtitle.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        
        return slide
    
    def create_content_slide(self, prs, slide_data):
        """コンテンツスライドの作成"""
        slide_layout = prs.slide_layouts[1]  # コンテンツレイアウト
        slide = prs.slides.add_slide(slide_layout)
        
        content = slide_data.get('content', {})
        
        # タイトル設定
        title = slide.shapes.title
        title.text = slide_data.get('title', 'タイトル')
        title.text_frame.paragraphs[0].font.size = Pt(36)
        title.text_frame.paragraphs[0].font.color.rgb = self.colors['primary']
        title.text_frame.paragraphs[0].font.name = self.default_font
        
        # メインコンテンツエリア
        content_placeholder = slide.placeholders[1]
        
        # メインメッセージ
        main_message = content.get('main_message', '')
        if main_message:
            content_placeholder.text = main_message
            
            # メインメッセージのフォーマット
            p = content_placeholder.text_frame.paragraphs[0]
            p.font.size = Pt(20)
            p.font.color.rgb = self.colors['text']
            p.font.name = self.default_font
            p.font.bold = True
        
        # サポートポイントの追加
        supporting_points = content.get('supporting_points', [])
        if supporting_points:
            text_frame = content_placeholder.text_frame
            
            for point in supporting_points:
                p = text_frame.add_paragraph()
                p.text = f"• {point}"
                p.font.size = Pt(16)
                p.font.color.rgb = self.colors['text']
                p.font.name = self.default_font
                p.level = 1
        
        return slide
    
    def create_chart_slide(self, prs, slide_data):
        """チャートスライドの作成"""
        slide_layout = prs.slide_layouts[5]  # 空白レイアウト
        slide = prs.slides.add_slide(slide_layout)
        
        content = slide_data.get('content', {})
        
        # タイトル追加
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.2), Inches(12), Inches(1))
        title_frame = title_box.text_frame
        title_frame.text = slide_data.get('title', 'チャート')
        title_frame.paragraphs[0].font.size = Pt(36)
        title_frame.paragraphs[0].font.color.rgb = self.colors['primary']
        title_frame.paragraphs[0].font.name = self.default_font
        title_frame.paragraphs[0].font.bold = True
        
        # チャートタイプに応じた処理
        chart_type = content.get('chart_type', 'timeline')
        
        if chart_type == 'timeline':
            self.create_timeline_chart(slide, content)
        elif chart_type == 'bar_chart':
            self.create_bar_chart(slide, content)
        else:
            # デフォルト：テキストベースの表示
            self.create_text_chart(slide, content)
        
        return slide
    
    def create_timeline_chart(self, slide, content):
        """タイムラインチャートの作成"""
        timeline_data = content.get('timeline', [])
        
        start_x = Inches(1)
        start_y = Inches(2.5)
        box_width = Inches(2.5)
        box_height = Inches(1.5)
        spacing = Inches(0.5)
        
        for i, phase in enumerate(timeline_data):
            x = start_x + i * (box_width + spacing)
            
            # フェーズボックス
            box = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, x, start_y, box_width, box_height
            )
            box.fill.solid()
            box.fill.fore_color.rgb = self.colors['secondary']
            box.line.color.rgb = self.colors['primary']
            
            # フェーズテキスト
            text_frame = box.text_frame
            text_frame.text = f"{phase.get('phase', f'Phase {i+1}')}\n{phase.get('duration', '')}"
            
            p = text_frame.paragraphs[0]
            p.font.size = Pt(14)
            p.font.color.rgb = self.colors['white']
            p.font.name = self.default_font
            p.font.bold = True
            p.alignment = PP_ALIGN.CENTER
            
            # 活動リスト
            activities = phase.get('activities', [])
            if activities:
                activity_y = start_y + box_height + Inches(0.3)
                activity_box = slide.shapes.add_textbox(x, activity_y, box_width, Inches(2))
                activity_frame = activity_box.text_frame
                
                for activity in activities:
                    p = activity_frame.add_paragraph() if activity_frame.text else activity_frame.paragraphs[0]
                    p.text = f"• {activity}"
                    p.font.size = Pt(12)
                    p.font.color.rgb = self.colors['text']
                    p.font.name = self.default_font
    
    def create_financial_slide(self, prs, slide_data):
        """財務データスライドの作成"""
        slide_layout = prs.slide_layouts[5]  # 空白レイアウト
        slide = prs.slides.add_slide(slide_layout)
        
        content = slide_data.get('content', {})
        financial_data = content.get('financial_data', {})
        
        # タイトル
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.2), Inches(12), Inches(1))
        title_frame = title_box.text_frame
        title_frame.text = slide_data.get('title', '財務予測')
        title_frame.paragraphs[0].font.size = Pt(36)
        title_frame.paragraphs[0].font.color.rgb = self.colors['primary']
        title_frame.paragraphs[0].font.name = self.default_font
        title_frame.paragraphs[0].font.bold = True
        
        # 収益予測グラフ（簡易版）
        revenue_projection = financial_data.get('revenue_projection', [])
        if revenue_projection:
            self.create_revenue_chart(slide, revenue_projection)
        
        # ROI情報
        roi_info = financial_data.get('roi', '')
        if roi_info:
            roi_box = slide.shapes.add_textbox(Inches(8), Inches(2), Inches(4.5), Inches(3))
            roi_frame = roi_box.text_frame
            roi_frame.text = f"投資回収期間\n{roi_info}"
            
            p = roi_frame.paragraphs[0]
            p.font.size = Pt(24)
            p.font.color.rgb = self.colors['accent']
            p.font.name = self.default_font
            p.font.bold = True
            p.alignment = PP_ALIGN.CENTER
        
        return slide
    
    def create_revenue_chart(self, slide, revenue_data):
        """収益チャートの簡易作成"""
        start_x = Inches(1)
        start_y = Inches(5)
        bar_width = Inches(1.5)
        max_height = Inches(3)
        
        # 最大値を取得してスケール調整
        amounts = [int(item['amount'].replace('万円', '').replace('円', '')) for item in revenue_data]
        max_amount = max(amounts) if amounts else 1
        
        for i, item in enumerate(revenue_data):
            year = item.get('year', i + 1)
            amount_str = item.get('amount', '0')
            amount = int(amount_str.replace('万円', '').replace('円', ''))
            
            # バーの高さを計算
            bar_height = (amount / max_amount) * max_height
            bar_y = start_y - bar_height
            
            x = start_x + i * (bar_width + Inches(0.5))
            
            # バー作成
            bar = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, x, bar_y, bar_width, bar_height
            )
            bar.fill.solid()
            bar.fill.fore_color.rgb = self.colors['accent']
            bar.line.color.rgb = self.colors['primary']
            
            # 年ラベル
            year_box = slide.shapes.add_textbox(x, start_y + Inches(0.1), bar_width, Inches(0.5))
            year_frame = year_box.text_frame
            year_frame.text = f"Year {year}"
            year_frame.paragraphs[0].font.size = Pt(12)
            year_frame.paragraphs[0].font.color.rgb = self.colors['text']
            year_frame.paragraphs[0].font.name = self.default_font
            year_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
            
            # 金額ラベル
            amount_box = slide.shapes.add_textbox(x, bar_y - Inches(0.4), bar_width, Inches(0.3))
            amount_frame = amount_box.text_frame
            amount_frame.text = amount_str
            amount_frame.paragraphs[0].font.size = Pt(10)
            amount_frame.paragraphs[0].font.color.rgb = self.colors['text']
            amount_frame.paragraphs[0].font.name = self.default_font
            amount_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    
    def apply_design_patterns(self, prs, design_patterns):
        """学習したデザインパターンを適用"""
        # 実装を簡略化：基本的なカラーテーマの適用
        if design_patterns and len(design_patterns) > 0:
            pattern = design_patterns[0]
            pattern_data = json.loads(pattern.get('pattern_data', '{}'))
            
            # カラーパターンの適用
            if 'color_pattern' in pattern_data:
                color_info = pattern_data['color_pattern']
                palette = color_info.get('palette', [])
                
                if palette and len(palette) > 0:
                    # メインカラーの更新
                    primary_color = palette[0]
                    if 'rgb' in primary_color:
                        rgb = primary_color['rgb']
                        self.colors['primary'] = RGBColor(rgb[0], rgb[1], rgb[2])
```

## Phase 3: プレビュー・修正機能 (Week 6-7)

### Week 6: プレビュー機能

#### フロントエンドのプレビューシステム
**app/templates/index.html**:
```html
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BCG スライドジェネレーター</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <div class="container">
        <header>
            <h1>BCG スライドジェネレーター</h1>
            <div class="status-indicator" id="status">待機中</div>
        </header>
        
        <main>
            <div class="tabs">
                <button class="tab active" data-tab="generate">スライド生成</button>
                <button class="tab" data-tab="learn">デザイン学習</button>
                <button class="tab" data-tab="preview">プレビュー・修正</button>
            </div>
            
            <!-- スライド生成タブ -->
            <div id="generate-tab" class="tab-content active">
                <div class="input-section">
                    <label for="content-input">作成したいスライドの内容を記述してください：</label>
                    <textarea 
                        id="content-input" 
                        placeholder="例：新規事業としてAIチャットボットサービスを提案したい。市場規模は1000億円、競合は3社、差別化ポイントは業界特化型である点。収益予測は1年目100万円、3年目1億円。"
                        rows="8">
                    </textarea>
                </div>
                
                <div class="design-selection">
                    <label for="design-pattern">デザインパターン：</label>
                    <select id="design-pattern">
                        <option value="auto">自動選択（推奨）</option>
                        <option value="bcg_standard">BCG標準</option>
                        <option value="financial">財務重視</option>
                        <option value="creative">クリエイティブ</option>
                    </select>
                </div>
                
                <button id="generate-btn" class="primary-btn">
                    <span class="btn-text">スライドを生成</span>
                    <span class="spinner" style="display: none;">⟳</span>
                </button>
                
                <div id="progress-area" class="progress-section" style="display: none;">
                    <div class="progress-bar">
                        <div class="progress-fill"></div>
                    </div>
                    <div class="progress-text">AIがスライドを作成中...</div>
                </div>
            </div>
            
            <!-- デザイン学習タブ -->
            <div id="learn-tab" class="tab-content">
                <div class="upload-section">
                    <div class="upload-area" id="design-upload">
                        <input type="file" id="design-files" multiple accept=".pdf,.png,.jpg,.jpeg,.pptx">
                        <div class="upload-placeholder">
                            <div class="upload-icon">📁</div>
                            <p>デザインファイルをドラッグ&ドロップ<br>または クリックして選択</p>
                            <small>PDF, PNG, JPG, PPTX対応（最大50MB）</small>
                        </div>
                    </div>
                    
                    <div class="file-list" id="file-list" style="display: none;"></div>
                </div>
                
                <div class="categorization">
                    <div class="form-row">
                        <div class="form-group">
                            <label for="category">カテゴリー：</label>
                            <select id="category">
                                <option value="strategy">戦略・企画</option>
                                <option value="financial">財務・会計</option>
                                <option value="marketing">マーケティング</option>
                                <option value="operation">オペレーション</option>
                                <option value="general">その他</option>
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label for="quality">品質評価：</label>
                            <select id="quality">
                                <option value="5">★★★★★ 最高品質</option>
                                <option value="4">★★★★☆ 高品質</option>
                                <option value="3" selected>★★★☆☆ 標準</option>
                                <option value="2">★★☆☆☆ 低品質</option>
                                <option value="1">★☆☆☆☆ 参考程度</option>
                            </select>
                        </div>
                    </div>
                </div>
                
                <button id="learn-btn" class="secondary-btn">デザインパターンを学習</button>
                
                <div id="learned-patterns" class="patterns-section">
                    <h3>学習済みデザインパターン</h3>
                    <div class="pattern-grid" id="pattern-list">
                        <!-- 動的に生成 -->
                    </div>
                </div>
            </div>
            
            <!-- プレビュー・修正タブ -->
            <div id="preview-tab" class="tab-content">
                <div class="preview-section">
                    <div class="slide-viewer">
                        <div class="slide-container">
                            <div id="slide-preview" class="slide-preview">
                                <div class="no-slides">
                                    まずはスライドを生成してください
                                </div>
                            </div>
                        </div>
                        
                        <div class="slide-navigation">
                            <button id="prev-slide" class="nav-btn" disabled>◀ 前</button>
                            <span id="slide-counter" class="slide-counter">0 / 0</span>
                            <button id="next-slide" class="nav-btn" disabled>次 ▶</button>
                        </div>
                    </div>
                    
                    <div class="controls-panel">
                        <div class="revision-section">
                            <h3>修正指示</h3>
                            <textarea 
                                id="revision-input" 
                                placeholder="修正したい内容を自然言語で入力してください&#10;例：2枚目のタイトルを短くして、グラフの色を青にして"
                                rows="4">
                            </textarea>
                            <button id="apply-revision" class="secondary-btn">修正を適用</button>
                        </div>
                        
                        <div class="download-section">
                            <h3>ダウンロード</h3>
                            <button id="download-pptx" class="primary-btn" disabled>
                                PowerPointファイルをダウンロード
                            </button>
                            <div class="file-info" id="file-info" style="display: none;">
                                <small>ファイル名: <span id="filename"></span></small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>
    
    <script src="{{ url_for('static', filename='js/app.js') }}"></script>
</body>
</html>
```

#### JavaScript アプリケーション
**app/static/js/app.js**:
```javascript
class SlideGeneratorApp {
    constructor() {
        this.currentPresentation = null;
        this.currentSlideIndex = 0;
        this.slides = [];
        
        this.initializeEventListeners();
        this.loadLearnedPatterns();
    }
    
    initializeEventListeners() {
        // タブ切り替え
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });
        
        // スライド生成
        document.getElementById('generate-btn').addEventListener('click', () => this.generateSlides());
        
        // デザイン学習
        document.getElementById('learn-btn').addEventListener('click', () => this.learnDesigns());
        
        // ファイルアップロード
        this.setupFileUpload();
        
        // プレビュー操作
        document.getElementById('prev-slide').addEventListener('click', () => this.navigateSlide(-1));
        document.getElementById('next-slide').addEventListener('click', () => this.navigateSlide(1));
        
        // 修正機能
        document.getElementById('apply-revision').addEventListener('click', () => this.applyRevision());
        
        // ダウンロード
        document.getElementById('download-pptx').addEventListener('click', () => this.downloadPresentation());
    }
    
    switchTab(tabName) {
        // アクティブタブの更新
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        document.getElementById(`${tabName}-tab`).classList.add('active');
    }
    
    async generateSlides() {
        const content = document.getElementById('content-input').value.trim();
        if (!content) {
            alert('コンテンツを入力してください');
            return;
        }
        
        const designPattern = document.getElementById('design-pattern').value;
        const generateBtn = document.getElementById('generate-btn');
        const progressArea = document.getElementById('progress-area');
        
        // UI更新
        generateBtn.disabled = true;
        generateBtn.querySelector('.btn-text').style.display = 'none';
        generateBtn.querySelector('.spinner').style.display = 'inline';
        progressArea.style.display = 'block';
        
        this.updateStatus('生成中...');
        
        try {
            const response = await fetch('/api/generate-slides', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    content: content,
                    design_preference: designPattern
                })
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                this.currentPresentation = result;
                await this.loadPresentationPreview(result.presentation_id);
                this.updateStatus('生成完了');
                this.switchTab('preview');
                
                // ダウンロードボタンを有効化
                document.getElementById('download-pptx').disabled = false;
                document.getElementById('file-info').style.display = 'block';
                document.getElementById('filename').textContent = result.download_url.split('/').pop();
                
            } else {
                throw new Error(result.error || '生成に失敗しました');
            }
            
        } catch (error) {
            console.error('Generation error:', error);
            alert('スライド生成中にエラーが発生しました: ' + error.message);
            this.updateStatus('エラー');
        } finally {
            // UI復元
            generateBtn.disabled = false;
            generateBtn.querySelector('.btn-text').style.display = 'inline';
            generateBtn.querySelector('.spinner').style.display = 'none';
            progressArea.style.display = 'none';
        }
    }
    
    async loadPresentationPreview(presentationId) {
        try {
            const response = await fetch(`/api/presentation/${presentationId}/preview`);
            const previewData = await response.json();
            
            if (previewData.status === 'success') {
                this.slides = previewData.slides;
                this.currentSlideIndex = 0;
                this.renderSlidePreview();
                this.updateSlideNavigation();
            }
            
        } catch (error) {
            console.error('Preview loading error:', error);
        }
    }
    
    renderSlidePreview() {
        const previewContainer = document.getElementById('slide-preview');
        
        if (!this.slides || this.slides.length === 0) {
            previewContainer.innerHTML = '<div class="no-slides">スライドがありません</div>';
            return;
        }
        
        const currentSlide = this.slides[this.currentSlideIndex];
        
        // スライドのHTML生成（簡易版）
        previewContainer.innerHTML = `
            <div class="slide-content">
                <h2 class="slide-title">${currentSlide.title}</h2>
                <div class="slide-body">
                    ${this.renderSlideContent(currentSlide)}
                </div>
                <div class="slide-number">${this.currentSlideIndex + 1}</div>
            </div>
        `;
    }
    
    renderSlideContent(slide) {
        const content = slide.content;
        let html = '';
        
        if (content.main_message) {
            html += `<div class="main-message">${content.main_message}</div>`;
        }
        
        if (content.supporting_points && content.supporting_points.length > 0) {
            html += '<ul class="supporting-points">';
            content.supporting_points.forEach(point => {
                html += `<li>${point}</li>`;
            });
            html += '</ul>';
        }
        
        if (content.timeline && content.timeline.length > 0) {
            html += '<div class="timeline">';
            content.timeline.forEach(phase => {
                html += `
                    <div class="timeline-item">
                        <h4>${phase.phase}</h4>
                        <p>${phase.duration}</p>
                        <ul>
                            ${phase.activities.map(activity => `<li>${activity}</li>`).join('')}
                        </ul>
                    </div>
                `;
            });
            html += '</div>';
        }
        
        return html;
    }
    
    updateSlideNavigation() {
        const prevBtn = document.getElementById('prev-slide');
        const nextBtn = document.getElementById('next-slide');
        const counter = document.getElementById('slide-counter');
        
        if (this.slides && this.slides.length > 0) {
            counter.textContent = `${this.currentSlideIndex + 1} / ${this.slides.length}`;
            prevBtn.disabled = this.currentSlideIndex === 0;
            nextBtn.disabled = this.currentSlideIndex === this.slides.length - 1;
        } else {
            counter.textContent = '0 / 0';
            prevBtn.disabled = true;
            nextBtn.disabled = true;
        }
    }
    
    navigateSlide(direction) {
        if (!this.slides || this.slides.length === 0) return;
        
        const newIndex = this.currentSlideIndex + direction;
        if (newIndex >= 0 && newIndex < this.slides.length) {
            this.currentSlideIndex = newIndex;
            this.renderSlidePreview();
            this.updateSlideNavigation();
        }
    }
    
    async applyRevision() {
        const revisionText = document.getElementById('revision-input').value.trim();
        if (!revisionText) {
            alert('修正指示を入力してください');
            return;
        }
        
        if (!this.currentPresentation) {
            alert('修正対象のプレゼンテーションがありません');
            return;
        }
        
        const applyBtn = document.getElementById('apply-revision');
        applyBtn.disabled = true;
        applyBtn.textContent = '修正中...';
        
        try {
            const response = await fetch('/api/revise', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    presentation_id: this.currentPresentation.presentation_id,
                    revision_instruction: revisionText,
                    target_slide: this.currentSlideIndex + 1
                })
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                // 新しいプレゼンテーションデータで更新
                this.currentPresentation.presentation_id = result.updated_presentation_id;
                await this.loadPresentationPreview(result.updated_presentation_id);
                
                // 修正指示をクリア
                document.getElementById('revision-input').value = '';
                
                alert('修正が完了しました:\n' + result.changes_applied.join('\n'));
                
            } else {
                throw new Error(result.error || '修正に失敗しました');
            }
            
        } catch (error) {
            console.error('Revision error:', error);
            alert('修正中にエラーが発生しました: ' + error.message);
        } finally {
            applyBtn.disabled = false;
            applyBtn.textContent = '修正を適用';
        }
    }
    
    downloadPresentation() {
        if (!this.currentPresentation) {
            alert('ダウンロード対象のプレゼンテーションがありません');
            return;
        }
        
        const downloadUrl = this.currentPresentation.download_url;
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = downloadUrl.split('/').pop();
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
    
    setupFileUpload() {
        const uploadArea = document.getElementById('design-upload');
        const fileInput = document.getElementById('design-files');
        
        // クリックでファイル選択
        uploadArea.addEventListener('click', () => fileInput.click());
        
        // ドラッグ&ドロップ
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, this.preventDefaults, false);
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => uploadArea.classList.add('dragover'), false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => uploadArea.classList.remove('dragover'), false);
        });
        
        uploadArea.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            this.handleFileSelection(files);
        });
        
        fileInput.addEventListener('change', (e) => {
            this.handleFileSelection(e.target.files);
        });
    }
    
    handleFileSelection(files) {
        const fileList = document.getElementById('file-list');
        const filesArray = Array.from(files);
        
        if (filesArray.length > 0) {
            fileList.style.display = 'block';
            fileList.innerHTML = '<h4>選択されたファイル:</h4>';
            
            filesArray.forEach(file => {
                const fileItem = document.createElement('div');
                fileItem.className = 'file-item';
                fileItem.innerHTML = `
                    <span class="file-name">${file.name}</span>
                    <span class="file-size">${(file.size / 1024 / 1024).toFixed(2)} MB</span>
                `;
                fileList.appendChild(fileItem);
            });
        }
    }
    
    async learnDesigns() {
        const fileInput = document.getElementById('design-files');
        const files = fileInput.files;
        
        if (files.length === 0) {
            alert('学習させるファイルを選択してください');
            return;
        }
        
        const category = document.getElementById('category').value;
        const quality = document.getElementById('quality').value;
        
        const formData = new FormData();
        Array.from(files).forEach(file => {
            formData.append('files', file);
        });
        formData.append('category', category);
        formData.append('quality', quality);
        
        const learnBtn = document.getElementById('learn-btn');
        learnBtn.disabled = true;
        learnBtn.textContent = '学習中...';
        
        try {
            const response = await fetch('/api/upload-design', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                alert(`${result.uploaded_files.length}個のファイルの学習が完了しました`);
                this.loadLearnedPatterns();
                
                // ファイル選択をクリア
                fileInput.value = '';
                document.getElementById('file-list').style.display = 'none';
                
            } else {
                throw new Error(result.error || '学習に失敗しました');
            }
            
        } catch (error) {
            console.error('Learning error:', error);
            alert('学習中にエラーが発生しました: ' + error.message);
        } finally {
            learnBtn.disabled = false;
            learnBtn.textContent = 'デザインパターンを学習';
        }
    }
    
    async loadLearnedPatterns() {
        try {
            const response = await fetch('/api/design-patterns');
            const patterns = await response.json();
            
            const patternList = document.getElementById('pattern-list');
            
            if (patterns && patterns.length > 0) {
                patternList.innerHTML = patterns.map(pattern => `
                    <div class="pattern-card">
                        <h4>${pattern.filename}</h4>
                        <p>カテゴリー: ${pattern.category}</p>
                        <p>品質: ${'★'.repeat(pattern.quality_rating)}</p>
                        <p>使用回数: ${pattern.usage_count}</p>
                    </div>
                `).join('');
            } else {
                patternList.innerHTML = '<p>学習済みパターンがありません</p>';
            }
            
        } catch (error) {
            console.error('Pattern loading error:', error);
        }
    }
    
    updateStatus(status) {
        document.getElementById('status').textContent = status;
    }
    
    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
}

// アプリケーション初期化
document.addEventListener('DOMContentLoaded', () => {
    new SlideGeneratorApp();
});
```

## Phase 4: テスト・最適化 (Week 8)

### 統合テスト・最終調整

#### テストスクリプト
**tests/test_integration.py**:
```python
import pytest
import os
import json
from app.main import app
from app.database.db_manager import DatabaseManager

class TestIntegration:
    @pytest.fixture
    def client(self):
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    @pytest.fixture
    def db(self):
        test_db_path = 'test_database.db'
        db_manager = DatabaseManager(test_db_path)
        yield db_manager
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
    
    def test_slide_generation_flow(self, client):
        """スライド生成フローのテスト"""
        
        # 1. ヘルスチェック
        response = client.get('/api/health')
        assert response.status_code == 200
        
        # 2. スライド生成
        response = client.post('/api/generate-slides', 
            json={
                'content': 'テスト用の新規事業提案です。市場規模は100億円です。',
                'design_preference': 'bcg_standard'
            })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'presentation_id' in data
        assert 'download_url' in data
    
    def test_design_learning_flow(self, client):
        """デザイン学習フローのテスト"""
        
        # テスト用PDFファイルのアップロード
        with open('tests/sample.pdf', 'rb') as f:
            response = client.post('/api/upload-design',
                data={
                    'files': (f, 'sample.pdf'),
                    'category': 'strategy',
                    'quality': '4'
                })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert len(data['uploaded_files']) == 1
    
    def test_database_operations(self, db):
        """データベース操作のテスト"""
        
        # デザインアセットの保存
        asset_id = db.save_design_asset(
            'test.pdf', '/path/to/test.pdf', 'pdf', 'strategy', 4
        )
        assert asset_id is not None
        
        # アセット取得
        assets = db.get_design_assets(category='strategy')
        assert len(assets) == 1
        assert assets[0]['filename'] == 'test.pdf'
```

#### パフォーマンス最適化
**app/core/optimizer.py**:
```python
import time
import functools
from collections import lru_cache
import logging

class PerformanceOptimizer:
    def __init__(self):
        self.cache_stats = {
            'hits': 0,
            'misses': 0
        }
    
    @staticmethod
    def timing_decorator(func):
        """実行時間計測デコレーター"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            
            execution_time = end_time - start_time
            logging.info(f"{func.__name__} executed in {execution_time:.2f} seconds")
            
            return result
        return wrapper
    
    @lru_cache(maxsize=100)
    def cached_pattern_analysis(self, file_hash, file_size):
        """デザインパターン分析のキャッシュ"""
        # 実際の分析処理は別途実装
        pass
    
    def optimize_api_usage(self, prompt_text):
        """OpenAI APIの使用量最適化"""
        
        # 1. プロンプトの圧縮
        optimized_prompt = self.compress_prompt(prompt_text)
        
        # 2. キャッシュチェック
        cached_result = self.check_cache(optimized_prompt)
        if cached_result:
            self.cache_stats['hits'] += 1
            return cached_result
        
        self.cache_stats['misses'] += 1
        return None
    
    def compress_prompt(self, prompt):
        """プロンプト圧縮（トークン数削減）"""
        # 不要な空白・改行の削除
        compressed = ' '.join(prompt.split())
        
        # 冗長な表現の置換
        replacements = {
            'について詳細に説明してください': 'を説明せよ',
            'ということができます': 'できる',
            'と考えられます': 'と思われる'
        }
        
        for old, new in replacements.items():
            compressed = compressed.replace(old, new)
        
        return compressed
```

## 運用・保守計画

### デプロイメント手順
```bash
# 1. 本番環境構築
git clone https://github.com/your-repo/bcg-slide-generator.git
cd bcg-slide-generator

# 2. 環境設定
cp config/.env.example config/.env
# OpenAI APIキーを設定

# 3. 依存関係インストール
pip install -r requirements.txt

# 4. データベース初期化
python app/database/init_db.py

# 5. アプリケーション起動
python app/main.py
```

### 継続的改善プロセス
1. **週次**: 使用量・コスト分析
2. **月次**: パフォーマンス最適化
3. **四半期**: 機能追加・改善

この開発手順に従うことで、8週間でMVPから完成版まで段階的に実装できます。各段階で動作確認を行いながら進めることで、リスクを最小化しつつ高品質なシステムを構築できます。