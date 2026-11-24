#!/usr/bin/env python3
"""Find theme variables that nothing reads.

A theme cannot fail loudly: an unknown variable becomes a CSS custom property
that no stylesheet consumes, so a typo or a dead token looks exactly like a live
one. This check answers the only useful question — "does anything read this
name?" — by searching the frontend source and any extra directories for read
sites.

Declarations do not count. Comparing against the variables the frontend
*declares* (`src/resources/theme/**`) is wrong in both directions: a name can be
read without being declared (legacy fallbacks, `getPropertyValue`) and declared
without being read. See ISSUES.md, issue 2 and 3.

Three read signals are searched:

1. `var(--name` — a literal read in a stylesheet;
2. `"--name"` / `'--name'` — programmatic access (`getPropertyValue`,
   `setProperty`);
3. runtime construction — `--state-${domain}-${stateKey}-color`, where the final
   name never appears literally. Every prefix found in the source is collected
   and names matching it are reported as runtime-built, not dead.

Usage:
    python tools/check_vars.py                        # report
    python tools/check_vars.py --baseline tools/vars_baseline.txt
    python tools/check_vars.py --extra /path/to/www   # local CSS and cards
    python tools/check_vars.py --strict-baseline      # also fail on stale baseline entries
    python tools/check_vars.py --strict               # fail on any unread name
    python tools/check_vars.py --self-test            # no network

The frontend source is fetched from `--ref` (default `heads/master`). CI pins a
tag so an unrelated frontend commit cannot turn a pull request red; run the
default locally to see what the next release will flag.

The baseline is a ratchet: known-dead names live there with a reason, CI fails on
anything new, and an entry that stops being dead is reported as stale so it can be
removed. Nothing gets quietly accepted.
"""

from __future__ import annotations

import argparse
import re
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

SOURCE_URL = "https://codeload.github.com/home-assistant/frontend/tar.gz/{ref}"
DEFAULT_REF = "heads/master"
CACHE = Path(tempfile.gettempdir()) / "ha-theme-check"
SUFFIXES = {".ts", ".js", ".css"}

# A name built as a template literal: `rgb-${key}` or var(--state-${domain}-...)
TEMPLATE_NAME_RE = re.compile(r"`(--?[a-z0-9_-]*)\$\{")
TEMPLATE_INLINE_RE = re.compile(r"--([a-z0-9_-]+)\$\{")

# Families consumed outside the frontend source tree, so a source search cannot
# see their readers. Keep this list short and justified.
EXTERNAL_PREFIXES = {
    "wa-": "Web Awesome tokens; its stylesheet is not in the frontend source tree",
    "mdc-": "Material component tokens; their stylesheet is not in the source tree",
    "material-": "Material variables read by third-party cards",
    "paper-": "Paper-era variables read by third-party cards",
    "switch-": "old switch variables read by third-party cards",
    "slider-": "slider variables read by Mushroom and vacuum cards",
    "swiper-": "Swiper library tokens",
}

# Exact names with a known reader outside the frontend and outside this repo, so
# CI (which has neither) does not flag them.
EXTERNAL_CONSUMERS = {
    "font-stack": "used by this dashboard's own CSS (www/floorplan-namo.css)",
}


def load_source(refresh: bool, ref: str) -> Path:
    """Return the frontend `src` directory for `ref`, downloading it once per machine."""
    slug = ref.replace("/", "-")
    base = CACHE / f"frontend-{slug}"
    src = base / "src"
    if not refresh and src.is_dir():
        return src

    CACHE.mkdir(parents=True, exist_ok=True)
    archive = CACHE / f"frontend-{slug}.tar.gz"
    url = SOURCE_URL.format(ref=ref)
    print(f"downloading {url} ...", file=sys.stderr)
    request = urllib.request.Request(url, headers={"User-Agent": "theme-check"})
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            archive.write_bytes(response.read())
    except (urllib.error.URLError, TimeoutError) as err:
        raise SystemExit(f"cannot download the frontend source: {err}") from err

    with tarfile.open(archive) as tar:
        if hasattr(tarfile, "data_filter"):
            tar.extractall(base, filter="data")
        else:  # pragma: no cover - Python < 3.12
            tar.extractall(base)

    if not src.is_dir():
        roots = [path for path in base.iterdir() if (path / "src").is_dir()]
        if not roots:
            raise SystemExit(f"unexpected archive layout under {base}: no */src directory")
        src = roots[0] / "src"

    return src


