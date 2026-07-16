#!/usr/bin/env python3
"""
Merge split text cells in YH_HandBook.db.

Usage: python3 merge_split_cells.py
"""

import sqlite3
import sys

DB_PATH = "/home/ubuntu/Personal Projects /HTML Material database query/Plumber/YH_HandBook.db"


def is_numeric(cell):
    s = str(cell).strip()
    if not s:
        return False
    for part in s.replace('\n', ' ').split():
        part = part.strip()
        if not part:
            continue
        cleaned = part.replace(',', '').replace('%', '').replace('$', '').replace('€', '').replace('£', '').replace('¥', '').replace(' ', '')
        if not cleaned:
            continue
        try:
            float(cleaned)
        except ValueError:
            return False
    return True


def is_column_numeric(rows, col_idx):
    numeric_count = 0
    total_check = 0
    for row in rows:
        val = str(row[col_idx]).strip() if row[col_idx] is not None else ""
        if val:
            total_check += 1
            if is_numeric(val):
                numeric_count += 1
    if total_check == 0:
        return True
    return numeric_count / total_check > 0.5


def detect_splits(rows, col_indices):
    splits = []
    for idx in range(len(col_indices) - 1):
        col_a = col_indices[idx]
        col_b = col_indices[idx + 1]

        if is_column_numeric(rows, col_a) or is_column_numeric(rows, col_b):
            continue

        matched_count = 0
        total_non_empty = 0
        space_in_pair_count = 0

        for row in rows:
            val_a = str(row[col_a]).strip() if row[col_a] is not None else ""
            val_b = str(row[col_b]).strip() if row[col_b] is not None else ""

            if not val_a or not val_b:
                continue

            total_non_empty += 1

            last_char = val_a[-1]
            first_char = val_b[0]

            # Both boundary chars must be alphanumeric
            if not (last_char.isalnum() and first_char.isalnum()):
                continue

            # Fragments always continue with a letter, never a digit/symbol
            if not first_char.isalpha():
                continue

            # Case consistency: if both are letters, they must be same case
            if last_char.isalpha():
                if last_char.isupper() != first_char.isupper():
                    continue

            matched_count += 1
            if ' ' in val_a or ' ' in val_b:
                space_in_pair_count += 1

        if total_non_empty == 0:
            continue

        split_ratio = matched_count / total_non_empty
        space_ratio = space_in_pair_count / matched_count if matched_count > 0 else 0

        if split_ratio >= 0.5 and space_ratio >= 0.3:
            splits.append((col_a, col_b))
        elif split_ratio >= 0.5:
            print(f"      SKIP col {col_a}+{col_b}: split={split_ratio:.2f} space_ratio={space_ratio:.2f}", file=sys.stderr)

    return splits


def merge_two_columns(table_data, col_a, col_b):
    new_data = []
    for row in table_data:
        new_row = list(row)
        val_a = str(new_row[col_a]) if new_row[col_a] is not None else ""
        val_b = str(new_row[col_b]) if new_row[col_b] is not None else ""

        if val_a and val_b:
            last_char = val_a[-1]
            first_char = val_b[0]
            if last_char.isalnum() and first_char.isalnum():
                new_row[col_a] = val_a + val_b
            else:
                new_row[col_a] = val_a + " " + val_b
        elif val_b:
            new_row[col_a] = val_b

        del new_row[col_b]
        new_data.append(new_row)
    return new_data


def process_table(cursor, table_name):
    cursor.execute(f"PRAGMA table_info([{table_name}])")
    columns = cursor.fetchall()
    col_names = [col[1] for col in columns]

    if 'page_number' in col_names:
        page_idx = col_names.index('page_number')
    else:
        page_idx = len(col_names)

    text_col_indices = [i for i in range(len(col_names)) if i != page_idx and col_names[i] != 'page_number']

    if len(text_col_indices) < 2:
        return False

    cursor.execute(f"SELECT rowid, * FROM [{table_name}] ORDER BY rowid")
    all_rows = cursor.fetchall()
    if len(all_rows) < 2:
        return False

    table_data = [list(row[1:]) for row in all_rows]

    any_merge_done = False
    iteration = 0
    max_iterations = 15

    while iteration < max_iterations:
        iteration += 1
        splits = detect_splits(table_data, text_col_indices)
        if not splits:
            break

        any_merge_done = True
        print(f"    Pass {iteration}: {len(splits)} split(s): {splits}", file=sys.stderr)

        for col_a, col_b in sorted(splits, key=lambda x: -x[1]):
            if col_b >= len(col_names):
                continue

            name_a = col_names[col_a]
            name_b = col_names[col_b]

            table_data = merge_two_columns(table_data, col_a, col_b)

            new_name = f"{name_a}_{name_b}"
            new_name = new_name.strip('_')
            col_names[col_a] = new_name
            del col_names[col_b]

            text_col_indices = [i for i in range(len(col_names)) if i != page_idx and col_names[i] != 'page_number']

            print(f"      Merged [{col_a}] {name_a} + {name_b} -> {new_name}", file=sys.stderr)

    if not any_merge_done:
        return False

    new_col_defs = []
    for name in col_names:
        if name == 'page_number':
            new_col_defs.append(f"[{name}] INTEGER")
        else:
            new_col_defs.append(f"[{name}] TEXT")

    temp_name = f"[{table_name}_merged]"

    try:
        cursor.execute(f"DROP TABLE IF EXISTS {temp_name}")
        create_sql = f"CREATE TABLE {temp_name} ({', '.join(new_col_defs)})"
        cursor.execute(create_sql)

        placeholders = ", ".join(["?"] * len(col_names))
        insert_sql = f"INSERT INTO {temp_name} VALUES ({placeholders})"

        for row in table_data:
            cleaned = [v if v is not None else "" for v in row]
            cursor.execute(insert_sql, cleaned)

        cursor.execute(f"DROP TABLE [{table_name}]")
        cursor.execute(f"ALTER TABLE {temp_name} RENAME TO [{table_name}]")
        return True

    except Exception as e:
        print(f"    ERROR: {e}", file=sys.stderr)
        cursor.execute(f"DROP TABLE IF EXISTS {temp_name}")
        return False


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'cat_%' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Found {len(tables)} cat_* tables to process", file=sys.stderr)

    modified_count = 0
    for table_name in tables:
        try:
            print(f"Processing {table_name}...", file=sys.stderr)
            if process_table(cursor, table_name):
                modified_count += 1
                conn.commit()
                print(f"  -> MODIFIED", file=sys.stderr)
            else:
                conn.rollback()
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            conn.rollback()

    conn.close()
    print(f"\nDone. Modified {modified_count} of {len(tables)} tables.", file=sys.stderr)


if __name__ == "__main__":
    main()
