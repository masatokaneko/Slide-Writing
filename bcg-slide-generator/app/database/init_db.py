import sqlite3
import os
from datetime import datetime

def create_database(db_path):
    """データベースの初期化"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript('''
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
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            description TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_design_assets_category ON design_assets(category);
        CREATE INDEX IF NOT EXISTS idx_design_patterns_type ON design_patterns(pattern_type);
        CREATE INDEX IF NOT EXISTS idx_presentations_date ON generated_presentations(creation_date);
    ''')
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