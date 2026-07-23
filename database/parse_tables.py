import json
import os
import re
import sys
import argparse
from collections import OrderedDict

from schemas import (
    LEAVES, LEAF_SCHEMAS_BY_ID, ALL_LEAF_IDS,
    get_leaf_by_id, get_page_group_for_page,
    LEAF_DATA_TABLE, LEAF_DATA_SKIP,
    PageGroup, ColumnDef,
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(SCRIPT_DIR, "raw_handbook.json")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "firestore_export")


def load_raw_data(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_numeric(val):
    val = val.strip()
    has_asterisk = val.endswith("*")
    if has_asterisk:
        val = val.rstrip("*")
    val = val.lstrip("'‘’").rstrip("'‘’")
    val = val.replace("\u00b1", "").replace("\u2020", "").replace("\u2021", "")
    val = val.replace("†", "").replace("‡", "")
    if ',' in val:
        parts = val.rsplit(',', 1)
        if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) <= 4:
            val = parts[0] + '.' + parts[1]
        else:
            val = val.replace(",", "")
    frac = parse_fraction(val)
    if frac is not None:
        return frac
    try:
        return float(val)
    except ValueError:
        return None


def parse_fraction(val):
    val = val.strip().replace(" ", "")
    m = re.match(r'^(\d+)/(\d+)$', val)
    if m:
        try:
            return float(m.group(1)) / float(m.group(2))
        except (ValueError, ZeroDivisionError):
            return None
    m = re.match(r'^(\d+)\s*(\d+)/(\d+)$', val)
    if m:
        try:
            return float(m.group(1)) + float(m.group(2)) / float(m.group(3))
        except (ValueError, ZeroDivisionError):
            return None
    m = re.match(r'^(\d+)-(\d+)/(\d+)$', val)
    if m:
        try:
            return float(m.group(1)) + float(m.group(2)) / float(m.group(3))
        except (ValueError, ZeroDivisionError):
            return None
    return None


def strip_parenthetical_metrics(val):
    return re.sub(r'\([^)]*\)', '', val).strip()


def preprocess_merge_fraction_rows(rows, pg):
    merged = []
    i = 0
    while i < len(rows):
        if row_is_footer(rows[i], pg):
            merged.append(rows[i])
            i += 1
            continue
        row = rows[i]
        has_fraction_start = any(
            re.match(r'^\d+/\s*$', c.strip()) for c in row
        )
        if has_fraction_start and i + 1 < len(rows):
            next_row = rows[i + 1]
            for j, cell in enumerate(row):
                if re.match(r'^\d+/\s*$', cell.strip()):
                    num = cell.strip().rstrip("/")
                    if j < len(next_row):
                        next_row[j] = num + "/" + next_row[j].strip().lstrip("/")
                    break
            i += 1
        else:
            merged.append(row)
            i += 1
    return merged


def row_is_footer(row_cells, pg):
    for cell in row_cells:
        if re.search(pg.footer_pattern, cell, re.IGNORECASE):
            return True
    return False


def extract_section_name(line, pg):
    m = re.match(pg.section_pattern, line)
    if m:
        return m.group(1).strip()
    return None


def row_is_header(rownum, pg):
    return rownum < pg.skip_header_rows


def slugify(name):
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "_", s)
    s = s.strip("_")
    return s


def build_doc_from_tokens(tokens, previous_section, pg):
    if pg.join_remaining:
        if len(tokens) < pg.value_count - 1:
            return None
        core_count = pg.value_count - 1
        core = tokens[:core_count]
        extra = tokens[core_count:]
        last_val = " ".join(extra) if extra else ""
        all_vals = list(core) + [last_val]
    else:
        if len(tokens) < pg.value_count:
            return None
        all_vals = tokens[:pg.value_count]
    doc = OrderedDict()
    doc["section"] = previous_section
    doc["_section_slug"] = slugify(previous_section)
    for i, col in enumerate(pg.columns):
        raw = all_vals[i] if i < len(all_vals) else ""
        if pg.strip_metrics:
            raw = strip_parenthetical_metrics(raw)
        if col.type == "float":
            val = parse_numeric(raw)
            doc[col.name] = val if val is not None else raw
        else:
            doc[col.name] = raw
    return doc


