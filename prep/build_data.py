#!/usr/bin/env python3
"""
Data-prep for the Texture Trial Builder (static GitHub-Pages tool).

Outputs (written into ../ , i.e. the trial_builder/ root the tool is served from):
  manifest.json  -> { "STUFF": {cat: [files...]}, "THINGS": {cat: [files...]} }
  used.json      -> { "STUFF": {cat: {num: [ "match:trial 2", ... ]}}, "THINGS": {...} }
  web_images/STUFF/<cat>/<num>.jpg    (downsized ~PREVIEW_PX previews)   [--stuff only]
  web_images/THINGS/<cat>/<file>.jpg  (copied; already small)

Originals are never modified.

Usage:
  python3 build_data.py                # manifest + used + THINGS previews (fast)
  python3 build_data.py --stuff        # ALSO generate the ~350MB STUFF previews (slow)
"""
import argparse, json, re, shutil, sys
from pathlib import Path
from PIL import Image
from openpyxl import load_workbook

# ---- paths --------------------------------------------------------------
PREP_DIR   = Path(__file__).resolve().parent
BUILDER    = PREP_DIR.parent                      # .../trial_builder
TASK_DIR   = BUILDER.parent                       # .../texture_task
IMG_ROOT   = TASK_DIR / "texture_image_sets"
STUFF_SRC  = IMG_ROOT / "STUFF_enhanced_dataset_3514_images"
THINGS_SRC = IMG_ROOT / "THINGS"
WEB        = BUILDER / "web_images"
XLSX_A     = TASK_DIR / "Updated_Texture_Spreadsheet.xlsx"
XLSX_B     = TASK_DIR / "texture_trials_list.xlsx"

PREVIEW_PX = 800   # long-edge target for STUFF previews
JPEG_Q     = 82

# ---- helpers ------------------------------------------------------------
def norm_cat(name):
    """Normalize a category string to its folder-name form."""
    if name is None:
        return None
    s = str(name).strip().lower()
    s = s.replace(" ", "_")
    return s or None

def norm_num(v):
    """Normalize an image reference to a 4-digit zero-padded string, or None."""
    if v is None:
        return None
    s = str(v).strip()
    m = re.fullmatch(r"0*(\d+)", s)
    if not m:
        return None
    return f"{int(m.group(1)):04d}"

def split_nums(cell):
    """A cell like '0205; 0213' or '325; 327' -> ['0205','0213']."""
    if cell is None:
        return []
    out = []
    for tok in re.split(r"[;,/]+|\s+and\s+|\s+", str(cell)):
        n = norm_num(tok)
        if n:
            out.append(n)
    return out

# ---- 1. manifest --------------------------------------------------------
def list_images(root):
    cats = {}
    for cat_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        files = sorted(f.name for f in cat_dir.iterdir()
                       if f.suffix.lower() in (".jpg", ".jpeg", ".png"))
        if files:
            cats[cat_dir.name] = files
    return cats

def build_manifest():
    manifest = {
        "STUFF":  list_images(STUFF_SRC),
        "THINGS": list_images(THINGS_SRC),
    }
    for ds, cats in manifest.items():
        n = sum(len(v) for v in cats.values())
        print(f"  manifest[{ds}]: {len(cats)} categories, {n} images")
    return manifest

# ---- 2. used-list -------------------------------------------------------
def add_used(used, dataset, cat, num, tag):
    if not cat or not num:
        return
    used.setdefault(dataset, {}).setdefault(cat, {}).setdefault(num, [])
    if tag not in used[dataset][cat][num]:
        used[dataset][cat][num].append(tag)

def parse_used():
    """Collect every image referenced by an existing trial in either spreadsheet."""
    used = {}

    def parse_matching(ws, num_cols, dist_cols, cat_col, trial_col, tag_prefix):
        for row in ws.iter_rows(values_only=True):
            cat = norm_cat(row[cat_col]) if cat_col < len(row) else None
            if not cat or cat in ("material type", "category"):
                continue
            trial = row[trial_col] if trial_col < len(row) else None
            trial = str(trial).strip() if trial is not None else "?"
            for c in num_cols:
                if c < len(row):
                    for n in split_nums(row[c]):
                        add_used(used, "STUFF", cat, n, f"{tag_prefix}:match:{trial}")
            for c in dist_cols:
                if c < len(row):
                    for n in split_nums(row[c]):
                        add_used(used, "STUFF", cat, n, f"{tag_prefix}:distractor:{trial}")

    # -- Updated_Texture_Spreadsheet.xlsx --
    wb = load_workbook(XLSX_A, read_only=True, data_only=True)
    if "matching" in wb.sheetnames:
        # cols: 0 Trial, 1 Material, 2 DB, 3 Match#, 4 Distractor#, ...
        parse_matching(wb["matching"], num_cols=[3], dist_cols=[4],
                       cat_col=1, trial_col=0, tag_prefix="A")
    if "oddball" in wb.sheetnames:
        # cols: 0 Trial, 1 Material, 2 DB, 3 Oddball#, 4 Match#
        for row in wb["oddball"].iter_rows(values_only=True):
            cat = norm_cat(row[1]) if len(row) > 1 else None
            if not cat or cat == "material type":
                continue
            trial = str(row[0]).strip() if row[0] is not None else "?"
            for n in split_nums(row[3] if len(row) > 3 else None):
                add_used(used, "STUFF", cat, n, f"A:oddball:{trial}")
            for n in split_nums(row[4] if len(row) > 4 else None):
                add_used(used, "STUFF", cat, n, f"A:match:{trial}")

    # -- texture_trials_list.xlsx --
    wb2 = load_workbook(XLSX_B, read_only=True, data_only=True)
    if "match trials" in wb2.sheetnames:
        # cols: 0 trial, 1 category, 2 match, 3 distractor1, 4 distractor2
        parse_matching(wb2["match trials"], num_cols=[2], dist_cols=[3, 4],
                       cat_col=1, trial_col=0, tag_prefix="B")
    if "oddball trials" in wb2.sheetnames:
        # cols: 0 trial, 1 category, 2 oddball, 3 distractor
        for row in wb2["oddball trials"].iter_rows(values_only=True):
            cat = norm_cat(row[1]) if len(row) > 1 else None
            if not cat or cat == "category":
                continue
            trial = str(row[0]).strip() if row[0] is not None else "?"
            for n in split_nums(row[2] if len(row) > 2 else None):
                add_used(used, "STUFF", cat, n, f"B:oddball:{trial}")
            for n in split_nums(row[3] if len(row) > 3 else None):
                add_used(used, "STUFF", cat, n, f"B:distractor:{trial}")

    # -- free-text "completed ... (1815 + 1823)" parentheticals in material lists --
    for wb_, sheet in ((wb, "material list"), (wb2, "Sheet1")):
        if sheet not in wb_.sheetnames:
            continue
        for row in wb_[sheet].iter_rows(values_only=True):
            for cell in row:
                if not isinstance(cell, str):
                    continue
                m = re.match(r"\s*([A-Za-z_ ]+?)\s*\((.*?)\)", cell)
                if not m:
                    continue
                cat = norm_cat(m.group(1))
                for n in split_nums(m.group(2)):
                    add_used(used, "STUFF", cat, n, "note:completed")
    return used

