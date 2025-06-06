# 詳細実装ガイド・技術仕様

## 5. エラーハンドリング・ログ管理

### 5.1 包括的エラーハンドリングシステム

#### カスタム例外クラス
**app/core/exceptions.py**:
```python
class SlideGeneratorException(Exception):
    """ベース例外クラス"""
    def __init__(self, message, error_code=None, details=None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

class FileProcessingError(SlideGeneratorException):
    """ファイル処理関連エラー"""
    pass

class AIServiceError(SlideGeneratorException):
    """AI API関連エラー"""
    pass

class DesignAnalysisError(SlideGeneratorException):
    """デザイン分析関連エラー"""
    pass

class DatabaseError(SlideGeneratorException):
    """データベース関連エラー"""
    pass

class ValidationError(SlideGeneratorException):
    """入力値検証エラー"""
    pass

# エラーコード定義
ERROR_CODES = {
    'FILE_TOO_LARGE': 'ファイルサイズが上限を超えています',
    'UNSUPPORTED_FORMAT': 'サポートされていないファイル形式です',
    'API_RATE_LIMIT': 'API呼び出し制限に達しました',
    'API_QUOTA_EXCEEDED': 'API使用量上限に達しました',
    'INVALID_CONTENT': '入力内容が不正です',
    'DESIGN_ANALYSIS_FAILED': 'デザイン分析に失敗しました',
    'PPTX_GENERATION_FAILED': 'PowerPoint生成に失敗しました',
    'DATABASE_CONNECTION_FAILED': 'データベース接続に失敗しました'
}
```

#### エラーハンドラー
**app/core/error_handler.py**:
```python
import logging
import traceback
from flask import jsonify
from datetime import datetime
from .exceptions import *

logger = logging.getLogger(__name__)

class ErrorHandler:
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Flaskアプリにエラーハンドラーを登録"""
        app.errorhandler(SlideGeneratorException)(self.handle_custom_exception)
        app.errorhandler(Exception)(self.handle_generic_exception)
        app.errorhandler(404)(self.handle_not_found)
        app.errorhandler(500)(self.handle_internal_error)
    
    def handle_custom_exception(self, error):
        """カスタム例外のハンドリング"""
        logger.error(f"Custom Exception: {error.message}", extra={
            'error_code': error.error_code,
            'details': error.details,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'status': 'error',
            'error_code': error.error_code,
            'error_message': error.message,
            'user_message': ERROR_CODES.get(error.error_code, error.message),
            'details': error.details,
            'timestamp': datetime.now().isoformat()
        }), self._get_status_code(error)
    
    def handle_generic_exception(self, error):
        """一般的な例外のハンドリング"""
        logger.error(f"Unhandled Exception: {str(error)}", extra={
            'traceback': traceback.format_exc(),
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'status': 'error',
            'error_code': 'INTERNAL_ERROR',
            'error_message': 'システム内部エラーが発生しました',
            'user_message': '一時的なエラーが発生しました。しばらく待ってから再試行してください。',
            'timestamp': datetime.now().isoformat()
        }), 500
    
    def handle_not_found(self, error):
        """404エラーのハンドリング"""
        return jsonify({
            'status': 'error',
            'error_code': 'NOT_FOUND',
            'error_message': 'リソースが見つかりません',
            'user_message': '指定されたページまたはリソースが見つかりません'
        }), 404
    
    def handle_internal_error(self, error):
        """500エラーのハンドリング"""
        logger.error(f"Internal Server Error: {str(error)}")
        return jsonify({
            'status': 'error',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'error_message': 'サーバー内部エラー',
            'user_message': 'サーバーで問題が発生しました。管理者に連絡してください。'
        }), 500
    
    def _get_status_code(self, error):
        """例外タイプに基づくHTTPステータスコード決定"""
        if isinstance(error, ValidationError):
            return 400
        elif isinstance(error, FileProcessingError):
            return 422
        elif isinstance(error, AIServiceError):
            return 503
        else:
            return 500

# リトライデコレーター
def retry_on_failure(max_retries=3, delay=1):
    """失敗時のリトライデコレーター"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (AIServiceError, requests.RequestException) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {str(e)}")
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
                    else:
                        logger.error(f"Max retries exceeded for {func.__name__}")
            
            raise last_exception
        return wrapper
    return decorator
```

