import requests
from bs4 import BeautifulSoup, NavigableString
import sys
import re
import os

def convert_heading(tag_name):
    # Example: h2 -> level 2 -> "##"
    level = int(tag_name[1])  # 'h2' -> 2, 'h3' -> 3, etc.
    return "#" * level

def clean_text(element, inside_table=False):
    """
    Recursively extract text and inline formatting, removing references and URLs.
    If inside_table=True, handle lists differently (comma-separated) to avoid breaking the table layout.
    """
    parts = []
    for child in element.children:
        if isinstance(child, NavigableString):
            parts.append(str(child))
        elif child.name in ["b", "strong"]:
            inner = clean_text(child, inside_table=inside_table).strip()
            if inner:
                parts.append("**" + inner + "**")
        elif child.name in ["i", "em"]:
            inner = clean_text(child, inside_table=inside_table).strip()
            if inner:
                parts.append("*" + inner + "*")
        elif child.name == "a":
            # Just the link text
            inner = clean_text(child, inside_table=inside_table)
            parts.append(inner)
        elif child.name in ["ul", "ol"]:
            # If inside table, join items with commas instead of bullets/new lines
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
            # Skip references like [1], [2]
            if "class" in child.attrs and "reference" in child.attrs["class"]:
                continue
            else:
                inner = clean_text(child, inside_table=inside_table)
                parts.append(inner)
        elif child.name in ["span", "div", "small", "br"]:
            # Inline elements: just recurse
            inner = clean_text(child, inside_table=inside_table)
            parts.append(inner)
        elif child.name in ["dl", "dt", "dd"]:
            # Definition lists
            inner = clean_text(child, inside_table=inside_table).strip()
            if inner:
                parts.append(inner + "\n")
        else:
            # Other tags: just recurse
            inner = clean_text(child, inside_table=inside_table)
            parts.append(inner)
    return "".join(parts)

def convert_infobox_to_markdown(table_element):
    """
    Convert an infobox table into a two-column Markdown table: Property | Value.
    We look for rows with a <th scope="row"> and a <td>.
    """
    rows = table_element.find_all("tr", recursive=False)
    entries = []
    for row in rows:
        # Infobox property rows often: <th scope="row">Property</th><td>Value</td>
        header = row.find("th", recursive=False, scope="row")
        value = row.find("td", recursive=False)

        if header and value:
            prop = clean_text(header, inside_table=True).strip()
            val = clean_text(value, inside_table=True).strip()
            if prop or val:
                entries.append((prop, val))

    if not entries:
        return ""

    md_lines = ["| Property | Value |", "| --- | --- |"]
    for (prop, val) in entries:
        md_lines.append(f"| {prop} | {val} |")
    return "\n".join(md_lines)

def convert_standard_table_to_markdown(table_element):
    """
    Convert a generic Wikipedia HTML table to Markdown.
    """
    rows = table_element.find_all("tr", recursive=False)
    if not rows:
        return ""

    table_data = []
    header_row = None
    max_cols = 0

    for i, row in enumerate(rows):
        headers = row.find_all("th", recursive=False)
        cells = row.find_all("td", recursive=False)

        if headers:
            header_texts = [clean_text(h, inside_table=True).strip() for h in headers]
            header_row = header_texts
            max_cols = max(max_cols, len(header_row))
        elif cells:
            cell_texts = [clean_text(c, inside_table=True).strip() for c in cells]
            max_cols = max(max_cols, len(cell_texts))
            table_data.append(cell_texts)

    if header_row is None and table_data:
        # No explicit header, use first row as header
        header_row = table_data.pop(0)

    if not header_row:
        return ""

    def pad_row(r, length):
        return r + [""] * (length - len(r))

    header_row = pad_row(header_row, max_cols)
    table_data = [pad_row(r, max_cols) for r in table_data]

    header_line = "| " + " | ".join(header_row) + " |"
    separator_line = "| " + " | ".join([":---"] * max_cols) + " |"
    rows_lines = ["| " + " | ".join(r) + " |" for r in table_data]

    return "\n".join([header_line, separator_line] + rows_lines)

def convert_table_to_markdown(table_element):
    """
    Decide how to convert the table.
    If it has 'infobox' in one of its classes, treat as infobox.
    Otherwise, standard table.
    """
    table_classes = table_element.get("class", [])
    if any("infobox" in cls.lower() for cls in table_classes):
        return convert_infobox_to_markdown(table_element)
    else:
        return convert_standard_table_to_markdown(table_element)

def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py <wikipedia_article_url>")
        sys.exit(1)

    url = sys.argv[1]

    # Fetch HTML
    r = requests.get(url)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')

    # Get page title
    page_title_el = soup.find("h1", id="firstHeading")
    if page_title_el:
        page_title = page_title_el.get_text().strip()
    else:
        page_title = url.split('/')[-1].replace("_", " ")

    # Clean filename
    filename = re.sub(r'[\\/*?:"<>|]', "-", page_title) + ".md"
    home = os.path.expanduser("~")
    download_dir = os.path.join(home, "Downloads")
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    output_path = os.path.join(download_dir, filename)

    content_div = soup.find("div", id="mw-content-text")
    if not content_div:
        print("Could not find main content on this page.")
        sys.exit(1)

    stop_sections = {"references", "notes", "bibliography"}

    markdown_lines = []
    for element in content_div.find_all(["h1","h2","h3","h4","h5","h6","p","ul","ol","dl","table"], recursive=True):
        # If a heading matches stop sections, break
        if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            heading_text = element.get_text().strip().lower()
            if heading_text in stop_sections:
                break
            heading_mark = convert_heading(element.name)
            heading_clean = clean_text(element).strip()
            if heading_clean:
                markdown_lines.append(f"{heading_mark} {heading_clean}\n")

        elif element.name in ["p", "dl"]:
            text = clean_text(element).strip()
            if text:
                markdown_lines.append(text + "\n")

        elif element.name in ["ul", "ol"]:
            text = clean_text(element).strip()
            if text:
                markdown_lines.append(text + "\n")

        elif element.name == "table":
            table_md = convert_table_to_markdown(element)
            if table_md:
                markdown_lines.append(table_md + "\n")

    final_output = "\n".join(line.strip() for line in markdown_lines if line.strip())

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_output)

    print(f"Markdown file created at: {output_path}")

if __name__ == "__main__":
    main()