def theme_names(path: Path) -> set[str]:
    """Return every CSS variable name used by the theme."""
    themes = yaml.safe_load(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for theme in themes.values():
        names |= {key for key in theme if key != "modes"}
        for mode in (theme.get("modes") or {}).values():
            names |= set(mode)
    return names


def read_texts(roots: list[Path]) -> list[tuple[str, str]]:
    texts: list[tuple[str, str]] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.suffix in SUFFIXES and path.is_file():
                texts.append(
                    (path.as_posix(), path.read_text(encoding="utf-8", errors="replace"))
                )
    return texts


def runtime_prefixes(texts: list[tuple[str, str]]) -> set[str]:
    """Collect the prefixes of names built with a template literal.

    Two shapes exist in the frontend:

        var(--state-${domain}-${stateKey}-color)     -- inline
        const rgbKey = `rgb-${key}`;                 -- a template literal

    The second one carries no leading `--`, so matching only the first shape
    reported every `rgb-*` variable as dead.
    """
    prefixes: set[str] = set()
    for _, text in texts:
        for match in TEMPLATE_NAME_RE.finditer(text):
            prefixes.add(match.group(1).lstrip("-"))
        for match in TEMPLATE_INLINE_RE.finditer(text):
            prefixes.add(match.group(1))
        # `const rgbKey = `rgb-${key}`` builds --rgb-<theme key> for every key.
        if "rgb-${" in text:
            prefixes.add("rgb-")
    # A one-character or empty prefix matches almost everything and would exempt
    # the whole theme; a CSS variable prefix is hyphenated and specific.
    return {p for p in prefixes if len(p) >= 4 and p.endswith("-")}


def is_read(name: str, texts: list[tuple[str, str]]) -> bool:
    """True when some file reads this exact name.

    The `var(` search runs on the whole file because the argument can be on the
    next line (`var(\n  --name, ...)`). A quoted occurrence counts only when it
    is not a write: `setProperty()` stores a value, it does not consume the
    theme's. Multi-line calls put the quote on its own line, so the two
    neighbouring lines are inspected too.
    """
    pattern = re.compile(rf"var\(\s*--{re.escape(name)}(?![a-z0-9_-])")
    quoted = (f'"--{name}"', f"'--{name}'")
    for _, text in texts:
        if pattern.search(text):
            return True
        if quoted[0] not in text and quoted[1] not in text:
            continue
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if quoted[0] in line or quoted[1] in line:
                window = " ".join(lines[max(0, index - 1) : index + 2])
                if "getPropertyValue" in window or "setProperty" not in window:
                    return True
    return False


def is_declared(name: str, texts: list[tuple[str, str]]) -> bool:
    """True when the frontend defines a default for this name.

    A declaration is not a reader: it is evidence that the token exists on
    purpose, not that anything consumes it. Kept as a separate bucket because a
    declared-but-unread token is usually a public theming API, while a name
    nobody mentions anywhere is almost always a leftover.
    """
    needle = f"--{name}:"
    return any(needle in text for _, text in texts)


def classify(
    names: set[str], texts: list[tuple[str, str]], extra_texts: list[tuple[str, str]]
) -> dict[str, list[str]]:
    dynamic = runtime_prefixes(texts)
    buckets: dict[str, list[str]] = {
        "read": [],
        "read-extra": [],
        "external": [],
        "runtime": [],
        "legacy": [],
        "declared-only": [],
        "unreferenced": [],
    }
    for name in sorted(names):
        if is_read(name, texts):
            buckets["read"].append(name)
        elif is_read(name, extra_texts):
            buckets["read-extra"].append(name)
        elif name in EXTERNAL_CONSUMERS:
            buckets["external"].append(name)
        elif any(name.startswith(prefix) for prefix in dynamic):
            buckets["runtime"].append(name)
        elif any(name.startswith(prefix) for prefix in EXTERNAL_PREFIXES):
            buckets["legacy"].append(name)
        elif is_declared(name, texts):
            buckets["declared-only"].append(name)
        else:
            buckets["unreferenced"].append(name)
    return buckets


def load_baseline(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()
    names: set[str] = set()
    # utf-8-sig: a Windows editor or pipeline may prepend a BOM, and a BOM on the
    # first line turns the first name into "\ufeffname" — present, matched by
    # nothing, reported at night.
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            names.add(line)
    return names


def self_test() -> int:
    """Prove the three read signals without the network."""
    texts = [
        (
            "fake.ts",
            "var(--literal-one);\n"
            'el.style.getPropertyValue("--quoted-two");\n'
            "css`--state-${domain}-${state}-color`;\n"
            "var(--prefix-of-three-extra);\n"
            'el.style.setProperty("--write-only", "1");\n',
        )
    ]
    checks = {
        "literal-one": True,
        "quoted-two": True,
        "prefix-of-three": False,  # exact matching, not substring
        "write-only": False,  # setProperty stores, it does not read
        "never-mentioned": False,
    }
    failures = []
    for name, expected in checks.items():
        actual = is_read(name, texts)
        if actual is not expected:
            failures.append(f"{name}: expected {expected}, got {actual}")

    dynamic = runtime_prefixes(texts)
    if "state-" not in dynamic:
        failures.append(f"runtime prefix not detected: {sorted(dynamic)}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("self-test: ok (literal, quoted, exact-name, runtime prefix, write excluded)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--theme", type=Path, default=Path(__file__).resolve().parents[1] / "themes" / "modern.yaml"
    )
    parser.add_argument(
        "--extra",
        type=Path,
        action="append",
        default=[],
        help="additional directory to search for readers, e.g. a local www/",
    )
    parser.add_argument("--baseline", type=Path, help="known-dead names, one per line")
    parser.add_argument("--refresh", action="store_true", help="re-download the source")
    parser.add_argument(
        "--ref",
        default=DEFAULT_REF,
        help=f"frontend git ref to check against, e.g. tags/20261028.6 (default: {DEFAULT_REF})",
    )
    parser.add_argument(
        "--strict-baseline",
        action="store_true",
        help="fail when a baseline entry is no longer unread instead of only reporting it",
    )
    parser.add_argument(
        "--strict", action="store_true", help="fail on any unread name, baseline or not"
    )
    parser.add_argument("--verbose", action="store_true", help="print every bucket")
    parser.add_argument("--self-test", action="store_true", help="check the signals, no network")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    if not args.theme.exists():
        raise SystemExit(f"theme not found: {args.theme}")

    src = load_source(args.refresh, args.ref)
    texts = read_texts([src])
    extra = read_texts(args.extra)
    names = theme_names(args.theme)
    buckets = classify(names, texts, extra)
    baseline = load_baseline(args.baseline)

    unread = set(buckets["unreferenced"]) | set(buckets["declared-only"])
    new = sorted(unread - baseline)
    stale = sorted(baseline - unread)

    print(f"frontend ref: {args.ref}")
    print(f"theme variables: {len(names)}")
    for label in ("read", "read-extra", "external", "runtime", "legacy"):
        print(f"  {label:14} {len(buckets[label])}")
    print(f"  {'declared-only':14} {len(buckets['declared-only'])}")
    print(f"  {'unreferenced':14} {len(buckets['unreferenced'])}")
    print(f"  {'unread total':14} {len(unread)}  (baseline {len(baseline)})")

    if args.verbose:
        for label, items in buckets.items():
            if items:
                print(f"\n{label}:")
                for name in items:
                    print(f"  {name}")

    if new:
        print("\nunread and not in the baseline:", file=sys.stderr)
        for name in new:
            print(f"  {name}", file=sys.stderr)
        print(
            "\nRemove the name or record the consumer. Only add to the baseline "
            "when the reader lives outside both the frontend and this repository.",
            file=sys.stderr,
        )
        return 1

    if stale:
        print("\nbaseline entries that are no longer unread (remove them):")
        for name in stale:
            print(f"  {name}")
        if args.strict_baseline:
            print("\n--strict-baseline: stale entries are a failure", file=sys.stderr)
            return 1

    if args.strict and unread:
        print(f"\n--strict: {len(unread)} unread name(s)", file=sys.stderr)
        return 1

    print("\nok: no unread variable outside the baseline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
