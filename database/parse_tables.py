import json
import os
import re
import sys
import argparse
from collections import OrderedDict

from schemas import ALL_SCHEMAS, get_schema_for_page

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(SCRIPT_DIR, "raw_handbook.json")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "firestore_export")


def load_raw_data(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_numeric(val):
    val = val.strip()
    # Strip trailing asterisk (footnote markers)
    has_asterisk = val.endswith("*")
    if has_asterisk:
        val = val.rstrip("*")
    # Strip leading/trailing punctuation markers
    val = val.lstrip("'‘’").rstrip("'‘’")
    # Strip ± (tolerance marker — data has it as a rogue token)
    val = val.replace("\u00b1", "")
    # Handle European decimal commas (e.g., "4,5" -> "4.5", "5,44" -> "5.44")
    # A comma with 1-4 trailing digits is a decimal separator, not a thousands separator
    if ',' in val:
        parts = val.rsplit(',', 1)
        if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) <= 4:
            val = parts[0] + '.' + parts[1]
        else:
            val = val.replace(",", "")
    try:
        return float(val)
    except ValueError:
        return None


def row_is_footer(row_cells, schema):
    for cell in row_cells:
        if re.search(schema.footer_pattern, cell, re.IGNORECASE):
            return True
    return False


def extract_section_name(line, schema):
    m = re.match(schema.section_pattern, line)
    if m:
        return m.group(1).strip()
    return None


def row_is_header(rownum, schema):
    return rownum < schema.skip_header_rows


def parse_row(row_cells, schema, previous_section):
    if row_is_footer(row_cells, schema):
        return None, previous_section

    line = " ".join(c.strip() for c in row_cells if c.strip())
    if not line:
        return None, previous_section

    section = extract_section_name(line, schema)
    if section:
        rest = line[len(section):].strip()
        previous_section = section
    elif previous_section:
        rest = line
    else:
        return None, previous_section

    # Fix merged decimal numbers from raw extraction (e.g., "2.9536.5" -> "2.953 6.5")
    rest = re.sub(r'(\d+\.\d{3})(?=\d)', r'\1 ', rest)
    tokens = rest.split()
    expected = schema.value_count

    if len(tokens) < expected:
        return None, previous_section

    tokens = tokens[:expected]

    doc = OrderedDict()
    doc["section"] = previous_section
    doc["_section_slug"] = slugify(previous_section)

    for i, col in enumerate(schema.columns):
        raw = tokens[i]
        if col.type == "float":
            val = parse_numeric(raw)
            doc[col.name] = val if val is not None else raw
        else:
            doc[col.name] = raw

    return doc, previous_section


def slugify(name):
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "_", s)
    s = s.strip("_")
    return s


def build_document_id(page, section_slug, index):
    return f"p{page}_{section_slug}_{index}"


def process_page(page_data, schema):
    page_num = page_data["page"]
    rows = page_data["rows"]
    docs = []
    previous_section = None

    for rownum, row_cells in enumerate(rows):
        if row_is_header(rownum, schema):
            continue
        result = parse_row(row_cells, schema, previous_section)
        if result is None or result[0] is None:
            continue
        doc, previous_section = result
        doc["page"] = page_num
        docs.append(doc)
        if schema.max_data_rows and len(docs) >= schema.max_data_rows:
            break

    return docs


def process_all_pages(raw_data):
    all_docs_by_group = {}
    for page_data in raw_data["tables"]:
        page_num = page_data["page"]
        schema = get_schema_for_page(page_num)
        if schema is None:
            continue
        docs = process_page(page_data, schema)
        if not docs:
            continue
        group_key = schema.page_type
        all_docs_by_group.setdefault(group_key, []).extend(docs)
    return all_docs_by_group


