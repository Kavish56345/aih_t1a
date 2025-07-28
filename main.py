from pathlib import Path
import fitz  # PyMuPDF
import os
import json
import re
from collections import defaultdict, Counter

# Base path of the script
BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"


def is_numbered_heading(text):
    return bool(re.match(r"^(\d+(\.\d+)*|[a-zA-Z]\)|\([a-zA-Z]\))[\s.:]+.+", text.strip()))

def is_subsection_item(text):
    stripped = text.strip()
    if '(' in stripped and ')' in stripped:
        paren_content = re.findall(r'\([^)]+\)', stripped)
        for content in paren_content:
            if any(word in content.lower() for word in ['to appoint', 'to name', 'executive', 'role of']):
                return True
    if re.match(r'^\d+\.\d+', stripped) and len(stripped) > 50:
        return True
    explanatory_phrases = ['to appoint', 'to name', 'role of', 'executive', 'responsible for', 'in consultation with']
    if any(phrase in stripped.lower() for phrase in explanatory_phrases):
        return True
    return False

def is_table_like_line(line):
    spans = line.get("spans", [])
    if len(spans) < 4:
        return False

    short_spans = [s for s in spans if len(s["text"].strip()) <= 15]
    if len(short_spans) >= 3:
        avg_size = sum(s["size"] for s in spans) / len(spans)
        if avg_size <= 9:  # Common small font in tables
            return True

    # Additional check: if most spans are tightly packed and short
    total_width = sum(span["bbox"][2] - span["bbox"][0] for span in spans)
    avg_width = total_width / len(spans)
    if avg_width < 55 and all(len(s["text"]) < 20 for s in spans):
        return True

    return False