### 5.2 構造化ログシステム

#### ログ設定
**app/core/logging_config.py**:
```python
import logging
import logging.handlers
import json
import os
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """JSON形式のログフォーマッター"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # 追加属性の処理
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'execution_time'):
            log_entry['execution_time'] = record.execution_time
        if hasattr(record, 'api_cost'):
            log_entry['api_cost'] = record.api_cost
        
        # 例外情報の処理
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)

def setup_logging(app_name='bcg_slide_generator', log_level='INFO'):
    """ログシステムの初期化"""
    
    # ログディレクトリの作成
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # ルートロガーの設定
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # ハンドラーのクリア
    root_logger.handlers.clear()
    
    # ファイルハンドラー（ローテーション）
    file_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, f'{app_name}.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(file_handler)
    
    # エラー専用ファイルハンドラー
    error_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, f'{app_name}_error.log'),
        maxBytes=10*1024*1024,
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(error_handler)
    
    # コンソールハンドラー（開発環境用）
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    root_logger.addHandler(console_handler)
    
    return root_logger

# パフォーマンス計測デコレーター
def log_performance(logger_name=None):
    """パフォーマンス計測・ログ出力デコレーター"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(logger_name or func.__module__)
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logger.info(f"Function executed successfully: {func.__name__}", extra={
                    'execution_time': execution_time,
                    'function': func.__name__,
                    'args_count': len(args),
                    'kwargs_count': len(kwargs)
                })
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Function failed: {func.__name__}", extra={
                    'execution_time': execution_time,
                    'function': func.__name__,
                    'error': str(e),
                    'error_type': type(e).__name__
                })
                raise
        
        return wrapper
    return decorator

# API コスト追跡
class APIUsageTracker:
    def __init__(self):
        self.logger = logging.getLogger('api_usage')
        self.session_costs = {}
    
    def track_openai_usage(self, prompt_tokens, completion_tokens, model='gpt-4o'):
        """OpenAI使用量の追跡"""
        costs = {
            'gpt-4o': {'input': 0.005, 'output': 0.015},  # $per 1K tokens
            'gpt-4o-mini': {'input': 0.00015, 'output': 0.0006}
        }
        
        model_cost = costs.get(model, costs['gpt-4o'])
        
        input_cost = (prompt_tokens / 1000) * model_cost['input']
        output_cost = (completion_tokens / 1000) * model_cost['output']
        total_cost = input_cost + output_cost
        
        # 円換算（1ドル=150円として計算）
        cost_jpy = total_cost * 150
        
        self.logger.info("OpenAI API usage", extra={
            'model': model,
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': prompt_tokens + completion_tokens,
            'cost_usd': total_cost,
            'cost_jpy': cost_jpy,
            'timestamp': datetime.now().isoformat()
        })
        
        return cost_jpy
```

## 6. セキュリティ・設定管理

### 6.1 セキュアな設定管理

