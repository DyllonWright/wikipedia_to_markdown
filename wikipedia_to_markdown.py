import requests
from bs4 import BeautifulSoup, NavigableString
import re
import os
import sys
import urllib.parse
import tempfile
import pdfplumber

### HTML Extraction Helpers ###

def convert_heading(tag_name):
    # Convert heading tag (h1, h2, …) to Markdown (e.g. h2 -> "##")
    level = int(tag_name[1])
    return "#" * level

def clean_text(element, inside_table=False):
    """
    Recursively extract text from an element.
    Removes inline reference markers like [1], [2], etc.
    """
    parts = []
    for child in element.children:
        if isinstance(child, NavigableString):
            text = str(child)
            text = re.sub(r'\[\d+\]', '', text)
            parts.append(text)
        elif child.name in ["b", "strong"]:
            inner = clean_text(child, inside_table=inside_table).strip()
            if inner:
                parts.append("**" + inner + "**")
        elif child.name in ["i", "em"]:
            inner = clean_text(child, inside_table=inside_table).strip()
            if inner:
                parts.append("*" + inner + "*")
        elif child.name == "a":
            inner = clean_text(child, inside_table=inside_table)
            parts.append(inner)
        elif child.name in ["ul", "ol"]:
            items = []
            for li in child.find_all("li", recursive=False):
                item_text = clean_text(li, inside_table=inside_table).strip()
                if item_text:
                    items.append(item_text)
            if inside_table:
                parts.append(", ".join(items))
            else:
                for it in items:
                    parts.append("- " + it + "\n")
        elif child.name == "sup":
            # Skip reference markers typically in <sup class="reference">
            if "class" in child.attrs and "reference" in child.attrs["class"]:
                continue
            else:
                inner = clean_text(child, inside_table=inside_table)
                parts.append(inner)
        elif child.name in ["span", "div", "small", "br"]:
            inner = clean_text(child, inside_table=inside_table)
            parts.append(inner)
        elif child.name in ["dl", "dt", "dd"]:
            inner = clean_text(child, inside_table=inside_table).strip()
            if inner:
                parts.append(inner + "\n")
        else:
            inner = clean_text(child, inside_table=inside_table)
            parts.append(inner)
    return "".join(parts)

### PDF Extraction Helpers ###

def download_pdf_from_wikipedia(input_url):
    """
    Given a Wikipedia article URL, extract the page title and download the PDF
    version via Wikipedia's REST API. Returns the path to a temporary PDF file.
    """
    m = re.search(r'/wiki/(.+)$', input_url)
    if not m:
        raise ValueError("Invalid Wikipedia URL")
    page_title = m.group(1)
    encoded_page_title = urllib.parse.quote(page_title, safe='')
    pdf_url = f"https://en.wikipedia.org/api/rest_v1/page/pdf/{encoded_page_title}"
    headers = {"Cache-Control": "no-cache"}
    response = requests.get(pdf_url, headers=headers)
    response.raise_for_status()
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_file.write(response.content)
    temp_file.close()
    return temp_file.name

def convert_pdf_table_to_markdown(table):
    """
    Given a table extracted by pdfplumber (a list of rows),
    convert it to a Markdown table.
    """
    processed_rows = []
    max_cols = 0
    for row in table:
        if row is None:
            continue
        processed_row = [cell if cell is not None else "" for cell in row]
        processed_rows.append(processed_row)
        max_cols = max(max_cols, len(processed_row))
    if not processed_rows:
        return ""
    # Pad each row so that all rows have the same number of columns.
    padded_rows = [row + [""] * (max_cols - len(row)) for row in processed_rows]
    header = padded_rows[0]
    separator = [":---" for _ in range(max_cols)]
    data_rows = padded_rows[1:]
    header_line = "| " + " | ".join(header) + " |"
    separator_line = "| " + " | ".join(separator) + " |"
    data_lines = ["| " + " | ".join(row) + " |" for row in data_rows]
    markdown = "\n".join([header_line, separator_line] + data_lines)
    return markdown

def extract_pdf_tables(pdf_path):
    """
    Open the PDF file at pdf_path and extract all tables using pdfplumber.
    Returns a list of Markdown-formatted tables.
    """
    pdf_tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                md = convert_pdf_table_to_markdown(table)
                if md.strip():
                    pdf_tables.append(md)
    return pdf_tables

### Main Script ###

def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py <wikipedia_article_url>")
        sys.exit(1)
    input_url = sys.argv[1]

    # -------------------------
    # Step 1. Download the PDF and extract its tables.
    print("Downloading PDF from Wikipedia...")
    pdf_path = download_pdf_from_wikipedia(input_url)
    print("PDF downloaded to:", pdf_path)
    pdf_tables = extract_pdf_tables(pdf_path)
    os.remove(pdf_path)
    print("Temporary PDF file removed.")

    # -------------------------
    # Step 2. Download and parse the HTML article.
    response = requests.get(input_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    # Get the page title.
    page_title_el = soup.find("h1", id="firstHeading")
    if page_title_el:
        page_title = page_title_el.get_text().strip()
    else:
        page_title = input_url.split('/wiki/')[-1].replace("_", " ")

    # Top-level heading (Obsidian-style link).
    markdown_lines = [f"# [{page_title}]({input_url})\n"]

    # Get the main content container.
    content_div = soup.find("div", id="mw-content-text")
    if not content_div:
        print("Could not find main content on this page.")
        sys.exit(1)

    # Define stop sections; if encountered, stop processing further.
    stop_sections = {"references", "notes", "bibliography"}

    # Process the content—but skip inline tables.
    for element in content_div.find_all(
            ["h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "dl", "table"], recursive=True):
        if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            heading_text = element.get_text().strip().lower()
            if heading_text in stop_sections:
                break
            heading_mark = convert_heading(element.name)
            heading_clean = clean_text(element).strip()
            if heading_clean:
                markdown_lines.append(f"{heading_mark} {heading_clean}\n")
        elif element.name in ["p", "ul", "ol", "dl"]:
            text = clean_text(element).strip()
            if text:
                markdown_lines.append(text + "\n")
        elif element.name == "table":
            # Skip inline tables.
            continue

    # -------------------------
    # Step 3. Append the extracted tables at the end.
    if pdf_tables:
        markdown_lines.append("## Extracted Tables\n")
        for i, table_md in enumerate(pdf_tables, start=1):
            markdown_lines.append(f"### Table {i}\n")
            markdown_lines.append(table_md + "\n")

    final_output = "\n".join(line.strip() for line in markdown_lines if line.strip())

    # -------------------------
    # Step 4. Write the final Markdown to a file.
    filename = re.sub(r'[\\/*?:"<>|]', "-", page_title) + ".md"
    home = os.path.expanduser("~")
    download_dir = os.path.join(home, "Downloads")
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    output_path = os.path.join(download_dir, filename)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_output)
    print(f"Markdown file created at: {output_path}")

if __name__ == "__main__":
    main()
