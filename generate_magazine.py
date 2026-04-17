#!/usr/bin/env python3
"""
Morning Edition – Daily HN Curated Magazine
Fetches Hacker News, curates stories via Claude, renders an editorial HTML magazine.
"""
import html as _hl
import json
import os
from datetime import datetime
from pathlib import Path

import requests
import anthropic

# ─── Config ────────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
TELEGRAM_TOKEN    = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID  = os.environ.get("TELEGRAM_CHAT_ID", "")
PAGES_BASE        = os.environ.get("GITHUB_PAGES_URL", "").rstrip("/")
OUTPUT_DIR        = Path("magazines")

# ─── HN Fetch ──────────────────────────────────────────────────────────────

def fetch_hn(limit: int = 40) -> list[dict]:
    top = requests.get(
        "https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10
    ).json()[:limit]
    stories = []
    for sid in top:
        try:
            item = requests.get(
                f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=5
            ).json() or {}
            if item.get("type") == "story" and item.get("url"):
                stories.append({
                    "id":       item["id"],
                    "title":    item.get("title", ""),
                    "url":      item.get("url", ""),
                    "score":    item.get("score", 0),
                    "comments": item.get("descendants", 0),
                    "hn_url":   f"https://news.ycombinator.com/item?id={item['id']}",
                })
        except Exception:
            pass
    return stories

# ─── Curation via Claude ────────────────────────────────────────────────────

def curate(stories: list[dict]) -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    today  = datetime.now().strftime("%B %d, %Y")
    block  = "\n".join(
        f"{i+1}. [{s['score']}pts] {s['title']}\n   {s['url']}\n   HN: {s['hn_url']}"
        for i, s in enumerate(stories)
    )
    resp = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4096,
        messages=[{"role": "user", "content": f"""You are the editor of Morning Edition — a sharp personal tech briefing for a software developer / AI practitioner.

Date: {today}

MY TASTE:
  LOVE: startups, founder stories, early-stage companies, longevity/healthspan research, biotech that extends life, physical world tech (robotics, manufacturing, energy, climate, construction, agriculture), space, weird science, anything actionable for a builder/founder
  LIKE: venture capital, fundraising, tech-adjacent economics, geopolitics affecting tech, open source, productivity for founders
  SKIP: pure AI dev tools, LLM benchmarks, coding tools, politics, sports, celebrity, real estate, pure finance without tech angle

CANDIDATE STORIES ({len(stories)} total):
{block}

Select exactly 10 stories that best match my taste. For each:
- original_index  (1-based number from the list)
- headline        (punchy magazine rewrite, max 10 words)
- summary         (exactly 2 crisp opinionated sentences — be direct and interesting)
- why_matters     (impact tagline, max 10 words)
- key_stat        (a compelling number/stat string if one exists in the story, else null — e.g. "3.2x faster", "$4B", "40% drop")
- flagged         (true if immediately actionable for an AI/software practitioner today)
- category        AI | CYBER | SCIENCE | HEALTH | TOOLS | FRONTIER | WEIRD | ECONOMICS
- url             (source url)
- hn_url          (HN discussion url)
- score           (HN upvote score)

Also provide: issue_title — a punchy 4-6 word theme capturing today's feel.

Respond with ONLY valid JSON. No markdown fences, no preamble:
{{"issue_title":"...","stories":[{{"original_index":1,"headline":"...","summary":"...","why_matters":"...","key_stat":null,"flagged":false,"category":"AI","url":"...","hn_url":"...","score":0}}]}}"""}]
    )
    raw = resp.content[0].text.strip()
    # Strip any accidental markdown fences
    for prefix in ("```json", "```"):
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
    raw = raw.rstrip("`").strip()
    return json.loads(raw)

# ─── HTML helpers ──────────────────────────────────────────────────────────

def e(s: str) -> str:
    return _hl.escape(str(s))

CAT_COLORS: dict[str, tuple[str, str]] = {
    "AI":        ("#5B21B6", "#EDE9FE"),
    "CYBER":     ("#991B1B", "#FEE2E2"),
    "SCIENCE":   ("#065F46", "#D1FAE5"),
    "HEALTH":    ("#0C4A6E", "#E0F2FE"),
    "TOOLS":     ("#92400E", "#FEF3C7"),
    "FRONTIER":  ("#4C1D95", "#EDE9FE"),
    "WEIRD":     ("#831843", "#FCE7F3"),
    "ECONOMICS": ("#1E3A5F", "#DBEAFE"),
}

def chip(cat: str) -> str:
    bg, fg = CAT_COLORS.get(cat, ("#555", "#eee"))
    return (
        f'<span style="display:inline-block;background:{bg};color:{fg};font-family:var(--sans);'
        f'font-size:0.58rem;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;'
        f'padding:0.28em 0.75em;border-radius:2px">{cat}</span>'
    )

