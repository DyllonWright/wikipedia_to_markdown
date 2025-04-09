# Wikipedia to Markdown Converter

This script converts a Wikipedia article into a clean, Obsidian-compatible Markdown file, preserving structure, references, and images.

## Features

- **Accurate Markdown Structure:** Converts Wikipedia headings (`h1`–`h6`) into Markdown (`#`–`######`), and lists and paragraphs are preserved.
- **Obsidian-Compatible Images:** Extracts and converts images into `![alt text](image_url)` format.
- **Inline References Preserved:** Inline citation markers (e.g., `[1]`) are escaped and preserved as `\[1]`.
- **Reference Section Included:** A `## References` section is appended with the extracted footnotes numbered and listed.
- **PDF Table Extraction:** Downloads the Wikipedia PDF and extracts tabular data, appending it as proper Markdown tables with blank lines before each (required by Obsidian).
- **Outputs Clean `.md` File:** The final Markdown file is saved in the user's `Downloads` directory with the article title as the filename.

## Requirements

- Python 3.x
- `requests` (`pip install requests`)
- `beautifulsoup4` (`pip install beautifulsoup4`)
- `pdfplumber` (`pip install pdfplumber`)

## Usage

1. Save the script as `wikipedia_to_markdown.py`.
2. Run it from the command line with a Wikipedia article URL:
   ```bash
   python wikipedia_to_markdown.py "https://en.wikipedia.org/wiki/Example_Article"
   ```

## Output

- A Markdown `.md` file will be created in your `~/Downloads` folder.
- It will contain:
  - A top-level heading linking to the source
  - All main content (headings, paragraphs, lists)
  - Obsidian-style image embeds
  - Escaped inline reference markers
  - A full References section
  - Extracted PDF tables with proper formatting
