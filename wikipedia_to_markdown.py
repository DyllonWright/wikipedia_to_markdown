#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import re
import sys
import tempfile
import time
import urllib.parse
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup, NavigableString

# Optional dependency isolated: pdfplumber only imported when needed.
try:
    import pdfplumber
except ImportError:
    pdfplumber = None

# -------------------------
# Networking: polite defaults

DEFAULT_HEADERS = {
    "User-Agent": "wikipedia_to_markdown/1.1 (+contact: your_email@example.com)",
    "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.8",
    "Cache-Control": "no-cache",
}

RETRY_STATUS = {429, 500, 502, 503, 504}

def http_get(url: str, headers: Optional[dict] = None, timeout: int = 30, max_retries: int = 4) -> requests.Response:
    """
    GET with simple exponential backoff on transient errors (429/5xx).
    """
    hdrs = dict(DEFAULT_HEADERS)
    if headers:
        hdrs.update(headers)

    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(url, headers=hdrs, timeout=timeout)
            if resp.status_code in RETRY_STATUS:
                # Backoff then retry
                delay = 2 ** attempt
                time.sleep(delay)
            else:
                resp.raise_for_status()
                return resp
        except requests.RequestException as e:
            last_exc = e
            # Backoff then retry
            delay = min(2 ** attempt, 8)
            time.sleep(delay)
    # Exhausted
    if last_exc:
        raise last_exc
    raise RuntimeError("GET failed unexpectedly")

# -------------------------
# HTML Extraction Helpers

def convert_heading(tag_name: str) -> str:
    return "#" * int(tag_name[1])

def clean_text(element, inside_table: bool = False, base_url: str = "") -> str:
    parts: List[str] = []
    for child in element.children:
        if isinstance(child, NavigableString):
            text = str(child)
            text = re.sub(r'\[(\d+)\]', r'\\[\1]', text)  # escape [1]
            parts.append(text)
        elif getattr(child, "name", None) == "img":
            alt = child.get("alt", "")
            src = child.get("src", "")
            src = urllib.parse.urljoin(base_url, src) if base_url else src
            parts.append(f"![{alt}]({src})")
        elif child.name in ["b", "strong"]:
            inner = clean_text(child, inside_table=inside_table, base_url=base_url).strip()
            if inner:
                parts.append("**" + inner + "**")
        elif child.name in ["i", "em"]:
            inner = clean_text(child, inside_table=inside_table, base_url=base_url).strip()
            if inner:
                parts.append("*" + inner + "*")
        elif child.name == "a":
            inner = clean_text(child, inside_table=inside_table, base_url=base_url)
            parts.append(inner)
        elif child.name in ["ul", "ol"]:
            items = []
            for li in child.find_all("li", recursive=False):
                item_text = clean_text(li, inside_table=inside_table, base_url=base_url).strip()
                if item_text:
                    items.append(item_text)
            if inside_table:
                parts.append(", ".join(items))
            else:
                for it in items:
                    parts.append("- " + it + "\n")
        elif child.name == "sup":
            if "class" in child.attrs and "reference" in child.attrs["class"]:
                ref_text = child.get_text()
                match = re.search(r'\[(\d+)\]', ref_text)
                if match:
                    parts.append(f"\\[{match.group(1)}]")
            else:
                parts.append(clean_text(child, inside_table=inside_table, base_url=base_url))
        elif child.name in ["span", "div", "small", "br"]:
            parts.append(clean_text(child, inside_table=inside_table, base_url=base_url))
        elif child.name in ["dl", "dt", "dd"]:
            inner = clean_text(child, inside_table=inside_table, base_url=base_url).strip()
            if inner:
                parts.append(inner + "\n")
        else:
            parts.append(clean_text(child, inside_table=inside_table, base_url=base_url))
    return "".join(parts)

def extract_references(soup: BeautifulSoup, base_url: str = "") -> List[Dict[str, str]]:
    references = []
    ref_ol = soup.find("ol", class_="references")
    if ref_ol:
        li_items = ref_ol.find_all("li", recursive=False)
        for li in li_items:
            ref_text = clean_text(li, base_url=base_url).strip()
            ref_number = len(references) + 1
            references.append({"number": str(ref_number), "text": ref_text})
    return references

# -------------------------
# PDF Extraction Helpers

def build_pdf_url(article_url: str) -> str:
    m = re.search(r'/wiki/(.+)$', article_url)
    if not m:
        raise ValueError("Invalid Wikipedia article URL")
    page_title = m.group(1)
    encoded = urllib.parse.quote(page_title, safe='')
    return f"https://en.wikipedia.org/api/rest_v1/page/pdf/{encoded}"

def download_pdf_from_wikipedia(article_url: str) -> str:
    """
    Returns path to a temporary PDF file.
    Raises on failure. Caller may catch and fallback.
    """
    pdf_url = build_pdf_url(article_url)
    resp = http_get(
        pdf_url,
        headers={"Accept": "application/pdf"},
        timeout=45,
        max_retries=4,
    )
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_file.write(resp.content)
    temp_file.close()
    return temp_file.name

def convert_pdf_table_to_markdown(table: List[List[Optional[str]]]) -> str:
    processed_rows = []
    max_cols = 0
    for row in table or []:
        if row is None:
            continue
        processed = [(cell if cell is not None else "").strip() for cell in row]
        processed_rows.append(processed)
        max_cols = max(max_cols, len(processed))
    if not processed_rows:
        return ""
    padded = [r + [""] * (max_cols - len(r)) for r in processed_rows]
    header = padded[0]
    sep = ["---"] * max_cols
    data = padded[1:]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(sep) + " |",
    ] + ["| " + " | ".join(row) + " |" for row in data]
    return "\n" + "\n".join(lines)

