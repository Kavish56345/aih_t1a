# 📄 PDF Title and Heading Extractor

This Python tool uses **PyMuPDF (fitz)** to extract the **main title** and **structured headings** (like H1, H2, etc.) from PDF documents and exports the results as JSON files. It's especially useful for organizing documents, creating outlines, or building searchable content structures.

---

## 🛠 Features

- 🔍 Extracts the **document title** from the first page
- 📑 Detects **headings** based on font size, boldness, and layout
- 🚫 Ignores tables and non-heading content
- 📁 Processes **multiple PDFs** in a folder
- 💾 Outputs the result as clean and readable `.json` files

---


---

## 🧠 How It Works

1. **Title Extraction**
   - Analyzes the first page of each PDF.
   - Picks the largest, bolded text block(s) as the title.

2. **Heading Detection**
   - Parses all pages and identifies lines as headings based on:
     - Font size relative to the most common font
     - Boldness
     - Text patterns (e.g., numbered sections like `1.2`, `a)`, etc.)
     - Vertical layout and spacing
   - Filters out table-like rows and overly long paragraph text.

3. **Output Format**

Each PDF will have a corresponding `.json` file with structure like:

```json
{
  "title": "Sample PDF Document",
  "outline": [
    {
      "level": "H1",
      "text": "1. Introduction",
      "page": 1
    },
    {
      "level": "H2",
      "text": "1.1 Purpose",
      "page": 1
    }
  ]
}

