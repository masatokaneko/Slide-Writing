import os
import sys
import unittest
import logging
import psutil
import time
from pathlib import Path
from datetime import datetime
from app.slide_generator import SlideGenerator
from app.pptx_creator import PPTXCreator

# ログ設定
log_filename = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class TestBCGSlideGenerator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """テストクラスの初期設定"""
        cls.base_path = Path(__file__).parent
        cls.output_path = cls.base_path / "output"
        cls.output_path.mkdir(exist_ok=True)
        
        # テスト用の設定
        cls.test_prompt = "BCGの戦略フレームワークについて説明するスライドを作成してください。"
        cls.test_filename = "テスト_スライド.pptx"

    def setUp(self):
        """各テストケースの前の準備"""
        self.start_time = time.time()
        self.start_memory = psutil.Process().memory_info().rss

    def tearDown(self):
        """各テストケースの後のクリーンアップ"""
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss
        
        logger.info(f"テスト実行時間: {end_time - self.start_time:.2f}秒")
        logger.info(f"メモリ使用量: {(end_memory - self.start_memory) / 1024 / 1024:.2f}MB")

    def test_environment(self):
        """環境テスト"""
        # Pythonバージョン確認
        self.assertGreaterEqual(sys.version_info, (3, 8))
        
        # 必要なパッケージのインポート確認
        try:
            import openai
            import flask
            import python_pptx
        except ImportError as e:
            self.fail(f"必要なパッケージのインポートに失敗: {e}")
        
        # OpenAI APIキーの確認
        self.assertIsNotNone(os.getenv('OPENAI_API_KEY'), "OpenAI APIキーが設定されていません")

    def test_windows_paths(self):
        """Windowsパス処理のテスト"""
        # 日本語パス名のテスト
        japanese_path = self.output_path / "日本語_テスト.pptx"
        try:
            japanese_path.touch()
            self.assertTrue(japanese_path.exists())
            japanese_path.unlink()
        except Exception as e:
            self.fail(f"日本語パス名の処理に失敗: {e}")

    def test_slide_generation(self):
        """スライド生成テスト"""
        generator = SlideGenerator()
        try:
            structure = generator.generate_structure(self.test_prompt)
            self.assertIsNotNone(structure)
            self.assertIn('slides', structure)
        except Exception as e:
            self.fail(f"スライド生成に失敗: {e}")

    def test_pptx_creation(self):
        """PowerPoint生成テスト"""
        creator = PPTXCreator()
        output_file = self.output_path / self.test_filename
        
        try:
            # テスト用のスライド構造
            test_structure = {
                'slides': [
                    {'title': 'テストスライド', 'content': 'テストコンテンツ'}
                ]
            }
            
            creator.create_presentation(test_structure, str(output_file))
            self.assertTrue(output_file.exists())
            
            # ファイルサイズの確認
            self.assertGreater(output_file.stat().st_size, 0)
            
        except Exception as e:
            self.fail(f"PowerPoint生成に失敗: {e}")
        finally:
            if output_file.exists():
                output_file.unlink()

    def test_error_handling(self):
        """エラーハンドリングテスト"""
        generator = SlideGenerator()
        
        # 無効なプロンプト
        with self.assertRaises(Exception):
            generator.generate_structure("")
        
        # 無効なファイルパス
        creator = PPTXCreator()
        with self.assertRaises(Exception):
            creator.create_presentation({}, "invalid/path/file.pptx")

    def test_performance(self):
        """パフォーマンステスト"""
        generator = SlideGenerator()
        creator = PPTXCreator()
        
        # 生成時間の測定
        start_time = time.time()
        structure = generator.generate_structure(self.test_prompt)
        generation_time = time.time() - start_time
        
        self.assertLess(generation_time, 30, "スライド生成に30秒以上かかりました")
        
        # メモリ使用量の確認
        memory_usage = psutil.Process().memory_info().rss / 1024 / 1024
        self.assertLess(memory_usage, 500, "メモリ使用量が500MBを超えています")

if __name__ == '__main__':
    unittest.main() 