def flag_el(dark: bool = False) -> str:
    c = "#ff6b8a" if dark else "#ff2d55"
    return (
        f'<div style="display:inline-block;border:2px solid {c};color:{c};font-family:var(--sans);'
        f'font-size:0.6rem;font-weight:800;letter-spacing:0.18em;text-transform:uppercase;'
        f'padding:0.25em 0.8em;transform:rotate(-3deg);margin-bottom:1.2rem">⚡ FLAGGED FOR YOU</div>'
    )

def stat_el(stat, dark: bool = False) -> str:
    if not stat:
        return ""
    bg = "rgba(255,255,255,0.14)" if dark else "rgba(0,0,0,0.08)"
    return (
        f'<span style="display:inline-block;background:{bg};font-family:var(--sans);font-size:0.78rem;'
        f'font-weight:700;padding:0.35em 0.95em;border-radius:100px;margin-top:1.2rem">{e(stat)}</span>'
    )

def link_row(url: str, hn_url: str, score: int, dark: bool = False) -> str:
    op = "rgba(255,255,255,0.38)" if dark else "rgba(0,0,0,0.3)"
    return (
        f'<div style="display:flex;gap:1.5rem;margin-top:2.5rem;font-family:var(--sans);font-size:0.72rem;color:{op}">'
        f'<a href="{url}" target="_blank" style="color:inherit;text-decoration:none">↗ Read Story</a>'
        f'<a href="{hn_url}" target="_blank" style="color:inherit;text-decoration:none">HN · {score} pts</a>'
        f'</div>'
    )

# ─── 10 Spread Designs ─────────────────────────────────────────────────────

def sp1(s: dict) -> str:
    """HERO — warm champagne, oversized watermark numeral"""
    return f"""
<section id="s1" style="min-height:100vh;background:#F4E4C0;position:relative;overflow:hidden;display:flex;flex-direction:column;justify-content:center;padding:clamp(3rem,8vw,7rem)">
  <div style="position:absolute;right:-3vw;top:50%;transform:translateY(-50%);font-family:var(--serif);font-weight:900;font-size:35vw;line-height:1;color:#1A0A00;opacity:0.055;user-select:none;pointer-events:none">01</div>
  <div style="position:relative;z-index:2">
    <div style="display:flex;align-items:center;gap:1rem;flex-wrap:wrap;margin-bottom:0.5rem">{chip(s["category"])}{flag_el() if s.get("flagged") else ""}</div>
    <h2 style="font-family:var(--serif);font-size:clamp(2.6rem,6.5vw,5.8rem);font-weight:300;color:#1A0A00;line-height:1.05;max-width:18ch;margin-top:1.2rem">{e(s["headline"])}</h2>
    <p style="font-family:var(--sans);font-size:clamp(1rem,1.4vw,1.2rem);color:#3D2211;line-height:1.75;margin-top:2rem;max-width:58ch">{e(s["summary"])}</p>
    <div style="font-family:var(--sans);font-size:0.82rem;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#8B6914;margin-top:1.5rem">— {e(s["why_matters"])}</div>
    {stat_el(s.get("key_stat"))}
    {link_row(s["url"], s["hn_url"], s["score"])}
  </div>
</section>"""


def sp2(s: dict) -> str:
    """MIDNIGHT — deep navy, cream type, gold rule"""
    return f"""
<section id="s2" style="min-height:100vh;background:#0D0F1A;position:relative;overflow:hidden;display:flex;flex-direction:column;justify-content:center;padding:clamp(3rem,8vw,7rem)">
  <div style="position:absolute;right:3vw;top:-1rem;font-family:var(--serif);font-weight:900;font-size:22vw;line-height:0.85;color:#F5EDD0;opacity:0.07;user-select:none">02</div>
  <div style="position:relative;z-index:2">
    <div style="display:flex;align-items:center;gap:1rem;flex-wrap:wrap;margin-bottom:0.5rem">{chip(s["category"])}{flag_el(dark=True) if s.get("flagged") else ""}</div>
    <div style="width:3.5rem;height:2px;background:#C9A84C;margin:1.5rem 0"></div>
    <h2 style="font-family:var(--serif);font-size:clamp(2.5rem,5.5vw,5rem);font-weight:400;color:#F5EDD0;line-height:1.1;max-width:20ch">{e(s["headline"])}</h2>
    <p style="font-family:var(--sans);font-size:clamp(0.95rem,1.3vw,1.1rem);color:rgba(245,237,208,0.68);line-height:1.8;margin-top:2rem;max-width:58ch">{e(s["summary"])}</p>
    <div style="font-family:var(--sans);font-size:0.7rem;font-weight:700;letter-spacing:0.22em;text-transform:uppercase;color:#C9A84C;margin-top:1.5rem">{e(s["why_matters"])}</div>
    {stat_el(s.get("key_stat"), dark=True)}
    {link_row(s["url"], s["hn_url"], s["score"], dark=True)}
  </div>
</section>"""