#### 設定管理システム
**app/core/config_manager.py**:
```python
import os
import json
import base64
from cryptography.fernet import Fernet
from typing import Dict, Any

class SecureConfigManager:
    def __init__(self, config_path='config'):
        self.config_path = config_path
        self.encryption_key = self._get_or_create_key()
        self.cipher = Fernet(self.encryption_key)
        
        # 設定ファイルの読み込み
        self.config = self._load_config()
    
    def _get_or_create_key(self):
        """暗号化キーの取得または生成"""
        key_file = os.path.join(self.config_path, '.key')
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            os.makedirs(self.config_path, exist_ok=True)
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    def _load_config(self):
        """設定ファイルの読み込み"""
        config_file = os.path.join(self.config_path, 'settings.json')
        
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return self._create_default_config()
    
    def _create_default_config(self):
        """デフォルト設定の作成"""
        default_config = {
            'app': {
                'name': 'BCG Slide Generator',
                'version': '1.0.0',
                'host': 'localhost',
                'port': 5000,
                'debug': False
            },
            'ai': {
                'model': 'gpt-4o',
                'max_tokens': 4000,
                'temperature': 0.2,
                'timeout': 30
            },
            'file_processing': {
                'allowed_extensions': ['pdf', 'png', 'jpg', 'jpeg', 'pptx'],
                'max_file_size_mb': 50,
                'analysis_timeout': 300,
                'upload_folder': 'data/design_assets',
                'output_folder': 'data/generated_slides'
            },
            'database': {
                'path': 'data/database.db',
                'backup_frequency': 'daily',
                'cleanup_old_records_days': 90
            },
            'security': {
                'rate_limit_per_minute': 10,
                'max_concurrent_requests': 5,
                'session_timeout_hours': 24
            },
            'monitoring': {
                'log_level': 'INFO',
                'api_cost_alert_threshold_jpy': 3000,
                'performance_alert_threshold_seconds': 30
            }
        }
        
        self.save_config(default_config)
        return default_config
    
    def get(self, key_path: str, default=None):
        """設定値の取得（ドット記法対応）"""
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value):
        """設定値の更新"""
        keys = key_path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
        self.save_config(self.config)
    
    def get_secret(self, key: str):
        """暗号化された秘密情報の取得"""
        encrypted_value = os.getenv(f'ENCRYPTED_{key.upper()}')
        if encrypted_value:
            try:
                return self.cipher.decrypt(encrypted_value.encode()).decode()
            except Exception:
                return None
        return None
    
    def set_secret(self, key: str, value: str):
        """秘密情報の暗号化保存"""
        encrypted_value = self.cipher.encrypt(value.encode()).decode()
        # 環境変数として保存（実際の運用では.envファイルなどに保存）
        os.environ[f'ENCRYPTED_{key.upper()}'] = encrypted_value
    
    def save_config(self, config):
        """設定ファイルの保存"""
        config_file = os.path.join(self.config_path, 'settings.json')
        os.makedirs(self.config_path, exist_ok=True)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        self.config = config
    
    def validate_config(self):
        """設定値の妥当性チェック"""
        errors = []
        
        # 必須設定のチェック
        required_keys = [
            'app.name',
            'ai.model',
            'file_processing.max_file_size_mb',
            'database.path'
        ]
        
        for key in required_keys:
            if self.get(key) is None:
                errors.append(f"Required configuration missing: {key}")
        
        # 数値範囲のチェック
        if self.get('file_processing.max_file_size_mb', 0) > 100:
            errors.append("file_processing.max_file_size_mb must be <= 100")
        
        if self.get('ai.temperature', 0) > 1:
            errors.append("ai.temperature must be <= 1.0")
        
        # OpenAI APIキーのチェック
        api_key = os.getenv('OPENAI_API_KEY') or self.get_secret('openai_api_key')
        if not api_key:
            errors.append("OpenAI API key not configured")
        
        return errors

# グローバル設定インスタンス
config_manager = SecureConfigManager()
```

### 6.2 入力値検証システム