def extract_pdf_tables(pdf_path: str) -> List[str]:
    if pdfplumber is None:
        return []
    pdf_tables: List[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            try:
                for table in page.extract_tables() or []:
                    md = convert_pdf_table_to_markdown(table)
                    if md.strip():
                        pdf_tables.append(md)
            except Exception:
                # Keep going if a single page/table extraction fails
                continue
    return pdf_tables

# -------------------------
# Core HTML → Markdown

def build_markdown_from_article(article_url: str,
                                stop_sections: Optional[List[str]] = None,
                                include_pdf_tables: bool = True) -> str:
    # Fetch HTML
    resp = http_get(article_url, timeout=30)
    soup = BeautifulSoup(resp.text, 'html.parser')

    # Title
    page_title_el = soup.find("h1", id="firstHeading")
    page_title = page_title_el.get_text().strip() if page_title_el else article_url.split('/wiki/')[-1].replace("_", " ")

    markdown_lines: List[str] = [f"# [{page_title}]({article_url})\n"]

    # Optionally attempt PDF tables first (polite to minimize extra calls)
    pdf_tables_md: List[str] = []
    if include_pdf_tables:
        try:
            print("Downloading PDF for table extraction...")
            pdf_path = download_pdf_from_wikipedia(article_url)
            print("PDF downloaded to:", pdf_path)
            pdf_tables_md = extract_pdf_tables(pdf_path)
            try:
                os.remove(pdf_path)
                print("Temporary PDF file removed.")
            except OSError:
                pass
        except Exception as e:
            print(f"PDF fetch/extract skipped due to error: {e}")

    # Main content
    content_div = soup.find("div", id="mw-content-text")
    if not content_div:
        raise RuntimeError("Could not find main content on this page.")

    default_stop = {"references", "notes", "bibliography"}
    if stop_sections:
        default_stop |= {s.lower() for s in stop_sections}

    for element in content_div.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "dl", "table"],
        recursive=True
    ):
        if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            heading_text = element.get_text().strip().lower()
            if heading_text in default_stop:
                break
            heading_mark = convert_heading(element.name)
            heading_clean = clean_text(element, base_url=article_url).strip()
            if heading_clean:
                markdown_lines.append(f"{heading_mark} {heading_clean}\n")
        elif element.name in ["p", "ul", "ol", "dl"]:
            text = clean_text(element, base_url=article_url).strip()
            if text:
                markdown_lines.append(text + "\n")
        elif element.name == "table":
            # Skip inline tables from HTML for now (keeps output clean)
            continue

    # References
    refs = extract_references(soup, base_url=article_url)
    if refs:
        markdown_lines.append("## References\n")
        for ref in refs:
            markdown_lines.append(f"\\[{ref['number']}] {ref['text']}\n")

    # PDF tables (if any)
    if pdf_tables_md:
        markdown_lines.append("## Extracted Tables\n")
        for i, table_md in enumerate(pdf_tables_md, start=1):
            markdown_lines.append(f"### Table {i}\n")
            markdown_lines.append(table_md + "\n")

    return "\n".join(markdown_lines)

# -------------------------
# FS helpers

def default_download_dir() -> str:
    home = os.path.expanduser("~")
    dl = os.path.join(home, "Downloads")
    os.makedirs(dl, exist_ok=True)
    return dl

def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "-", name).strip() or "wikipedia"

def write_markdown(markdown: str, title: str, outdir: str) -> str:
    filename = sanitize_filename(title) + ".md"
    path = os.path.join(outdir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(markdown)
    return path

# -------------------------
# CLI

def main():
    parser = argparse.ArgumentParser(description="Convert a Wikipedia article to Markdown (with optional PDF table extraction).")
    parser.add_argument("url", help="Wikipedia article URL, e.g. https://en.wikipedia.org/wiki/The_Gambler_(2014_film)")
    parser.add_argument("-o", "--outdir", default=default_download_dir(), help="Output directory (default: ~/Downloads)")
    parser.add_argument("--no-pdf", action="store_true", help="Disable PDF download/table extraction")
    parser.add_argument("--stop", nargs="*", default=[], help="Additional section headings at which to stop (case-insensitive)")
    args = parser.parse_args()

    article_url = args.url.strip()
    include_pdf_tables = not args.no_pdf

    print("Fetching and converting article...")
    md = build_markdown_from_article(article_url, stop_sections=args.stop, include_pdf_tables=include_pdf_tables)

    # Title for filename
    m = re.search(r'/wiki/(.+)$', article_url)
    page_title = urllib.parse.unquote(m.group(1)).replace("_", " ") if m else "wikipedia"

    out_path = write_markdown(md, page_title, args.outdir)
    print(f"Markdown file created at: {out_path}")

if __name__ == "__main__":
    main()

"""
# Default (saves to ~/Downloads, tries PDF tables with retries & timeouts)
python wikipedia_to_markdown.py "https://en.wikipedia.org/wiki/The_Gambler_(2014_film)"

# Disable PDF table extraction (HTML only)
python wikipedia_to_markdown.py "https://en.wikipedia.org/wiki/The_Gambler_(2014_film)" --no-pdf

# Custom output directory + extra stop sections
python wikipedia_to_markdown.py "https://en.wikipedia.org/wiki/The_Gambler_(2014_film)" -o "C:\path\to\out" --stop "External links" "Further reading"
"""
