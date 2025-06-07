import os
import uuid
from pathlib import Path
from flask import Blueprint, render_template, request, jsonify, send_from_directory, current_app
from flask_cors import CORS
from dotenv import load_dotenv
from app.slide_generator import generate_slide_structure
from app.pptx_creator import create_presentation

# パス設定
BASE_DIR = Path(__file__).parent.parent.resolve()
DATA_DIR = BASE_DIR / "data" / "generated"
DATA_DIR.mkdir(parents=True, exist_ok=True)

main = Blueprint('main', __name__)
CORS(main)

# 環境変数の読み込み
load_dotenv(os.path.join(BASE_DIR, 'config', '.env'))

@main.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@main.route('/api/generate', methods=['POST'])
def generate_slide():
    try:
        data = request.get_json()
        content = data.get('content', '').strip()
        if not content:
            return jsonify({"status": "error", "message": "コンテンツが空です。"}), 400

        # スライド構造生成
        slide_structure = generate_slide_structure(content)
        print(slide_structure)
        # ファイル名生成（UUIDで一意化）
        filename = f"presentation_{uuid.uuid4().hex}.pptx"
        output_path = DATA_DIR / filename

        # PowerPointファイル生成
        create_presentation(slide_structure, str(output_path))

        download_url = f"/api/download/{filename}"
        return jsonify({
            "status": "success",
            "filename": filename,
            "download_url": download_url
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@main.route('/api/download/<path:filename>', methods=['GET'])
def download_file(filename):
    try:
        # 日本語ファイル名対応
        file_path = DATA_DIR / filename
        if not file_path.exists():
            return jsonify({"status": "error", "message": "ファイルが存在しません。"}), 404
        return send_from_directory(
            directory=str(DATA_DIR),
            path=filename,
            as_attachment=True,
            download_name=filename.encode('utf-8').decode('utf-8')
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# 追加: アプリケーションの起動部分
if __name__ == '__main__':
    from flask import Flask
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.register_blueprint(main)
    app.run(debug=True, host='0.0.0.0', port=5000) 