#### バリデーター
**app/core/validators.py**:
```python
import re
import mimetypes
from typing import List, Dict, Any
from .exceptions import ValidationError

class InputValidator:
    
    # ファイル関連の制限
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = ['pdf', 'png', 'jpg', 'jpeg', 'pptx']
    ALLOWED_MIME_TYPES = [
        'application/pdf',
        'image/png',
        'image/jpeg',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    ]
    
    # テキスト関連の制限
    MIN_CONTENT_LENGTH = 10
    MAX_CONTENT_LENGTH = 10000
    
    @classmethod
    def validate_slide_content(cls, content: str) -> str:
        """スライドコンテンツの検証"""
        if not content or not content.strip():
            raise ValidationError("コンテンツが空です", "EMPTY_CONTENT")
        
        content = content.strip()
        
        if len(content) < cls.MIN_CONTENT_LENGTH:
            raise ValidationError(
                f"コンテンツが短すぎます（最小{cls.MIN_CONTENT_LENGTH}文字）",
                "CONTENT_TOO_SHORT"
            )
        
        if len(content) > cls.MAX_CONTENT_LENGTH:
            raise ValidationError(
                f"コンテンツが長すぎます（最大{cls.MAX_CONTENT_LENGTH}文字）",
                "CONTENT_TOO_LONG"
            )
        
        # 悪意のあるスクリプトの検出
        if cls._contains_script_tags(content):
            raise ValidationError(
                "不正なスクリプトが検出されました",
                "MALICIOUS_CONTENT"
            )
        
        return content
    
    @classmethod
    def validate_file_upload(cls, file) -> Dict[str, Any]:
        """アップロードファイルの検証"""
        if not file or not file.filename:
            raise ValidationError("ファイルが選択されていません", "NO_FILE_SELECTED")
        
        filename = file.filename
        file_extension = filename.split('.')[-1].lower()
        
        # 拡張子チェック
        if file_extension not in cls.ALLOWED_EXTENSIONS:
            raise ValidationError(
                f"サポートされていないファイル形式: {file_extension}",
                "UNSUPPORTED_FORMAT",
                {"allowed_extensions": cls.ALLOWED_EXTENSIONS}
            )
        
        # ファイルサイズチェック（ここではContent-Lengthヘッダーをチェック）
        # 実際のサイズはアップロード後に再チェック
        
        # MIMEタイプチェック
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type not in cls.ALLOWED_MIME_TYPES:
            raise ValidationError(
                f"無効なファイル形式: {mime_type}",
                "INVALID_MIME_TYPE"
            )
        
        return {
            'filename': cls._sanitize_filename(filename),
            'extension': file_extension,
            'mime_type': mime_type
        }
    
    @classmethod
    def validate_uploaded_file_content(cls, file_path: str, expected_extension: str):
        """アップロード後のファイル内容検証"""
        import os
        
        # ファイルサイズの再チェック
        file_size = os.path.getsize(file_path)
        if file_size > cls.MAX_FILE_SIZE:
            raise ValidationError(
                f"ファイルサイズが上限を超えています: {file_size / 1024 / 1024:.2f}MB",
                "FILE_TOO_LARGE",
                {"max_size_mb": cls.MAX_FILE_SIZE / 1024 / 1024}
            )
        
        # ファイルの実際の形式チェック（マジックナンバー）
        if not cls._verify_file_format(file_path, expected_extension):
            raise ValidationError(
                "ファイルの実際の形式が拡張子と一致しません",
                "FORMAT_MISMATCH"
            )
    
    @classmethod
    def validate_revision_instruction(cls, instruction: str) -> str:
        """修正指示の検証"""
        if not instruction or not instruction.strip():
            raise ValidationError("修正指示が空です", "EMPTY_INSTRUCTION")
        
        instruction = instruction.strip()
        
        if len(instruction) < 5:
            raise ValidationError("修正指示が短すぎます", "INSTRUCTION_TOO_SHORT")
        
        if len(instruction) > 1000:
            raise ValidationError("修正指示が長すぎます", "INSTRUCTION_TOO_LONG")
        
        return instruction
    
    @classmethod
    def validate_design_preference(cls, preference: str) -> str:
        """デザイン設定の検証"""
        valid_preferences = ['auto', 'bcg_standard', 'financial', 'creative', 'custom']
        
        if preference not in valid_preferences:
            raise ValidationError(
                f"無効なデザイン設定: {preference}",
                "INVALID_DESIGN_PREFERENCE",
                {"valid_options": valid_preferences}
            )
        
        return preference
    
    @classmethod
    def validate_category(cls, category: str) -> str:
        """カテゴリーの検証"""
        valid_categories = ['strategy', 'financial', 'marketing', 'operation', 'general']
        
        if category not in valid_categories:
            raise ValidationError(
                f"無効なカテゴリー: {category}",
                "INVALID_CATEGORY",
                {"valid_options": valid_categories}
            )
        
        return category
    
    @classmethod
    def validate_quality_rating(cls, rating) -> int:
        """品質評価の検証"""
        try:
            rating = int(rating)
        except (ValueError, TypeError):
            raise ValidationError("品質評価は数値で入力してください", "INVALID_RATING_TYPE")
        
        if rating < 1 or rating > 5:
            raise ValidationError("品質評価は1-5の範囲で入力してください", "RATING_OUT_OF_RANGE")
        
        return rating
    
    @classmethod
    def _sanitize_filename(cls, filename: str) -> str:
        """ファイル名のサニタイズ"""
        # 危険な文字の除去
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # 長すぎるファイル名の短縮
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255-len(ext)] + ext
        
        return filename
    
    @classmethod
    def _contains_script_tags(cls, content: str) -> bool:
        """スクリプトタグの検出"""
        script_patterns = [
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'eval\s*\(',
            r'Function\s*\('
        ]
        
        for pattern in script_patterns:
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                return True
        
        return False
    
    @classmethod
    def _verify_file_format(cls, file_path: str, expected_extension: str) -> bool:
        """ファイル形式の実際の検証（マジックナンバー）"""
        magic_numbers = {
            'pdf': b'%PDF',
            'png': b'\x89PNG\r\n\x1a\n',
            'jpg': b'\xff\xd8\xff',
            'jpeg': b'\xff\xd8\xff',
            'pptx': b'PK'  # ZIP形式の開始
        }
        
        magic = magic_numbers.get(expected_extension)
        if not magic:
            return True  # 不明な形式は通す
        
        try:
            with open(file_path, 'rb') as f:
                file_start = f.read(len(magic))
                return file_start.startswith(magic)
        except Exception:
            return False

# リクエスト検証デコレーター
def validate_request(validators: Dict[str, str]):
    """リクエスト検証デコレーター"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request
            
            # JSONリクエストの検証
            if request.is_json:
                data = request.get_json()
                for field, validator_name in validators.items():
                    if field in data:
                        validator = getattr(InputValidator, f'validate_{validator_name}')
                        data[field] = validator(data[field])
            
            # フォームデータの検証
            elif request.form:
                for field, validator_name in validators.items():
                    if field in request.form:
                        validator = getattr(InputValidator, f'validate_{validator_name}')
                        request.form[field] = validator(request.form[field])
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

## 7. パフォーマンス最適化・キャッシュシステム

### 7.1 インテリジェントキャッシュシステム

#### キャッシュマネージャー
**app/core/cache_manager.py**:
```python
import hashlib
import pickle
import os
import time
import json
from typing import Any, Optional, Callable
from datetime import datetime, timedelta