def parse_row_token(row_cells, pg, previous_section):
    if row_is_footer(row_cells, pg):
        return None, previous_section

    line = " ".join(c.strip() for c in row_cells if c.strip())
    if not line:
        return None, previous_section

    section = extract_section_name(line, pg)
    if section:
        rest = line[len(section):].strip()
        previous_section = section
    elif previous_section:
        rest = line
    else:
        return None, previous_section

    rest = re.sub(r'(\d+\.\d{3})(?=\d)', r'\1 ', rest)
    tokens = rest.split()

    doc = build_doc_from_tokens(tokens, previous_section, pg)
    if doc is None:
        return None, previous_section

    return doc, previous_section


def join_tilde_ranges(tokens):
    result = []
    i = 0
    while i < len(tokens):
        if (i + 2 < len(tokens) and tokens[i+1] == "~"
                and re.match(r'^[\d.]+$', tokens[i+2])):
            result.append(f"{tokens[i]}~{tokens[i+2]}")
            i += 3
        elif (i + 2 < len(tokens) and tokens[i] == "~"
              and re.match(r'^[\d.]+$', tokens[i+1])
              and re.match(r'^[\d.]+$', tokens[i+2])):
            result.append(f"{tokens[i+1]}~{tokens[i+2]}")
            i += 3
        else:
            result.append(tokens[i])
            i += 1
    return result


def preprocess_rows_two_row(rows, pg):
    merged = []
    i = 0
    while i < len(rows):
        if row_is_footer(rows[i], pg):
            i += 1
            continue
        entry_row = rows[i]
        entry_line = " ".join(c.strip() for c in entry_row if c.strip())
        if i + 1 < len(rows) and not row_is_footer(rows[i+1], pg):
            cont = rows[i+1]
            cont_line = " ".join(c.strip() for c in cont if c.strip())
            entry_tokens = entry_line.split()
            cont_tokens = cont_line.split()
            tilde_positions = [j for j, t in enumerate(entry_tokens) if t == "~"]
            for idx, pos in enumerate(tilde_positions):
                if idx < len(cont_tokens):
                    entry_tokens.insert(pos + 1 + idx, cont_tokens[idx])
            remaining = len(cont_tokens) - len(tilde_positions)
            if remaining > 0:
                entry_tokens.extend(cont_tokens[-remaining:])
            entry_tokens = join_tilde_ranges(entry_tokens)
            merged.append([" ".join(entry_tokens)])
            i += 2
        else:
            merged.append([entry_line])
            i += 1
    return merged


def preprocess_rows_paired(rows, pg):
    pairs = []
    for row in rows:
        if row_is_footer(row, pg):
            continue
        non_empty = [c for c in row if c.strip()]
        if len(non_empty) < 2:
            continue
        mid = (len(non_empty) + 1) // 2
        left = non_empty[:mid]
        right = non_empty[mid:]
        if pg.pair_invert:
            for cell in right:
                combined = left + [cell]
                if any(c.strip() for c in combined):
                    pairs.append(combined)
        else:
            if any(c.strip() for c in left):
                pairs.append(left)
            if any(c.strip() for c in right):
                pairs.append(right)
    return pairs


def parse_matrix_rows(rows, pg, page_num):
    docs = []
    if len(rows) < 2:
        return docs
    col_headers = []
    for cell in rows[0]:
        cleaned = cell.strip()
        if cleaned:
            col_headers.append(cleaned)
    previous_section = None
    for row in rows[1:]:
        if row_is_footer(row, pg):
            continue
        row_header = row[0].strip() if row else ""
        if not row_header or row_header == row[0].strip() and not any(c.strip() for c in row[1:]):
            continue
        section = extract_section_name(row_header, pg)
        if section:
            previous_section = section
        elif previous_section:
            pass
        else:
            continue
        row_key = previous_section
        for i, cell in enumerate(row[1:], 1):
            val = cell.strip()
            if not val:
                continue
            col_name = col_headers[i-1] if i-1 < len(col_headers) else f"col{i}"
            col_name_slug = slugify(col_name)
            doc = OrderedDict()
            doc["section"] = row_key
            doc["_section_slug"] = slugify(row_key)
            doc["row_header"] = row_key
            doc["col_header"] = col_name
            doc["value_raw"] = val
            numeric = parse_numeric(val)
            doc["value"] = numeric if numeric is not None else val
            doc["page"] = page_num
            docs.append(doc)
    return docs


