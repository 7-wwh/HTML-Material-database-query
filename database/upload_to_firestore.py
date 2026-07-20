import json
import os
import sys
import argparse
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
NDJSON_DIR = os.path.join(SCRIPT_DIR, "firestore_export")
DEFAULT_KEY = os.path.join(SCRIPT_DIR, "..", "firebase-key.json")

COLLECTIONS = [
    "front_matter", "i_beams", "universal_beams_and_columns",
    "light_beams_and_joists", "bearing_piles", "steel_piles",
    "api_pipes", "cold_formed_hollow_sections", "hot_formed_hollow_sections",
    "pipes", "channels", "z_purlins", "c_purlins", "angles", "bars",
    "plates", "galvanised_serrated_gratings", "expanded_metal",
    "wrought_steel_fittings", "flanges", "stainless_steel_products",
    "machinery_steel_products", "non_ferrous_metals", "appendix",
]


def init_firestore(key_path):
    if not firebase_admin._apps:
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)
    return firestore.client()


def read_ndjson(filepath):
    docs = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                docs.append(json.loads(line))
    return docs


def upload_docs(db, collection_id, docs, dry_run=False):
    if not docs:
        print(f"  Nothing to upload for '{collection_id}'")
        return 0

    doc_ids_display = [d["_doc_id"] for d in docs[:3]]
    suffix = "..." if len(docs) > 3 else ""
    print(f"  {len(docs)} docs: {', '.join(doc_ids_display)}{suffix}")

    if dry_run:
        return len(docs)

    batch = db.batch()
    count = 0
    for doc in docs:
        doc_id = doc.pop("_doc_id")
        rows = doc.get("rows", [])
        doc["rows"] = [{str(ci): cell for ci, cell in enumerate(row)} for row in rows]
        ref = db.collection(collection_id).document(doc_id)
        batch.set(ref, doc)
        count += 1
        if count % 500 == 0:
            batch.commit()
            batch = db.batch()
    if count % 500 != 0:
        batch.commit()

    return count


def main():
    parser = argparse.ArgumentParser(description="Upload NDJSON handbook data to Firestore")
    parser.add_argument("-k", "--key", default=str(DEFAULT_KEY),
                        help="Path to Firebase service account key JSON")
    parser.add_argument("-c", "--collection", default=None,
                        help="Specific collection to upload (omit for test mode)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without writing to Firestore")
    parser.add_argument("--all", action="store_true",
                        help="Upload all 24 collections")
    args = parser.parse_args()

    if not os.path.exists(args.key):
        print(f"ERROR: Service account key not found at: {args.key}")
        sys.exit(1)

    ndjson_dir = Path(NDJSON_DIR)
    if not ndjson_dir.exists():
        print(f"ERROR: NDJSON export directory not found at: {NDJSON_DIR}")
        sys.exit(1)

    db = init_firestore(args.key)

    if args.all:
        targets = [(c, os.path.join(NDJSON_DIR, f"{c}.ndjson")) for c in COLLECTIONS]
    elif args.collection:
        targets = [(args.collection, os.path.join(NDJSON_DIR, f"{args.collection}.ndjson"))]
    else:
        targets = [("i_beams", os.path.join(NDJSON_DIR, "i_beams.ndjson"))]

    total_uploaded = 0
    for col_id, filepath in targets:
        if not os.path.exists(filepath):
            print(f"  WARNING: {filepath} not found, skipping")
            continue

        docs = read_ndjson(filepath)

        if not args.all and not args.collection:
            docs = docs[:1]

        print(f"\n[{col_id}]")
        count = upload_docs(db, col_id, docs, dry_run=args.dry_run)
        total_uploaded += count

    label = "Would upload" if args.dry_run else "Uploaded"
    print(f"\n{label} {total_uploaded} document(s) total.")


if __name__ == "__main__":
    main()
