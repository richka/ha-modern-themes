"""Generate a neutral, self-contained demo page from the built theme file.

The page exists so the repository can produce screenshots without a running
Home Assistant: no entities, no names, no configuration of any real install.
It only reads `themes/modern.yaml` and writes plain HTML with the theme's own
custom properties on `:root`.

    python tools/demo_page.py --theme "Modern Red" --mode light --out page.html
    python tools/demo_page.py --grid "Modern Blue,Modern Green" --out grid.html

Kinds:
  hero    a dashboard-shaped page (header, sidebar, cards, controls)
  states  the colour families: state-*, label badges, switches, sliders
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
THEME_FILE = ROOT / "themes" / "modern.yaml"


# --------------------------------------------------------------------------- data


def load_theme(name: str) -> tuple[dict[str, str], dict[str, str]]:
    """Return (base+light values, dark values) for one theme."""
    data = yaml.safe_load(THEME_FILE.read_text(encoding="utf-8"))
    if name not in data:
        sys.exit(f"unknown theme {name!r}; choose one of: {', '.join(data)}")
    theme = data[name]
    light = {k: v for k, v in theme.items() if k != "modes"}
    dark = dict(light)
    dark.update(theme["modes"]["dark"])
    light.update(theme["modes"]["light"])
    return light, dark


def css_vars(values: dict[str, str]) -> str:
    lines = [f"  --{key}: {value};" for key, value in sorted(values.items())]
    return "\n".join(lines)


# --------------------------------------------------------------------- fragments

ICON = {
    "bulb": '<svg viewBox="0 0 24 24"><path d="M12 2a7 7 0 0 0-4 12.7V17a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1v-2.3A7 7 0 0 0 12 2Zm-2 18h4v1a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1Z"/></svg>',
    "thermo": '<svg viewBox="0 0 24 24"><path d="M14 14.8V5a2 2 0 1 0-4 0v9.8a4 4 0 1 0 4 0ZM11 19a2 2 0 1 1 0-4 2 2 0 0 1 0 4Z"/></svg>',
    "drop": '<svg viewBox="0 0 24 24"><path d="M12 2.7 6.9 9.6A7 7 0 1 0 17.1 9.6Z"/></svg>',
    "lock": '<svg viewBox="0 0 24 24"><path d="M7 10V7a5 5 0 0 1 10 0v3h1a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1Zm2 0h6V7a3 3 0 0 0-6 0Z"/></svg>',
    "person": '<svg viewBox="0 0 24 24"><path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm0 2c-4 0-7 2.2-7 5v1h14v-1c0-2.8-3-5-7-5Z"/></svg>',
    "gauge": '<svg viewBox="0 0 24 24"><path d="M12 4a9 9 0 0 0-7.8 13.5l1.7-1A7 7 0 1 1 19 12h2A9 9 0 0 0 12 4Zm1 5v5.6l3.4 2-1 1.7L11 15.4V9Z"/></svg>',
    "wifi": '<svg viewBox="0 0 24 24"><path d="M12 18.5 15 15a4.2 4.2 0 0 0-6 0ZM4.9 11.4a10 10 0 0 1 14.2 0l-1.7 1.7a7.6 7.6 0 0 0-10.8 0ZM1.5 8a15 15 0 0 1 21 0l-1.7 1.7a12.6 12.6 0 0 0-17.6 0Z"/></svg>',
    "bolt": '<svg viewBox="0 0 24 24"><path d="M13 2 4 14h6l-1 8 9-12h-6Z"/></svg>',
    "home": '<svg viewBox="0 0 24 24"><path d="M12 3 2 12h3v8h5v-5h4v5h5v-8h3Z"/></svg>',
}


def icon(name: str, cls: str = "") -> str:
    return f'<i class="ic {cls}">{ICON[name]}</i>'


def sidebar() -> str:
    items = [
        ("home", "Overview", True),
        ("bolt", "Energy", False),
        ("wifi", "Network", False),
        ("thermo", "Climate", False),
        ("gauge", "Metrics", False),
    ]
    rows = "".join(
        f'<div class="nav{" sel" if sel else ""}">{icon(ic)}<span>{label}</span></div>'
        for ic, label, sel in items
    )
    return f'<aside class="sidebar"><div class="brand">Modern<span>Themes</span></div>{rows}</aside>'


def header(title: str, tabs: list[str], selected: int = 0) -> str:
    tab_html = "".join(
        f'<div class="tab{" sel" if i == selected else ""}">{t}</div>'
        for i, t in enumerate(tabs)
    )
    return f"""
    <header class="appbar">
      <div class="appbar-title">{title}</div>
      <div class="pills">
        <span class="pill">{icon('thermo')}21.5&deg;C</span>
        <span class="pill">{icon('drop')}48%</span>
        <span class="pill">{icon('wifi')}online</span>
      </div>
    </header>
    <nav class="tabs">{tab_html}</nav>"""


def tile(name: str, state: str, ic: str, *, on: bool = False, note: str = "") -> str:
    cls = "tile on" if on else "tile"
    return f"""
      <div class="{cls}">
        <div class="tile-head">{icon(ic)}<span>{name}</span></div>
        <div class="tile-state">{state}</div>
        <div class="tile-note">{note}</div>
      </div>"""


def rows_card() -> str:
    data = [
        ("Front door", "Locked", "lock", "var(--state-lock-locked-color)"),
        ("Garage", "Open", "lock", "var(--state-lock-unlocked-color)"),
        ("Living room light", "On", "bulb", "var(--state-light-active-color)"),
        ("Alarm", "Disarmed", "home", "var(--state-alarm_control_panel-disarmed-color)"),
        ("Solar", "Unavailable", "bolt", "var(--state-unavailable-color)"),
    ]
    body = "".join(
        f'<div class="row"><span class="row-ic" style="color:{color}">{icon(ic)}</span>'
        f'<span class="row-name">{name}</span>'
        f'<span class="row-state" style="color:{color}">{state}</span></div>'
        for name, state, ic, color in data
    )
    return f'<section class="card"><h2>Devices</h2>{body}</section>'


def thermostat_card() -> str:
    return """
      <section class="card thermo-card">
        <h2>Heating</h2>
        <div class="thermo">
          <div class="thermo-ring"><div class="thermo-core">
            <div class="thermo-mode">Heating</div>
            <div class="thermo-value">21&deg;C</div>
            <div class="thermo-target">target 21.5&deg;C</div>
          </div></div>
        </div>
        <div class="seg">
          <span class="seg-btn sel">Heat</span><span class="seg-btn">Cool</span>
          <span class="seg-btn">Auto</span><span class="seg-btn">Off</span>
        </div>
      </section>"""


def controls_card() -> str:
    return """
      <section class="card">
        <h2>Controls</h2>
        <label class="ctl"><span>Brightness</span>
          <input type="range" min="0" max="100" value="72" class="slider"></label>
        <label class="ctl"><span>Volume</span>
          <input type="range" min="0" max="100" value="35" class="slider"></label>
        <div class="switches">
          <div class="sw"><span>Fan</span><span class="switch on"><i></i></span></div>
          <div class="sw"><span>Presence</span><span class="switch"><i></i></span></div>
        </div>
        <div class="btn-row">
          <button class="btn filled">Turn on</button>
          <button class="btn tonal">Details</button>
          <button class="btn outlined">Cancel</button>
        </div>
        <div class="chips">
          <span class="chip filled">Auto</span>
          <span class="chip active">Away</span>
          <span class="chip">Night</span>
        </div>
      </section>"""


def badges_card() -> str:
    badges = [
        ("success", "Armed"),
        ("warning", "Low battery"),
        ("error", "Offline"),
        ("info", "Update ready"),
    ]
    pills = "".join(f'<span class="badge {k}">{v}</span>' for k, v in badges)
    return f"""
      <section class="card">
        <h2>Badges &amp; links</h2>
        <div class="badges">{pills}</div>
        <p class="prose">A card with body text, a
          <a href="#" class="link">themed link</a> and secondary text for context.
          Everything on this page comes from <code>themes/modern.yaml</code>.</p>
        <table class="table">
          <tr><th>Sensor</th><th>Value</th></tr>
          <tr><td>Outdoor temperature</td><td>4.2 &deg;C</td></tr>
          <tr><td>Energy today</td><td>12.4 kWh</td></tr>
          <tr><td>Water pressure</td><td>1.02 bar</td></tr>
        </table>
      </section>"""


def sparkline() -> str:
    return """
      <svg class="spark" viewBox="0 0 300 70" preserveAspectRatio="none">
        <path class="spark-fill" d="M0,55 L25,50 L50,52 L75,40 L100,44 L125,30 L150,34 L175,22 L200,28 L225,16 L250,24 L275,12 L300,18 L300,70 L0,70 Z"/>
        <path class="spark-line" d="M0,55 L25,50 L50,52 L75,40 L100,44 L125,30 L150,34 L175,22 L200,28 L225,16 L250,24 L275,12 L300,18"/>
      </svg>"""


def hero_page(theme: str, mode: str) -> str:
    light, dark = load_theme(theme)
    values = dark if mode == "dark" else light
    tiles = "".join(
        [
            tile("Hall light", "On", "bulb", on=True, note="80%"),
            tile("Thermostat", "21.5 °C", "thermo", note="heating"),
            tile("Humidity", "48 %", "drop", note="stable"),
            tile("Solar", "640 W", "bolt", note="exporting"),
        ]
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{theme} — {mode}</title>
<style>
:root {{
{css_vars(values)}
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; background: var(--primary-background-color);
  color: var(--primary-text-color);
  font-family: var(--ha-font-family-body); font-size: 14px;
  -webkit-font-smoothing: antialiased;
}}
.app {{ display: grid; grid-template-columns: 220px 1fr; min-height: 100vh; }}
.sidebar {{
  background: var(--sidebar-background-color); border-right: 1px solid var(--divider-color);
  padding: 18px 12px;
}}
.brand {{
  font-family: var(--ha-font-family-heading); font-weight: var(--ha-font-weight-heading);
  font-size: 17px; padding: 4px 10px 18px;
}}
.brand span {{ color: var(--primary-color); }}
.nav {{
  display: flex; align-items: center; gap: 10px; padding: 9px 10px;
  border-radius: var(--ha-border-radius-md); color: var(--sidebar-text-color);
  margin-bottom: 2px;
}}
.nav.sel {{ background: rgba(var(--rgb-primary-color), 0.12); color: var(--sidebar-selected-text-color); font-weight: 600; }}
.ic {{ display: inline-flex; width: 18px; height: 18px; }}
.ic svg {{ width: 100%; height: 100%; fill: currentColor; }}
.main {{ padding: 0 22px 26px; }}
.appbar {{
  display: flex; align-items: center; justify-content: space-between;
  background: var(--app-header-background-color);
  border-bottom: var(--app-header-border-bottom);
  padding: 14px 2px; color: var(--app-header-text-color);
}}
.appbar-title {{
  font-family: var(--ha-font-family-heading); font-size: 22px;
  font-weight: var(--ha-font-weight-heading);
}}
.pills {{ display: flex; gap: 8px; }}
.pill {{
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--chip-background-color); color: var(--primary-text-color);
  padding: 6px 12px; border-radius: 999px; font-size: 13px;
}}
.tabs {{ display: flex; gap: 4px; margin: 10px 0 16px; position: relative; }}
.tab {{
  padding: 8px 14px 10px; color: var(--secondary-text-color);
  border-bottom: 2px solid transparent;
}}
.tab.sel {{
  color: var(--app-header-selection-bar-color); border-bottom-color: var(--app-header-selection-bar-color);
  font-weight: 600;
}}
.grid {{ display: grid; gap: 14px; }}
.tiles {{ grid-template-columns: repeat(4, 1fr); }}
.two {{ grid-template-columns: 1.1fr 1fr; }}
.card, .tile {{
  background: var(--ha-card-background); border: var(--ha-card-border-width) solid var(--ha-card-border-color);
  border-radius: var(--ha-card-border-radius); box-shadow: var(--ha-card-box-shadow);
  padding: 16px;
}}
.card h2 {{
  margin: 0 0 12px; font-size: var(--ha-card-header-font-size);
  color: var(--ha-card-header-color); font-weight: var(--ha-font-weight-heading);
  font-family: var(--ha-font-family-heading);
}}
.tile-head {{ display: flex; align-items: center; gap: 8px; color: var(--secondary-text-color); }}
.tile.on .tile-head {{ color: var(--state-light-active-color); }}
.tile-state {{ font-size: 24px; font-weight: 600; margin-top: 10px; }}
.tile-note {{ color: var(--secondary-text-color); margin-top: 4px; }}
.row {{ display: flex; align-items: center; gap: 10px; padding: 9px 0; border-top: 1px solid var(--divider-color); }}
.row:first-of-type {{ border-top: 0; }}
.row-ic {{ display: inline-flex; width: 20px; height: 20px; }}
.row-ic svg {{ width: 100%; height: 100%; fill: currentColor; }}
.row-name {{ flex: 1; }}
.row-state {{ font-weight: 600; }}
.thermo {{ display: flex; justify-content: center; padding: 6px 0 14px; }}
.thermo-ring {{
  width: 190px; height: 190px; border-radius: 50%;
  background: conic-gradient(from 210deg, var(--primary-color) 0 62%, var(--divider-color) 62% 100%);
  display: grid; place-items: center;
}}
.thermo-core {{
  width: 156px; height: 156px; border-radius: 50%; background: var(--card-background-color);
  display: grid; place-content: center; text-align: center;
}}
.thermo-mode {{ color: var(--state-climate-heat-color); font-weight: 600; }}
.thermo-value {{ font-size: 34px; font-weight: 600; }}
.thermo-target {{ color: var(--secondary-text-color); font-size: 12px; }}
.seg {{ display: flex; background: var(--secondary-background-color); border-radius: var(--ha-border-radius-md); padding: 4px; }}
.seg-btn {{ flex: 1; text-align: center; padding: 7px 0; border-radius: var(--ha-border-radius-sm); color: var(--secondary-text-color); }}
.seg-btn.sel {{ background: var(--primary-color); color: var(--text-primary-color); font-weight: 600; }}
.ctl {{ display: block; margin-bottom: 14px; color: var(--secondary-text-color); }}
.slider {{ width: 100%; margin-top: 8px; accent-color: var(--slider-color); }}
.switches {{ display: flex; gap: 18px; margin-bottom: 14px; }}
.sw {{ display: flex; align-items: center; gap: 8px; }}
.switch {{
  width: 42px; height: 24px; border-radius: 999px; background: var(--switch-unchecked-track-color);
  position: relative; display: inline-block;
}}
.switch i {{
  position: absolute; top: 3px; left: 3px; width: 18px; height: 18px; border-radius: 50%;
  background: var(--switch-unchecked-button-color);
}}
.switch.on {{ background: var(--switch-checked-track-color); }}
.switch.on i {{ left: 21px; background: var(--switch-checked-button-color); }}
.btn-row {{ display: flex; gap: 8px; margin-bottom: 14px; }}
.btn {{ font: inherit; padding: 8px 14px; border-radius: var(--ha-border-radius-md); cursor: pointer; }}
.btn.filled {{ background: var(--primary-color); color: var(--text-primary-color); border: 0; font-weight: 600; }}
.btn.tonal {{ background: rgba(var(--rgb-primary-color), 0.12); color: var(--primary-color); border: 0; }}
.btn.outlined {{ background: transparent; color: var(--primary-color); border: 1px solid var(--outline-color); }}
.chips {{ display: flex; gap: 8px; }}
.chip {{
  padding: 5px 12px; border-radius: 999px; font-size: 13px;
  border: 1px solid var(--outline-color); color: var(--secondary-text-color);
}}
.chip.filled {{ background: var(--ha-assist-chip-filled-container-color); color: var(--primary-color); border-color: transparent; }}
.chip.active {{ background: var(--ha-assist-chip-active-container-color); color: var(--primary-color); border-color: transparent; font-weight: 600; }}
.badges {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }}
.badge {{ padding: 5px 11px; border-radius: var(--ha-border-radius-sm); font-size: 13px; font-weight: 600; }}
.badge.success {{ background: rgba(var(--rgb-success-color), 0.14); color: var(--success-color); }}
.badge.warning {{ background: rgba(var(--rgb-warning-color), 0.16); color: var(--warning-color); }}
.badge.error {{ background: rgba(var(--rgb-error-color), 0.14); color: var(--error-color); }}
.badge.info {{ background: rgba(var(--rgb-info-color), 0.14); color: var(--info-color); }}
.prose {{ color: var(--secondary-text-color); line-height: var(--ha-line-height-normal); }}
.link {{ color: var(--ha-color-text-link); }}
code {{ background: var(--markdown-code-background-color); color: var(--markdown-code-text-color); padding: 1px 5px; border-radius: 4px; }}
.table {{ width: 100%; border-collapse: collapse; background: var(--data-table-background-color); }}
.table th, .table td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--divider-color); }}
.table th {{ background: var(--table-header-background-color); color: var(--secondary-text-color); font-weight: 600; }}
.table tr:last-child td {{ background: var(--table-row-background-color); }}
.spark {{ width: 100%; height: 70px; margin-top: 6px; }}
.spark-line {{ fill: none; stroke: var(--primary-color); stroke-width: 2.5; }}
.spark-fill {{ fill: rgba(var(--rgb-primary-color), 0.14); stroke: none; }}
</style></head>
<body>
<div class="app">
  {sidebar()}
  <div class="main">
    {header("Overview", ["Home", "Energy", "Climate", "Security"])}
    <div class="grid tiles">{tiles}</div>
    <div class="grid two" style="margin-top:14px">
      {thermostat_card()}
      <div class="grid" style="gap:14px">
        {controls_card()}
        <section class="card"><h2>Energy today</h2>{sparkline()}
          <div class="tile-note">peak 1.4 kW · 12.4 kWh used</div>
        </section>
      </div>
    </div>
    <div class="grid two" style="margin-top:14px">
      {rows_card()}
      {badges_card()}
    </div>
  </div>
</div>
</body></html>
"""


