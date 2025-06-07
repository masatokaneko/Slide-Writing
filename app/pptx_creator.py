from pathlib import Path
import os
from datetime import datetime
from pptx import Presentation
from pptx.util import Cm, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
import tempfile

class PPTXCreator:
    def __init__(self, output_dir=None):
        if output_dir is None:
            self.output_dir = Path("data") / "generated"
        else:
            self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.fonts = ["游ゴシック", "Yu Gothic", "メイリオ", "Meiryo", "sans-serif"]
        self.bcgb = RGBColor(0, 112, 192)  # BCGブルー
        self.accent = RGBColor(255, 192, 0)  # アクセント
        self.slide_width = Cm(33.867)
        self.slide_height = Cm(19.05)

    def create_presentation(self, structure: dict) -> str:
        """
        スライド構造からPowerPointファイルを生成し、パスを返す
        """
        prs = Presentation()
        prs.slide_width = self.slide_width
        prs.slide_height = self.slide_height
        try:
            # タイトルスライド
            if structure.get("slides") and structure["slides"][0]["type"] == "title_slide":
                self._add_title_slide(prs, structure["slides"][0], structure.get("title", ""))
                slides = structure["slides"][1:]
            else:
                slides = structure.get("slides", [])

            for slide in slides:
                stype = slide.get("type", "content_slide")
                if stype == "content_slide":
                    self._add_content_slide(prs, slide)
                elif stype == "chart_slide":
                    self._add_chart_slide(prs, slide)
                elif stype == "conclusion_slide":
                    self._add_conclusion_slide(prs, slide)
                elif stype == "title_slide":
                    self._add_title_slide(prs, slide, structure.get("title", ""))
                else:
                    self._add_content_slide(prs, slide)

            # ファイル名生成
            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"presentation_{now}.pptx"
            output_path = self.output_dir / filename

            # 一時ファイルで保存してから移動（Windows権限対策）
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as tmp:
                tmp_path = Path(tmp.name)
                try:
                    prs.save(str(tmp_path))
                    tmp.close()
                    tmp_path.replace(output_path)
                except PermissionError:
                    return "ファイル書き込み権限エラー"
                except OSError as e:
                    if e.errno == 28:
                        return "ディスク容量不足エラー"
                    return f"ファイル保存エラー: {str(e)}"
                finally:
                    if tmp_path.exists():
                        try:
                            tmp_path.unlink()
                        except Exception:
                            pass
            return str(output_path)
        except Exception as e:
            return f"PPTX生成エラー: {str(e)}"

    def _set_font(self, shape, size=32, bold=False, color=None):
        for p in shape.text_frame.paragraphs:
            for run in p.runs:
                run.font.size = Pt(size)
                run.font.bold = bold
                run.font.name = self.fonts[0]
                if color:
                    run.font.color.rgb = color

    def _add_title_slide(self, prs, slide, pres_title):
        layout = prs.slide_layouts[5]  # 空白
        s = prs.slides.add_slide(layout)
        title = slide.get("title", pres_title)
        subtitle = slide["content"].get("main_message", "")
        # タイトル
        title_shape = s.shapes.add_textbox(Cm(2), Cm(6), Cm(30), Cm(3))
        title_shape.text = title
        self._set_font(title_shape, size=54, bold=True, color=self.bcgb)
        for p in title_shape.text_frame.paragraphs:
            p.alignment = PP_ALIGN.CENTER
        # サブタイトル
        if subtitle:
            sub_shape = s.shapes.add_textbox(Cm(2), Cm(10), Cm(30), Cm(2.5))
            sub_shape.text = subtitle
            self._set_font(sub_shape, size=32, color=self.accent)
            for p in sub_shape.text_frame.paragraphs:
                p.alignment = PP_ALIGN.CENTER

    def _add_content_slide(self, prs, slide):
        layout = prs.slide_layouts[5]
        s = prs.slides.add_slide(layout)
        title = slide.get("title", "")
        points = slide["content"].get("supporting_points", [])[:5]
        # タイトル
        title_shape = s.shapes.add_textbox(Cm(1), Cm(1), Cm(31), Cm(2.5))
        title_shape.text = title
        self._set_font(title_shape, size=38, bold=True, color=self.bcgb)
        # 箇条書き
        y = 4
        for pt in points:
            box = s.shapes.add_textbox(Cm(2), Cm(y), Cm(28), Cm(2))
            box.text = pt
            self._set_font(box, size=28)
            for p in box.text_frame.paragraphs:
                p.alignment = PP_ALIGN.LEFT
            y += 2.2

    def _add_chart_slide(self, prs, slide):
        layout = prs.slide_layouts[5]
        s = prs.slides.add_slide(layout)
        title = slide.get("title", "")
        # タイトル
        title_shape = s.shapes.add_textbox(Cm(1), Cm(1), Cm(31), Cm(2.5))
        title_shape.text = title
        self._set_font(title_shape, size=38, bold=True, color=self.bcgb)
        # チャートエリア（プレースホルダー）
        chart_box = s.shapes.add_textbox(Cm(4), Cm(5), Cm(25), Cm(10))
        chart_box.text = "[グラフや図表をここに挿入]"
        self._set_font(chart_box, size=28, color=self.accent)
        for p in chart_box.text_frame.paragraphs:
            p.alignment = PP_ALIGN.CENTER

    def _add_conclusion_slide(self, prs, slide):
        layout = prs.slide_layouts[5]
        s = prs.slides.add_slide(layout)
        title = slide.get("title", "まとめ")
        main_msg = slide["content"].get("main_message", "")
        # タイトル
        title_shape = s.shapes.add_textbox(Cm(1), Cm(1), Cm(31), Cm(2.5))
        title_shape.text = title
        self._set_font(title_shape, size=38, bold=True, color=self.bcgb)
        # まとめ
        box = s.shapes.add_textbox(Cm(2), Cm(5), Cm(28), Cm(6))
        box.text = main_msg
        self._set_font(box, size=30, color=self.accent)
        for p in box.text_frame.paragraphs:
            p.alignment = PP_ALIGN.LEFT

# 追加: main.pyから直接呼び出せる関数
def create_presentation(structure: dict, output_path: str = None) -> str:
    creator = PPTXCreator()
    result = creator.create_presentation(structure)
    if output_path and isinstance(result, str) and not result.startswith("PPTX生成エラー"):
        # ファイルを指定パスに移動
        try:
            Path(result).replace(output_path)
            return output_path
        except Exception as e:
            return f"ファイル移動エラー: {str(e)}"
    return result 