class CacheManager:
    def __init__(self, cache_dir='data/cache', default_ttl=3600):
        self.cache_dir = cache_dir
        self.default_ttl = default_ttl
        os.makedirs(cache_dir, exist_ok=True)
        
        # メモリキャッシュ（小さなデータ用）
        self.memory_cache = {}
        self.memory_cache_timestamps = {}
        
        # キャッシュ統計
        self.stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0
        }
    
    def get_cache_key(self, *args, **kwargs) -> str:
        """キャッシュキーの生成"""
        # 引数をシリアライズしてハッシュ化
        key_data = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str, default=None) -> Any:
        """キャッシュからデータを取得"""
        
        # メモリキャッシュをチェック
        if key in self.memory_cache:
            timestamp = self.memory_cache_timestamps.get(key, 0)
            if time.time() - timestamp < self.default_ttl:
                self.stats['hits'] += 1
                return self.memory_cache[key]
            else:
                # 期限切れのため削除
                del self.memory_cache[key]
                del self.memory_cache_timestamps[key]
        
        # ファイルキャッシュをチェック
        cache_file = os.path.join(self.cache_dir, f"{key}.cache")
        meta_file = os.path.join(self.cache_dir, f"{key}.meta")
        
        if os.path.exists(cache_file) and os.path.exists(meta_file):
            try:
                # メタデータをチェック
                with open(meta_file, 'r') as f:
                    meta = json.load(f)
                
                if datetime.fromisoformat(meta['expires_at']) > datetime.now():
                    # キャッシュが有効
                    with open(cache_file, 'rb') as f:
                        data = pickle.load(f)
                    
                    # メモリキャッシュにも保存
                    self.memory_cache[key] = data
                    self.memory_cache_timestamps[key] = time.time()
                    
                    self.stats['hits'] += 1
                    return data
                else:
                    # 期限切れのため削除
                    os.remove(cache_file)
                    os.remove(meta_file)
            
            except Exception as e:
                # ファイル破損などの場合は削除
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                if os.path.exists(meta_file):
                    os.remove(meta_file)
        
        self.stats['misses'] += 1
        return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """キャッシュにデータを保存"""
        ttl = ttl or self.default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        # メモリキャッシュに保存
        self.memory_cache[key] = value
        self.memory_cache_timestamps[key] = time.time()
        
        # ファイルキャッシュに保存
        cache_file = os.path.join(self.cache_dir, f"{key}.cache")
        meta_file = os.path.join(self.cache_dir, f"{key}.meta")
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(value, f)
            
            with open(meta_file, 'w') as f:
                json.dump({
                    'created_at': datetime.now().isoformat(),
                    'expires_at': expires_at.isoformat(),
                    'ttl': ttl
                }, f)
        
        except Exception as e:
            # ファイル保存に失敗した場合はメモリキャッシュのみ
            pass
    
    def delete(self, key: str) -> None:
        """キャッシュからデータを削除"""
        
        # メモリキャッシュから削除
        if key in self.memory_cache:
            del self.memory_cache[key]
            del self.memory_cache_timestamps[key]
        
        # ファイルキャッシュから削除
        cache_file = os.path.join(self.cache_dir, f"{key}.cache")
        meta_file = os.path.join(self.cache_dir, f"{key}.meta")
        
        for file_path in [cache_file, meta_file]:
            if os.path.exists(file_path):
                os.remove(file_path)
        
        self.stats['invalidations'] += 1
    
    def clear_expired(self) -> int:
        """期限切れキャッシュの削除"""
        cleared_count = 0
        
        # メモリキャッシュのクリーンアップ
        current_time = time.time()
        expired_keys = []
        
        for key, timestamp in self.memory_cache_timestamps.items():
            if current_time - timestamp >= self.default_ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.memory_cache[key]
            del self.memory_cache_timestamps[key]
            cleared_count += 1
        
        # ファイルキャッシュのクリーンアップ
        if os.path.exists(self.cache_dir):
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.meta'):
                    meta_file = os.path.join(self.cache_dir, filename)
                    cache_file = os.path.join(self.cache_dir, filename.replace('.meta', '.cache'))
                    
                    try:
                        with open(meta_file, 'r') as f:
                            meta = json.load(f)
                        
                        if datetime.fromisoformat(meta['expires_at']) <= datetime.now():
                            os.remove(meta_file)
                            if os.path.exists(cache_file):
                                os.remove(cache_file)
                            cleared_count += 1
                    
                    except Exception:
                        # メタファイルが破損している場合は削除
                        os.remove(meta_file)
                        if os.path.exists(cache_file):
                            os.remove(cache_file)
                        cleared_count += 1
        
        return cleared_count
    
    def get_stats(self) -> dict:
        """キャッシュ統計の取得"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'hit_rate_percent': round(hit_rate, 2),
            'invalidations': self.stats['invalidations'],
            'memory_cache_size': len(self.memory_cache)
        }

# グローバルキャッシュインスタンス
cache_manager = CacheManager()

# キャッシュデコレーター
def cached(ttl: int = 3600, key_prefix: str = ''):
    """関数結果をキャッシュするデコレーター"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # キャッシュキーの生成
            cache_key = f"{key_prefix}:{func.__name__}:" + cache_manager.get_cache_key(*args, **kwargs)
            
            # キャッシュから取得を試行
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # キャッシュミスの場合は実行
            result = func(*args, **kwargs)
            
            # 結果をキャッシュに保存
            cache_manager.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator

