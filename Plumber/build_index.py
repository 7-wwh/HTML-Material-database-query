import json, os, re, sys

input_path = "/home/ubuntu/Personal Projects /HTML Material database query/Plumber/YH_HandBook.json"
output_path = "/home/ubuntu/Personal Projects /HTML Material database query/Plumber/YH_HandBook.json"

print("Loading existing JSON...", flush=True)
with open(input_path, "r", encoding="utf-8") as f:
    data = json.load(f)

content = data["content"]
search_index = data["search_index"]
doc_info = data["document_info"]

print(f"Loaded: {len(content)} items, {doc_info['total_paragraphs']} paragraphs, {doc_info['total_tables']} tables", flush=True)

# ── Build section hierarchy ──
# ── Build section hierarchy ──
# Track major section (Heading 1 or all-caps) and minor section (Heading 2/3 or short all-caps)
major = ""
minor = ""
HEADING_LIKE = {"Heading 1", "Heading 2", "Heading 3"}

section_of_table = {}
for item in content:
    if item["type"] != "paragraph":
        if item["type"] == "table":
            section_of_table[item["table_idx"]] = [major] + ([minor] if minor and minor != major else [])
        continue

    style = item.get("style", "")
    text = item.get("text", "").strip()
    if not text:
        continue

    is_heading = style in HEADING_LIKE
    is_allcaps = (style == "Normal" and text.isupper() and len(text) >= 6
                  and not text.startswith("*")
                  and not re.search(r'\d', text[:8])
                  and not text.endswith(":") and not text.endswith(")"))
    if not (is_heading or is_allcaps):
        continue

    clean = re.sub(r'\s+\d+$', '', text).strip()
    clean = re.sub(r'\s+$', '', clean).strip()
    if not clean:
        continue
    is_page_num = re.match(r'^\d+$', clean)
    if is_page_num:
        continue

    if style == "Heading 1":
        major = clean
        minor = ""
    elif style == "Heading 2":
        minor = clean
    elif style == "Heading 3":
        minor = clean
    elif is_allcaps:
        # Long all-caps = major section; short all-caps = subsection label
        if len(clean) > 12:
            major = clean
            minor = ""
        else:
            minor = clean

print(f"Section mapping built for {len(section_of_table)} tables", flush=True)

# ── Parse all tables ──
tables = {}
total_data_rows = 0

UNIT_PATTERNS = re.compile(r'^(in|mm|cm|lb/ft|kg/m|in2|in4|in3|cm2|cm4|kN|MPa|N/mm2|—|–|—|yes|no)$', re.I)
HEADER_KEYWORDS = ['size', 'specif', 'wall', 'unit', 'section', 'grade',
                   'quality', 'composition', 'tensile', 'classification',
                   'standard', 'other test', 'scope', 'application', 'chemical']

