# BCGスライドジェネレーター システム要件定義書

## 1. プロジェクト概要

### 1.1 目的
デザイン性に優れたPDF・画像ファイルからデザインパターンを学習し、自然言語入力から最適なデザインのスライドを自動生成するシステム

### 1.2 対象ユーザー
- 個人利用（開発者本人）
- 社内での資料作成業務

### 1.3 成功指標
- スライド作成時間を80%以上短縮
- BCGレベルのデザイン品質を維持
- 年間運用コスト3万円以下

## 2. 機能要件

### 2.1 デザイン学習機能

#### 2.1.1 ファイル管理
**機能名**: Design Asset Manager
**概要**: 優秀なデザインファイルの蓄積・管理

**詳細仕様**:
- **入力形式**: PDF、PNG、JPG、PPTX
- **ファイルサイズ制限**: 50MB以下
- **保存方式**: ローカルファイルシステム + SQLiteメタデータ
- **分類機能**: 
  - ビジネス分野（戦略、財務、マーケティング等）
  - デザインタイプ（プレゼン、レポート、インフォグラフィック等）
  - 品質評価（5段階）

**データ構造**:
```sql
CREATE TABLE design_assets (
    id INTEGER PRIMARY KEY,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_type TEXT NOT NULL,
    category TEXT,
    subcategory TEXT,
    quality_rating INTEGER CHECK(quality_rating BETWEEN 1 AND 5),
    upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    analysis_status TEXT DEFAULT 'pending',
    extracted_patterns TEXT -- JSON形式でデザインパターン保存
);
```

#### 2.1.2 デザイン分析エンジン
**機能名**: Design Pattern Analyzer
**概要**: アップロードされたファイルからデザイン要素を自動抽出・分析

**分析対象要素**:
1. **レイアウト構造**
   - グリッドシステム
   - 要素配置パターン
   - 余白・マージン比率
   - ヘッダー・フッターレイアウト

2. **色彩設計**
   - メインカラー・サブカラー
   - カラーパレット
   - 背景色・テキスト色の組み合わせ
   - アクセントカラーの使用パターン

3. **タイポグラフィー**
   - フォントファミリー
   - フォントサイズ階層
   - 行間・文字間
   - 見出し・本文のスタイル

4. **視覚要素**
   - アイコン・図形のスタイル
   - 罫線・境界線の処理
   - 影・エフェクトの使用
   - 画像・チャートの配置パターン

**技術実装**:
```python
class DesignAnalyzer:
    def analyze_pdf(self, pdf_path):
        """PDFからデザインパターンを抽出"""
        return {
            'layout': self.extract_layout_patterns(pdf_path),
            'colors': self.extract_color_palette(pdf_path),
            'typography': self.extract_typography_info(pdf_path),
            'visual_elements': self.extract_visual_elements(pdf_path)
        }
    
    def extract_layout_patterns(self, pdf_path):
        """レイアウトパターンの分析"""
        # PDF.jsやPyMuPDFを使用してページ構造を分析
        pass
    
    def extract_color_palette(self, pdf_path):
        """カラーパレットの抽出"""
        # 画像処理ライブラリで色彩分析
        pass
```

#### 2.1.3 パターンデータベース
**機能名**: Design Pattern Database
**概要**: 抽出されたデザインパターンの構造化保存

**データスキーマ**:
```sql
CREATE TABLE design_patterns (
    id INTEGER PRIMARY KEY,
    asset_id INTEGER REFERENCES design_assets(id),
    pattern_type TEXT, -- 'layout', 'color', 'typography', 'visual'
    pattern_data TEXT, -- JSON形式
    usage_frequency INTEGER DEFAULT 0,
    quality_score REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE pattern_combinations (
    id INTEGER PRIMARY KEY,
    layout_pattern_id INTEGER,
    color_pattern_id INTEGER,
    typography_pattern_id INTEGER,
    visual_pattern_id INTEGER,
    combination_score REAL,
    usage_count INTEGER DEFAULT 0
);
```

