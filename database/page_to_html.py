import json
import os
import sys
import argparse
import re
import webbrowser

import firebase_admin
from firebase_admin import credentials, firestore

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_KEY = os.path.join(SCRIPT_DIR, "..", "firebase-key.json")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "html_output")


def init_firestore(key_path):
    if not firebase_admin._apps:
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)
    return firestore.client()


def rows_to_arrays(rows_maps):
    return [list(row.values()) for row in rows_maps]


def find_page(db, collection_id, page_num):
    doc = db.collection(collection_id).document(f"page_{page_num:03d}").get()
    if doc.exists:
        d = doc.to_dict()
        d["rows"] = rows_to_arrays(d.get("rows", []))
        return d
    return None


def find_page_by_scan(db, page_num):
    for col in db.collections():
        doc = find_page(db, col.id, page_num)
        if doc:
            return doc, col.id
    return None, None


def build_blocks(rows):
    blocks = []
    cur = []
    for r in rows:
        nz = sum(1 for c in r if c.strip())
        if nz == 0:
            continue
        if nz == 1:
            text = next(c.strip() for c in r if c.strip())
            if cur and (text.isupper() or re.match(r"^YICK HOE", text, re.I)):
                blocks.append(("table", cur))
                cur = []
            if not cur:
                blocks.append(("single", text))
                continue
            cur.append(r)
        else:
            cur.append(r)
    if cur:
        blocks.append(("table", cur))
    return blocks


def is_header_like(cells):
    clean = [c for c in cells if c]
    if not clean:
        return False
    label = sum(1 for c in clean if c and len(c) <= 28 and re.match(r"^[\w\s\.\(\)\/\-\&]+$", c) and not re.match(r"^[\d\.\,\/\s\-]+$", c))
    short_ratio = label / len(clean)
    return short_ratio >= 0.3 and label >= 1


def generate_html(page_num, category, subcategory, rows):
    blocks = build_blocks(rows)

    parts = []
    parts.append(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Page {page_num} — {category}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: Georgia, "Times New Roman", Times, serif;
    background: #f5f3ef;
    color: #1a1a1a;
    padding: 0;
  }}
  .pg-head {{
    background: #1c2e4a;
    border-bottom: 4px solid #c8a45c;
    padding: 24px 28px 20px;
    text-align: center;
  }}
  .pg-head .pg-num {{
    display: inline-block;
    background: #c8a45c;
    color: #1c2e4a;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 2px 14px;
    border-radius: 8px;
    margin-bottom: 6px;
  }}
  .pg-head h1 {{
    font-size: 22px;
    font-weight: 700;
    color: #fff;
    letter-spacing: 0.5px;
  }}
  .pg-head .sub {{
    font-size: 14px;
    color: #b0b8c8;
    margin-top: 3px;
    font-style: italic;
  }}
  .body {{
    max-width: 1100px;
    margin: 0 auto;
    padding: 28px 24px 50px;
  }}
  h2 {{
    font-size: 18px;
    color: #1c2e4a;
    margin: 28px 0 2px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    border-bottom: 2px solid #d8d0c4;
    padding-bottom: 5px;
  }}
  h2:first-of-type {{ margin-top: 0; }}
  .note {{
    font-style: italic;
    color: #5a5a5a;
    margin: 6px 0;
    line-height: 1.55;
    font-size: 13.5px;
  }}
  .mono {{
    font-family: "Courier New", monospace;
    font-style: normal;
    background: #eeebe6;
    padding: 5px 9px;
    border-radius: 3px;
    margin: 3px 0;
    font-size: 12.5px;
    line-height: 1.45;
    white-space: pre-wrap;
    word-break: break-all;
    color: #3a3a3a;
  }}
  .twrap {{
    overflow-x: auto;
    margin: 8px 0 18px;
    border: 1px solid #d8d0c4;
    border-radius: 5px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 12.5px;
    min-width: 100%;
  }}
  thead th {{
    background: #1c2e4a;
    color: #e8e0d4;
    font-weight: 600;
    text-align: left;
    padding: 6px 8px;
    border-bottom: 2px solid #c8a45c;
    font-size: 11.5px;
    letter-spacing: 0.2px;
    white-space: nowrap;
  }}
  tbody td {{
    padding: 4px 8px;
    border-bottom: 1px solid #e0d8cc;
    vertical-align: top;
    line-height: 1.45;
    color: #2a2a2a;
  }}
  tbody tr:nth-child(even) td {{
    background: #faf8f5;
  }}
  tbody tr:hover td {{
    background: #f0ebe4;
  }}
  .hdr td {{
    background: #e8e3dc !important;
    color: #4a4a4a;
    font-size: 11px;
    border-bottom: 1px solid #d0c8b8;
  }}
  .fwrap td {{
    color: #888;
    font-size: 10.5px;
    text-align: right;
    border: none;
    padding: 8px 8px 2px;
  }}
  .ftr {{
    text-align: center;
    color: #888;
    font-size: 11px;
    padding: 16px 24px 24px;
    border-top: 1px solid #d8d0c4;
    margin-top: 16px;
  }}
  @media (max-width: 600px) {{
    .body {{ padding: 16px 10px 36px; }}
    .pg-head {{ padding: 18px 12px 14px; }}
    table {{ font-size: 11px; }}
    thead th, tbody td {{ padding: 3px 4px; }}
  }}
