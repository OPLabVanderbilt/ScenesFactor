# Texture Trial Builder

A browser-based tool for building **texture-task** trials (Matching + Oddball) by
selecting image regions from the **STUFF** (materials) and **THINGS** (objects)
datasets, adjusting lightness/saturation/contrast, and exporting finished
**250×250 px** stimulus tiles.

It is **fully static** — no server, no accounts, no database. It runs from a
folder of files and can be hosted on **GitHub Pages** so a collaborator can build
trials in their browser and send back a ZIP.

---

## What it does

- Browse a **category** (algae, aluminium, … for STUFF; artichoke, bacon, … for
  THINGS). Distractors are always drawn from the **same category**.
- Already-used images (from the existing texture spreadsheets) are flagged
  **USED**; images you use this session are flagged **USED•**. Reusing an image is
  **not blocked** — but if you assign one that's used elsewhere, the slot shows a
  **⚠ used elsewhere** warning, and hovering a USED badge or the warning lists where
  it was used (which existing/spreadsheet trial, or which trial this session).
- **Matching trial** = 1 *study* + 3 options (the correct *match* is a second,
  possibly-overlapping crop of the study image; 2 *distractors* are crops from two
  other same-category images).
- **Oddball trial** = 4 tiles: 3 crops of one "same" image + 1 *oddball* crop from
  a different same-category image.
- **Quadrant zoom, not destructive cropping:** you place square crop regions on the
  full preview and set their size — the final tile is rendered from that region.
- **Adjustments** — lightness / saturation / contrast (plus a Grayscale shortcut),
  so texture — not color or brightness — is the cue. Two modes:
  - **All tiles** — one adjustment applied to every tile in the trial.
  - **Per tile** — click a tile in the preview grid to give it its own
    lightness/saturation/contrast. Tiles with a custom adjustment show an `adj` badge.
- **Review** — the "Built trials — review" panel below the workspace shows every
  built trial: each tile at a glance with its role, the **correct answer starred and
  outlined**, and its filename. **Edit** loads a trial back into the workspace to
  change it (it re-adds at the end); **Remove** deletes it.
- **Export ZIP** produces the finished PNGs + a manifest + a used-list for merge-back.

---

## Running it locally

The tool loads `manifest.json` / `used.json` / images with `fetch`, which needs
**http://** (not `file://`). From this folder:

```bash
cd TASKS/texture_task/trial_builder
python3 -m http.server 8899
# open http://localhost:8899
```

(There is also a Claude Code launch config named `trial_builder` on port 8899.)

---

## Export contents

`texture_trials_<n>_<timestamp>.zip`:

```
stimuli/
  t01_algae0012_study.png             # matching study tile (the reference)
  t01_algae0012_part3_match.png       # the MATCH = correct answer (same source as study)
  t01_algae0010_part1_distractor.png  # a distractor
  t01_algae0011_part2_distractor.png  # a distractor
  ...
  t02_algae0001_part1_same.png        # oddball trial: a "same" tile
  t02_algae0002_part2_oddball.png     # the ODDBALL = correct answer
  ...
manifest.json                    # per-trial: task, category, answer_part, adjustment_mode,
                                 #   each tile's role, source image, crop region, and its
                                 #   own adjustments (lightness/saturation/contrast)
used_update.json                 # { dataset: { category: { imagenum: true } } }
```

Filename format: **`t##_category####_part#_role.png`** (the study tile uses `_study`).
`####` is the source-image id (provenance in the name), and **`role` marks the
correct answer**: the `_match` tile (matching) or the `_oddball` tile (oddball) is
the target; the others are `_distractor` / `_same`. The numeric answer key is also
in `manifest.json` (`answer_part`).

> Note: because the answer role is in the filename, don't hand the raw filenames to
> participants in a way they could inspect — use them for building/QA, and let your
> experiment code map them to neutral display names.

---

## Merge-back workflow (export-and-merge)

Because static hosting has no shared database, a collaborator's picks come back in
the ZIP rather than syncing live. To fold them into the master used-list so the
**next** deployment shows them as used:

```bash
cd TASKS/texture_task/trial_builder/prep
python3 merge_used.py /path/to/used_update.json     # updates ../used.json (.bak kept)
```

Then re-deploy the folder. Drop the `stimuli/*.png` into the experiment as usual.

---

## Regenerating the data (`prep/build_data.py`)

`build_data.py` builds `manifest.json`, `used.json`, and the downsized web
previews from the originals in `../texture_image_sets/`.

```bash
cd prep
python3 build_data.py            # manifest + used-list + THINGS previews (fast)
python3 build_data.py --stuff    # ALSO the ~350 MB STUFF previews (slow)
```

- `used.json` is parsed from `Updated_Texture_Spreadsheet.xlsx` and
  `texture_trials_list.xlsx`; references are resolved to their true category by the
  globally-unique file number (fixes spreadsheet misspellings/mis-attributions).
- STUFF previews are ~800 px JPEGs (originals are 3456 px, ~1.7 GB — too large to
  host). 800 px is ample to render a crisp 250 px crop. Originals are never modified.

---

## Deploying to GitHub Pages (later)

1. Put this `trial_builder/` folder in a GitHub repo (its own repo, or a subfolder).
2. Ensure `web_images/` (including the generated STUFF previews) is committed.
3. Enable Pages for the repo/branch; share the resulting URL.
4. The tool works identically online — collaborators build trials and email the ZIP.

> Size note: the STUFF previews are a few hundred MB. That fits GitHub Pages'
> ~1 GB soft limit, but keep an eye on repo size if you add more datasets.
