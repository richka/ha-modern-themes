# Issues — Modern Themes

Review of `ha-modern-themes` against the Home Assistant frontend and the theme
documentation.

- **Commit:** the commit that adds this file — `git log -1 --format=%h -- ISSUES.md`
  (code baseline `b2d0f69`)
- **Checked against:** HA **2026.11.2**; `home-assistant/frontend` at
  `tags/20261028.6` (the frontend tag that release ships) and `heads/master`; the
  running configuration through its Samba mount `Z:\www`, read on 2026-11-24
- **Scope:** a native **Marketplace** theme repository. No Python runs inside Home
  Assistant; the scripts under `tools/` only build and check the files here.

References use YAML keys and file names rather than line numbers: theme keys are
stable identifiers and `themes/modern.yaml` is regenerated.

| # | Issue | Type | Severity | Status |
|---|---|---|---|---|
| [1](#issue-1) | README claims are not enforced by the build | `compliance` | medium | fixed |
| [2](#issue-2) | Legacy families are partly proven, mostly assumed | `docs` | low | fixed (wording) |
| [3](#issue-3) | Twenty variables had no reader | `cleanup` | low | fixed (10 removed, 10 kept) |
| [4](#issue-4) | `hacs.json` does not ask HACS to render the README | `packaging` | low | wontfix |
| [5](#issue-5) | Two dated claims are unverified | `docs` | low | fixed |

## Method

A theme cannot fail loudly. An unknown variable becomes a CSS custom property
that nothing reads, so "is this name still useful" is the only question worth
asking — and it cannot be answered by comparing against declarations.

Comparing the theme with the variables the frontend *declares*
(`src/resources/theme/**`) produces errors in both directions:

- **False dead.** `--dialog-backdrop-filter` is not declared by the theme sources
  but is read in `src/components/ha-dialog.ts` as a legacy fallback:
  `var(--ha-dialog-scrim-backdrop-filter, var(--dialog-backdrop-filter, none))`.
- **False dead.** `--app-header-edit-background-color` is read in
  `src/panels/lovelace/hui-root.ts`, `hui-editor.ts` and
  `components/hui-card-options.ts`; `--app-header-selection-bar-color` is the
  first fallback of `--ha-tab-indicator-color` in `hui-root.ts`. Neither is
  declared by the theme sources.
- **False dead.** `--font-stack` is read by this repository's own dashboard CSS
  (`www/floorplan-namo.css`) — a local alias, not a leftover.
- **False dead.** `--lovelace-background` is read through
  `getPropertyValue("--lovelace-background")` in
  `src/panels/lovelace/views/hui-view-background.ts`, which a `var(--` search
  cannot see.
- **False alive.** A declaration can exist for a token nothing consumes.

The check therefore looks for read signals in the frontend source and in the local
configuration:

1. `var(--name` — a literal read, including the argument on the next line;
2. `getPropertyValue("--name")` — programmatic access;
3. runtime construction, in two shapes: `--state-${domain}-${stateKey}-color` in
   `src/common/entity/state_color.ts`, and `` `rgb-${key}` `` in
   `src/common/dom/apply_themes_on_element.ts`, which has no leading `--` at all.
   No literal search can find the final names of either.

`setProperty("--name")` is **not** a read. It stores a value on an element, which
actually overrides whatever the theme set. Counting it as a consumer would hide a
dead name, so the checker skips it; an earlier pass counted it and was wrong.

Two traps found while doing this, worth recording:

- **Substring matching lies.** `card-title-font-size` appeared to be used because
  it is a substring of `ha-heading-card-title-font-size`. Exact-name matching is
  required.
- **Vendor tokens live outside `src/`.** `--wa-*` and `--mdc-*` belong to
  component libraries whose stylesheets are not part of this source tree, so a
  search here can see them neither as read nor as dead.

Result on the current theme (263 names), as the checker reports it without
`--extra`:

| Bucket | Count |
|---|---|
| Read by the frontend (`var(--…)` or `getPropertyValue`) | 137 |
| Recorded external consumer (`font-stack`) | 1 |
| Belong to a runtime-built family (`state-*`, `rgb-*`) | 69 |
| Belong to a vendor/legacy family consumed outside `src/` | 46 |
| Declared by the frontend, read by nothing | 10 |
| Referenced nowhere at all | 0 |
| **Total** | **263** |

Pointing the checker at the **running** configuration
(`--extra Z:\www`) moves two names from "assumed" to "proven": `font-stack`
(this repository's floorplan CSS) and `slider-color` (Mushroom).

> **Trap, recorded after pass 1.** That run must use the configuration the server
> actually loads. An earlier pass pointed `--extra` at a stale copy,
> `D:\Projects\HA\www`, and proved nine names — including `paper-item-icon-color`
> for button-card and `swiper-theme-color` for swipe-card. Those cards are not
> installed on the server, and the running configuration proved only two. A copy
> of `www/` is not the configuration.

## Issue 1

**README claims are not enforced by the build** — fixed

- **Labels:** `compliance`
- **Where:** `tools/build.py`, `README.md`

### Problem

`build.py` proved that the shipped file matches the source (`generated == data`)
and that the theme count matches the number of blocks. It did not prove the
properties the README sells:

- every variant carries the full `ha-color-primary-05 … -95` ramp,
- every variant defines both `modes: light` and `modes: dark`,
- the README table matches the file.

Deleting a ramp step from `src/modern.src.yaml` still produced a file equal to its
source, so CI stayed green while two README claims became false.

### Fix applied

`build()` now asserts, for every generated theme:

- `modes` is exactly `{light, dark}`;
- all eleven `ha-color-primary-*` steps are present;
- the top-level key set is identical to the base variant;
- the `light` and `dark` key sets are identical to the base variant's.

The variant table in `README.md` is generated between
`<!-- BEGIN VARIANTS -->` / `<!-- END VARIANTS -->` from the same data, so it
cannot drift. `--check` verifies both the theme file and the table.

### Acceptance

- Removing one ramp step from `src/modern.src.yaml` makes `python tools/build.py --check` fail.
- Removing `dark` from one variant fails the same way.
- Editing a color in the table makes `--check` fail.
- CI still runs one command.

---

## Issue 2

**Legacy families are partly proven, mostly assumed** — fixed by narrowing the wording

- **Labels:** `docs`
- **Where:** `themes/modern.yaml`, `README.md` ("Legacy tokens")

### Problem

`README.md` said the `paper-*`, `mdc-*` and Material variables are there "so older
cards and dialogs match the modern look". That reads as a guarantee.

### What is actually proven

Against the **running** configuration (`Z:\www`):

| Variable | Read by |
|---|---|
| `font-stack` | `www/floorplan-namo.css` |
| `slider-color` | `lovelace-mushroom/mushroom.js` |

Everything else in the vendor/legacy bucket (45 names) is **assumed**: `--wa-*`
and `--mdc-*` belong to component libraries whose stylesheets are not in the
frontend source tree, and cards that are not installed here could read the rest.

### Fix applied

The README no longer implies verification. It now says the legacy names are kept
because third-party cards still read them, names two examples, and states that the
frontend itself no longer declares them. The baseline file repeats that this is a
deliberate compatibility layer, not a verified set.

---

## Issue 3

**Twenty variables had no reader** — fixed; ten removed, ten kept on purpose

- **Labels:** `cleanup`
- **Where:** `src/modern.src.yaml`, `themes/modern.yaml`, `tools/vars_baseline.txt`

### Problem

Two groups of ten had no reader in the frontend or in the running configuration.

### Fix applied

**Removed** — no read, no declaration, no local consumer. These were legacy names
with no justification:

```
accent-text-color                  body-font-size
card-title-font-size               card-title-font-weight
dark-theme-disabled-color          light-theme-disabled-color
ha-card-header-font-weight         ha-card-header-letter-spacing
hue-primary-color                  sidebar-selected-background-color
```

`hue-primary-color` in particular came from the Metrology-era conventions this
project says it does not reuse.

**Kept** — declared by the frontend, read by nothing today:

```
chip-background-color              darker-primary-color
ha-color-surface-lower             ha-color-text-link
ha-font-family-longform            ha-font-weight-action
ha-font-weight-body                ha-font-weight-heading
outline-hover-color                sidebar-selected-text-color
```

These exist on purpose as part of the frontend's theming surface. Removing them
would save nothing and could silently change a third-party card that starts
reading one. They stay in `tools/vars_baseline.txt` with the reason.

Notes on the ones that are easy to get wrong:

- `ha-card-header-color` **is** read; only the `font-weight` and `letter-spacing`
  siblings were not.
- `card-title-*` is not the same as the `ha-heading-card-title-*` tokens that
  replaced it — the first audit confused them by substring.
- `darker-primary-color` is *written* by `apply_themes_on_element.ts`, so a theme
  value for it is overridden anyway; it is harmless, not useful.

### Acceptance

- `tools/vars_baseline.txt` holds only the ten kept names, each with a reason.
- CI fails on a new unread name and on a baseline entry that stops being unread
  (`--strict-baseline`).
- Removing `dark-theme-disabled-color` and its siblings changed no reader, so the
  theme renders identically.

---

## Issue 4

**`hacs.json` does not ask HACS to render the README** — wontfix

- **Labels:** `packaging`
- **Where:** `hacs.json`

### Why this is not a defect

`render_readme` is a HACS-only key. This repository targets the native Marketplace,
which reads `hacs.json` as its repository manifest
(`homeassistant/components/marketplace/repositories/base.py`,
`RepositoryManifest.from_dict`) and **silently skips keys it does not know**:

```python
if (validator := REPOSITORY_MANIFEST_VALUES.get(key)) is None:
    continue
```

The model accepts `content_in_root`, `filename`, `hacs`, `hide_default_branch`,
`homeassistant`, `manifest`, `name`, `persistent_directory` and `zip_release`.
Adding `render_readme` would change nothing in the Marketplace and only re-add a
dependency on a tool this project does not use.

### Decision

Keep `hacs.json` as `{name, homeassistant}`. The file itself is required — the
Marketplace refuses a repository without it — but its name is a leftover of the
format, which is why the README says so explicitly.

---

## Issue 5

**Two dated claims are unverified** — fixed

- **Labels:** `docs`
- **Where:** `README.md` (Requirements, Installation)

### Problem

Two sentences were checkable against release history and were not checked anywhere.

### Fix applied

Both now link their evidence instead of carrying a bare date:

- `--ha-color-*` — the README links the frontend file at
  `20250806.0`, the tag shipped with HA 2025.8. Verified against
  `2025.7.4 → frontend 20250702.3` (no such file) and
  `2025.8.0 → frontend 20250806.0` (present).
- Marketplace — the README links
  `core/tree/2026.11.2/homeassistant/components/marketplace`. Verified present at
  `2026.11.2` and absent at `2026.10.0`.

The wording also changed from "the release where it appeared" to "first appears in
the frontend shipped with 2025.8", which is what was actually checked.

---

## Verified

Checked at the commit that adds this file:

- `python tools/build.py --check`: the shipped file matches the source, the README
  table matches the file, the ramp and both modes are present in all 11 variants,
  and every variant has the base variant's key set.
- `python tools/check_vars.py --baseline tools/vars_baseline.txt --strict-baseline`:
  263 variables, 137 read, 1 external, 69 runtime, 46 vendor/legacy, 10 declared
  but unread, 0 referenced nowhere. No new and no stale baseline entries.
- The same run against the pinned `tags/20261028.6` produces identical numbers.
- CI runs that command plus the self-test on push and pull request.
- 11 themes in the source, in the shipped file, and in the README table.
- README table vs YAML: `primary-color`, `accent-color` and `text-primary-color`
  match for all 11 variants (`white` / `black` normalize to `#ffffff` / `#000000`).
- No duplicate keys in the shipped file.
- `--ha-color-primary-*` exists: the frontend maps
  `--primary-color: var(--ha-color-primary-40)`.
- Install instructions match the documentation: `!include_dir_merge_named` works
  recursively and only scans `.yaml` (not `.yml`).
- `hacs.json` `homeassistant: 2025.8.0` matches the README requirement.
- Marketplace theme layout: `ThemeRepository.resolve_content()` requires `.yaml`
  files directly under `themes/`, which is exactly this repository's layout.

## Checked and dismissed

Suspicions that turned out to be wrong — recorded so nobody re-investigates:

- **`state-climate-heat_cool-color` looked like a typo.** The frontend declares
  `state-climate-heat-cool-color` (hyphen), but the lookup in
  `src/common/entity/state_color.ts` builds
  `--state-${domain}-${slugify(state, "_")}-color`, so the underscore form is the
  one that works. The theme is right; the frontend's own hyphenated default is
  unreachable.
- **The install instruction looked broken.** If the Marketplace installs to
  `themes/modern/modern.yaml`, a non-recursive include would miss it. The docs
  state that the `!include_dir_*` options work recursively, so the instruction is
  correct.
- **`dialog-backdrop-filter`, `app-header-edit-background-color`,
  `app-header-selection-bar-color`, `font-stack` looked unused.** All are read:
  the dialog token as a legacy fallback in `ha-dialog.ts`, the two `app-header`
  tokens in `hui-root.ts` and `hui-card-options.ts`, and `font-stack` by this
  configuration's own dashboard CSS.
- **`lovelace-background` looked dead.** It is read via
  `getPropertyValue("--lovelace-background")`, which a `var(--` search cannot see.
- **A variable read only in a multi-line `var()` looked dead.** `var(` and its
  first argument can be on different lines (`var(\n  --name,`), so the search has
  to run over the whole file, not line by line.
- **A variable written with `setProperty` looked alive.** Writing a property is not
  reading it; the checker now excludes those.

## Not checked

- Visual rendering in a browser, in both modes, across all 11 variants
- Which cards that are **not** installed here read the remaining legacy names
- Vendor tokens consumed inside `node_modules`-style bundles (`--wa-*`, `--mdc-*`)
- Typos inside a runtime-built family: `--state-ligth-active-color` matches the
  `state-` prefix and is exempted, so the checker cannot catch a misspelled domain
  or state name
- The Marketplace install path end to end (the layout was checked against its
  source, not by installing)

## Audit history

| Pass | Result |
|---|---|
| 1 | 5 issues. Issues 2 and 3 were derived from frontend *declarations*, which produced both false dead names and false live ones. |
| 2 | Method replaced with read-based detection in frontend source plus local config; the cleanup list shrank from 40 names to 20. |
| 3 | `tools/check_vars.py` and `tools/vars_baseline.txt` added; CI ratcheted on new unread names. |
| 4 | `--extra` re-run against the running configuration instead of a stale `www/` copy; `setProperty` excluded; ten dead names removed; build assertions and the generated README table added; Issue 4 closed; claims linked to their evidence. |

### Lessons

1. **A theme cannot fail loudly.** Validate names against the code that reads
   them, not against a schema or a declaration list.
2. **Four read signals, not one.** `var(--x)` across line breaks,
   `getPropertyValue("--x")`, and runtime-built names (`--state-${...}`,
   `` `rgb-${...}` ``) all count. Writes do not.
3. **Exact names, not substrings.** `card-title-font-size` matched inside
   `ha-heading-card-title-font-size` and looked alive.
4. **Vendor libraries are invisible to a source search.** `--wa-*` and `--mdc-*`
   are consumed outside `src/`, so their absence proves nothing.
5. **Test the configuration that runs, not a copy of it.** The same `--extra` run
   proved nine names against a stale `www/` copy and two against the server.
6. **README claims need the same guard as code.** The build now asserts what the
   file *is* and what the README *promises*.