</style>
</head>
<body>
<div class="pg-head">
  <div class="pg-num">PAGE {page_num:03d}</div>
  <h1>{category}</h1>
""")
    if subcategory:
        parts.append(f'  <div class="sub">{subcategory}</div>\n')
    parts.append('</div>\n<div class="body">\n')

    for btype, bdata in blocks:
        if btype == "single":
            text = bdata
            if re.match(r"^\d+$", text):
                parts.append(f'  <div class="mono">{text}</div>\n')
            elif text.isupper() and len(text) > 2:
                parts.append(f'  <h2>{text}</h2>\n')
            else:
                parts.append(f'  <p class="note">{text}</p>\n')
            continue

        mc = max(len(r) for r in bdata)
        padded = [list(r) + [""] * (mc - len(r)) for r in bdata]

        header_end = 0
        for i, r in enumerate(padded):
            cells = [c.strip() for c in r]
            if not is_header_like(cells):
                break
            header_end = i + 1

        parts.append('  <div class="twrap"><table>\n')

        if header_end > 0:
            parts.append("    <thead>\n")
            for ri in range(header_end):
                cells = [c.strip() for c in padded[ri]]
                parts.append("      <tr>" + "".join(f"<th>{c}</th>" for c in cells) + "</tr>\n")
            parts.append("    </thead>\n")

        parts.append("    <tbody>\n")
        for ri in range(header_end, len(padded)):
            row = padded[ri]
            cells = [c.strip() for c in row]
            nz = sum(1 for c in cells if c)

            if any("YICK HOE" in c.upper() for c in cells):
                parts.append(f'      <tr class="fwrap"><td colspan="{mc}">{cells[0]}</td></tr>\n')
                continue

            combined = " ".join(cells).strip()
            if nz <= 1:
                parts.append(f'      <tr><td class="mono" colspan="{mc}">{combined}</td></tr>\n')
            elif is_header_like(cells):
                parts.append(f'      <tr class="hdr">' + "".join(f"<td>{c}</td>" for c in cells) + "</tr>\n")
            else:
                parts.append("      <tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>\n")

        parts.append("    </tbody>\n")
        parts.append("  </table></div>\n")

    parts.append(f"""  <div class="ftr">
    Yick Hoe Group of Companies &mdash; Structural Steel Handbook &mdash; Page {page_num}
  </div>
</div>
</body>
</html>""")

    return "".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Generate HTML table from Firestore handbook page")
    parser.add_argument("-k", "--key", default=str(DEFAULT_KEY))
    parser.add_argument("-p", "--page", type=int, required=True)
    parser.add_argument("-o", "--open", action="store_true", default=True)
    parser.add_argument("--no-open", action="store_false", dest="open")
    args = parser.parse_args()

    if not os.path.exists(args.key):
        print(f"ERROR: Service account key not found at: {args.key}")
        sys.exit(1)

    db = init_firestore(args.key)
    doc_data, col_id = find_page_by_scan(db, args.page)
    if not doc_data:
        print(f"Page {args.page} not found.")
        sys.exit(1)

    html = generate_html(
        args.page,
        doc_data["category"],
        doc_data.get("subcategory"),
        doc_data["rows"],
    )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, f"page_{args.page:03d}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Generated: {out_path}")
    if args.open:
        webbrowser.open(f"file://{os.path.abspath(out_path)}")


if __name__ == "__main__":
    main()
