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

SCHEMA_TO_COLLECTION = {
    "beam_dimensions": "ms_beams_universal",
    "beam_inertia": "ms_beams_universal",
    "beam_metric_dimensions": "ms_beams_universal",
    "beam_metric_inertia": "ms_beams_universal",
    "light_beam_dimensions": "ms_beams_light",
    "light_beam_inertia": "ms_beams_light",
    "light_beam_metric": "ms_beams_light",
    "bearing_pile_dimensions": "ms_bearing_piles",
    "bearing_pile_inertia": "ms_bearing_piles",
    "frodingham_pile": "ms_steel_piles",
    "larssen_pile": "ms_steel_piles",
    "ksp_u_pile": "ms_steel_piles",
    "ksp_u_pile_imp": "ms_steel_piles",
    "z_type_pile": "ms_steel_piles",
    "cf_square_metric": "ms_hollow_cold_formed",
    "cf_rect_metric": "ms_hollow_cold_formed",
    "cf_square_imperial": "ms_hollow_cold_formed",
    "cf_rect_imperial": "ms_hollow_cold_formed",
    "hf_square": "ms_hollow_hot_formed",
    "hf_rect": "ms_hollow_hot_formed",
    "hf_circular": "ms_hollow_hot_formed",
    "cs_pipe_light_aa": "ms_pipes",
    "cs_pipe_sgp": "ms_pipes",
    "cs_pipe_stk": "ms_pipes",
    "plain_channel": "ms_channels",
    "lipped_channel": "ms_channels",
    "din_channel": "ms_channels",
    "u_channel_dim": "ms_channels",
    "u_channel_prop": "ms_channels",
    "equal_angle": "ms_angles",
    "unequal_angle_dim": "ms_angles",
    "unequal_angle_prop": "ms_angles",
    "bulb_flat": "ms_bars",
    "square_bar": "ms_bars",
    "deformed_round_bar": "ms_bars",
    "gauge_table": "appendix_gauge",
}


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


def is_recategorized(filename):
    stem = filename.replace(".ndjson", "")
    return "__" in stem


def upload_docs(db, collection_id, docs, dry_run=False):
    if not docs:
        return 0

    ref = db.collection(collection_id)

    doc_ids_display = [d.get("_doc_id", "no_id") for d in docs[:3]]
    suffix = "..." if len(docs) > 3 else ""
    print(f"  {len(docs)} docs -> {collection_id}: {', '.join(doc_ids_display)}{suffix}")

    if dry_run:
        return len(docs)

    batch = db.batch()
    count = 0
    for doc in docs:
        doc_id = doc.pop("_doc_id", None)
        if doc_id is None:
            continue
        doc.pop("page", None)

        batch.set(ref.document(doc_id), doc)
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
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without writing to Firestore")
    parser.add_argument("--file", default=None,
                        help="Upload a single NDJSON file (stem only, e.g. 'beam_dimensions')")
    parser.add_argument("--all", action="store_true",
                        help="Upload all NDJSON files")
    args = parser.parse_args()

    if not os.path.exists(args.key):
        print(f"ERROR: Service account key not found at: {args.key}")
        sys.exit(1)

    ndjson_dir = Path(NDJSON_DIR)
    if not ndjson_dir.exists():
        print(f"ERROR: NDJSON export directory not found at: {NDJSON_DIR}")
        sys.exit(1)

    db = init_firestore(args.key)

    ndjson_files = sorted(ndjson_dir.glob("*.ndjson"))

    if args.file:
        target = ndjson_dir / f"{args.file}.ndjson"
        if not target.exists():
            print(f"ERROR: {target} not found")
            sys.exit(1)
        targets = [target]
    elif args.all:
        targets = ndjson_files
    else:
        targets = [ndjson_dir / "beam_dimensions.ndjson"]

    total_uploaded = 0
    for fp in targets:
        fname = fp.name
        if fname == "category_map.json" or fname == "beam_metric.ndjson":
            continue
        if is_recategorized(fname):
            continue

        stem = fname.replace(".ndjson", "")
        collection_id = SCHEMA_TO_COLLECTION.get(stem)
        if collection_id is None:
            print(f"  SKIP {fname}: unknown collection mapping")
            continue

        docs = read_ndjson(str(fp))
        print(f"\n[{fname}]")
        count = upload_docs(db, collection_id, docs, dry_run=args.dry_run)
        total_uploaded += count

    label = "Would upload" if args.dry_run else "Uploaded"
    print(f"\n{label} {total_uploaded} document(s) total.")


if __name__ == "__main__":
    main()