def parse_row_cell_aligned(row_cells, pg, previous_section):
    if row_is_footer(row_cells, pg):
        return None, previous_section
    if not row_cells or not any(c.strip() for c in row_cells):
        return None, previous_section

    section = row_cells[pg.section_column_idx].strip() if pg.section_column_idx < len(row_cells) else ""
    if extract_section_name(section, pg):
        previous_section = section
    elif not previous_section:
        return None, previous_section

    data_start = pg.section_column_idx + 1
    value_cells = row_cells[data_start:data_start + pg.value_count]

    if len(value_cells) < pg.value_count:
        return None, previous_section

    doc = OrderedDict()
    doc["section"] = previous_section
    doc["_section_slug"] = slugify(previous_section)

    for i, col in enumerate(pg.columns):
        raw = value_cells[i].strip()
        if col.type == "float":
            val = parse_numeric(raw)
            doc[col.name] = val if val is not None else raw
        else:
            doc[col.name] = raw

    return doc, previous_section


def process_grid_page(rows, pg, page_num):
    docs = []
    if len(rows) < pg.grid_header_row + 2:
        return docs
    col_header_row = rows[pg.grid_header_row]
    col_line = " ".join(c.strip() for c in col_header_row if c.strip())
    col_tokens = col_line.split()
    use_column_defs = len(pg.columns) > 0
    previous_section = None
    max_rows = pg.max_data_rows
    for row in rows[pg.grid_header_row + 1:]:
        if row_is_footer(row, pg):
            continue
        line = " ".join(c.strip() for c in row if c.strip())
        if not line:
            continue
        section = extract_section_name(line, pg)
        if section:
            rest = line[len(section):].strip()
            previous_section = section
        elif previous_section:
            rest = line
        else:
            continue
        tokens = rest.split()
        col_count = len(pg.columns) if use_column_defs else len(col_tokens)
        if len(tokens) < col_count:
            continue
        doc = OrderedDict()
        doc["section"] = previous_section
        doc["_section_slug"] = slugify(previous_section)
        doc["page"] = page_num
        for j in range(col_count):
            raw = tokens[j] if j < len(tokens) else ""
            if use_column_defs:
                key = pg.columns[j].name
            else:
                key = slugify(col_tokens[j])
            val = parse_numeric(raw)
            doc[key] = val if val is not None else raw
        docs.append(doc)
        if max_rows and len(docs) >= max_rows:
            break
    return docs


def process_api_pipes_page(data_rows, pg, page_num):
    docs = []
    col_defs = pg.columns
    base_section = None
    for row_cells in data_rows:
        if row_is_footer(row_cells, pg):
            continue
        line = " ".join(c.strip() for c in row_cells if c.strip())
        if not line:
            continue
        section = extract_section_name(line, pg)
        if section:
            rest = line[len(section):].strip()
            base_section = section
            tokens = rest.split()
            start_offset = 0
        elif base_section:
            rest = line
            tokens = rest.split()
            start_offset = detect_api_offset(tokens)
        else:
            continue
        if not tokens:
            continue
        section_key = build_api_section_key(base_section, tokens, start_offset)
        if not section_key:
            continue
        doc = OrderedDict()
        doc["section"] = section_key
        doc["_section_slug"] = slugify(section_key)
        doc["page"] = page_num
        sec_parts = base_section.split()
        if len(sec_parts) >= 3:
            doc["nominal_size"] = sec_parts[0]
            doc["od_in"] = parse_numeric(sec_parts[-2])
            doc["od_mm"] = parse_numeric(sec_parts[-1])
        for j, col in enumerate(col_defs):
            if j < start_offset:
                doc[col.name] = None
            else:
                tidx = j - start_offset
                if tidx < len(tokens):
                    raw = tokens[tidx]
                    if raw in ("--", "-", "—", ""):
                        doc[col.name] = None
                    else:
                        val = parse_numeric(raw)
                        doc[col.name] = val if val is not None else raw
                else:
                    doc[col.name] = None
        docs.append(doc)
    return docs


def detect_api_offset(tokens):
    if not tokens:
        return 2
    first = tokens[0]
    if first.startswith("(") and first.endswith(")"):
        return 1
    if first.replace(".", "", 1).isdigit() and "." in first:
        return 2
    if first.isdigit():
        return 0
    return 2


def build_api_section_key(base_section, tokens, offset):
    if offset == 0 and len(tokens) >= 2 and tokens[1].startswith("("):
        return f"{base_section} {tokens[0]} {tokens[1]}"
    elif offset == 0 and len(tokens) >= 1:
        return f"{base_section} {tokens[0]}"
    elif offset == 1 and len(tokens) >= 1:
        return f"{base_section} {tokens[0]}"
    elif offset == 2 and len(tokens) >= 2:
        return f"{base_section} {tokens[0]}x{tokens[1]}"
    else:
        return base_section


