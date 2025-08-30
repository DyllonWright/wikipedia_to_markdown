# Wikipedia to Markdown Converter

This script converts any Wikipedia article into a clean, **Obsidian-compatible Markdown file**, preserving structure, references, images, and (optionally) tables from the official PDF export. It is designed to be **robust, polite to Wikipedia servers**, and easy to use.

---

## ✨ Features

* **Accurate Markdown Structure:** Converts Wikipedia headings (`h1`–`h6`) into Markdown (`#`–`######`), with lists and paragraphs preserved.
* **Obsidian-Compatible Images:** Extracts images into `![alt text](image_url)` format.
* **Inline References Preserved:** Inline citation markers (e.g., `[1]`) are escaped as `\[1]`.
* **Reference Section:** Appends a `## References` section with numbered footnotes.
* **Optional PDF Table Extraction:** Downloads the Wikipedia PDF and extracts tabular data as Markdown tables (with proper spacing for Obsidian).
* **Safe HTTP Requests:** Uses a descriptive `User-Agent`, request timeouts, and retry with exponential backoff (for compliance with Wikimedia API policies).
* **Flexible CLI Options:**

  * `--no-pdf` → skip PDF download/table extraction.
  * `-o` / `--outdir` → choose output directory (default: `~/Downloads`).
  * `--stop` → stop processing at extra section headings (e.g., `"External links"`).
* **Clean Output:** Saves the final `.md` file with the article title as the filename.

---

## 📦 Requirements

* **Python** 3.8 or newer
* Dependencies:

  ```bash
  pip install requests beautifulsoup4
  ```
* Optional (for table extraction):

  ```bash
  pip install pdfplumber
  ```

---

## 🚀 Usage

1. Save the script as `wikipedia_to_markdown.py`.

2. Run it with a Wikipedia article URL:

   ```bash
   python wikipedia_to_markdown.py "https://en.wikipedia.org/wiki/The_Gambler_(2014_film)"
   ```

3. Find the Markdown file in your `~/Downloads` folder (or custom directory if specified).

---

### 🔧 Options

* **Disable PDF tables**

  ```bash
  python wikipedia_to_markdown.py "URL" --no-pdf
  ```
* **Custom output directory**

  ```bash
  python wikipedia_to_markdown.py "URL" -o ./notes
  ```
* **Stop at extra sections**

  ```bash
  python wikipedia_to_markdown.py "URL" --stop "External links" "Further reading"
  ```

---

## 📄 Output Example

The Markdown file will include:

* A top-level heading linking back to the article
* All main content (headings, paragraphs, lists)
* Obsidian-style image embeds
* Escaped inline reference markers
* A full References section
* (Optional) Extracted PDF tables with proper Markdown formatting

---

## ⚙️ Development Notes

* The script uses the [Wikipedia REST API PDF endpoint](https://en.wikipedia.org/api/rest_v1/#/Page%20content/get_page_pdf__title_) for tables.
* Requests are retried on transient errors (429, 503, etc.) with exponential backoff.
* Please replace the placeholder contact in the `User-Agent` string with your own (email or website), per Wikimedia API policy.