### 2.2 スライド生成機能

#### 2.2.1 自然言語処理
**機能名**: Content Structure Generator
**概要**: 自然言語入力からスライド構造を生成

**入力例**:
```
新規事業としてAIチャットボットサービスを提案したい。
市場規模は1000億円、主要競合は3社ある。
我々の差別化ポイントは業界特化型である点。
収益予測は1年目100万円、3年目1億円。
投資回収期間は18ヶ月を想定。
```

**処理フロー**:
1. **構造分析**: OpenAI APIでコンテンツを論理構造に分解
2. **スライド設計**: BCGフレームワークに基づく構成決定
3. **デザイン選択**: 蓄積されたパターンから最適なデザインを選択

**API連携**:
```python
class ContentGenerator:
    def generate_structure(self, natural_input):
        """自然言語からスライド構造を生成"""
        prompt = f"""
        以下の内容をBCGスタイルのプレゼンテーション構造に変換してください。
        
        入力: {natural_input}
        
        出力形式:
        {{
            "title": "プレゼンテーションタイトル",
            "slides": [
                {{
                    "slide_number": 1,
                    "title": "スライドタイトル",
                    "type": "title_slide|content_slide|chart_slide|conclusion_slide",
                    "content": {{
                        "main_message": "メインメッセージ",
                        "supporting_points": ["ポイント1", "ポイント2"],
                        "data": {{"key": "value"}} if applicable
                    }}
                }}
            ]
        }}
        """
        
        response = self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        
        return json.loads(response.choices[0].message.content)
```

#### 2.2.2 デザイン適用エンジン
**機能名**: Design Application Engine
**概要**: 生成されたコンテンツに学習済みデザインパターンを適用

**処理ステップ**:
1. **コンテンツタイプ判定**: スライドの種類（タイトル、チャート、テキスト等）
2. **パターンマッチング**: 適切なデザインパターンの選択
3. **レイアウト生成**: PowerPointテンプレートの動的生成
4. **要素配置**: テキスト、図形、チャートの最適配置

```python
class DesignEngine:
    def apply_design(self, content_structure, design_preferences=None):
        """コンテンツ構造にデザインを適用"""
        
        # 1. 最適なデザインパターンの選択
        design_pattern = self.select_optimal_pattern(
            content_type=content_structure['type'],
            quality_threshold=0.8
        )
        
        # 2. PowerPointテンプレートの生成
        template = self.generate_pptx_template(design_pattern)
        
        # 3. コンテンツの配置
        slides = []
        for slide_data in content_structure['slides']:
            slide = self.create_slide(template, slide_data, design_pattern)
            slides.append(slide)
        
        return self.finalize_presentation(slides)
```

#### 2.2.3 PowerPoint出力
**機能名**: PPTX Generator
**概要**: 最終的なPowerPointファイルの生成

**技術実装**: python-pptx ライブラリ使用
**出力形式**: .pptx（Microsoft PowerPoint形式）
**ファイル名規則**: `{project_name}_{timestamp}.pptx`

### 2.3 プレビュー・修正機能

#### 2.3.1 スライドプレビュー
**機能名**: Slide Preview System
**概要**: 生成されたスライドのWeb上でのプレビュー表示

**技術仕様**:
- **フロントエンド**: HTML5 Canvas または SVG での描画
- **バックエンド**: PowerPointファイルをJSONに変換
- **レスポンシブ**: デスクトップ・タブレット対応

**データフロー**:
```
PPTX → 画像変換 → Base64エンコード → JSON → フロントエンド描画
```