def process_scaffolding_page(data_rows, pg, page_num):
    docs = []
    col_defs = pg.columns
    base_group = None
    max_rows = pg.max_data_rows
    for row_cells in data_rows:
        if row_is_footer(row_cells, pg):
            continue
        line = " ".join(c.strip() for c in row_cells if c.strip())
        if not line:
            continue
        tokens = line.split()
        if not tokens:
            continue
        if "O/D" in line:
            idx = line.index("O/D") + 3
            base_group = line[:idx].strip()
            rest_tokens = line[idx:].strip().split()
            if len(rest_tokens) < 2:
                continue
            section_key = f"{base_group} {rest_tokens[0]} {rest_tokens[1]}"
            doc = OrderedDict()
            doc["section"] = section_key
            doc["_section_slug"] = slugify(section_key)
            doc["page"] = page_num
            doc["stk_grade"] = f"{rest_tokens[0]} {rest_tokens[1]}"
            for j, col in enumerate(col_defs):
                if col.name == "stk_grade":
                    continue
                idx_val = 2 + j - 1
                if idx_val < len(rest_tokens):
                    raw = rest_tokens[idx_val]
                    if raw in ("--", "-", "—", ""):
                        doc[col.name] = None
                    else:
                        val = parse_numeric(raw)
                        doc[col.name] = val if val is not None else raw
                else:
                    doc[col.name] = None
            docs.append(doc)
        elif base_group:
            rest_tokens = tokens
            if not rest_tokens[0].replace(".", "", 1).isdigit():
                continue
            if len(rest_tokens) < 2:
                continue
            section_key = f"{base_group} {rest_tokens[0]}x{rest_tokens[1]}"
            doc = OrderedDict()
            doc["section"] = section_key
            doc["_section_slug"] = slugify(section_key)
            doc["page"] = page_num
            doc["stk_grade"] = None
            doc["od_min_mm"] = None
            doc["od_max_mm"] = None
            for j, col in enumerate(col_defs):
                if col.name in ("stk_grade", "od_min_mm", "od_max_mm"):
                    continue
                idx_val = j - 3
                if idx_val < len(rest_tokens):
                    raw = rest_tokens[idx_val]
                    if raw in ("--", "-", "—", ""):
                        doc[col.name] = None
                    else:
                        val = parse_numeric(raw)
                        doc[col.name] = val if val is not None else raw
                else:
                    doc[col.name] = None
            docs.append(doc)
        else:
            continue
        if max_rows and len(docs) >= max_rows:
            break
    return docs


def process_bs1387_page(data_rows, pg, page_num):
    docs = []
    col_defs = pg.columns
    current_class = None
    max_rows = pg.max_data_rows
    for row_cells in data_rows:
        if row_is_footer(row_cells, pg):
            continue
        line = " ".join(c.strip() for c in row_cells if c.strip())
        if not line:
            continue
        tokens = line.split()
        if not tokens:
            continue
        if tokens[0] in ("A1", "Light", "Medium", "Heavy"):
            current_class = tokens[0]
            tokens = tokens[1:]
        if not tokens or len(tokens) < 2:
            continue
        section_key = f"{current_class} {tokens[0]} {tokens[1]}"
        doc = OrderedDict()
        doc["section"] = section_key
        doc["_section_slug"] = slugify(section_key)
        doc["page"] = page_num
        for j, col in enumerate(col_defs):
            idx = j + 2
            if idx < len(tokens):
                raw = tokens[idx]
                if raw in ("--", "-", "—", ""):
                    doc[col.name] = None
                else:
                    val = parse_numeric(raw)
                    doc[col.name] = val if val is not None else raw
            else:
                doc[col.name] = None
        docs.append(doc)
        if max_rows and len(docs) >= max_rows:
            break
    return docs