def extract_title_and_headings(pdf_path):
    doc = fitz.open(pdf_path)
    title = None
    title_parts = set()
    outline = []

    # Extract title from first page
    first_page = doc[0]
    spans = []
    for block in first_page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            if is_table_like_line(line):
                continue
            for span in line.get("spans", []):
                text = span["text"].strip()
                size = round(span["size"], 1)
                font = span.get("font", "").lower()
                bold = "bold" in font
                y = span["bbox"][1]
                if text:
                    spans.append((text, size, bold, y, font))

    spans.sort(key=lambda x: (-x[1], x[3]))
    if spans:
        top_line = spans[0]
        title = top_line[0]
        title_parts.add(top_line[0])
        if len(spans) > 1:
            second_line = spans[1]
            if second_line[1] == top_line[1] and second_line[2] == top_line[2]:
                title += " " + second_line[0]
                title_parts.add(second_line[0])
        title = title.strip()

    heading_lines = []

    for page_num, page in enumerate(doc, start=1):
        font_sizes = defaultdict(int)
        font_names = []

        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                if is_table_like_line(line):
                    continue
                for span in line.get("spans", []):
                    text = span["text"].strip()
                    size = round(span["size"], 1)
                    font = span.get("font", "").lower()
                    if text:
                        font_sizes[size] += 1
                        font_names.append(font)

        if not font_sizes:
            continue

        most_common_size = max(font_sizes.items(), key=lambda x: x[1])[0]
        common_font = Counter(font_names).most_common(1)[0][0]

        page_lines = []

        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                if is_table_like_line(line):
                    continue

                line_data = {
                    "text": "",
                    "sizes": [],
                    "fonts": set(),
                    "bold_flags": [],
                    "y": line["bbox"][1]
                }

                for span in line.get("spans", []):
                    text = span["text"].strip()
                    size = round(span["size"], 1)
                    font = span.get("font", "").lower()
                    if not text:
                        continue
                    line_data["text"] += text + " "
                    line_data["sizes"].append(size)
                    line_data["fonts"].add(font)
                    line_data["bold_flags"].append("bold" in font)

                line_data["text"] = line_data["text"].strip()
                if not line_data["text"]:
                    continue

                avg_size = round(sum(line_data["sizes"]) / len(line_data["sizes"]), 1)
                is_bold = any(line_data["bold_flags"])
                line_data["avg_size"] = avg_size
                line_data["bold"] = is_bold
                line_data["page"] = page_num
                
                page_lines.append(line_data)
                
        for i, line in enumerate(page_lines):
            text = line["text"]
            word_count = len(text.split())
            avg_size = line["avg_size"]
            is_bold = line["bold"]
            fonts = line["fonts"]
            y_coord = line["y"]

            if text in title_parts or is_subsection_item(text):
                continue

            if word_count > 15 and avg_size <= most_common_size + 1 and not is_bold:
                continue

            if avg_size >= most_common_size + 2:
                pass
            elif avg_size >= most_common_size + 0.5:
                font_different = any(f not in common_font for f in fonts)
                if not (is_bold or font_different or is_numbered_heading(text)):
                    continue
            elif is_numbered_heading(text) and avg_size == most_common_size:
                font_different = any(f != common_font for f in fonts)
                same_boldness = all(b == is_bold for b in line["bold_flags"])
                if (is_bold or font_different) and same_boldness:
                    pass
                else:
                    continue
            elif ":" in text:
                font_different = any(f not in common_font for f in fonts)
                size_larger = avg_size > most_common_size + 0.1
                same_font = len(fonts) == 1
                same_size = all(abs(s - avg_size) < 0.1 for s in line["sizes"])
                same_bold = all(b == is_bold for b in line["bold_flags"])
                if not (is_bold or font_different or size_larger):
                    continue
                if not (same_font and same_size and same_bold):
                    continue
                if any(substr in text.lower() for substr in ["@", "email", "mail", "only by", "p.m.", "a.m.", "fax", "submit"]):
                    continue
            else:
                continue

            word_count_below = 0
            for l in page_lines:
                if l["y"] > y_coord and abs(l["avg_size"] - most_common_size) < 0.2:
                    word_count_below += len(l["text"].split())
                if word_count_below >= 25:
                    break

            if word_count_below < 25:
                continue
            if len(text.strip()) <= 2 or (len(text.split()) == 1 and not re.search(r"[a-zA-Z]{2,}", text)):
                continue

            heading_lines.append({
                "text": text,
                "size": avg_size,
                "bold": is_bold,
                "page": page_num,
                "y": y_coord
            })

    sizes_in_headings = sorted(set(h["size"] for h in heading_lines), reverse=True)
    size_to_level = {sz: f"H{i+1}" for i, sz in enumerate(sizes_in_headings)}

    heading_lines.sort(key=lambda x: (x["page"], x["y"]))
    seen_headings = set()
    i = 0

    while i < len(heading_lines):
        current = heading_lines[i]
        if i + 1 < len(heading_lines):
            next_heading = heading_lines[i + 1]
            if (
                current["size"] == next_heading["size"]
                and current["page"] == next_heading["page"]
                and not (current["text"].strip().endswith(":") and next_heading["text"].strip().endswith(":"))
            ):
                page = doc[current["page"] - 1]
                has_body_between = False
                y1 = current["y"]
                y2 = next_heading["y"]
                for block in page.get_text("dict")["blocks"]:
                    for line in block.get("lines", []):
                        y = line["bbox"][1]
                        if y1 < y < y2:
                            for span in line.get("spans", []):
                                if span["text"].strip():
                                    has_body_between = True
                                    break
                        if has_body_between:
                            break
                if not has_body_between:
                    current["text"] = (current["text"] + " " + next_heading["text"]).strip()
                    i += 2
                    if current["text"] not in seen_headings:
                        outline.append({
                            "text": current["text"],
                            "page": current["page"],
                            "level": size_to_level.get(current["size"], "Unknown")
                        })
                        seen_headings.add(current["text"])
                    continue

        if current["text"] not in seen_headings and current["size"] in size_to_level:
            outline.append({
                "level": size_to_level[current["size"]],
                "text": current["text"],
                "page": current["page"]
            })
            seen_headings.add(current["text"])
        i += 1

    doc.close()
    return {
        "title": title if title else "Untitled Document",
        "outline": outline
    }

def process_all_pdfs_in_folder(input_folder, output_folder):
    """Process all PDF files in the input folder and create JSON outputs"""
    os.makedirs(output_folder, exist_ok=True)

    # Get all PDF files from input folder
    pdf_files = [f for f in os.listdir(str(input_folder)) if f.lower().endswith('.pdf')]

    if not pdf_files:
        print("❌ No PDF files found in the input folder!")
        return

    print(f"📁 Found {len(pdf_files)} PDF files to process...")

    processed_count = 0
    failed_files = []

    for pdf_file in pdf_files:
        try:
            print(f"🔄 Processing: {pdf_file}")

            input_pdf_path = input_folder / pdf_file
            output_filename = input_pdf_path.stem + ".json"
            output_path = output_folder / output_filename

            result = extract_title_and_headings(str(input_pdf_path))

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=4, ensure_ascii=False)

            print(f"✅ Successfully processed: {pdf_file} -> {output_filename}")
            processed_count += 1

        except Exception as e:
            print(f"❌ Failed to process {pdf_file}: {str(e)}")
            failed_files.append(pdf_file)

    print(f"\n📊 Processing Complete!")
    print(f"✅ Successfully processed: {processed_count} files")
    if failed_files:
        print(f"❌ Failed to process: {len(failed_files)} files")
        print("Failed files:", failed_files)
    print(f"📂 Output saved to: {output_folder}")

if __name__ == "__main__":
    process_all_pdfs_in_folder(INPUT_DIR, OUTPUT_DIR)