**実装例**:
```javascript
class SlidePreview {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.currentSlide = 0;
        this.slides = [];
    }
    
    loadPresentation(presentationData) {
        this.slides = presentationData.slides;
        this.renderSlide(0);
        this.setupNavigation();
    }
    
    renderSlide(slideIndex) {
        const slide = this.slides[slideIndex];
        const canvas = this.container.querySelector('canvas');
        const ctx = canvas.getContext('2d');
        
        // スライド内容の描画
        this.drawSlideContent(ctx, slide);
    }
}
```

#### 2.3.2 修正指示システム
**機能名**: Revision Request System
**概要**: 自然言語での修正指示を受け付け、スライドを更新

**修正指示の例**:
```
「2枚目のスライドのタイトルをもっと短くして」
「グラフの色を青系にして」
「箇条書きの順番を変更して、重要な順にして」
「4枚目に競合分析のスライドを追加して」
```

**処理フロー**:
1. **修正内容の解析**: OpenAI APIで指示内容を構造化
2. **対象特定**: どのスライド・要素を修正するか判定
3. **修正実行**: 該当部分の更新
4. **再生成**: 修正されたPowerPointファイルの出力

```python
class RevisionSystem:
    def process_revision_request(self, instruction, current_presentation):
        """修正指示を処理してプレゼンテーションを更新"""
        
        # 1. 修正指示の解析
        revision_plan = self.analyze_instruction(instruction)
        
        # 2. 修正の実行
        updated_presentation = self.apply_revisions(
            current_presentation, 
            revision_plan
        )
        
        # 3. 新しいPowerPointファイルの生成
        output_path = self.generate_updated_pptx(updated_presentation)
        
        return {
            'success': True,
            'output_path': output_path,
            'changes_summary': revision_plan['summary']
        }
    
    def analyze_instruction(self, instruction):
        """修正指示を構造化された計画に変換"""
        prompt = f"""
        以下の修正指示を分析し、具体的な修正計画を作成してください。
        
        修正指示: {instruction}
        
        出力形式:
        {{
            "target_slide": "スライド番号 or 'all'",
            "modification_type": "content|design|structure|addition",
            "specific_changes": [
                {{
                    "element": "対象要素",
                    "action": "変更内容",
                    "new_value": "新しい値"
                }}
            ],
            "summary": "修正内容の要約"
        }}
        """
        # OpenAI API呼び出し
        pass
```

### 2.4 ユーザーインターフェース

#### 2.4.1 メイン画面
**レイアウト**: シングルページアプリケーション
**フレームワーク**: HTML + CSS + Vanilla JavaScript（軽量化重視）

**画面構成**:
1. **ヘッダー**: アプリタイトル・設定リンク
2. **メインエリア**: タブ形式で機能切り替え
   - スライド生成タブ
   - デザイン学習タブ  
   - プレビュー・修正タブ
3. **フッター**: ステータス表示・ヘルプリンク

#### 2.4.2 各タブの仕様

**スライド生成タブ**:
```html
<div class="tab-content" id="generate-tab">
    <!-- 自然言語入力エリア -->
    <textarea id="content-input" placeholder="作成したいスライドの内容を自然に記述してください..."></textarea>
    
    <!-- デザインパターン選択 -->
    <div class="design-selector">
        <h4>デザインパターン</h4>
        <select id="design-pattern">
            <option value="auto">自動選択（推奨）</option>
            <option value="bcg_standard">BCG標準</option>
            <option value="financial">財務重視</option>
            <option value="creative">クリエイティブ</option>
        </select>
    </div>
    
    <!-- 生成ボタン -->
    <button id="generate-btn" class="primary-btn">スライドを生成</button>
    
    <!-- 進捗表示 -->
    <div id="progress-area" style="display: none;">
        <div class="progress-bar"></div>
        <div class="progress-text">AIがスライドを作成中...</div>
    </div>
</div>
```