def process_safe_loads_page(data_rows, pg, page_num):
    docs = []
    col_defs = pg.columns
    span_cols = col_defs[1:-1]
    previous_section = None
    max_rows = pg.max_data_rows
    for row_cells in data_rows:
        if row_is_footer(row_cells, pg):
            continue
        line = " ".join(c.strip() for c in row_cells if c.strip())
        if not line:
            continue
        section = extract_section_name(line, pg)
        if section:
            rest = line[len(section):].strip()
            previous_section = section
        elif previous_section:
            rest = line
        else:
            continue
        tokens = rest.split()
        if len(tokens) < 3:
            continue
        mass_val = tokens[0] if tokens else ""
        doc = OrderedDict()
        section_key = f"{previous_section} {mass_val}"
        doc["section"] = section_key
        doc["_section_slug"] = slugify(section_key)
        doc["page"] = page_num
        idx = 0
        doc[col_defs[0].name] = parse_numeric(tokens[idx])
        idx += 1
        for sc in span_cols:
            if idx < len(tokens) - 1:
                val = parse_numeric(tokens[idx])
                doc[sc.name] = val
                idx += 1
            else:
                break
        doc[col_defs[-1].name] = parse_numeric(tokens[-1])
        if doc[col_defs[0].name] is None:
            continue
        docs.append(doc)
        if max_rows and len(docs) >= max_rows:
            break
    return docs


def process_machinery_page(data_rows, pg, page_num):
    docs = []
    col_defs = pg.columns
    value_keys = [c.name for c in col_defs]
    max_rows = pg.max_data_rows
    i = 0
    while i < len(data_rows):
        if row_is_footer(data_rows[i], pg):
            i += 1
            continue
        row = data_rows[i]
        line = " ".join(c.strip() for c in row if c.strip())
        if not line:
            i += 1
            continue
        tokens = line.split()
        if not tokens:
            i += 1
            continue
        grade = tokens[0]
        if not grade[0].isalpha():
            i += 1
            continue
        doc = OrderedDict()
        doc["section"] = grade
        doc["_section_slug"] = slugify(grade)
        doc["page"] = page_num
        rest = tokens[1:] if len(tokens) > 1 else []
        idx = 0
        for key in value_keys:
            if key == "aisi":
                continue
            if idx < len(rest):
                val = rest[idx]
                if val in ("--", "-", "—", ""):
                    doc[key] = None
                elif col_defs[value_keys.index(key)].type == "float":
                    parsed = parse_numeric(val)
                    doc[key] = parsed if parsed is not None else val
                else:
                    doc[key] = val
            else:
                doc[key] = None
            idx += 1
        if i + 1 < len(data_rows):
            next_row = data_rows[i + 1]
            next_line = " ".join(c.strip() for c in next_row if c.strip())
            if next_line:
                nxt = next_line.split()
                if not nxt[0][0].isalpha():
                    doc["aisi"] = nxt[0]
                    rest_aisi = nxt[1:] if len(nxt) > 1 else []
                    aidx = 0
                    for key in value_keys:
                        if key == "aisi" or key not in value_keys:
                            continue
                        if aidx < len(rest_aisi):
                            val = rest_aisi[aidx]
                            if val not in ("--", "-", "—", "") and val[:1].isdigit() or val[:1] in ("<", "≤", ">", "≥", "."):
                                if doc.get(key) is None:
                                    doc[key] = val
                        aidx += 1
                    i += 1
        docs.append(doc)
        if max_rows and len(docs) >= max_rows:
            break
        i += 1
    return docs


def process_page(page_data, pg):
    page_num = page_data["page"]
    rows = page_data["rows"]
    docs = []
    previous_section = None

    data_rows = [r for r in rows[pg.skip_header_rows:]]

    if pg.merge_fractions:
        data_rows = preprocess_merge_fraction_rows(data_rows, pg)

    if pg.parser == "two_row":
        data_rows = preprocess_rows_two_row(data_rows, pg)

    if pg.parser == "paired":
        data_rows = preprocess_rows_paired(data_rows, pg)

    if pg.parser == "matrix":
        return parse_matrix_rows(data_rows, pg, page_num)

    if pg.parser == "grid":
        return process_grid_page(data_rows, pg, page_num)

    if pg.parser == "safe_loads":
        return process_safe_loads_page(data_rows, pg, page_num)

    if pg.parser == "api_pipes":
        return process_api_pipes_page(data_rows, pg, page_num)

    if pg.parser == "bs1387":
        return process_bs1387_page(data_rows, pg, page_num)

    if pg.parser == "scaffolding":
        return process_scaffolding_page(data_rows, pg, page_num)

    if pg.parser == "machinery":
        return process_machinery_page(data_rows, pg, page_num)

    if pg.parser == "flange":
        if pg.strip_metrics:
            for row in data_rows:
                for j in range(len(row)):
                    row[j] = strip_parenthetical_metrics(row[j])

    for row_cells in data_rows:
        if row_is_footer(row_cells, pg):
            continue
        if pg.cell_aligned:
            result = parse_row_cell_aligned(row_cells, pg, previous_section)
        else:
            result = parse_row_token(row_cells, pg, previous_section)
        if result is None or result[0] is None:
            continue
        doc, previous_section = result
        doc["page"] = page_num
        docs.append(doc)
        if pg.max_data_rows and len(docs) >= pg.max_data_rows:
            break

    return docs