def sp3(s: dict) -> str:
    """ROSE ALERT — hot coral, white type, rubber-stamp flagging"""
    return f"""
<section id="s3" style="min-height:100vh;background:#FF2B55;position:relative;overflow:hidden;display:flex;flex-direction:column;justify-content:center;padding:clamp(3rem,8vw,7rem)">
  <div style="position:absolute;right:-4vw;bottom:-2rem;font-family:var(--serif);font-weight:900;font-size:30vw;line-height:0.9;color:#fff;opacity:0.08;user-select:none">03</div>
  <div style="position:absolute;top:2.5rem;right:3vw;font-family:var(--sans);font-size:0.58rem;font-weight:700;letter-spacing:0.25em;text-transform:uppercase;color:rgba(255,255,255,0.45)">No. 03</div>
  <div style="position:relative;z-index:2">
    <div style="display:flex;align-items:center;gap:1rem;flex-wrap:wrap;margin-bottom:0.5rem">
      <span style="display:inline-block;background:rgba(255,255,255,0.2);color:#fff;font-family:var(--sans);font-size:0.58rem;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;padding:0.28em 0.75em;border-radius:2px">{s["category"]}</span>
      {flag_el(dark=True) if s.get("flagged") else ""}
    </div>
    <h2 style="font-family:var(--serif);font-size:clamp(2.6rem,6.5vw,5.8rem);font-weight:700;color:#fff;line-height:1.05;max-width:20ch;margin-top:1.2rem">{e(s["headline"])}</h2>
    <p style="font-family:var(--sans);font-size:clamp(1rem,1.4vw,1.2rem);color:rgba(255,255,255,0.82);line-height:1.75;margin-top:2rem;max-width:58ch">{e(s["summary"])}</p>
    <div style="font-family:var(--sans);font-size:0.8rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:rgba(255,255,255,0.62);margin-top:1.5rem">— {e(s["why_matters"])}</div>
    {stat_el(s.get("key_stat"), dark=True)}
    {link_row(s["url"], s["hn_url"], s["score"], dark=True)}
  </div>
</section>"""


def sp4(s: dict) -> str:
    """TERMINAL — phosphor-green CRT, scanline overlay"""
    scan = "repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,255,64,0.025) 2px,rgba(0,255,64,0.025) 4px)"
    flagged_el = (
        '<div style="display:inline-block;border:1px solid #ff6b6b;color:#ff6b6b;font-family:Courier New,monospace;'
        'font-size:0.65rem;font-weight:700;letter-spacing:0.18em;text-transform:uppercase;'
        'padding:0.25em 0.75em;margin-bottom:1rem">⚡ FLAGGED</div>'
    ) if s.get("flagged") else ""
    return f"""
<section id="s4" style="min-height:100vh;background:#020202;background-image:{scan};position:relative;overflow:hidden;display:flex;flex-direction:column;justify-content:center;padding:clamp(3rem,8vw,7rem)">
  <div style="position:absolute;right:3vw;bottom:3rem;font-family:'Courier New',monospace;font-weight:900;font-size:18vw;line-height:1;color:#33FF00;opacity:0.05;user-select:none">04</div>
  <div style="position:relative;z-index:2">
    <div style="font-family:'Courier New',monospace;font-size:0.72rem;color:rgba(51,255,0,0.5);margin-bottom:1.5rem">[{s["category"]}]  //  {s["score"]} upvotes</div>
    {flagged_el}
    <div style="font-family:'Courier New',monospace;font-size:0.85rem;color:rgba(51,255,0,0.4);margin-bottom:0.4rem">$&gt; ./morning-edition --story 04</div>
    <h2 style="font-family:var(--serif);font-size:clamp(2.2rem,5vw,4.5rem);font-weight:700;color:#33FF00;line-height:1.1;max-width:22ch;text-shadow:0 0 25px rgba(51,255,0,0.3)">{e(s["headline"])}</h2>
    <p style="font-family:'Courier New',monospace;font-size:clamp(0.82rem,1.05vw,0.95rem);color:rgba(51,255,0,0.7);line-height:1.85;margin-top:2rem;max-width:68ch">{e(s["summary"])}</p>
    <div style="font-family:'Courier New',monospace;font-size:0.75rem;color:rgba(51,255,0,0.45);margin-top:1.5rem;border-left:2px solid rgba(51,255,0,0.25);padding-left:1rem"># {e(s["why_matters"])}</div>
    {stat_el(s.get("key_stat"), dark=True)}
    {link_row(s["url"], s["hn_url"], s["score"], dark=True)}
  </div>
</section>"""