**デザイン学習タブ**:
```html
<div class="tab-content" id="learn-tab">
    <!-- ファイルアップロードエリア -->
    <div class="upload-area" id="design-upload">
        <input type="file" id="design-files" multiple accept=".pdf,.png,.jpg,.pptx">
        <div class="upload-placeholder">
            <i class="upload-icon">📁</i>
            <p>デザインファイルをドラッグ&ドロップ<br>または クリックして選択</p>
        </div>
    </div>
    
    <!-- カテゴリー分類 -->
    <div class="categorization">
        <label for="category">カテゴリー:</label>
        <select id="category">
            <option value="strategy">戦略・企画</option>
            <option value="financial">財務・会計</option>
            <option value="marketing">マーケティング</option>
            <option value="operation">オペレーション</option>
        </select>
        
        <label for="quality">品質評価:</label>
        <select id="quality">
            <option value="5">★★★★★ 最高品質</option>
            <option value="4">★★★★☆ 高品質</option>
            <option value="3">★★★☆☆ 標準</option>
        </select>
    </div>
    
    <!-- 学習実行ボタン -->
    <button id="learn-btn" class="primary-btn">デザインパターンを学習</button>
    
    <!-- 学習済みパターン一覧 -->
    <div id="learned-patterns">
        <h4>学習済みデザインパターン</h4>
        <div class="pattern-grid" id="pattern-list">
            <!-- 動的に生成される -->
        </div>
    </div>
</div>
```

**プレビュー・修正タブ**:
```html
<div class="tab-content" id="preview-tab">
    <!-- スライドプレビューエリア -->
    <div class="preview-container">
        <div class="slide-viewer">
            <canvas id="slide-canvas" width="800" height="600"></canvas>
        </div>
        
        <!-- スライドナビゲーション -->
        <div class="slide-navigation">
            <button id="prev-slide">◀ 前</button>
            <span id="slide-counter">1 / 5</span>
            <button id="next-slide">次 ▶</button>
        </div>
    </div>
    
    <!-- 修正指示エリア -->
    <div class="revision-area">
        <h4>修正指示</h4>
        <textarea id="revision-input" placeholder="修正したい内容を自然言語で入力してください..."></textarea>
        <button id="apply-revision" class="secondary-btn">修正を適用</button>
    </div>
    
    <!-- ダウンロードエリア -->
    <div class="download-area">
        <button id="download-pptx" class="primary-btn">PowerPointファイルをダウンロード</button>
        <div class="file-info">
            <small>ファイル名: presentation_20241207_143022.pptx</small>
        </div>
    </div>
</div>
```

## 3. 非機能要件

### 3.1 性能要件
- **スライド生成時間**: 5分以内
- **ファイルアップロード**: 50MB以下のファイルを30秒以内
- **プレビュー表示**: 3秒以内
- **修正適用**: 2分以内

### 3.2 可用性要件
- **稼働率**: 99%以上（ローカル環境）
- **データ保持**: ローカルファイルシステムでの永続化
- **バックアップ**: 手動バックアップ機能提供

### 3.3 セキュリティ要件
- **データ管理**: 完全ローカル保存（外部送信なし）
- **API認証**: OpenAI APIキーの暗号化保存
- **ファイルアクセス**: ユーザー権限内でのファイル操作のみ

### 3.4 運用要件
- **年間運用コスト**: 30,000円以下（API費用のみ）
- **メンテナンス頻度**: 月1回、15分以内
- **アップデート**: 四半期1回の機能追加

## 4. 技術仕様

### 4.1 システム構成
```
┌─────────────────────────────────────────┐
│             フロントエンド               │
│        (HTML + CSS + JavaScript)        │
├─────────────────────────────────────────┤
│             バックエンド                 │
│         (Python Flask / Node.js)        │
├─────────────────────────────────────────┤
│             データ層                     │
│  SQLite + ローカルファイルシステム       │
├─────────────────────────────────────────┤
│             外部API                      │
│            OpenAI API                    │
└─────────────────────────────────────────┘
```