def merge_docs(docs_by_key):
    merged = []
    for section_key, doc_list in docs_by_key.items():
        base = OrderedDict()
        base["section"] = section_key
        for d in doc_list:
            for key, value in d.items():
                if key in ("section", "_section_slug", "page"):
                    continue
                if key not in base and value is not None:
                    base[key] = value
        merged.append(base)
    return merged


def process_leaf(leaf, raw_pages_by_num):
    docs_by_key = {}

    for pg_num in sorted(leaf.pages):
        if pg_num not in raw_pages_by_num:
            continue
        pg = get_page_group_for_page(leaf, pg_num)
        if pg is None:
            continue

        page_data = raw_pages_by_num[pg_num]
        page_docs = process_page(page_data, pg)

        for doc in page_docs:
            section_key = doc["section"]
            if section_key not in docs_by_key:
                docs_by_key[section_key] = []
            docs_by_key[section_key].append(doc)

    merged = merge_docs(docs_by_key)
    return merged


def output_ndjson(docs_by_leaf, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for leaf_id, docs in sorted(docs_by_leaf.items()):
        for i, doc in enumerate(docs):
            slug = slugify(doc.get("section", "unknown"))
            doc["_doc_id"] = f"{leaf_id}_{slug}_{i}"
        filename = f"{leaf_id}.ndjson"
        out_path = os.path.join(output_dir, filename)
        with open(out_path, "w", encoding="utf-8") as f:
            for doc in docs:
                f.write(json.dumps(doc, ensure_ascii=False) + "\n")
        print(f"  {len(docs):>4} docs -> {filename}")


def main():
    parser = argparse.ArgumentParser(
        description="Parse raw handbook JSON into structured Firestore documents (leaf-based)"
    )
    parser.add_argument("--input", default=INPUT_PATH)
    parser.add_argument("--output", default=OUTPUT_DIR)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    print(f"Loading raw data from {args.input}...")
    raw_data = load_raw_data(args.input)
    pages_by_num = {t["page"]: t for t in raw_data["tables"]}
    print(f"Loaded {len(raw_data['tables'])} pages")

    print(f"\nProcessing {len(LEAVES)} leaf schemas...")

    docs_by_leaf = {}
    total_docs = 0
    skipped = 0

    for leaf in LEAVES:
        if leaf.data_type == LEAF_DATA_SKIP or not leaf.page_groups:
            skipped += 1
            continue

        docs = process_leaf(leaf, pages_by_num)
        if docs:
            docs_by_leaf[leaf.leaf_id] = docs
            total_docs += len(docs)

    print(f"\nParsed {total_docs} documents across {len(docs_by_leaf)} leaf collections ({skipped} leaves skipped):")
    for leaf_id, docs in sorted(docs_by_leaf.items(), key=lambda x: -len(x[1])):
        leaf = get_leaf_by_id(leaf_id)
        label = leaf.name if leaf else leaf_id
        print(f"  {leaf_id:50s} {len(docs):>4} docs  ({label})")

    print(f"\nWriting NDJSON to {args.output}...")
    output_ndjson(docs_by_leaf, args.output)
    print("Done writing NDJSON files.")

    if args.verify:
        verify_parsing(raw_data, docs_by_leaf)


def verify_parsing(raw_data, docs_by_leaf):
    print("\n=== VERIFICATION ===\n")
    pages_by_num = {t["page"]: t for t in raw_data["tables"]}

    total_pages_covered = set()
    for leaf in LEAVES:
        if leaf.data_type != LEAF_DATA_SKIP and leaf.page_groups:
            total_pages_covered.update(leaf.pages)

    all_pages = set(pages_by_num.keys())
    uncovered = all_pages - total_pages_covered
    print(f"Pages covered by active schemas: {len(total_pages_covered)}/{len(all_pages)}")
    if uncovered:
        print(f"Uncovered pages: {sorted(uncovered)}")

    total_docs = sum(len(docs) for docs in docs_by_leaf.values())
    print(f"\nTotal documents: {total_docs}")
    print(f"Total leaf NDJSON files: {len(docs_by_leaf)}")
    print("\nDone.")


if __name__ == "__main__":
    main()