# OpenAI APIレスポンス専用キャッシュ
class OpenAIResponseCache:
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.prefix = 'openai_response'
    
    @cached(ttl=86400, key_prefix='openai_response')  # 24時間キャッシュ
    def get_cached_response(self, prompt: str, model: str, temperature: float):
        """OpenAIレスポンスのキャッシュ取得（実際のAPI呼び出しは外部で実行）"""
        # このメソッド自体はキャッシュチェックのみ
        # 実際のAPI呼び出しは呼び出し側で行う
        return None
    
    def cache_response(self, prompt: str, model: str, temperature: float, response: dict):
        """OpenAIレスポンスをキャッシュに保存"""
        cache_key = f"{self.prefix}:get_cached_response:" + self.cache_manager.get_cache_key(prompt, model, temperature)
        self.cache_manager.set(cache_key, response, ttl=86400)

# PDF分析結果専用キャッシュ
@cached(ttl=604800, key_prefix='pdf_analysis')  # 1週間キャッシュ
def get_cached_pdf_analysis(file_hash: str, file_size: int):
    """PDF分析結果のキャッシュ取得"""
    return None

def cache_pdf_analysis(file_hash: str, file_size: int, analysis_result: dict):
    """PDF分析結果をキャッシュに保存"""
    cache_key = f"pdf_analysis:get_cached_pdf_analysis:" + cache_manager.get_cache_key(file_hash, file_size)
    cache_manager.set(cache_key, analysis_result, ttl=604800)
