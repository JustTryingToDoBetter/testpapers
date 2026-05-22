# Consolidate Topics from Exam PDFs

This workspace includes `consolidate_topics.py`, a script that extracts text from the PDFs listed in `grade11_mathematical_literacy_papers/manifest.csv`, clusters documents by topic, and writes consolidated summaries per topic to `consolidated_output/`.

Setup

1. Create a Python virtual environment and install requirements:

```bash
python -m venv .venv
.
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Install Tesseract OCR for your OS (required for image-based PDFs):
- Windows: install from https://github.com/tesseract-ocr/tesseract (add to PATH)

Run

```bash
python consolidate_topics.py --manifest grade11_mathematical_literacy_papers/manifest.csv --outdir consolidated_output
```

Notes

- The script first tries to extract selectable text using `PyPDF2`. If that fails or returns little text, it falls back to OCR using `pdf2image` + `pytesseract`.
- You can control number of clusters with `--n-clusters`.
- Outputs: `consolidated_output/index.txt` and `topic_XX.txt` files containing source file list, a short summary, and combined text.
