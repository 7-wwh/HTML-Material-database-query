import json
import os
import sys
import argparse
import re
import shutil

import firebase_admin
from firebase_admin import credentials, firestore

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_KEY = os.path.join(SCRIPT_DIR, "..", "firebase-key.json")

BOLD = "\033[1;37m"
DIM = "\033[2;37m"
ITALIC = "\033[3;37m"
CYAN = "\033[1;36m"
RESET = "\033[0m"


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


def print_page(rows, tw):
    for r in rows:
        cells = [c.strip() for c in r if c.strip()]
        if not cells:
            continue

        if len(cells) == 1:
            t = cells[0]
            if re.match(r"^\d+$", t):
                print(f"  {DIM}{t}{RESET}")
            elif t.isupper():
                print(f"\n  {BOLD}{t}{RESET}")
            else:
                print(f"  {ITALIC}{t}{RESET}")
            continue

        nz = sum(1 for c in cells if c)
        line = " │ ".join(cells)
        if len(line) > tw - 4:
            line = line[:tw - 7] + "…"
        print(f"  {line}")


def main():
    parser = argparse.ArgumentParser(description="Pull and display a handbook page table from Firestore")
    parser.add_argument("-k", "--key", default=str(DEFAULT_KEY))
    parser.add_argument("-c", "--collection", default=None)
    parser.add_argument("-d", "--doc", default=None)
    parser.add_argument("-p", "--page", type=int, default=None)
    args = parser.parse_args()

    if not os.path.exists(args.key):
        print(f"ERROR: Service account key not found at: {args.key}")
        sys.exit(1)

    if not args.page and not (args.collection and args.doc):
        print("ERROR: provide --page, or --collection + --doc")
        sys.exit(1)

    db = init_firestore(args.key)

    if args.page:
        doc_data, col_id = find_page_by_scan(db, args.page)
        if not doc_data:
            print(f"Page {args.page} not found.")
            sys.exit(1)
        page_num = args.page
    else:
        doc_data = find_page(db, args.collection, int(args.doc.split("_")[1]))
        if not doc_data:
            print(f"Document {args.collection}/{args.doc} not found.")
            sys.exit(1)
        col_id = args.collection
        page_num = int(args.doc.split("_")[1])

    tw = shutil.get_terminal_size().columns

    print()
    print(f"  {CYAN}{'═' * min(tw - 2, 60)}{RESET}")
    print(f"  {CYAN}  Page {page_num:3d}  │  {doc_data['category']}{RESET}")
    if doc_data.get("subcategory"):
        print(f"  {CYAN}           │  {doc_data['subcategory']}{RESET}")
    print(f"  {CYAN}{'═' * min(tw - 2, 60)}{RESET}")

    print_page(doc_data["rows"], tw)
    print()


if __name__ == "__main__":
    main()
