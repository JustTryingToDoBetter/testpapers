#!/usr/bin/env python3
"""Consolidate PDFs by topic using text extraction and simple clustering.

Usage:
  python consolidate_topics.py --manifest grade11_mathematical_literacy_papers/manifest.csv

Notes:
- If PDFs are text-based, PyPDF2 extracts text. If not, the script tries OCR via pytesseract.
- Install Tesseract separately for OCR (not included in Python packages).
"""
import argparse
import csv
import os
import math
from pathlib import Path
from collections import defaultdict

try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None

try:
    from pdf2image import convert_from_path
    from PIL import Image
    import pytesseract
except Exception:
    convert_from_path = None
    pytesseract = None

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import nltk


def read_manifest(manifest_path):
    rows = []
    with open(manifest_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def extract_text_pypdf(path):
    if PdfReader is None:
        return ""
    try:
        reader = PdfReader(path)
        texts = []
        for p in reader.pages:
            txt = p.extract_text()
            if txt:
                texts.append(txt)
        return "\n".join(texts)
    except Exception:
        return ""


def extract_text_ocr(path, dpi=200):
    if convert_from_path is None or pytesseract is None:
        return ""
    try:
        images = convert_from_path(path, dpi=dpi)
        parts = []
        for img in images:
            parts.append(pytesseract.image_to_string(img))
        return "\n".join(parts)
    except Exception:
        return ""


def extract_text(path):
    text = extract_text_pypdf(path)
    if len(text.strip()) > 200:
        return text
    # fallback to OCR
    ocr_text = extract_text_ocr(path)
    return ocr_text if ocr_text and len(ocr_text.strip())>0 else text


def cluster_texts(docs, n_clusters=None):
    keys = list(docs.keys())
    texts = [docs[k] for k in keys]
    if len(texts) == 0:
        return {}
    if n_clusters is None:
        n_clusters = max(2, int(math.sqrt(len(texts))))
    vectorizer = TfidfVectorizer(max_df=0.8, min_df=1, stop_words='english')
    X = vectorizer.fit_transform(texts)
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = km.fit_predict(X)
    clusters = defaultdict(list)
    for k, lab in zip(keys, labels):
        clusters[lab].append(k)
    return clusters


def summarize_text(text, top_n=5):
    # sentence scoring via TF-IDF
    nltk.download('punkt', quiet=True)
    from nltk.tokenize import sent_tokenize
    sents = sent_tokenize(text)
    if not sents:
        return ""
    vec = TfidfVectorizer(stop_words='english')
    X = vec.fit_transform(sents)
    scores = X.sum(axis=1).A1
    top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_n]
    top_idx = sorted(top_idx)
    return '\n'.join([sents[i] for i in top_idx])


def save_output(outdir, clusters, docs):
    os.makedirs(outdir, exist_ok=True)
    report = []
    for cid, files in clusters.items():
        combined = "\n\n".join(docs[f] for f in files)
        summary = summarize_text(combined, top_n=6)
        fname = f"topic_{cid:02d}.txt"
        p = Path(outdir) / fname
        with open(p, 'w', encoding='utf-8') as f:
            f.write(f"Files:\n")
            for fpath in files:
                f.write(f"- {fpath}\n")
            f.write('\n--- Summary ---\n')
            f.write(summary)
            f.write('\n\n--- Full Combined Text ---\n')
            f.write(combined)
        report.append((cid, fname, len(files)))
    # write simple index
    with open(Path(outdir)/'index.txt', 'w', encoding='utf-8') as idx:
        for cid, fname, count in sorted(report):
            idx.write(f"topic {cid}: {fname} — {count} files\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', default='grade11_mathematical_literacy_papers/manifest.csv')
    parser.add_argument('--outdir', default='consolidated_output')
    parser.add_argument('--n-clusters', type=int, default=None)
    args = parser.parse_args()

    manifest = read_manifest(args.manifest)
    docs = {}
    base = Path('.').resolve()
    for row in manifest:
        local = row.get('local_path') or row.get('localpath')
        if not local:
            continue
        local = local.replace('\\', os.sep).replace('/', os.sep)
        path = (base / local).resolve()
        if not path.exists():
            print(f"Warning: file not found: {path}")
            continue
        print(f"Extracting: {path}")
        text = extract_text(str(path))
        if not text:
            print(f"  No text extracted for {path}")
            continue
        docs[str(path)] = text

    clusters = cluster_texts(docs, n_clusters=args.n_clusters)
    save_output(args.outdir, clusters, docs)
    print(f"Done. Outputs in {args.outdir}")


if __name__ == '__main__':
    main()
