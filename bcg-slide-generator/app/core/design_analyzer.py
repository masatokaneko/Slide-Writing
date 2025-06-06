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