#!/usr/bin/env python3
"""Convert topic_*.txt files in consolidated_output/ to PDFs using reportlab."""
import os
from pathlib import Path
import textwrap

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm


def txt_to_pdf(txt_path: Path, pdf_path: Path, page_size=A4, font_name='Helvetica', font_size=10):
    width, height = page_size
    left_margin = 20 * mm
    right_margin = 20 * mm
    top_margin = 20 * mm
    bottom_margin = 20 * mm
    usable_width = width - left_margin - right_margin
    max_chars = int(usable_width / (font_size * 0.55))

    c = canvas.Canvas(str(pdf_path), pagesize=page_size)
    c.setFont(font_name, font_size)
    y = height - top_margin

    with open(txt_path, 'r', encoding='utf-8', errors='replace') as f:
        for raw_line in f:
            line = raw_line.rstrip('\n')
            if not line:
                y -= font_size * 0.8
                if y < bottom_margin:
                    c.showPage()
                    c.setFont(font_name, font_size)
                    y = height - top_margin
                continue
            wrapped = textwrap.wrap(line, width=max_chars) or ['']
            for w in wrapped:
                c.drawString(left_margin, y, w)
                y -= font_size * 1.15
                if y < bottom_margin:
                    c.showPage()
                    c.setFont(font_name, font_size)
                    y = height - top_margin

    c.save()


def main():
    base = Path('.')
    src_dir = base / 'consolidated_output'
    out_dir = base / 'consolidated_output_pdf'
    out_dir.mkdir(exist_ok=True)

    txt_files = sorted(src_dir.glob('topic_*.txt'))
    if not txt_files:
        print('No topic_*.txt files found in consolidated_output/')
        return

    for t in txt_files:
        pdf_name = t.stem + '.pdf'
        pdf_path = out_dir / pdf_name
        print(f'Converting {t} -> {pdf_path}')
        try:
            txt_to_pdf(t, pdf_path)
        except Exception as e:
            print('Failed to convert', t, e)

    print('Done. PDFs in', out_dir)


if __name__ == '__main__':
    main()