### 4.2 技術スタック
- **フロントエンド**: HTML5, CSS3, Vanilla JavaScript
- **バックエンド**: Python 3.9+ (Flask) または Node.js
- **データベース**: SQLite 3.x
- **AI処理**: OpenAI GPT-4o API
- **ファイル処理**: 
  - PDF: PyMuPDF (Python) / pdf.js (JavaScript)
  - PowerPoint: python-pptx
  - 画像: Pillow (Python)
- **デプロイ**: ローカル実行（localhost）

### 4.3 ディレクトリ構造
```
bcg-slide-generator/
├── app/
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   ├── templates/
│   ├── api/
│   ├── core/
│   │   ├── design_analyzer.py
│   │   ├── content_generator.py
│   │   ├── design_engine.py
│   │   └── pptx_generator.py
│   └── database/
├── data/
│   ├── design_assets/
│   ├── generated_slides/
│   ├── temp/
│   └── backups/
├── config/
│   ├── settings.json
│   └── .env
├── tests/
└── docs/
```

### 4.4 データベース設計
```sql
-- デザインアセット管理
CREATE TABLE design_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_type TEXT NOT NULL CHECK(file_type IN ('pdf', 'png', 'jpg', 'pptx')),
    category TEXT,
    subcategory TEXT,
    quality_rating INTEGER CHECK(quality_rating BETWEEN 1 AND 5),
    file_size INTEGER,
    upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    analysis_status TEXT DEFAULT 'pending' CHECK(analysis_status IN ('pending', 'processing', 'completed', 'failed')),
    extracted_patterns TEXT, -- JSON形式
    usage_count INTEGER DEFAULT 0,
    last_used DATETIME
);

-- デザインパターン保存
CREATE TABLE design_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER REFERENCES design_assets(id),
    pattern_type TEXT NOT NULL CHECK(pattern_type IN ('layout', 'color', 'typography', 'visual')),
    pattern_name TEXT,
    pattern_data TEXT NOT NULL, -- JSON形式
    quality_score REAL CHECK(quality_score BETWEEN 0 AND 1),
    usage_frequency INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 生成されたプレゼンテーション履歴
CREATE TABLE generated_presentations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    original_input TEXT NOT NULL,
    content_structure TEXT, -- JSON形式
    applied_patterns TEXT, -- JSON形式（使用されたパターンID）
    file_path TEXT,
    creation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    modification_count INTEGER DEFAULT 0,
    last_modified DATETIME,
    revision_history TEXT -- JSON形式
);

-- システム設定
CREATE TABLE system_settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    description TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 5. API仕様

### 5.1 スライド生成API
```python
POST /api/generate
Content-Type: application/json

Request:
{
    "content": "自然言語での入力テキスト",
    "design_preference": "auto|bcg_standard|financial|creative",
    "slide_count_limit": 10,
    "include_charts": true
}

Response:
{
    "status": "success|processing|error",
    "presentation_id": "12345",
    "preview_data": {
        "slides": [
            {
                "slide_number": 1,
                "title": "スライドタイトル",
                "preview_image": "base64画像データ",
                "elements": [...]
            }
        ]
    },
    "download_url": "/download/presentation_12345.pptx",
    "generation_time": 180
}
```

### 5.2 デザイン学習API
```python
POST /api/learn-design
Content-Type: multipart/form-data

Request:
- files: [ファイル1, ファイル2, ...]
- category: "strategy|financial|marketing|operation"
- quality: 1-5

Response:
{
    "status": "success|error",
    "processed_files": [
        {
            "filename": "example.pdf",
            "asset_id": 123,
            "extracted_patterns": 5,
            "analysis_time": 45
        }
    ],
    "total_patterns": 127
}
```

### 5.3 修正指示API
```python
POST /api/revise
Content-Type: application/json

Request:
{
    "presentation_id": "12345",
    "revision_instruction": "2枚目のタイトルを短くして、グラフの色を青にして",
    "target_slide": 2 // optional
}

