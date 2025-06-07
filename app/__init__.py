from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # 環境変数の読み込み
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', '.env'))
    
    # 設定
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
    
    # ルートの登録
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    return app 