def output_ndjson(docs_by_group, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for group_key, docs in docs_by_group.items():
        for i, doc in enumerate(docs):
            doc["_doc_id"] = build_document_id(doc["page"], doc["_section_slug"], i)
            del doc["_section_slug"]
            del doc["page"]
        filename = f"{group_key}.ndjson"
        out_path = os.path.join(output_dir, filename)
        with open(out_path, "w", encoding="utf-8") as f:
            for doc in docs:
                f.write(json.dumps(doc, ensure_ascii=False) + "\n")
        print(f"  {len(docs):>4} docs -> {filename}")


def verify_parsing(raw_data, docs_by_group):
    print("\n=== VERIFICATION ===\n")
    total_raw_rows = 0
    total_parsed = 0
    pages_by_p = {t["page"]: t for t in raw_data["tables"]}

    for page_data in raw_data["tables"]:
        page_num = page_data["page"]
        schema = get_schema_for_page(page_num)
        if schema is None:
            continue
        rows = page_data["rows"]
        data_rows = [
            r for i, r in enumerate(rows)
            if not row_is_header(i, schema) and not row_is_footer(r, schema)
        ]
        parsed_docs = [
            d for d in docs_by_group.get(schema.page_type, [])
            if d.get("page") == page_num
        ]
        total_raw_rows += len(data_rows)
        total_parsed += len(parsed_docs)

    coverage = (total_parsed / total_raw_rows * 100) if total_raw_rows else 0
    print(f"Raw data rows (non-header): {total_raw_rows}")
    print(f"Parsed documents:           {total_parsed}")
    print(f"Coverage:                   {total_parsed}/{total_raw_rows} ({coverage:.1f}%)")
    return total_parsed == total_raw_rows


def verify_sample(docs_by_group, raw_data, sample_size=100):
    print(f"\n=== SAMPLE VERIFICATION ({sample_size} documents) ===\n")

    all_docs = []
    for group, docs in docs_by_group.items():
        for d in docs:
            all_docs.append((group, d))
    all_docs.sort(key=lambda x: x[1].get("page", 0))

    sample = all_docs[:sample_size]
    errors = []
    pages_by_p = {t["page"]: t for t in raw_data["tables"]}

    for _, doc in sample:
        page_num = doc["page"]
        section = doc["section"]
        schema = get_schema_for_page(page_num)
        if not schema:
            continue

        raw_page = pages_by_p.get(page_num)
        if not raw_page:
            continue

        raw_data_rows = [
            " ".join(c.strip() for c in row if c.strip())
            for row in raw_page["rows"]
        ]

        raw_row = next(
            (rl for rl in raw_data_rows if rl.strip() and section in rl),
            None,
        )
        if raw_row is None:
            errors.append(f"section '{section}' not found in any raw row")

        null_cols = [col.name for col in schema.columns if doc.get(col.name) is None]
        if null_cols:
            errors.append(f"section '{section}' null cols: {null_cols}")

    total = len(sample)
    clean = total - len(errors)
    pct = (clean / total * 100) if total else 0
    print(f"Sample: {clean}/{total} validated ({pct:.0f}%)")
    if errors:
        print(f"  {len(errors)} issues:")
        for e in errors[:10]:
            print(f"    {e}")
    return len(errors) == 0


def main():
    parser = argparse.ArgumentParser(
        description="Parse raw handbook JSON into structured Firestore documents"
    )
    parser.add_argument("--input", default=INPUT_PATH)
    parser.add_argument("--output", default=OUTPUT_DIR)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--sample", type=int, default=0)
    args = parser.parse_args()

    print(f"Loading raw data from {args.input}...")
    raw_data = load_raw_data(args.input)
    print(f"Loaded {len(raw_data['tables'])} pages")

    print("\nProcessing pages...")
    docs_by_group = process_all_pages(raw_data)

    total = sum(len(docs) for docs in docs_by_group.values())
    print(f"\nParsed {total} structured documents across {len(docs_by_group)} groups:")
    for group, docs in sorted(docs_by_group.items()):
        schema = next((s for s in ALL_SCHEMAS if s.page_type == group), None)
        label = schema.name if schema else group
        print(f"  {group:30s} {len(docs):>4} docs  ({label})")

    print(f"\nWriting NDJSON to {args.output}...")
    output_ndjson(docs_by_group, args.output)
    print("Done writing NDJSON files.")

    if args.verify:
        verify_parsing(raw_data, docs_by_group)
    if args.sample > 0:
        verify_sample(docs_by_group, raw_data, args.sample)


if __name__ == "__main__":
    main()