def sp5(s: dict) -> str:
    """ACADEMIC — warm parchment, giant drop-cap, Roman numeral V"""
    h = e(s["headline"])
    dropcap = h[0] if h else "A"
    rest    = h[1:] if len(h) > 1 else ""
    return f"""
<section id="s5" style="min-height:100vh;background:#FAF6EE;position:relative;overflow:hidden;display:flex;flex-direction:column;justify-content:center;padding:clamp(3rem,8vw,7rem)">
  <div style="position:absolute;right:5vw;top:50%;transform:translateY(-50%);font-family:var(--serif);font-weight:900;font-style:italic;font-size:18vw;line-height:1;color:#C4A882;opacity:0.22;user-select:none">V</div>
  <div style="position:relative;z-index:2">
    <div style="border-top:1px solid #C4A882;padding-top:1.5rem;margin-bottom:1.5rem;font-family:var(--sans);font-size:0.6rem;letter-spacing:0.22em;text-transform:uppercase;color:#8B7355">Story Five · {s["category"]}</div>
    {flag_el() if s.get("flagged") else ""}
    <h2 style="font-family:var(--serif);font-size:clamp(2.2rem,5vw,4.5rem);font-weight:400;color:#2D1B00;line-height:1.15;max-width:24ch"><span style="float:left;font-family:var(--serif);font-size:4.8em;line-height:0.78;margin-right:0.06em;color:#8B6914;font-weight:700">{dropcap}</span>{rest}</h2>
    <div style="clear:both;height:1.5rem"></div>
    <p style="font-family:var(--sans);font-size:clamp(1rem,1.3vw,1.15rem);color:#3D2B00;line-height:1.9;max-width:62ch">{e(s["summary"])}</p>
    <div style="font-family:var(--serif);font-style:italic;font-size:1.05rem;color:#8B7355;margin-top:1.5rem">&ldquo;{e(s["why_matters"])}&rdquo;</div>
    {stat_el(s.get("key_stat"))}
    {link_row(s["url"], s["hn_url"], s["score"])}
    <div style="border-bottom:1px solid #C4A882;margin-top:3rem"></div>
  </div>
</section>"""


def sp6(s: dict) -> str:
    """BROADSHEET — black & white newspaper grid"""
    return f"""
<section id="s6" style="min-height:100vh;background:#F8F8F6;position:relative;overflow:hidden;padding:clamp(3rem,6vw,5rem);border-top:5px solid #111;display:grid;grid-template-rows:auto 1fr;align-items:start">
  <div style="display:flex;align-items:baseline;gap:1.5rem;border-bottom:2px solid #111;padding-bottom:1.2rem;margin-bottom:2.5rem;flex-wrap:wrap">
    <span style="font-family:var(--serif);font-weight:900;font-size:clamp(4rem,8vw,6.5rem);line-height:1;color:#111">VI</span>
    <div>
      <div style="font-family:var(--sans);font-size:0.58rem;letter-spacing:0.25em;text-transform:uppercase;color:#666;margin-bottom:0.4rem">{s["category"]} · {s["score"]} votes · {s.get("comments", 0)} comments</div>
      {flag_el() if s.get("flagged") else ""}
    </div>
  </div>
  <div style="display:grid;grid-template-columns:55% 1fr;gap:4vw;align-items:start">
    <div>
      <h2 style="font-family:var(--serif);font-size:clamp(2rem,4vw,3.5rem);font-weight:700;color:#111;line-height:1.1">{e(s["headline"])}</h2>
      <div style="width:100%;height:2px;background:#111;margin:1.5rem 0"></div>
      <div style="font-family:var(--sans);font-size:0.78rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#555">{e(s["why_matters"])}</div>
      {stat_el(s.get("key_stat"))}
    </div>
    <div>
      <p style="font-family:var(--sans);font-size:1rem;color:#222;line-height:1.9">{e(s["summary"])}</p>
      {link_row(s["url"], s["hn_url"], s["score"])}
    </div>
  </div>
</section>"""


