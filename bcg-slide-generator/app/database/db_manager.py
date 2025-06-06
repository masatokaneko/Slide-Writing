import sqlite3
import json
import os
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