```

### 7.2 非同期処理システム

#### バックグラウンドタスク処理
**app/core/background_tasks.py**:
```python
import threading
import queue
import time
import logging
from datetime import datetime
from typing import Callable, Any, Dict
from dataclasses import dataclass
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Task:
    id: str
    name: str
    func: Callable
    args: tuple
    kwargs: dict
    priority: int = 1
    created_at: datetime = None
    started_at: datetime = None
    completed_at: datetime = None
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str = None
    progress: float = 0.0

class BackgroundTaskManager:
    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers
        self.task_queue = queue.PriorityQueue()
        self.tasks: Dict[str, Task] = {}
        self.workers = []
        self.running = False
        self.logger = logging.getLogger(__name__)
        
        # ワーカースレッドを開始
        self.start_workers()
    
    def start_workers(self):
        """ワーカースレッドを開始"""
        self.running = True
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker, name=f"TaskWorker-{i}")
            worker.daemon = True
            worker.start()
            self.workers.append(worker)
        
        self.logger.info(f"Started {self.max_workers} background workers")
    
    def _worker(self):
        """ワーカースレッドのメイン処理"""
        while self.running:
            try:
                # タスクを取得（優先度順）
                priority, task_id = self.task_queue.get(timeout=1)
                task = self.tasks.get(task_id)
                
                if task and task.status == TaskStatus.PENDING:
                    self._execute_task(task)
                
                self.task_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Worker error: {e}")
    
    def _execute_task(self, task: Task):
        """タスクの実行"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        self.logger.info(f"Executing task: {task.name} (ID: {task.id})")
        
        try:
            # プログレスコールバックを含めてタスク実行
            if 'progress_callback' in task.kwargs:
                # 既存のコールバック関数をラップ
                original_callback = task.kwargs.get('progress_callback', lambda x: None)
                task.kwargs['progress_callback'] = lambda progress: self._update_progress(task.id, progress, original_callback)
            
            result = task.func(*task.args, **task.kwargs)
            
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.progress = 100.0
            task.completed_at = datetime.now()
            
            self.logger.info(f"Task completed: {task.name} (ID: {task.id})")
            
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            
            self.logger.error(f"Task failed: {task.name} (ID: {task.id}) - {e}")
    
    def _update_progress(self, task_id: str, progress: float, original_callback: Callable):
        """タスクのプログレス更新"""
        if task_id in self.tasks:
            self.tasks[task_id].progress = progress
        
        # 元のコールバックも実行
        if original_callback:
            original_callback(progress)
    
    def submit_task(self, name: str, func: Callable, args: tuple = (), kwargs: dict = {}, priority: int = 1) -> str:
        """タスクをキューに追加"""
        import uuid
        
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            created_at=datetime.now()
        )
        
        self.tasks[task_id] = task
        self.task_queue.put((priority, task_id))
        
        self.logger.info(f"Task submitted: {name} (ID: {task_id})")
        return task_id
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """タスクの状態取得"""
        task = self.tasks.get(task_id)
        if not task:
            return {"error": "Task not found"}
        
        return {
            "id": task.id,
            "name": task.name,
            "status": task.status.value,
            "progress": task.progress,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "result": task.result if task.status == TaskStatus.COMPLETED else None,
            "error": task.error if task.status == TaskStatus.FAILED else None
        }
    
    def cancel_task(self, task_id: str) -> bool:
        """タスクのキャンセル"""
        task = self.tasks.get(task_id)
        if task and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            return True
        return False
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """キューの統計情報"""
        status_counts = {}
        for task in self.tasks.values():
            status = task.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "queue_size": self.task_queue.qsize(),
            "total_tasks": len(self.tasks),
            "status_counts": status_counts,
            "workers": len(self.workers)
        }
    
    def cleanup_old_tasks(self, hours: int = 24):
        """古いタスクのクリーンアップ"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        old_task_ids = [
            task_id for task_id, task in self.tasks.items()
            if task.completed_at and task.completed_at < cutoff_time
        ]
        
        for task_id in old_task_ids:
            del self.tasks[task_id]
        
        self.logger.info(f"Cleaned up {len(old_task_ids)} old tasks")
        return len(old_task_ids)
    
    def shutdown(self):
        """ワーカーのシャットダウン"""
        self.running = False
        for worker in self.workers:
            worker.join(timeout=5)
        
        self.logger.info("Background task manager shut down")