def sp7(s: dict) -> str:
    """BRUTALIST — acid yellow, raw black edges, giant cropped 7"""
    flagged_el = (
        '<div style="display:inline-block;background:#111;color:#FFEE00;font-family:var(--sans);'
        'font-size:0.6rem;font-weight:800;letter-spacing:0.2em;text-transform:uppercase;'
        'padding:0.35em 0.9em;margin-bottom:1.5rem">⚡ FLAGGED</div>'
    ) if s.get("flagged") else ""
    return f"""
<section id="s7" style="min-height:100vh;background:#FFEE00;position:relative;overflow:hidden;display:flex;flex-direction:column;justify-content:flex-end;padding:clamp(3rem,6vw,5rem);box-shadow:inset 0 0 0 7px #111">
  <div style="position:absolute;top:-4vw;left:-3vw;font-family:var(--serif);font-weight:900;font-size:45vw;line-height:0.85;color:#111;opacity:0.07;user-select:none">7</div>
  <div style="position:absolute;top:0;right:0;width:0;height:0;border-style:solid;border-width:0 10rem 10rem 0;border-color:transparent #111 transparent transparent"></div>
  <div style="position:absolute;top:1.2rem;right:1.2rem;font-family:var(--sans);font-size:0.58rem;font-weight:800;letter-spacing:0.15em;text-transform:uppercase;color:#FFEE00;text-align:right">{s["category"]}</div>
  <div style="position:relative;z-index:2">
    {flagged_el}
    <h2 style="font-family:var(--serif);font-size:clamp(2.5rem,6vw,5.5rem);font-weight:900;color:#111;line-height:1;max-width:20ch">{e(s["headline"])}</h2>
    <div style="width:100%;height:4px;background:#111;margin:1.5rem 0"></div>
    <p style="font-family:var(--sans);font-size:clamp(1rem,1.3vw,1.15rem);color:#111;line-height:1.7;max-width:60ch">{e(s["summary"])}</p>
    <div style="font-family:var(--sans);font-size:0.78rem;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;color:#444;margin-top:1.5rem">{e(s["why_matters"])}</div>
    {stat_el(s.get("key_stat"))}
    {link_row(s["url"], s["hn_url"], s["score"])}
  </div>
</section>"""


def sp8(s: dict) -> str:
    """AZURE — sky-blue gradient, airy circle geometry, optimistic"""
    return f"""
<section id="s8" style="min-height:100vh;background:linear-gradient(145deg,#BFDBFE,#E0F2FE 55%,#F0F9FF);position:relative;overflow:hidden;display:flex;flex-direction:column;justify-content:center;padding:clamp(3rem,8vw,7rem)">
  <div style="position:absolute;right:-10vw;top:50%;transform:translateY(-50%);width:55vw;height:55vw;border-radius:50%;background:rgba(255,255,255,0.4);pointer-events:none"></div>
  <div style="position:absolute;left:3vw;bottom:3rem;font-family:var(--serif);font-weight:900;font-size:16vw;line-height:1;color:#1E40AF;opacity:0.1;user-select:none">08</div>
  <div style="position:relative;z-index:2">
    <div style="font-family:var(--sans);font-size:0.6rem;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;color:#3B82F6;margin-bottom:1rem">{s["category"]} · Issue 8</div>
    {flag_el() if s.get("flagged") else ""}
    <h2 style="font-family:var(--serif);font-size:clamp(2.5rem,5.5vw,5rem);font-weight:300;color:#1E3A5F;line-height:1.1;max-width:22ch;margin-top:0.8rem">{e(s["headline"])}</h2>
    <p style="font-family:var(--sans);font-size:clamp(1rem,1.3vw,1.15rem);color:#1E4D7B;line-height:1.8;margin-top:2rem;max-width:58ch">{e(s["summary"])}</p>
    <div style="font-family:var(--sans);font-size:0.8rem;font-weight:600;letter-spacing:0.08em;color:#3B82F6;margin-top:1.5rem">→ {e(s["why_matters"])}</div>
    {stat_el(s.get("key_stat"))}
    {link_row(s["url"], s["hn_url"], s["score"])}
  </div>
</section>"""


