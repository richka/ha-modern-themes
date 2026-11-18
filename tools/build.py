#!/usr/bin/env python3
"""Expand the anchored theme source into the standalone theme file Home Assistant loads.

``src/modern.src.yaml`` keeps the themes DRY with YAML anchors and merge keys.
Home Assistant's YAML loader reports every overridden merge key as a "duplicate key"
warning, so the shipped file is generated with the merges expanded: eleven complete
theme blocks, no anchors, no merge keys, no warnings.

Usage:
    python tools/build.py          # rewrite themes/modern.yaml
    python tools/build.py --check  # verify the checked-in file is up to date
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "modern.src.yaml"
OUT = ROOT / "themes" / "modern.yaml"

BLOCK_RE = re.compile(r"^([A-Za-z][A-Za-z0-9 _\-]*):(?:\s*&[A-Za-z0-9_]+)?\s*$")
ANCHOR_SUFFIX_RE = re.compile(r":\s*&[A-Za-z0-9_]+\s*$")
TOP_KEY_RE = re.compile(r"^  ([A-Za-z0-9_.\-]+):")
MODE_KEY_RE = re.compile(r"^      ([A-Za-z0-9_.\-]+):")
MODE_RE = re.compile(r"^    (light|dark):\s*$")


def split_blocks(text: str) -> list[tuple[str, list[str]]]:
    """Return (theme_name, raw_lines) for every top-level block, comments excluded."""
    lines = text.split("\n")
    starts = [(i, m.group(1)) for i, line in enumerate(lines) if (m := BLOCK_RE.match(line))]
    blocks = []
    for idx, (start, name) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(lines)
        while end > start and not lines[end - 1].strip():
            end -= 1
        blocks.append((name, lines[start:end]))
    return blocks


def explicit_overrides(lines: list[str]) -> dict[str, dict[str, object]]:
    """Extract only the keys this block sets itself, split by mode."""
    result: dict[str, dict[str, object]] = {"": {}}
    mode: str | None = None
    in_modes = False
    for line in lines[1:]:
        if line.startswith("  ") and not line.startswith("   "):
            key = TOP_KEY_RE.match(line)
            if key:
                in_modes = key.group(1) == "modes"
                mode = None
                if not in_modes:
                    result[""][key.group(1)] = None
            continue
        if not in_modes:
            continue
        mode_match = MODE_RE.match(line)
        if mode_match:
            mode = mode_match.group(1)
            result.setdefault(mode, {})
            continue
        key = MODE_KEY_RE.match(line)
        if key and mode:
            result[mode][key.group(1)] = None
    return result


def format_value(value: object) -> str:
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def expand(base_lines: list[str], name: str, data: dict[str, object], overrides: dict[str, dict[str, object]]) -> list[str]:
    out: list[str] = []
    mode: str | None = None
    in_modes = False

    for index, raw in enumerate(base_lines):
        if index == 0:
            out.append(f"{name}:")
            continue

        line = ANCHOR_SUFFIX_RE.sub(":", raw)

        if not in_modes:
            top = TOP_KEY_RE.match(line)
            if top:
                key = top.group(1)
                if key == "modes":
                    out.append(line)
                    in_modes = True
                    mode = None
                    continue
                if key in overrides[""]:
                    out.append(f"  {key}: {format_value(data[key])}")
                else:
                    out.append(line)
                continue
            out.append(line)
            continue

        if not line.strip():
            out.append(line)
            continue

        mode_match = MODE_RE.match(line)
        if mode_match:
            mode = mode_match.group(1)
            out.append(line)
            continue

        mode_key = MODE_KEY_RE.match(line)
        if mode_key and mode and mode_key.group(1) in overrides.get(mode, {}):
            key = mode_key.group(1)
            out.append(f"      {key}: {format_value(data['modes'][mode][key])}")
            continue

        out.append(line)

    return out


def build() -> str:
    text = SRC.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    blocks = split_blocks(text)
    base_name, base_lines = blocks[0]
    base_data = data[base_name]

    missing = [name for name, _ in blocks if name not in data]
    if missing:
        raise SystemExit(f"block(s) not parsed: {missing}")

    rendered: list[str] = []
    for name, lines in blocks:
        if name == base_name:
            expanded = expand(base_lines, name, base_data, {"": {}})
        else:
            expanded = expand(base_lines, name, data[name], explicit_overrides(lines))
        rendered.extend(expanded)
        rendered.append("")

    banner = "# Generated from src/modern.src.yaml by tools/build.py - do not edit by hand."
    body = "\n".join(rendered).rstrip("\n")
    document = f"{banner}\n{body}\n"

    if "<<:" in document:
        raise SystemExit("merge keys left in the generated output")
    if re.search(r"&\w+", document):
        raise SystemExit("anchors left in the generated output")

    generated = yaml.safe_load(document)
    if generated != data:
        for name in data:
            if generated.get(name) != data[name]:
                left = set((data[name] or {}).keys())
                right = set((generated.get(name) or {}).keys())
                raise SystemExit(
                    f"{name}: expanded theme differs from source "
                    f"(missing keys: {sorted(left - right)}, extra keys: {sorted(right - left)})"
                )
        raise SystemExit("expanded themes differ from source")

    if len(generated) != len(blocks):
        raise SystemExit(f"expected {len(blocks)} themes, generated {len(generated)}")

    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="only verify that themes/modern.yaml is current")
    args = parser.parse_args()

    document = build()
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != document:
            print(f"{OUT} is out of date; run python tools/build.py", file=sys.stderr)
            return 1
        print(f"{OUT} is up to date")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(document, encoding="utf-8", newline="\n")
    themes = yaml.safe_load(document)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(themes)} themes, {len(document.splitlines())} lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
