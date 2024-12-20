# Wikipedia to Markdown Converter

This script takes a Wikipedia article URL, fetches the page content, converts the headings, lists, and tables to Markdown, and saves the result as a `.md` file in the user's `Downloads` directory.

## Features

- **Exact Conversion:** Does not summarize or rewrite text.
- **Markdown Headings:** Converts Wikipedia headings (`h1`, `h2`, etc.) into `#`, `##`, etc.
- **Infobox Parsing:** Identifies "infobox" tables and converts them into a two-column Markdown table of properties and values.
- **Links and References Removed:** Only the link text is retained; inline references like `[1]` are removed.

## Requirements

- Python 3.x
- `requests` library (`pip install requests`)
- `beautifulsoup4` library (`pip install beautifulsoup4`)

## Usage

1. Save the script as `wikipedia_to_markdown.py`.
2. Run the script with:
   ```bash
   python wikipedia_to_markdown.py "https://en.wikipedia.org/wiki/Example_Article"