def sp9(s: dict) -> str:
    """NEON — electric cyan on near-black, glow effects"""
    flagged_el = (
        '<div style="display:inline-block;border:1px solid #00F5FF;color:#00F5FF;font-family:var(--sans);'
        'font-size:0.6rem;font-weight:700;letter-spacing:0.18em;text-transform:uppercase;'
        'padding:0.3em 0.8em;margin-bottom:1rem;box-shadow:0 0 12px rgba(0,245,255,0.35)">⚡ FLAGGED</div>'
    ) if s.get("flagged") else ""
    return f"""
<section id="s9" style="min-height:100vh;background:#060614;position:relative;overflow:hidden;display:flex;flex-direction:column;justify-content:center;padding:clamp(3rem,8vw,7rem)">
  <div style="position:absolute;inset:0;background:radial-gradient(ellipse at 30% 50%,rgba(0,245,255,0.05),transparent 65%);pointer-events:none"></div>
  <div style="position:absolute;right:3vw;top:50%;transform:translateY(-50%);font-family:var(--serif);font-weight:900;font-size:22vw;line-height:1;color:#00F5FF;opacity:0.055;user-select:none;text-shadow:0 0 80px rgba(0,245,255,0.4)">09</div>
  <div style="position:relative;z-index:2">
    <div style="font-family:var(--sans);font-size:0.6rem;font-weight:700;letter-spacing:0.28em;text-transform:uppercase;color:#00F5FF;margin-bottom:1rem;opacity:0.75">{s["category"]}</div>
    {flagged_el}
    <h2 style="font-family:var(--serif);font-size:clamp(2.5rem,5.5vw,5rem);font-weight:700;color:#fff;line-height:1.1;max-width:20ch">{e(s["headline"])}</h2>
    <div style="width:3rem;height:2px;background:#00F5FF;margin:1.5rem 0;box-shadow:0 0 8px #00F5FF"></div>
    <p style="font-family:var(--sans);font-size:clamp(0.95rem,1.3vw,1.1rem);color:rgba(255,255,255,0.62);line-height:1.85;max-width:58ch">{e(s["summary"])}</p>
    <div style="font-family:var(--sans);font-size:0.78rem;font-weight:600;letter-spacing:0.08em;color:#00F5FF;margin-top:1.5rem;opacity:0.8">→ {e(s["why_matters"])}</div>
    {stat_el(s.get("key_stat"), dark=True)}
    {link_row(s["url"], s["hn_url"], s["score"], dark=True)}
  </div>
</section>"""


def sp10(s: dict) -> str:
    """FINALE — deep indigo starfield, key stat as giant background"""
    stat = s.get("key_stat")
    stat_bg = ""
    if stat:
        stat_bg = (
            f'<div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);'
            f'font-family:var(--serif);font-weight:900;font-size:clamp(4rem,18vw,15rem);line-height:1;'
            f'color:#fff;opacity:0.07;user-select:none;white-space:nowrap;z-index:1">{e(stat)}</div>'
        )
    return f"""
<section id="s10" style="min-height:100vh;background:radial-gradient(ellipse at 40% 50%,#2D1869,#0F0521 70%);position:relative;overflow:hidden;display:flex;flex-direction:column;justify-content:center;padding:clamp(3rem,8vw,7rem)">
  <div style="position:absolute;inset:0;background-image:radial-gradient(rgba(255,255,255,0.08) 1px,transparent 1px);background-size:44px 44px;pointer-events:none;z-index:0"></div>
  {stat_bg}
  <div style="position:absolute;top:2.5rem;right:3vw;font-family:var(--sans);font-size:0.58rem;font-weight:700;letter-spacing:0.22em;text-transform:uppercase;color:rgba(255,255,255,0.22);z-index:2">10 / 10</div>
  <div style="position:relative;z-index:2">
    <div style="font-family:var(--sans);font-size:0.6rem;font-weight:700;letter-spacing:0.25em;text-transform:uppercase;color:rgba(255,255,255,0.32);margin-bottom:1rem">{s["category"]} · Final Story</div>
    {flag_el(dark=True) if s.get("flagged") else ""}
    <h2 style="font-family:var(--serif);font-size:clamp(2.5rem,6vw,5.5rem);font-weight:300;color:#fff;line-height:1.1;max-width:20ch">{e(s["headline"])}</h2>
    <div style="width:3rem;height:1px;background:rgba(255,255,255,0.3);margin:2rem 0"></div>
    <p style="font-family:var(--sans);font-size:clamp(1rem,1.3vw,1.15rem);color:rgba(255,255,255,0.62);line-height:1.85;max-width:58ch">{e(s["summary"])}</p>
    <div style="font-family:var(--sans);font-size:0.78rem;letter-spacing:0.1em;text-transform:uppercase;color:rgba(255,255,255,0.32);margin-top:1.5rem">{e(s["why_matters"])}</div>
    {stat_el(s.get("key_stat"), dark=True)}
    {link_row(s["url"], s["hn_url"], s["score"], dark=True)}
  </div>
</section>"""


SPREADS = [sp1, sp2, sp3, sp4, sp5, sp6, sp7, sp8, sp9, sp10]

# ─── Full HTML document ─────────────────────────────────────────────────────

