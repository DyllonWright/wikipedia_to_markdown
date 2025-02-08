# Wikipedia to Markdown Converter

This script takes a Wikipedia article URL, fetches both the HTML and PDF versions, extracts the content, and converts it to a well-structured Markdown file, which is then saved in the user's `Downloads` directory.

## Features

- **Preserves Full Article Content:** Extracts headings, paragraphs, lists, and tables without summarization.
- **Markdown Headings:** Converts Wikipedia headings (`h1`, `h2`, etc.) into `#`, `##`, etc.
- **Obsidian-Compatible Links:** The first heading is a clickable `[Title](URL)` instead of the full URL.
- **Cleans Up Formatting:** Removes inline reference markers like `[1]`, `[2]`, and unnecessary formatting.
- **PDF Table Extraction:** Downloads Wikipedia’s PDF version and extracts tables, ensuring better accuracy than HTML parsing.
- **Tables Placed at the End:** Inline tables are skipped in the main content to improve readability, and all extracted tables are appended in a dedicated **"Extracted Tables"** section.

## Requirements

- Python 3.x
- `requests` (`pip install requests`)
- `beautifulsoup4` (`pip install beautifulsoup4`)
- `pdfplumber` (`pip install pdfplumber`)

## Usage

1. Save the script as `wikipedia_to_markdown.py`.
2. Run the script with:
   ```bash
   python wikipedia_to_markdown.py "https://en.wikipedia.org/wiki/Example_Article"
   ```
3. The resulting Markdown file will be saved in your `Downloads` directory.

## Notes

- The script ensures tables are correctly formatted and does not alter article content.
- If tables are crucial to the article flow, consider manually repositioning them after conversion.