for item in content:
    if item["type"] != "table":
        continue

    tidx = item["table_idx"]
    raw_rows_data = item["rows"]
    if not raw_rows_data:
        continue

    raw_rows = [r["cols"] for r in raw_rows_data]
    num_cols = max(len(r) for r in raw_rows) if raw_rows else 0

    for i in range(len(raw_rows)):
        while len(raw_rows[i]) < num_cols:
            raw_rows[i].append("")

    # ── Identify header rows ──
    first_cell = raw_rows[0][0].strip() if raw_rows else ""
    first_is_header = (not first_cell) or any(kw in first_cell.lower() for kw in HEADER_KEYWORDS)

    header_row_count = 0
    if first_is_header:
        header_row_count = 1
        # Check if second row looks like units/sub-header
        if len(raw_rows) > 1:
            second_cell = raw_rows[1][0].strip()
            # A units row has very short values, often just units or numbers
            second_is_units = True
            for val in raw_rows[1][:min(5, num_cols)]:
                v = val.strip()
                if v and len(v) > 12:
                    second_is_units = False
                    break
                if v and not (UNIT_PATTERNS.match(v) or re.match(r'^[\d\.\,\/\s\-]+$', v) or v == ''):
                    second_is_units = False
                    break
            if second_is_units:
                header_row_count = 2
    else:
        header_row_count = 1

    # ── Generate unique column names ──
    header_rows = raw_rows[:header_row_count] if header_row_count > 0 else [raw_rows[0]]
    col_names = [""] * num_cols

    col_freq = {}
    for col_i in range(num_cols):
        parts = []
        for hr in header_rows:
            if col_i < len(hr) and hr[col_i].strip():
                parts.append(hr[col_i].strip().replace('\n', ' ').replace('\t', ' '))
        name = " / ".join(parts) if parts else f"col_{col_i + 1}"
        name = re.sub(r'\s+', ' ', name).strip()
        # Deduplicate
        if name in col_freq:
            col_freq[name] += 1
            name = f"{name}_{col_freq[name]}"
        else:
            col_freq[name] = 1
        col_names[col_i] = name

    # ── Parse data rows with inheritance ──
    data_rows = raw_rows[header_row_count:]
    parsed_rows = []
    last_leftmost = ""

    for row in data_rows:
        cells = list(row)
        while len(cells) < num_cols:
            cells.append("")

        if cells[0].strip():
            last_leftmost = cells[0].strip()
        elif last_leftmost:
            cells[0] = last_leftmost
        else:
            continue

        if not cells[0].strip():
            continue

        row_dict = {}
        for ci, col_name in enumerate(col_names):
            val = cells[ci] if ci < len(cells) else ""
            val = val.replace('\n', ' ').replace('\t', ' ').strip()
            row_dict[col_name] = val

        parsed_rows.append(row_dict)

    total_data_rows += len(parsed_rows)

    section_path = section_of_table.get(tidx, [])
    section_name = " / ".join(s for s in section_path if s)

    tables[str(tidx)] = {
        "section": section_name,
        "headers": col_names,
        "num_rows": len(parsed_rows),
        "num_cols": len(col_names),
        "rows": parsed_rows
    }

print(f"Parsed {len(tables)} tables, {total_data_rows} total data rows", flush=True)

# ── Build index by leftmost column value (first unique header) ──
index = {}
for tidx_str, tdata in tables.items():
    if not tdata["headers"]:
        continue
    leftmost_key = tdata["headers"][0]
    mm_key = tdata["headers"][1] if len(tdata["headers"]) > 1 else None
    if mm_key and mm_key == leftmost_key:
        mm_key = None

    for row_idx, row in enumerate(tdata["rows"]):
        key = row.get(leftmost_key, "").strip()
        if not key:
            continue
        if key not in index:
            index[key] = []
        index[key].append({
            "t": int(tidx_str),
            "r": row_idx
        })
    # Build alias for mm values
    if mm_key:
        for row_idx, row in enumerate(tdata["rows"]):
            key = row.get(leftmost_key, "").strip()
            mm_val = row.get(mm_key, "").strip()
            if mm_val and mm_val != key:
                if mm_val not in index:
                    index[mm_val] = []
                index[mm_val].append({
                    "t": int(tidx_str),
                    "r": row_idx
                })

print(f"Index: {len(index)} unique leftmost values", flush=True)

# ── Build section index ──
index_by_section = {}
for tidx_str, tdata in tables.items():
    sec = tdata["section"]
    if not sec:
        continue
    if sec not in index_by_section:
        index_by_section[sec] = {"tables": [], "sizes": {}}
    index_by_section[sec]["tables"].append(int(tidx_str))
    if tdata["headers"]:
        leftmost_key = tdata["headers"][0]
        for row in tdata["rows"]:
            leftmost = row.get(leftmost_key, "").strip()
            if leftmost:
                index_by_section[sec]["sizes"][leftmost] = True

for sec in index_by_section:
    index_by_section[sec]["sizes"] = sorted(index_by_section[sec]["sizes"].keys())
    index_by_section[sec]["tables"] = sorted(set(index_by_section[sec]["tables"]))

print(f"Section index: {len(index_by_section)} sections", flush=True)

# ── Write compact JSON ──
output = {
    "document_info": doc_info,
    "content": content,
    "tables": tables,
    "index": index,
    "index_by_section": index_by_section,
    "search_index": search_index
}

print("Writing JSON...", flush=True)
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False)

file_size = os.path.getsize(output_path)
print(f"Done! File: {output_path}")
print(f"Size: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")
print(f"Tables parsed: {len(tables)}")
print(f"Index keys: {len(index)}")
print(f"Sections: {len(index_by_section)}")