def generate_html(data: dict, date_str: str) -> str:
    today_pretty = datetime.now().strftime("%A, %B %d, %Y").upper()
    issue_title  = data["issue_title"]
    stories      = data["stories"][:10]

    # Cover TOC rows
    toc_rows = ""
    for i, s in enumerate(stories):
        flag_icon = " ⚡" if s.get("flagged") else ""
        bg, fg = CAT_COLORS.get(s["category"], ("#555", "#eee"))
        toc_rows += (
            f'<a href="#s{i+1}" style="display:grid;grid-template-columns:2.5rem auto;gap:0.8rem;'
            f'align-items:start;padding:1rem 0;border-bottom:1px solid rgba(255,255,255,0.07);'
            f'text-decoration:none;color:inherit">'
            f'<span style="font-family:var(--serif);font-weight:900;font-size:1.4rem;'
            f'color:rgba(255,255,255,0.22);line-height:1">{str(i+1).zfill(2)}</span>'
            f'<div>'
            f'<span style="display:inline-block;background:{bg};color:{fg};font-family:var(--sans);'
            f'font-size:0.55rem;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;'
            f'padding:0.2em 0.6em;border-radius:2px">{s["category"]}</span>'
            f'<div style="font-family:var(--sans);font-size:0.88rem;color:rgba(255,255,255,0.78);'
            f'margin-top:0.4rem;line-height:1.3">{e(s["headline"])}{flag_icon}</div>'
            f'</div></a>'
        )

    spreads_html = "\n".join(SPREADS[i](s) for i, s in enumerate(stories))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Morning Edition · {date_str}</title>