def states_page(theme: str, mode: str) -> str:
    light, dark = load_theme(theme)
    values = dark if mode == "dark" else light
    states = [
        ("Light", "on", "state-light-active-color", "bulb"),
        ("Switch", "off", "state-inactive-color", "bolt"),
        ("Lock", "locked", "state-lock-locked-color", "lock"),
        ("Lock", "unlocked", "state-lock-unlocked-color", "lock"),
        ("Person", "home", "state-person-home-color", "person"),
        ("Climate", "heat", "state-climate-heat-color", "thermo"),
        ("Climate", "cool", "state-climate-cool-color", "thermo"),
        ("Sun", "above_horizon", "state-sun-above_horizon-color", "home"),
        ("Sensor", "battery low", "state-sensor-battery-low-color", "gauge"),
        ("Alarm", "triggered", "state-alarm_control_panel-triggered-color", "home"),
        ("Update", "available", "state-update-active-color", "wifi"),
        ("Entity", "unavailable", "state-unavailable-color", "bolt"),
    ]
    cells = "".join(
        f'<div class="st"><span class="st-ic" style="color:var(--{var})">{icon(ic)}</span>'
        f'<span class="st-name">{name}</span>'
        f'<span class="st-state" style="color:var(--{var})">{state}</span></div>'
        for name, state, var, ic in states
    )
    ramp = "".join(
        f'<div class="step" style="--c:var(--ha-color-primary-{step})"><span>{step}</span></div>'
        for step in (5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95)
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{theme} — states ({mode})</title>
<style>
:root {{
{css_vars(values)}
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; padding: 26px; background: var(--primary-background-color);
  color: var(--primary-text-color); font-family: var(--ha-font-family-body); font-size: 14px;
}}
h1 {{ font-family: var(--ha-font-family-heading); font-size: 22px; margin: 0 0 4px; }}
.sub {{ color: var(--secondary-text-color); margin: 0 0 18px; }}
.layout {{ display: grid; grid-template-columns: 1.3fr 1fr; gap: 14px; align-items: start; }}
.card {{
  background: var(--ha-card-background); border: var(--ha-card-border-width) solid var(--ha-card-border-color);
  border-radius: var(--ha-card-border-radius); box-shadow: var(--ha-card-box-shadow); padding: 16px;
}}
.card h2 {{ margin: 0 0 10px; font-size: var(--ha-card-header-font-size); color: var(--ha-card-header-color); }}
.states {{ display: grid; grid-template-columns: 1fr 1fr; gap: 4px 18px; }}
.st {{ display: flex; align-items: center; gap: 9px; padding: 7px 0; border-bottom: 1px solid var(--divider-color); }}
.st-ic {{ display: inline-flex; width: 19px; height: 19px; }}
.st-ic svg {{ width: 100%; height: 100%; fill: currentColor; }}
.st-name {{ flex: 1; color: var(--secondary-text-color); }}
.st-state {{ font-weight: 600; }}
.ramp {{ display: flex; gap: 5px; }}
.step {{
  flex: 1; height: 54px; border-radius: var(--ha-border-radius-sm); background: var(--c);
  display: grid; place-items: end center; padding-bottom: 5px;
  color: rgba(255,255,255,0.9); font-size: 11px; font-weight: 600;
}}
.step:nth-child(n+7) span {{ color: rgba(0,0,0,0.7); }}
.switches {{ display: flex; gap: 16px; align-items: center; margin-top: 14px; flex-wrap: wrap; }}
.switch {{ width: 44px; height: 25px; border-radius: 999px; background: var(--switch-unchecked-track-color); position: relative; display: inline-block; }}
.switch i {{ position: absolute; top: 3px; left: 3px; width: 19px; height: 19px; border-radius: 50%; background: var(--switch-unchecked-button-color); }}
.switch.on {{ background: var(--switch-checked-track-color); }}
.switch.on i {{ left: 22px; background: var(--switch-checked-button-color); }}
.slider {{ width: 100%; margin-top: 12px; accent-color: var(--slider-color); }}
.badges {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 14px; }}
.badge {{ padding: 5px 11px; border-radius: var(--ha-border-radius-sm); font-weight: 600; font-size: 13px; }}
.badge.success {{ background: rgba(var(--rgb-success-color), 0.14); color: var(--success-color); }}
.badge.warning {{ background: rgba(var(--rgb-warning-color), 0.16); color: var(--warning-color); }}
.badge.error {{ background: rgba(var(--rgb-error-color), 0.14); color: var(--error-color); }}
.badge.info {{ background: rgba(var(--rgb-info-color), 0.14); color: var(--info-color); }}
.meta {{ display: flex; justify-content: space-between; color: var(--secondary-text-color); margin-top: 6px; }}
</style></head>
<body>
<h1>{theme} <span style="color:var(--primary-color)">&middot;</span> {mode}</h1>
<p class="sub">State colours, badges, controls and the <code>ha-color-primary</code> ramp — all read from the shipped file.</p>
<div class="layout">
  <section class="card"><h2>State colours</h2><div class="states">{cells}</div></section>
  <div class="grid" style="display:grid;gap:14px">
    <section class="card"><h2>Primary ramp</h2><div class="ramp">{ramp}</div></section>
    <section class="card"><h2>Controls</h2>
      <div class="switches"><span class="switch on"><i></i></span><span>Checked</span>
        <span class="switch"><i></i></span><span>Unchecked</span></div>
      <input type="range" min="0" max="100" value="64" class="slider">
      <div class="badges">
        <span class="badge success">success</span><span class="badge warning">warning</span>
        <span class="badge error">error</span><span class="badge info">info</span>
      </div>
      <div class="meta"><span>accent</span><span style="color:var(--accent-color)">{values['accent-color']}</span></div>
      <div class="meta"><span>primary</span><span style="color:var(--primary-color)">{values['primary-color']}</span></div>
    </section>
  </div>
