from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
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
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'settings.json')
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

app.config.update(config['app'])
app.config['MAX_CONTENT_LENGTH'] = config['file_processing']['max_file_size_mb'] * 1024 * 1024

# アップロードディレクトリの作成
data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
os.makedirs(os.path.join(data_dir, 'design_assets'), exist_ok=True)
os.makedirs(os.path.join(data_dir, 'generated_slides'), exist_ok=True)

# コンポーネント初期化
db_path = os.path.join(data_dir, 'database.db')
db_manager = DatabaseManager(db_path)
design_analyzer = DesignAnalyzer()
content_generator = ContentGenerator()
pptx_generator = PPTXGenerator()

@app.route('/')
def index():
    """メインページ"""
    return render_template('index2.html')

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
        quality_str = request.form.get('quality', 'medium')
        
        # 品質の文字列を整数に変換
        quality_map = {
            'high': 3,
            'medium': 2,
            'low': 1
        }
        quality = quality_map.get(quality_str, 2)  # デフォルトは中品質
        
        results = []
        for file in files:
            if file.filename == '':
                continue
            
            # ファイル保存
            filename = secure_filename(file.filename)
            file_path = os.path.join(data_dir, 'design_assets', filename)
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
    create_database(db_path)
    
    # アプリケーション起動
    app.run(
        host=config['app']['host'],
        port=config['app']['port'],
        debug=config['app'].get('debug', False)
    )
