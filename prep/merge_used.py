#!/usr/bin/env python3
"""
Merge a collaborator's exported used_update.json back into the master used.json,
so the next deployment of the trial builder shows their picks as already-used.

Usage:
  python3 merge_used.py path/to/used_update.json [more_updates.json ...]

Writes the merged result back to ../used.json (a .bak copy is kept first).
Reports how many new images were newly flagged as used.
"""
import json, sys, shutil
from pathlib import Path

BUILDER = Path(__file__).resolve().parent.parent
MASTER  = BUILDER / "used.json"

def main(updates):
    master = json.loads(MASTER.read_text()) if MASTER.exists() else {}
    added = 0
    for up_path in updates:
        upd = json.loads(Path(up_path).read_text())
        # used_update.json shape: { dataset: { cat: { num: true } } }
        for ds, cats in upd.items():
            for cat, nums in cats.items():
                dst = master.setdefault(ds, {}).setdefault(cat, {})
                for num in nums:
                    if num not in dst:
                        dst[num] = ["session:collaborator-export"]
                        added += 1
    if MASTER.exists():
        shutil.copy2(MASTER, MASTER.with_suffix(".json.bak"))
    MASTER.write_text(json.dumps(master, indent=0))
    print(f"Merged {len(updates)} update file(s); {added} new images flagged used.")
    print(f"Wrote {MASTER} (backup at {MASTER.with_suffix('.json.bak')}).")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    main(sys.argv[1:])