Response:
{
    "status": "success|error",
    "updated_presentation_id": "12346",
    "changes_applied": [
        "スライド2のタイトルを「新規事業提案」から「新規事業」に変更",
        "スライド2のグラフ色をオレンジから青に変更"
    ],
    "preview_data": {...},
    "download_url": "/download/presentation_12346.pptx"
}
```

## 6. エラーハンドリング

### 6.1 エラー分類
1. **ユーザー入力エラー**: 不正なファイル形式、空の入力等
2. **システムエラー**: ファイル読み込み失敗、DB接続エラー等
3. **外部APIエラー**: OpenAI API制限、ネットワークエラー等
4. **リソースエラー**: ディスク容量不足、メモリ不足等

### 6.2 エラーレスポンス形式
```json
{
    "status": "error",
    "error_code": "INVALID_FILE_FORMAT",
    "error_message": "サポートされていないファイル形式です",
    "user_message": "PDF、PNG、JPG、PPTXファイルのみアップロード可能です",
    "suggestions": [
        "ファイル形式を確認してください",
        "ファイルが破損していないか確認してください"
    ],
    "timestamp": "2024-12-07T14:30:22Z"
}
```

## 7. テスト仕様

### 7.1 単体テスト
- **対象**: 各クラス・関数の個別テスト
- **フレームワーク**: pytest (Python) / Jest (JavaScript)
- **カバレッジ目標**: 80%以上

### 7.2 統合テスト
- **対象**: API間の連携、ファイル処理フロー
- **テストケース**:
  - ファイルアップロード→分析→パターン抽出
  - 自然言語入力→構造化→デザイン適用→PPTX生成
  - 修正指示→解析→適用→再生成

### 7.3 ユーザビリティテスト
- **対象**: UI/UXの使いやすさ
- **テスト項目**:
  - 初回利用時の理解しやすさ
  - 各機能への到達性
  - エラー時の分かりやすさ

## 8. 運用・保守

### 8.1 ログ仕様
```python
# ログファイル: logs/app.log
2024-12-07 14:30:22 INFO [SlideGenerator] スライド生成開始: user_input_length=245
2024-12-07 14:30:25 INFO [DesignEngine] パターン適用: pattern_id=bcg_001, confidence=0.85
2024-12-07 14:30:28 SUCCESS [PPTXGenerator] ファイル生成完了: output_path=data/generated/pres_20241207_143028.pptx
2024-12-07 14:30:30 ERROR [APIClient] OpenAI API制限エラー: rate_limit_exceeded
```

### 8.2 バックアップ仕様
```bash
# 自動バックアップスクリプト
backup_daily.sh:
- data/design_assets/ → backups/daily/assets_YYYYMMDD/
- data/database.db → backups/daily/db_YYYYMMDD.db
- config/ → backups/daily/config_YYYYMMDD/
```

### 8.3 モニタリング
- **API使用量監視**: 月間コスト上限アラート
- **ディスク使用量**: 容量80%超過時の警告
- **エラー率**: 1時間あたり5回以上のエラーでアラート

## 9. マイルストーン

### 9.1 Phase 1: 基盤構築 (Week 1-2)
- [ ] プロジェクト環境構築
- [ ] データベース設計・実装
- [ ] 基本的なファイルアップロード機能
- [ ] OpenAI API連携テスト

### 9.2 Phase 2: コア機能開発 (Week 3-5)
- [ ] デザイン分析エンジン実装
- [ ] コンテンツ生成エンジン実装
- [ ] PowerPoint生成機能
- [ ] 基本UIの構築

### 9.3 Phase 3: プレビュー・修正機能 (Week 6-7)
- [ ] スライドプレビュー機能
- [ ] 修正指示システム
- [ ] UI/UXの改善

### 9.4 Phase 4: テスト・最適化 (Week 8)
- [ ] 統合テスト実行
- [ ] パフォーマンス最適化
- [ ] エラーハンドリング改善
- [ ] ドキュメント整備