def relocate_used(used, manifest):
    """Move any used ref that isn't in its stated category to its TRUE category,
    resolved by globally-unique file number (fixes spreadsheet misspellings /
    mis-attributed materials, e.g. 'zicronium'->zirconium, tar 2140->petroleum)."""
    # global number -> true category (STUFF numbers are unique across the set)
    num2cat = {}
    for cat, files in manifest.get("STUFF", {}).items():
        for f in files:
            num2cat[f.rsplit(".", 1)[0]] = cat
    moved, unresolved = [], []
    for ds in list(used.keys()):
        for cat in list(used[ds].keys()):
            have = set(f.rsplit(".", 1)[0] for f in manifest.get(ds, {}).get(cat, []))
            for num in list(used[ds][cat].keys()):
                if num in have:
                    continue
                true_cat = num2cat.get(num) if ds == "STUFF" else None
                if true_cat and true_cat != cat:
                    tags = used[ds][cat].pop(num)
                    tags.append(f"relocated-from:{cat}")
                    used[ds].setdefault(true_cat, {}).setdefault(num, [])
                    for t in tags:
                        if t not in used[ds][true_cat][num]:
                            used[ds][true_cat][num].append(t)
                    moved.append((num, cat, true_cat))
                else:
                    unresolved.append((ds, cat, num))
    # drop any now-empty categories
    for ds in list(used.keys()):
        for cat in list(used[ds].keys()):
            if not used[ds][cat]:
                del used[ds][cat]
    if moved:
        print(f"  relocated {len(moved)} used refs to true category: {moved}")
    if unresolved:
        print(f"  ! {len(unresolved)} used refs still unresolved: {unresolved}")
    else:
        print("  used refs: all resolved to real files")
    return used

# ---- 3. previews --------------------------------------------------------
def make_stuff_previews(manifest):
    out_root = WEB / "STUFF"
    total = sum(len(v) for v in manifest["STUFF"].values())
    done = 0
    for cat, files in manifest["STUFF"].items():
        d = out_root / cat
        d.mkdir(parents=True, exist_ok=True)
        for f in files:
            dst = d / f
            if dst.exists():
                done += 1; continue
            try:
                im = Image.open(STUFF_SRC / cat / f).convert("RGB")
                im.thumbnail((PREVIEW_PX, PREVIEW_PX), Image.LANCZOS)
                im.save(dst, "JPEG", quality=JPEG_Q)
            except Exception as e:
                print("  ! preview failed", cat, f, e)
            done += 1
            if done % 300 == 0:
                print(f"    STUFF previews {done}/{total}")
    print(f"  STUFF previews: {done}/{total} done")

def copy_things(manifest):
    out_root = WEB / "THINGS"
    for cat, files in manifest["THINGS"].items():
        d = out_root / cat
        d.mkdir(parents=True, exist_ok=True)
        for f in files:
            dst = d / f
            if not dst.exists():
                shutil.copy2(THINGS_SRC / cat / f, dst)
    print("  THINGS previews: copied")

# ---- main ---------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stuff", action="store_true",
                    help="also generate the heavy STUFF previews (~350MB)")
    args = ap.parse_args()

    print("Building manifest...")
    manifest = build_manifest()
    (BUILDER / "manifest.json").write_text(json.dumps(manifest, indent=0))

    print("Parsing used-list from spreadsheets...")
    used = parse_used()
    for ds, cats in used.items():
        n = sum(len(v) for v in cats.values())
        print(f"  used[{ds}]: {len(cats)} categories, {n} images flagged used")
    used = relocate_used(used, manifest)
    (BUILDER / "used.json").write_text(json.dumps(used, indent=0))

    print("Copying THINGS previews...")
    copy_things(manifest)

    if args.stuff:
        print("Generating STUFF previews (slow)...")
        make_stuff_previews(manifest)
    else:
        print("Skipping STUFF previews (pass --stuff to generate).")

    print("Done.")

if __name__ == "__main__":
    main()