</div>
</body></html>
"""


def grid_page(themes: list[str], mode: str) -> str:
    panels = []
    for name in themes:
        light, dark = load_theme(name)
        values = dark if mode == "dark" else light
        panels.append(f"""
  <div class="panel" style="{css_vars(values)}">
    <div class="panel-head">
      <div>
        <div class="panel-name">{name}</div>
        <div class="panel-mode">{mode}</div>
      </div>
      <div class="swatch">
        <span style="background:var(--primary-color)"></span>
        <span style="background:var(--accent-color)"></span>
        <span style="background:var(--success-color)"></span>
        <span style="background:var(--warning-color)"></span>
        <span style="background:var(--error-color)"></span>
      </div>
    </div>
    <div class="mini-card">
      <div class="mini-row"><span class="ic-slot" style="color:var(--state-light-active-color)">{icon('bulb')}</span>
        <span>Living room</span><b style="color:var(--state-light-active-color)">On</b></div>
      <div class="mini-row"><span class="ic-slot" style="color:var(--state-lock-locked-color)">{icon('lock')}</span>
        <span>Front door</span><b style="color:var(--state-lock-locked-color)">Locked</b></div>
      <div class="mini-row"><span class="ic-slot" style="color:var(--state-unavailable-color)">{icon('bolt')}</span>
        <span>Solar</span><b style="color:var(--state-unavailable-color)">Unavailable</b></div>
      <div class="mini-ctl">
        <span class="switch on"><i></i></span>
        <input type="range" min="0" max="100" value="70" class="slider">
      </div>
      <div class="mini-btns">
        <button class="btn filled">Turn on</button>
        <button class="btn outlined">Details</button>
        <span class="chip active">Auto</span>
      </div>
    </div>
  </div>""")
    body = "".join(panels)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Theme grid</title>
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 0; padding: 22px; background: #ECECEE; font-family: system-ui, sans-serif; color: #16181a; }}
h1 {{ font-size: 19px; margin: 0 0 16px; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
.panel {{ border-radius: 20px; padding: 18px; box-shadow: 0 10px 30px rgba(0,0,0,0.12); }}
.panel-head {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
.panel-name {{ font-size: 17px; font-weight: 700; }}
.panel-mode {{ opacity: 0.7; font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }}
.swatch {{ display: flex; gap: 6px; }}
.swatch span {{ width: 18px; height: 18px; border-radius: 50%; display: inline-block; }}
.mini-card {{ background: var(--ha-card-background); border: var(--ha-card-border-width) solid var(--ha-card-border-color);
  border-radius: var(--ha-card-border-radius); box-shadow: var(--ha-card-box-shadow); padding: 14px; color: var(--primary-text-color);
  font-family: var(--ha-font-family-body); }}
.mini-row {{ display: flex; align-items: center; gap: 9px; padding: 7px 0; border-bottom: 1px solid var(--divider-color); }}
.mini-row b {{ margin-left: auto; }}
.ic-slot {{ display: inline-flex; width: 18px; height: 18px; }}
.ic-slot svg {{ width: 100%; height: 100%; fill: currentColor; }}
.mini-ctl {{ display: flex; align-items: center; gap: 12px; margin-top: 12px; }}
.switch {{ width: 40px; height: 23px; border-radius: 999px; background: var(--switch-unchecked-track-color); position: relative; display: inline-block; flex: none; }}
.switch i {{ position: absolute; top: 3px; left: 3px; width: 17px; height: 17px; border-radius: 50%; background: var(--switch-unchecked-button-color); }}
.switch.on {{ background: var(--switch-checked-track-color); }}
.switch.on i {{ left: 20px; background: var(--switch-checked-button-color); }}
.slider {{ width: 100%; accent-color: var(--slider-color); }}
.mini-btns {{ display: flex; gap: 8px; align-items: center; margin-top: 12px; }}
.btn {{ font: inherit; font-size: 13px; padding: 7px 13px; border-radius: var(--ha-border-radius-md); cursor: pointer; }}
.btn.filled {{ background: var(--primary-color); color: var(--text-primary-color); border: 0; font-weight: 600; }}
.btn.outlined {{ background: transparent; color: var(--primary-color); border: 1px solid var(--outline-color); }}
.chip {{ padding: 5px 12px; border-radius: 999px; font-size: 13px; font-weight: 600;
  background: var(--ha-assist-chip-active-container-color); color: var(--primary-color); }}
</style></head>
<body>
<h1>Modern Themes — {len(themes)} variants ({mode} mode)</h1>
<div class="grid">{body}
</div>
</body></html>
"""


# ------------------------------------------------------------------------- cli


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theme", default="Modern Red")
    parser.add_argument("--mode", choices=("light", "dark"), default="light")
    parser.add_argument("--kind", choices=("hero", "states"), default="hero")
    parser.add_argument("--grid", help="comma-separated themes for a comparison page")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    if args.grid:
        html = grid_page([t.strip() for t in args.grid.split(",")], args.mode)
    elif args.kind == "states":
        html = states_page(args.theme, args.mode)
    else:
        html = hero_page(args.theme, args.mode)

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8", newline="\n")
    print(f"wrote {out} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