<meta name="description" content="{e(issue_title)} — Morning Edition {date_str}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;0,9..144,700;0,9..144,900;1,9..144,700&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after {{margin:0;padding:0;box-sizing:border-box}}
:root {{--serif:'Fraunces',serif;--sans:'Inter',sans-serif}}
html {{scroll-behavior:smooth}}
body {{background:#0A0A0A;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}}
a {{text-decoration:none}}
</style>
</head>
<body>

<!-- ░░ COVER ░░ -->
<section style="min-height:100vh;background:#0A0A0A;display:grid;grid-template-rows:auto 1fr auto;padding:clamp(2rem,5vw,4.5rem);position:relative;overflow:hidden">
  <div style="position:absolute;right:-5vw;top:50%;transform:translateY(-65%);font-family:var(--serif);font-weight:900;font-size:55vw;line-height:0.85;color:#fff;opacity:0.02;user-select:none;pointer-events:none">M</div>

  <!-- Masthead -->
  <div style="position:relative;z-index:2;border-bottom:1px solid rgba(255,255,255,0.1);padding-bottom:1.5rem;margin-bottom:3rem;display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:1rem">
    <div style="font-family:var(--serif);font-weight:900;font-size:clamp(1.8rem,4.5vw,3.8rem);letter-spacing:-0.02em;color:#fff">MORNING EDITION</div>
    <div style="font-family:var(--sans);font-size:0.6rem;font-weight:500;letter-spacing:0.22em;text-transform:uppercase;color:rgba(255,255,255,0.35)">{today_pretty}</div>
  </div>

  <!-- Hero title + TOC -->
  <div style="position:relative;z-index:2;display:flex;flex-direction:column;justify-content:center">
    <div style="font-family:var(--sans);font-size:0.58rem;font-weight:700;letter-spacing:0.28em;text-transform:uppercase;color:rgba(255,255,255,0.28);margin-bottom:1.5rem">Today's Issue</div>
    <h1 style="font-family:var(--serif);font-weight:300;font-size:clamp(2.8rem,7.5vw,6.5rem);color:#fff;line-height:1.05;max-width:16ch">{e(issue_title)}</h1>
    <div style="width:3.5rem;height:2px;background:#FF2B55;margin:2.5rem 0"></div>
    <div style="max-width:44rem">{toc_rows}</div>
  </div>

  <!-- Cover footer -->
  <div style="position:relative;z-index:2;margin-top:3rem;padding-top:1.5rem;border-top:1px solid rgba(255,255,255,0.07);font-family:var(--sans);font-size:0.58rem;letter-spacing:0.15em;text-transform:uppercase;color:rgba(255,255,255,0.18);display:flex;justify-content:space-between;flex-wrap:wrap;gap:0.5rem">
    <span>Morning Edition · Curated by Claude, Filtered for You</span>
    <span>10 Stories · Hacker News</span>
  </div>
</section>

{spreads_html}

<!-- ░░ COLOPHON ░░ -->
<section style="min-height:25vh;background:#0A0A0A;display:flex;align-items:center;justify-content:center;padding:4rem 2rem;border-top:1px solid rgba(255,255,255,0.06)">
  <div style="text-align:center">
    <div style="font-family:var(--serif);font-weight:900;font-size:1.8rem;color:rgba(255,255,255,0.12);letter-spacing:-0.02em">MORNING EDITION</div>
    <div style="font-family:var(--sans);font-size:0.58rem;letter-spacing:0.2em;text-transform:uppercase;color:rgba(255,255,255,0.18);margin-top:0.75rem">{today_pretty} · Generated from Hacker News · Curated by Claude</div>
  </div>
</section>

</body>
</html>"""

# ─── Archive index ──────────────────────────────────────────────────────────

def update_index(date_str: str, issue_title: str) -> None:
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest: list[dict] = []
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
        except Exception:
            manifest = []

    # Upsert today's entry
    manifest = [m for m in manifest if m.get("date") != date_str]
    manifest.insert(0, {"date": date_str, "title": issue_title, "file": f"{date_str}.html"})
    manifest.sort(key=lambda x: x["date"], reverse=True)
    manifest_path.write_text(json.dumps(manifest, indent=2))

    # Build cards
    cards = ""
    for m in manifest:
        cards += (
            f'<a href="{m["file"]}" style="display:block;padding:1.2rem 1.5rem;background:rgba(255,255,255,0.04);'
            f'border:1px solid rgba(255,255,255,0.08);border-radius:4px;text-decoration:none;color:inherit;'
            f'transition:background 0.15s">'
            f'<div style="font-family:var(--sans);font-size:0.58rem;letter-spacing:0.2em;text-transform:uppercase;color:rgba(255,255,255,0.32)">{m["date"]}</div>'
            f'<div style="font-family:var(--serif);font-size:1.2rem;font-weight:400;color:#fff;margin-top:0.4rem">{e(m["title"])}</div>'
            f'</a>'
        )

    index = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Morning Edition — Archive</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,900&family=Inter:wght@400;700&display=swap" rel="stylesheet">
<style>*{{margin:0;padding:0;box-sizing:border-box}}:root{{--serif:'Fraunces',serif;--sans:'Inter',sans-serif}}body{{background:#0A0A0A;color:#fff;-webkit-font-smoothing:antialiased;min-height:100vh;padding:clamp(2rem,5vw,4rem)}}a:hover{{background:rgba(255,255,255,0.07)!important}}</style>
</head>
<body>
<div style="max-width:36rem;margin:0 auto">
  <div style="font-family:var(--serif);font-weight:900;font-size:clamp(2rem,5vw,3.5rem);color:#fff;margin-bottom:0.5rem;letter-spacing:-0.02em">MORNING EDITION</div>
  <div style="font-family:var(--sans);font-size:0.6rem;letter-spacing:0.22em;text-transform:uppercase;color:rgba(255,255,255,0.28);margin-bottom:3rem">All Issues</div>
  <div style="display:flex;flex-direction:column;gap:0.75rem">{cards}</div>
</div>
</body>
</html>"""
    (OUTPUT_DIR / "index.html").write_text(index)

# ─── Telegram ───────────────────────────────────────────────────────────────

def send_telegram(msg: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("  (Telegram not configured — skipping)")
        return
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"},
            timeout=10,
        )
        r.raise_for_status()
        print("  Telegram ✓")
    except Exception as ex:
        print(f"  Telegram failed: {ex}")

# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    date_str = datetime.now().strftime("%Y-%m-%d")
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"{date_str}.html"

    print(f"[1/4] Fetching HN…")
    stories = fetch_hn(40)
    print(f"      {len(stories)} stories collected")

    print("[2/4] Curating with Claude…")
    data = curate(stories)
    print(f"      \"{data['issue_title']}\"")
    flagged = [s for s in data["stories"] if s.get("flagged")]
    print(f"      {len(data['stories'])} selected, {len(flagged)} flagged for you")

    print("[3/4] Rendering HTML…")
    html_content = generate_html(data, date_str)
    out_path.write_text(html_content, encoding="utf-8")
    update_index(date_str, data["issue_title"])
    print(f"      Saved → {out_path}  ({len(html_content)//1024}KB)")

    print("[4/4] Telegram…")
    issue_url   = f"{PAGES_BASE}/magazines/{date_str}.html" if PAGES_BASE else str(out_path)
    archive_url = f"{PAGES_BASE}/magazines/" if PAGES_BASE else str(OUTPUT_DIR)
    flag_lines  = "\n".join(f"  ⚡ {s['headline']}" for s in flagged) if flagged else "  None today"

    send_telegram(
        f"📰 *Morning Edition* — {date_str}\n"
        f"_{e(data['issue_title'])}_\n\n"
        f"[Read today's issue →]({issue_url})\n\n"
        f"*Flagged for you:*\n{flag_lines}\n\n"
        f"[Full archive →]({archive_url})"
    )

    print(f"\n✅  {issue_url}")


if __name__ == "__main__":
    main()