# グローバルタスクマネージャー
task_manager = BackgroundTaskManager()

# タスク実行デコレーター
def background_task(name: str = None, priority: int = 1):
    """関数をバックグラウンドタスクとして実行するデコレーター"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            task_name = name or f"{func.__module__}.{func.__name__}"
            return task_manager.submit_task(task_name, func, args, kwargs, priority)
        return wrapper
    return decorator

# 長時間実行タスクの例
@background_task(name="slide_generation", priority=1)
def generate_slides_async(content: str, design_preference: str, progress_callback=None):
    """非同期スライド生成"""
    from app.core.content_generator import ContentGenerator
    from app.core.pptx_generator import PPTXGenerator
    
    if progress_callback:
        progress_callback(10)  # 10% - 開始
    
    # コンテンツ生成
    content_generator = ContentGenerator()
    structure = content_generator.generate_structure(content)
    
    if progress_callback:
        progress_callback(50)  # 50% - 構造生成完了
    
    # PowerPoint生成
    pptx_generator = PPTXGenerator()
    output_path = pptx_generator.create_presentation(structure)
    
    if progress_callback:
        progress_callback(90)  # 90% - ファイル生成完了
    
    # データベース保存等の後処理
    time.sleep(0.5)  # 後処理のシミュレーション
    
    if progress_callback:
        progress_callback(100)  # 100% - 完了
    
    return {
        "output_path": output_path,
        "slide_count": len(structure.get('slides', [])),
        "title": structure.get('title', 'Untitled')
    }

@background_task(name="pdf_analysis", priority=2)
def analyze_pdf_async(file_path: str, category: str, progress_callback=None):
    """非同期PDF分析"""
    from app.core.design_analyzer import DesignAnalyzer
    
    if progress_callback:
        progress_callback(5)
    
    analyzer = DesignAnalyzer()
    
    if progress_callback:
        progress_callback(20)
    
    # 分析実行
    analysis_result = analyzer.analyze_file(file_path)
    
    if progress_callback:
        progress_callback(80)
    
    # データベース保存
    time.sleep(0.3)  # 保存処理のシミュレーション
    
    if progress_callback:
        progress_callback(100)
    
    return analysis_result
```

このような詳細な実装ガイドにより、開発者は実際のコーディング段階で発生する課題に対処でき、本格的なプロダクションレベルのシステムを構築できます。

続いて、運用・保守の詳細手順やユーザーマニュアルなど、さらに必要な部分があれば提供いたします。