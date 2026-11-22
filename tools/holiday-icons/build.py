"""Draws the holiday icon set (original art for this project) and writes frontend/src/holidayArt.js.

Run: python3 tools/holiday-icons/build.py [folder-for-svg-files]
Each icon is a 120x120 flat pastel circle; CLIP marks shapes clipped to the main circle.
"""
import json, math, os, re, sys
from pathlib import Path


INK="#475569"; SKIN="#fde2c8"; RED="#f87171"; PINKRED="#fca5a5"; WHITE="#ffffff"
GREEN="#86efac"; TREE="#6fcf97"; BUTTER="#fde68a"; GOLD="#f3c94f"; LILAC="#c4b5fd"
CHEEK="#f9a8d4"; ICE="#e0f2fe"; EDGE="#e5e7eb"; ORANGE="#fdba74"

def eyes(y, dx=11, r=3.2, cx=60, c=INK):
    return f'<circle cx="{cx-dx}" cy="{y}" r="{r}" fill="{c}"/><circle cx="{cx+dx}" cy="{y}" r="{r}" fill="{c}"/>'
def cheeks(y, dx=22, r=5.5, cx=60):
    return f'<g fill="{CHEEK}" opacity=".75"><circle cx="{cx-dx}" cy="{y}" r="{r}"/><circle cx="{cx+dx}" cy="{y}" r="{r}"/></g>'
def smile(y, w=6, cx=60, c=INK):
    return f'<path d="M{cx-w} {y} q{w} {w*0.8} {2*w} 0" stroke="{c}" stroke-width="2.6" stroke-linecap="round" fill="none"/>'
def star(cx, cy, r, ri=None):
    ri = ri or r*0.5; pts=[]
    for i in range(10):
        a = -math.pi/2 + i*math.pi/5; rr = r if i%2==0 else ri
        pts.append(f"{cx+rr*math.cos(a):.1f},{cy+rr*math.sin(a):.1f}")
    return f'<polygon points="{" ".join(pts)}" fill="#fcd34d" stroke="#fcd34d" stroke-width="2" stroke-linejoin="round"/>'
def mirror(d):  # mirror simple "M x y C ..." path across x=60 (numbers in pairs)
    import re; toks = re.sub(r"([A-Za-z])", r" \1 ", d).replace(",", " ").split(); out=[]; xs=True
    for t in toks:
        if t.isalpha(): out.append(t); xs=True; continue
        v=float(t); out.append(f"{120-v:g}" if xs else f"{v:g}"); xs = not xs
    return " ".join(out)

def _unused_icon(name, body):
    clip = f'<clipPath id="c-{name}"><circle cx="60" cy="64" r="50"/></clipPath>'
    body = body.replace("CLIP", f'clip-path="url(#c-{name})"')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="120" height="120"><defs>{clip}</defs>{body}</svg>'

C = '<circle cx="60" cy="64" r="50" fill="{}"/>'
icons = {}

icons["santa"] = (
  f'<path d="M66 18 Q102 2 108 32 L92 42 Z" fill="{RED}"/>'
  + C.format(SKIN) +
  f'<g CLIP><rect x="0" y="0" width="120" height="44" fill="{RED}"/>'
  f'<ellipse cx="60" cy="112" rx="60" ry="44" fill="{WHITE}"/></g>'
  f'<circle cx="60" cy="64" r="50" fill="none" stroke="#e2e8f0" stroke-width="1.5"/>'
  f'<circle cx="108" cy="34" r="8" fill="{WHITE}" stroke="{EDGE}" stroke-width="1.5"/>'
  f'<rect x="10" y="37" width="100" height="13" rx="6.5" fill="{WHITE}" stroke="{EDGE}" stroke-width="1.5"/>'
  + eyes(59) + cheeks(65) +
  f'<ellipse cx="49" cy="74" rx="12" ry="6.5" fill="{WHITE}" transform="rotate(-10 49 74)"/>'
  f'<ellipse cx="71" cy="74" rx="12" ry="6.5" fill="{WHITE}" transform="rotate(10 71 74)"/>'
  f'<circle cx="60" cy="68" r="4.5" fill="{PINKRED}"/>'
  f'<ellipse cx="60" cy="84" rx="4" ry="2.8" fill="{RED}"/>'
)

HAIR="#eef0f4"
icons["mrs-claus"] = (
  f'<circle cx="60" cy="13" r="13" fill="{HAIR}" stroke="{EDGE}" stroke-width="1.5"/>'
  + C.format(SKIN) +
  f'<g CLIP><path d="M0 0 H120 V48 Q100 32 80 42 Q60 28 40 42 Q20 32 0 48 Z" fill="{HAIR}"/>'
  f'<rect x="0" y="100" width="120" height="30" fill="{RED}"/></g>'
  f'<ellipse cx="60" cy="101" rx="20" ry="5" fill="{WHITE}"/>'
  f'<ellipse cx="79" cy="14" rx="7" ry="3.5" fill="{TREE}" transform="rotate(-30 79 14)"/>'
  f'<ellipse cx="81" cy="22" rx="7" ry="3.5" fill="{TREE}" transform="rotate(20 81 22)"/>'
  f'<circle cx="74" cy="19" r="3" fill="{RED}"/><circle cx="76" cy="24" r="3" fill="{RED}"/>'
  + eyes(62, r=2.6) +
  f'<g stroke="{INK}" stroke-width="2" fill="none"><circle cx="49" cy="62" r="8"/><circle cx="71" cy="62" r="8"/><path d="M57 62 h6"/></g>'
  + cheeks(74, dx=24) + smile(80)
)

icons["elf"] = (
  f'<path d="M14 56 L0 40 Q2 66 16 78 Z" fill="{SKIN}"/><path d="M106 56 L120 40 Q118 66 104 78 Z" fill="{SKIN}"/>'
  f'<path d="M12 56 L5 48 Q6 64 13 70 Z" fill="{CHEEK}" opacity=".6"/><path d="M108 56 L115 48 Q114 64 107 70 Z" fill="{CHEEK}" opacity=".6"/>'
  f'<path d="M30 30 Q56 -2 94 8 Q82 18 88 32 Z" fill="{TREE}"/>'
  + C.format(SKIN) +
  f'<g CLIP><rect x="0" y="0" width="120" height="42" fill="{TREE}"/>'
  f'<rect x="0" y="100" width="120" height="30" fill="{TREE}"/>'
  f'<path d="M20 100 L32 112 L44 100 L56 112 L68 100 L80 112 L92 100 L104 112 L104 100 Z" fill="{RED}"/></g>'
  f'<circle cx="95" cy="8" r="6.5" fill="#fcd34d"/>'
  f'<rect x="12" y="37" width="96" height="11" rx="5.5" fill="{RED}"/>'
  + eyes(62) + cheeks(70) + smile(76)
)

icons["snowman"] = (
  C.format(ICE) +
  f'<g CLIP><circle cx="54" cy="58" r="50" fill="{WHITE}"/>'
  f'<rect x="0" y="94" width="120" height="30" fill="{RED}"/>'
  + "".join(f'<rect x="{x}" y="94" width="9" height="30" fill="{GREEN}"/>' for x in (30,54,78)) +
  '</g>'
  f'<circle cx="60" cy="64" r="50" fill="none" stroke="#e2e8f0" stroke-width="1.5"/>'
  f'<g transform="rotate(10 83 104)"><rect x="76" y="96" width="15" height="24" rx="4" fill="{RED}"/><rect x="76" y="106" width="15" height="6" fill="{GREEN}"/></g>'
  f'<rect x="38" y="2" width="44" height="26" rx="4" fill="{INK}"/>'
  f'<rect x="38" y="17" width="44" height="6" fill="{RED}"/>'
  f'<rect x="24" y="24" width="72" height="8" rx="4" fill="{INK}"/>'
  f'<ellipse cx="76" cy="15" rx="5.5" ry="3" fill="{TREE}" transform="rotate(-25 76 15)"/><circle cx="72" cy="18" r="2.6" fill="{RED}"/>'
  + eyes(54, r=4) + cheeks(66, dx=24) +
  f'<path d="M58 61 L82 67 L58 69 Z" fill="{ORANGE}" stroke="{ORANGE}" stroke-width="2" stroke-linejoin="round"/>'
  + "".join(f'<circle cx="{x}" cy="{y}" r="2.3" fill="{INK}"/>' for x,y in ((46,77),(53,81),(60,83),(67,81),(74,77)))
)

DEER="#c9a27e"; ANT="#b98d63"
la = ["M46 24 C40 14 32 9 24 4", "M35 12 C29 13 23 17 17 20", "M41 18 C43 11 43 6 40 1"]
ant = "".join(f'<path d="{d}"/><path d="{mirror(d)}"/>' for d in la)
icons["reindeer"] = (
  f'<g stroke="{ANT}" stroke-width="6" stroke-linecap="round" fill="none">{ant}</g>'
  f'<ellipse cx="14" cy="48" rx="14" ry="7" fill="{DEER}" transform="rotate(-30 14 48)"/>'
  f'<ellipse cx="106" cy="48" rx="14" ry="7" fill="{DEER}" transform="rotate(30 106 48)"/>'
  f'<ellipse cx="13" cy="48" rx="8" ry="3.5" fill="{CHEEK}" transform="rotate(-30 13 48)"/>'
  f'<ellipse cx="107" cy="48" rx="8" ry="3.5" fill="{CHEEK}" transform="rotate(30 107 48)"/>'
  + C.format(DEER) +
  f'<g CLIP><ellipse cx="60" cy="98" rx="36" ry="28" fill="#f3e3cf"/>'
  f'<rect x="0" y="104" width="120" height="20" fill="{RED}"/></g>'
  f'<circle cx="60" cy="109" r="6" fill="#fcd34d"/><path d="M57 110 h6" stroke="{ANT}" stroke-width="1.6"/>'
  + eyes(58, dx=13) + cheeks(72, dx=26) +
  f'<ellipse cx="60" cy="80" rx="9" ry="6.5" fill="#8b5e3c"/><ellipse cx="57" cy="78" rx="3" ry="1.8" fill="#fff" opacity=".6"/>'
  + smile(90, w=5)
)

GING="#e0a96d"; CHOC="#7c4a2d"
icons["gingerbread"] = (
  C.format(GING) +
  f'<circle cx="60" cy="64" r="43" fill="none" stroke="{WHITE}" stroke-width="4" stroke-dasharray="0.1 9" stroke-linecap="round"/>'
  + eyes(58, r=4, c=CHOC) + cheeks(68, dx=23, r=6) +
  f'<path d="M45 72 Q60 86 75 72" stroke="{WHITE}" stroke-width="4" stroke-linecap="round" fill="none"/>'
  f'<path d="M60 108 L45 99 L45 117 Z" fill="{CHEEK}" stroke="{CHEEK}" stroke-width="2" stroke-linejoin="round"/>'
  f'<path d="M60 108 L75 99 L75 117 Z" fill="{CHEEK}" stroke="{CHEEK}" stroke-width="2" stroke-linejoin="round"/>'
  f'<circle cx="60" cy="108" r="4.5" fill="#f472b6"/>'
)

PENG="#5b6b82"
icons["penguin"] = (
  C.format(PENG) +
  f'<g CLIP><g fill="{WHITE}"><circle cx="47" cy="62" r="19"/><circle cx="73" cy="62" r="19"/><ellipse cx="60" cy="82" rx="30" ry="26"/></g>'
  f'<rect x="0" y="98" width="120" height="30" fill="{LILAC}"/>'
  + "".join(f'<rect x="{x}" y="98" width="8" height="30" fill="{WHITE}"/>' for x in (32,56,80)) +
  '</g>'
  f'<g transform="rotate(-10 32 106)"><rect x="25" y="100" width="14" height="20" rx="4" fill="{LILAC}"/><rect x="25" y="110" width="14" height="5" fill="{WHITE}"/></g>'
  + eyes(62, r=3.6) + cheeks(76, dx=22) +
  f'<path d="M54 70 L66 70 L60 78 Z" fill="{ORANGE}" stroke="{ORANGE}" stroke-width="2.5" stroke-linejoin="round"/>'
)

icons["polar-bear"] = (
  f'<path d="M23 30 Q60 -12 97 30" stroke="{LILAC}" stroke-width="6" fill="none" stroke-linecap="round"/>'
  + C.format(ICE) +
  f'<g CLIP><circle cx="54" cy="58" r="50" fill="{WHITE}"/>'
  f'<rect x="0" y="100" width="120" height="30" fill="{GREEN}"/>'
  + "".join(f'<rect x="{x}" y="100" width="8" height="30" fill="{BUTTER}"/>' for x in (34,58,82)) +
  '</g>'
  f'<circle cx="60" cy="64" r="50" fill="none" stroke="#e2e8f0" stroke-width="1.5"/>'
  f'<circle cx="22" cy="32" r="13" fill="{CHEEK}"/><circle cx="98" cy="32" r="13" fill="{CHEEK}"/>'
  f'<circle cx="18" cy="28" r="4" fill="#fff" opacity=".6"/><circle cx="94" cy="28" r="4" fill="#fff" opacity=".6"/>'
  f'<ellipse cx="60" cy="80" rx="19" ry="14" fill="#fef3c7"/>'
  + eyes(60, dx=14, r=3.6) + cheeks(74, dx=27) +
  f'<ellipse cx="60" cy="73" rx="7" ry="5" fill="{INK}"/>'
  f'<path d="M60 78 v4 M54 84 Q60 89 66 84" stroke="{INK}" stroke-width="2.4" stroke-linecap="round" fill="none"/>'
)

icons["tree"] = (
  f'<rect x="51" y="104" width="18" height="14" rx="3" fill="{ANT}"/>'
  + C.format(TREE) +
  f'<g CLIP stroke="{WHITE}" stroke-width="3.5" fill="none" stroke-linecap="round" opacity=".9">'
  f'<path d="M0 44 Q60 72 120 38"/><path d="M0 88 Q60 110 120 80"/></g>'
  + "".join(f'<circle cx="{x}" cy="{y}" r="5" fill="{c}"/>' for x,y,c in ((26,68,RED),(94,64,"#fcd34d"),(38,104,LILAC),(83,101,CHEEK),(60,32,PINKRED)))
  + star(60, 13, 12) + eyes(71, dx=10, r=3) + cheeks(79, dx=19, r=4.5) + smile(78, w=5)
)

icons["ornament"] = (
  f'<circle cx="60" cy="6" r="4" fill="none" stroke="{GOLD}" stroke-width="2.5"/>'
  f'<rect x="47" y="9" width="26" height="12" rx="3" fill="{GOLD}"/>'
  + C.format(PINKRED) +
  f'<g CLIP><rect x="0" y="36" width="120" height="9" fill="{BUTTER}"/><rect x="0" y="94" width="120" height="9" fill="{BUTTER}"/>'
  + "".join(f'<circle cx="{x}" cy="40.5" r="2" fill="{WHITE}"/><circle cx="{x}" cy="98.5" r="2" fill="{WHITE}"/>' for x in range(16,110,12)) +
  '</g>'
  f'<ellipse cx="30" cy="62" rx="4" ry="9" fill="#fff" opacity=".6" transform="rotate(20 30 62)"/>'
  + eyes(66) + cheeks(76, dx=21) + smile(74)
)

wedges = ""
for i in range(0, 8, 2):
    a1 = math.radians(i*45 - 90 + 10); a2 = math.radians((i+1)*45 - 90 + 10)
    p1 = (60+52*math.cos(a1), 64+52*math.sin(a1)); p2 = (60+52*math.cos(a2), 64+52*math.sin(a2))
    wedges += f'<path d="M60 64 Q{60+30*math.cos(a1-0.35):.1f} {64+30*math.sin(a1-0.35):.1f} {p1[0]:.1f} {p1[1]:.1f} L{p2[0]:.1f} {p2[1]:.1f} Q{60+30*math.cos(a2-0.35):.1f} {64+30*math.sin(a2-0.35):.1f} 60 64 Z" fill="{RED}"/>'
icons["peppermint"] = (
  f'<path d="M14 64 L1 48 Q-1 64 1 80 Z" fill="#bae6fd" stroke="#bae6fd" stroke-width="3" stroke-linejoin="round"/>'
  f'<path d="M106 64 L119 48 Q121 64 119 80 Z" fill="#bae6fd" stroke="#bae6fd" stroke-width="3" stroke-linejoin="round"/>'
  + f'<circle cx="60" cy="64" r="50" fill="{WHITE}" stroke="#fecaca" stroke-width="1.5"/>' +
  f'<g CLIP>{wedges}</g>'
  f'<circle cx="60" cy="64" r="20" fill="{WHITE}"/>'
  + eyes(61, dx=8, r=2.8) + cheeks(68, dx=13, r=3.5) + smile(68, w=4)
)

icons["present"] = (
  f'<ellipse cx="43" cy="13" rx="16" ry="9" fill="{BUTTER}" transform="rotate(-20 43 13)"/>'
  f'<ellipse cx="77" cy="13" rx="16" ry="9" fill="{BUTTER}" transform="rotate(20 77 13)"/>'
  f'<ellipse cx="43" cy="14" rx="7" ry="3.5" fill="{GOLD}" transform="rotate(-20 43 14)"/>'
  f'<ellipse cx="77" cy="14" rx="7" ry="3.5" fill="{GOLD}" transform="rotate(20 77 14)"/>'
  + C.format(LILAC) +
  f'<g CLIP>'
  + "".join(f'<circle cx="{x}" cy="{y}" r="4" fill="{WHITE}" opacity=".85"/>' for x,y in ((30,40),(84,36),(26,84),(90,82),(40,104),(80,106),(38,62),(84,58)))
  + f'<rect x="52" y="0" width="16" height="120" fill="{BUTTER}"/><rect x="0" y="66" width="120" height="14" fill="{BUTTER}"/></g>'
  f'<circle cx="60" cy="18" r="7" fill="{GOLD}"/>'
)

# ---- shared extra helpers ----
def heart(cx, cy, s):
    return (f"M{cx} {cy+s*0.85:.1f} C{cx-s*1.5:.1f} {cy-s*0.1:.1f} {cx-s*0.8:.1f} {cy-s*1.25:.1f} {cx} {cy-s*0.45:.1f} "
            f"C{cx+s*0.8:.1f} {cy-s*1.25:.1f} {cx+s*1.5:.1f} {cy-s*0.1:.1f} {cx} {cy+s*0.85:.1f} Z")
RING = '<circle cx="60" cy="64" r="50" fill="none" stroke="#e2e8f0" stroke-width="1.5"/>'
PURPLE="#c4b5fd"; LAV="#ddd6fe"; GOLDL="#fde68a"; TAN="#e8c28e"; BROWN="#b98d63"; PINK="#fbcfe8"; ROSE="#fecdd3"
SKY="#bae6fd"; BLUE="#93c5fd"; MINT="#bbf7d0"; SAGE="#d9f99d"; PEACH="#fed7aa"; SLATE="#5b6b82"; CREAM="#fef3c7"
def face(y=64, dx=11, cy=None, cdx=22, sy=None, w=6, r=3.2):
    return eyes(y, dx, r) + cheeks(cy if cy else y+8, cdx) + smile(sy if sy else y+7, w)
def icy(base_fill=ICE):  # white circle with soft ice shading + ring
    return C.format(base_fill) + f'<g CLIP><circle cx="54" cy="58" r="50" fill="{WHITE}"/></g>' + RING
more = {}

# ================= MARDI GRAS =================
more["mardi-jester"] = (
  f'<path d="M30 38 Q8 30 4 10 Q24 14 40 32 Z" fill="{PURPLE}"/>'
  f'<path d="M90 38 Q112 30 116 10 Q96 14 80 32 Z" fill="{GREEN}"/>'
  f'<path d="M44 30 Q52 8 60 2 Q68 8 76 30 Z" fill="{GOLDL}"/>'
  f'<circle cx="5" cy="10" r="5.5" fill="{GOLD}"/><circle cx="115" cy="10" r="5.5" fill="{GOLD}"/><circle cx="60" cy="4" r="5" fill="{PURPLE}"/>'
  + C.format(SKIN) +
  f'<g CLIP><rect x="0" y="0" width="60" height="42" fill="{PURPLE}"/><rect x="60" y="0" width="60" height="42" fill="{GREEN}"/>'
  f'<rect x="0" y="100" width="120" height="30" fill="{GOLDL}"/>'
  f'<path d="M20 100 L32 112 L44 100 L56 112 L68 100 L80 112 L92 100 L104 112 L104 100 Z" fill="{PURPLE}"/></g>'
  f'<rect x="12" y="37" width="96" height="10" rx="5" fill="{GOLD}"/>'
  f'<path d="M40 70 l3 -4 l3 4 l-3 4 Z" fill="{PURPLE}"/>'
  + face(62)
)
more["mardi-mask"] = (
  f'<ellipse cx="96" cy="22" rx="6" ry="18" fill="{GREEN}" transform="rotate(30 96 22)"/>'
  f'<ellipse cx="106" cy="30" rx="5" ry="15" fill="{PURPLE}" transform="rotate(55 106 30)"/>'
  f'<ellipse cx="86" cy="18" rx="5" ry="15" fill="{GOLD}" transform="rotate(10 86 18)"/>'
  + C.format(LAV) +
  f'<path d="M16 58 Q30 42 60 52 Q90 42 104 58 Q102 84 78 82 Q66 80 60 72 Q54 80 42 82 Q18 84 16 58 Z" fill="{GOLDL}" stroke="{GOLD}" stroke-width="2"/>'
  f'<ellipse cx="40" cy="64" rx="11" ry="7" fill="{PURPLE}"/><ellipse cx="80" cy="64" rx="11" ry="7" fill="{PURPLE}"/>'
  + eyes(64, dx=20, r=3.2) +
  "".join(f'<circle cx="{x}" cy="{y}" r="2.2" fill="{c}"/>' for x,y,c in ((60,60,GREEN),(26,56,GREEN),(94,56,GREEN),(60,30,GOLD),(36,96,GOLD),(84,96,GOLD)))
  + smile(94, w=5)
)
more["mardi-king-cake"] = (
  f'<circle cx="60" cy="64" r="34" fill="none" stroke="{TAN}" stroke-width="32"/>'
  + "".join(f'<circle cx="60" cy="64" r="34" fill="none" stroke="{c}" stroke-width="22" stroke-dasharray="35.6 71.2" stroke-dashoffset="{-35.6*i:.1f}" transform="rotate(-90 60 64)"/>' for i,c in enumerate((PURPLE,GREEN,GOLDL)))
  + f'<circle cx="60" cy="64" r="34" fill="none" stroke="{WHITE}" stroke-width="2.5" stroke-dasharray="6 7" stroke-linecap="round"/>'
  + "".join(f'<circle cx="{60+34*math.cos(a):.1f}" cy="{64+34*math.sin(a):.1f}" r="1.6" fill="{WHITE}"/>' for a in [i*0.5 for i in range(13)])
)
more["mardi-crown"] = (
  C.format(LAV) +
  f'<path d="M28 84 L26 46 L44 60 L60 36 L76 60 L94 46 L92 84 Z" fill="{GOLDL}" stroke="{GOLDL}" stroke-width="3" stroke-linejoin="round"/>'
  f'<circle cx="26" cy="44" r="5" fill="{GOLD}"/><circle cx="60" cy="34" r="5" fill="{GOLD}"/><circle cx="94" cy="44" r="5" fill="{GOLD}"/>'
  f'<rect x="26" y="80" width="68" height="12" rx="4" fill="{GOLD}"/>'
  f'<circle cx="40" cy="86" r="3.5" fill="{PURPLE}"/><circle cx="60" cy="86" r="3.5" fill="{GREEN}"/><circle cx="80" cy="86" r="3.5" fill="{PURPLE}"/>'
  + eyes(66, dx=10, r=3) + cheeks(72, dx=19, r=4.5) + smile(71, w=5)
)
fleur = (f'<path d="M60 26 Q76 48 60 82 Q44 48 60 26 Z"/>'
         f'<path d="M56 70 Q28 74 28 52 Q28 40 40 44 Q34 58 56 62 Z"/><path d="M64 70 Q92 74 92 52 Q92 40 80 44 Q86 58 64 62 Z"/>'
         f'<path d="M54 78 Q50 94 40 92 Q48 86 50 78 Z"/><path d="M66 78 Q70 94 80 92 Q72 86 70 78 Z"/>')
more["mardi-fleur"] = (
  C.format(GREEN) + f'<g fill="{GOLDL}" stroke="{GOLD}" stroke-width="2" stroke-linejoin="round">{fleur}</g>'
  f'<rect x="40" y="68" width="40" height="9" rx="4" fill="{PURPLE}"/>'
)
beads = ""
for k,(c,rx,ry) in enumerate(((PURPLE,40,62),(GREEN,30,50),(GOLD,20,38))):
    n = 13 - 2*k
    for i in range(n):
        a = math.pi*(0.08 + 0.84*i/(n-1))
        beads += f'<circle cx="{60-rx*math.cos(a):.1f}" cy="{30+ry*math.sin(a):.1f}" r="5.4" fill="{c}"/><circle cx="{60-rx*math.cos(a)-1.6:.1f}" cy="{30+ry*math.sin(a)-1.6:.1f}" r="1.5" fill="#fff" opacity=".7"/>'
more["mardi-beads"] = (C.format(CREAM) + f'<g CLIP>{beads}</g>')

# ================= VALENTINE =================
more["valentine-heart"] = (
  C.format(PINK) + f'<path d="{heart(60, 66, 30)}" fill="{RED}"/>'
  f'<ellipse cx="38" cy="50" rx="4" ry="7" fill="#fff" opacity=".55" transform="rotate(30 38 50)"/>'
  + eyes(62, dx=10, r=3.2, c=WHITE) + f'<path d="M54 70 q6 5 12 0" stroke="#fff" stroke-width="2.6" stroke-linecap="round" fill="none"/>'
  + f'<g fill="{PINK}"><circle cx="40" cy="70" r="4.5"/><circle cx="80" cy="70" r="4.5"/></g>'
)
more["valentine-letter"] = (
  C.format(LAV) +
  f'<rect x="24" y="40" width="72" height="50" rx="7" fill="{WHITE}"/>'
  f'<path d="M26 44 L60 70 L94 44" stroke="{PINK}" stroke-width="3" fill="none" stroke-linejoin="round"/>'
  f'<path d="{heart(60, 70, 11)}" fill="{RED}"/>'
  f'<path d="{heart(90, 26, 6)}" fill="#f9a8d4"/><path d="{heart(30, 22, 4.5)}" fill="#f9a8d4"/>'
)
BEAR="#d6b38a"
more["valentine-bear"] = (
  f'<circle cx="24" cy="28" r="14" fill="{BEAR}"/><circle cx="96" cy="28" r="14" fill="{BEAR}"/>'
  f'<circle cx="24" cy="28" r="7" fill="{CHEEK}"/><circle cx="96" cy="28" r="7" fill="{CHEEK}"/>'
  + C.format(BEAR) +
  f'<ellipse cx="60" cy="78" rx="18" ry="13" fill="{CREAM}"/>'
  + eyes(60, dx=14, r=3.6) + cheeks(72, dx=27) +
  f'<ellipse cx="60" cy="72" rx="6.5" ry="4.5" fill="{INK}"/>'
  f'<path d="M54 82 Q60 87 66 82" stroke="{INK}" stroke-width="2.4" stroke-linecap="round" fill="none"/>'
  f'<path d="{heart(60, 106, 12)}" fill="{RED}" stroke="#fff" stroke-width="2"/>'
)
more["valentine-candy"] = (
  C.format(MINT) + f'<path d="{heart(60, 66, 32)}" fill="{PINK}" stroke="#f9a8d4" stroke-width="2"/>'
  f'<text x="60" y="72" text-anchor="middle" font-family="system-ui, sans-serif" font-weight="800" font-size="20" fill="#f472b6">XO</text>'
)
more["valentine-rose"] = (
  C.format("#fce7f3") +
  f'<rect x="57" y="72" width="6" height="40" fill="{TREE}"/>'
  f'<ellipse cx="44" cy="90" rx="13" ry="6" fill="{TREE}" transform="rotate(-25 44 90)"/>'
  f'<ellipse cx="76" cy="96" rx="13" ry="6" fill="{TREE}" transform="rotate(25 76 96)"/>'
  f'<circle cx="46" cy="54" r="14" fill="{PINKRED}"/><circle cx="74" cy="54" r="14" fill="{PINKRED}"/>'
  f'<circle cx="60" cy="58" r="20" fill="{RED}"/>'
  f'<path d="M60 46 q10 2 8 12 q-4 9 -13 5 q-7 -4 -3 -12" stroke="#fca5a5" stroke-width="3" fill="none" stroke-linecap="round"/>'
)
more["valentine-bird"] = (
  f'<path d="M56 16 Q60 4 64 16 Q60 10 56 16 Z" fill="#f9a8d4" stroke="#f9a8d4" stroke-width="4" stroke-linejoin="round"/>'
  f'<path d="{heart(98, 18, 8)}" fill="{RED}"/>'
  + C.format("#f9a8d4") +
  f'<g CLIP><ellipse cx="60" cy="104" rx="38" ry="28" fill="{WHITE}"/></g>'
  + eyes(60, dx=13, r=3.4) + cheeks(70, dx=24) +
  f'<path d="M54 68 L66 68 L60 76 Z" fill="{ORANGE}" stroke="{ORANGE}" stroke-width="2.5" stroke-linejoin="round"/>'
)

# ================= EASTER =================
more["easter-bunny"] = (
  f'<ellipse cx="42" cy="22" rx="10" ry="22" fill="{WHITE}" stroke="{EDGE}" stroke-width="1.5" transform="rotate(-8 42 22)"/>'
  f'<ellipse cx="78" cy="22" rx="10" ry="22" fill="{WHITE}" stroke="{EDGE}" stroke-width="1.5" transform="rotate(8 78 22)"/>'
  f'<ellipse cx="42" cy="24" rx="5" ry="15" fill="{CHEEK}" transform="rotate(-8 42 24)"/>'
  f'<ellipse cx="78" cy="24" rx="5" ry="15" fill="{CHEEK}" transform="rotate(8 78 24)"/>'
  + icy() + eyes(62, dx=13, r=3.4) + cheeks(72, dx=25) +
  f'<path d="M56 70 h8 l-4 4 Z" fill="#f472b6" stroke="#f472b6" stroke-width="2" stroke-linejoin="round"/>'
  f'<path d="M60 74 v4 M54 80 q3 2 6 -2 q3 4 6 2" stroke="{INK}" stroke-width="2.2" stroke-linecap="round" fill="none"/>'
)
more["easter-chick"] = (
  f'<g fill="{GOLDL}"><ellipse cx="54" cy="12" rx="4" ry="9" transform="rotate(-25 54 12)"/><ellipse cx="62" cy="10" rx="4" ry="10"/><ellipse cx="70" cy="13" rx="4" ry="8" transform="rotate(25 70 13)"/></g>'
  + C.format(GOLDL) +
  f'<g CLIP><path d="M0 88 L12 80 L24 90 L36 80 L48 90 L60 80 L72 90 L84 80 L96 90 L108 80 L120 88 V130 H0 Z" fill="{WHITE}"/></g>' + RING +
  eyes(56, dx=12, r=3.4) + cheeks(66, dx=24) +
  f'<path d="M53 64 L60 58 L67 64 L60 70 Z" fill="{ORANGE}" stroke="{ORANGE}" stroke-width="2" stroke-linejoin="round"/>'
)
more["easter-egg"] = (
  C.format(MINT) +
  f'<ellipse cx="60" cy="66" rx="32" ry="40" fill="{PINK}"/>'
  f'<clipPath id="__CLIP__e"><ellipse cx="60" cy="66" rx="32" ry="40"/></clipPath>'
  f'<g clip-path="url(#__CLIP__e)"><path d="M20 44 L30 36 L40 44 L50 36 L60 44 L70 36 L80 44 L90 36 L100 44" stroke="{WHITE}" stroke-width="4" fill="none" stroke-linejoin="round"/>'
  f'<rect x="20" y="88" width="80" height="10" fill="{PURPLE}"/>'
  + "".join(f'<circle cx="{x}" cy="93" r="2" fill="#fff"/>' for x in range(30,95,10)) + '</g>'
  + eyes(64, dx=10, r=3) + cheeks(72, dx=19, r=4.5) + smile(71, w=5)
)
more["easter-basket"] = (
  C.format(SKY) +
  f'<path d="M32 66 Q60 0 88 66" stroke="{BROWN}" stroke-width="6" fill="none" stroke-linecap="round"/>'
  f'<ellipse cx="44" cy="64" rx="10" ry="13" fill="{PINK}"/><ellipse cx="60" cy="60" rx="10" ry="13" fill="{GOLDL}"/><ellipse cx="76" cy="64" rx="10" ry="13" fill="{LAV}"/>'
  f'<path d="M26 70 L34 64 L40 70 L48 64 L54 70 L62 64 L68 70 L76 64 L82 70 L88 64 L94 70 Z" fill="{GREEN}"/>'
  f'<g CLIP><path d="M22 70 H98 L90 106 Q60 114 30 106 Z" fill="{TAN}"/></g>'
  f'<g stroke="{BROWN}" stroke-width="2" opacity=".6"><path d="M26 82 H94 M28 94 H92"/></g>'
  + eyes(84, dx=12, r=3) + smile(90, w=5)
)
more["easter-carrot"] = (
  C.format(CREAM) +
  f'<g fill="{TREE}"><ellipse cx="50" cy="20" rx="5" ry="13" transform="rotate(-25 50 20)"/><ellipse cx="60" cy="16" rx="5" ry="14"/><ellipse cx="70" cy="20" rx="5" ry="13" transform="rotate(25 70 20)"/></g>'
  f'<path d="M36 34 Q60 22 84 34 Q80 76 60 110 Q40 76 36 34 Z" fill="{ORANGE}" stroke="{ORANGE}" stroke-width="2" stroke-linejoin="round"/>'
  f'<path d="M44 76 h8 M68 86 h-7 M50 96 h6" stroke="#fb923c" stroke-width="2.4" stroke-linecap="round"/>'
  + eyes(50, dx=10, r=3) + cheeks(58, dx=17, r=4) + smile(57, w=5)
)
wool = "".join(f'<circle cx="{60+45*math.cos(i*math.pi/7):.1f}" cy="{64+45*math.sin(i*math.pi/7):.1f}" r="10" fill="{WHITE}" stroke="{EDGE}" stroke-width="1.5"/>' for i in range(14))
more["easter-lamb"] = (
  wool + C.format(WHITE) +
  f'<ellipse cx="32" cy="62" rx="11" ry="6" fill="{TAN}" transform="rotate(20 32 62)"/><ellipse cx="88" cy="62" rx="11" ry="6" fill="{TAN}" transform="rotate(-20 88 62)"/>'
  f'<ellipse cx="60" cy="72" rx="24" ry="28" fill="#f3e3cf"/>'
  f'<g fill="{WHITE}" stroke="{EDGE}" stroke-width="1.2"><circle cx="50" cy="46" r="8"/><circle cx="70" cy="46" r="8"/><circle cx="60" cy="42" r="9"/></g>'
  + eyes(66, dx=10, r=3) + cheeks(76, dx=17, r=4.5) + smile(80, w=5)
)

# ================= SUMMER =================
rays = "".join(f'<path d="M{60+50*math.cos(a-0.12):.1f} {64+50*math.sin(a-0.12):.1f} L{60+59*math.cos(a):.1f} {64+59*math.sin(a):.1f} L{60+50*math.cos(a+0.12):.1f} {64+50*math.sin(a+0.12):.1f} Z" fill="{ORANGE}" stroke="{ORANGE}" stroke-width="3" stroke-linejoin="round"/>' for a in [i*math.pi/6 - math.pi/2 for i in range(12)] if math.sin(a) < 0.8)
more["summer-sun"] = (
  rays + C.format(GOLDL) +
  f'<rect x="34" y="52" width="22" height="14" rx="6" fill="{INK}"/><rect x="64" y="52" width="22" height="14" rx="6" fill="{INK}"/>'
  f'<path d="M56 57 h8" stroke="{INK}" stroke-width="3"/><path d="M38 55 l6 0" stroke="#fff" stroke-width="2" stroke-linecap="round" opacity=".6"/>'
  + cheeks(76, dx=24) + smile(78, w=7)
)
more["summer-watermelon"] = (
  C.format(TREE) + f'<circle cx="60" cy="64" r="44" fill="{WHITE}"/><circle cx="60" cy="64" r="40" fill="{PINKRED}"/>'
  + "".join(f'<ellipse cx="{x}" cy="{y}" rx="2" ry="3.4" fill="{INK}" transform="rotate({r} {x} {y})"/>' for x,y,r in ((40,40,-30),(60,34,0),(80,40,30),(34,84,30),(86,84,-30),(60,96,0)))
  + eyes(62, dx=11, r=3.2) + cheeks(70, dx=21, r=4.5) + smile(70, w=6)
)
more["summer-popsicle"] = (
  C.format(SKY) +
  f'<rect x="54" y="80" width="12" height="38" rx="6" fill="{TAN}"/>'
  f'<clipPath id="__CLIP__p"><rect x="36" y="22" width="48" height="66" rx="22"/></clipPath>'
  f'<g clip-path="url(#__CLIP__p)"><rect x="30" y="20" width="60" height="26" fill="{PINKRED}"/><rect x="30" y="46" width="60" height="22" fill="{PEACH}"/><rect x="30" y="68" width="60" height="24" fill="{GOLDL}"/></g>'
  f'<rect x="42" y="30" width="5" height="16" rx="2.5" fill="#fff" opacity=".6"/>'
  + eyes(56, dx=9, r=3) + cheeks(64, dx=16, r=4) + smile(63, w=5)
)
def qpanel(c1, c2, fill):
    return f'<path d="M60 14 Q{c1} 64 60 114 Q{c2} 64 60 14 Z" fill="{fill}"/>'
more["summer-beach-ball"] = (
  C.format(GOLDL) +
  f'<g CLIP>{qpanel(-70, 10, PINKRED)}{qpanel(10, 110, WHITE)}{qpanel(110, 190, BLUE)}</g>' + RING +
  f'<circle cx="60" cy="18" r="5" fill="{WHITE}" stroke="{EDGE}" stroke-width="1.5"/>'
  + face(64, dx=9, cdx=16, w=5, r=3)
)
CRAB="#fca5a5"
more["summer-crab"] = (
  f'<path d="M18 46 L10 40" stroke="{CRAB}" stroke-width="5" stroke-linecap="round"/><path d="M102 46 L110 40" stroke="{CRAB}" stroke-width="5" stroke-linecap="round"/>'
  f'<path d="M16 34 a13 13 0 1 1 12 -14 l-10 4 Z" fill="{CRAB}"/><path d="M104 34 a13 13 0 1 0 -12 -14 l10 4 Z" fill="{CRAB}"/>'
  f'<g stroke="{CRAB}" stroke-width="5" stroke-linecap="round"><path d="M12 76 L2 80 M14 90 L4 98 M108 76 L118 80 M106 90 L116 98"/></g>'
  + C.format(CRAB) + face(62, dx=12, cdx=24, r=3.6)
)
hatch = "".join(f'<path d="M{x} 0 L{x+120} 120 M{x+120} 0 L{x} 120" />' for x in range(-110, 120, 18))
more["summer-pineapple"] = (
  f'<g fill="{TREE}"><path d="M60 26 L50 4 L60 12 L70 4 Z"/><path d="M56 28 L34 12 L50 16 Z"/><path d="M64 28 L86 12 L70 16 Z"/></g>'
  + C.format(GOLDL) + f'<g CLIP stroke="{GOLD}" stroke-width="2.5" opacity=".8">{hatch}</g>'
  + f'<ellipse cx="60" cy="68" rx="24" ry="16" fill="{GOLDL}"/>' + face(64, dx=11, cdx=22, r=3.2)
)

# ================= JULY 4TH =================
burst = ""
for i in range(12):
    a = i*math.pi/6; c = (PINKRED, BLUE, WHITE)[i%3]
    x1,y1 = 60+14*math.cos(a), 64+14*math.sin(a); x2,y2 = 60+36*math.cos(a), 64+36*math.sin(a)
    burst += f'<path d="M{x1:.1f} {y1:.1f} L{x2:.1f} {y2:.1f}" stroke="{c}" stroke-width="5" stroke-linecap="round"/><circle cx="{60+44*math.cos(a):.1f}" cy="{64+44*math.sin(a):.1f}" r="3.5" fill="{c}"/>'
more["july4-firework"] = (C.format("#a5b4fc") + burst + f'<circle cx="60" cy="64" r="8" fill="{GOLDL}"/>')
more["july4-star"] = (
  C.format(BLUE) + star(60, 66, 38, 17).replace('#fcd34d', WHITE) + eyes(64, dx=8, r=3)
  + f'<g fill="{PINKRED}"><circle cx="48" cy="72" r="4"/><circle cx="72" cy="72" r="4"/></g>' + smile(71, w=4)
)
stripes = "".join(f'<rect x="0" y="{y}" width="120" height="7.7" fill="{PINKRED if k%2==0 else WHITE}"/>' for k,y in enumerate([14+7.7*i for i in range(13)]))
more["july4-flag"] = (
  C.format(WHITE) + f'<g CLIP>{stripes}<rect x="0" y="14" width="60" height="46" fill="{BLUE}"/>'
  + "".join(f'<circle cx="{x}" cy="{y}" r="2.2" fill="#fff"/>' for y in (22,32,42,52) for x in (range(18,58,10) if y%20==2 else range(23,58,10)))
  + '</g>' + RING
)
more["july4-eagle"] = (
  C.format(WHITE) + f'<g CLIP><path d="M0 92 Q20 84 30 92 Q45 82 60 92 Q75 82 90 92 Q100 84 120 92 V130 H0 Z" fill="{BROWN}"/></g>' + RING
  + f'<path d="M40 52 l14 4 M80 52 l-14 4" stroke="{INK}" stroke-width="2.6" stroke-linecap="round"/>'
  + eyes(62, dx=12, r=3.4) + cheeks(72, dx=24)
  + f'<path d="M52 68 Q60 62 68 68 Q70 78 62 84 Q64 76 56 74 Z" fill="#fcd34d" stroke="#fcd34d" stroke-width="2" stroke-linejoin="round"/>'
)
more["july4-hotdog"] = (
  C.format(SKY) +
  f'<rect x="14" y="48" width="92" height="32" rx="16" fill="{TAN}"/>'
  f'<rect x="8" y="56" width="104" height="18" rx="9" fill="#fb9a8a"/>'
  f'<path d="M16 64 q6 -6 12 0 t12 0 t12 0 t12 0 t12 0 t12 0 t12 0" stroke="#fcd34d" stroke-width="3.5" fill="none" stroke-linecap="round"/>'
  f'<rect x="14" y="68" width="92" height="22" rx="11" fill="#f3d9b1"/>'
  + eyes(77, dx=10, r=3) + cheeks(83, dx=20, r=4) + smile(82, w=5)
)
more["july4-hat"] = (
  C.format(LAV) +
  f'<clipPath id="__CLIP__h"><rect x="36" y="16" width="48" height="66" rx="5"/></clipPath>'
  f'<g clip-path="url(#__CLIP__h)"><rect x="36" y="16" width="48" height="66" fill="{WHITE}"/>'
  + "".join(f'<rect x="{x}" y="16" width="8" height="66" fill="{PINKRED}"/>' for x in (36,52,68,84)) +
  f'<rect x="36" y="58" width="48" height="14" fill="{BLUE}"/></g>'
  + "".join(f'<circle cx="{x}" cy="65" r="2" fill="#fff"/>' for x in (44,52,60,68,76)) +
  f'<ellipse cx="60" cy="84" rx="40" ry="9" fill="{BLUE}"/>'
)

# ================= HALLOWEEN =================
more["halloween-pumpkin"] = (
  f'<path d="M58 16 Q56 6 64 2" stroke="{TREE}" stroke-width="6" fill="none" stroke-linecap="round"/>'
  f'<ellipse cx="72" cy="12" rx="9" ry="4" fill="{GREEN}" transform="rotate(-20 72 12)"/>'
  + C.format(ORANGE) +
  f'<g CLIP fill="none" stroke="#fb923c" stroke-width="2.5"><ellipse cx="60" cy="64" rx="18" ry="50"/><ellipse cx="60" cy="64" rx="38" ry="50"/></g>'
  + eyes(60, dx=14, r=4) + cheeks(70, dx=26) +
  f'<path d="M48 74 Q60 86 72 74 Z" fill="{INK}"/><rect x="57" y="74" width="6" height="5" fill="{ORANGE}"/>'
)
more["halloween-ghost"] = (
  C.format(LAV) +
  f'<path d="M30 104 V58 a30 30 0 0 1 60 0 V104 l-10 -8 l-10 8 l-10 -8 l-10 8 l-10 -8 Z" fill="{WHITE}" stroke="{EDGE}" stroke-width="1.5" stroke-linejoin="round"/>'
  f'<ellipse cx="50" cy="60" rx="4" ry="6" fill="{INK}"/><ellipse cx="70" cy="60" rx="4" ry="6" fill="{INK}"/>'
  + cheeks(72, dx=18, r=4.5) + f'<ellipse cx="60" cy="76" rx="4" ry="5" fill="{INK}"/>'
)
more["halloween-cat"] = (
  f'<path d="M22 48 L24 12 L52 30 Z" fill="{SLATE}"/><path d="M98 48 L96 12 L68 30 Z" fill="{SLATE}"/>'
  f'<path d="M28 38 L29 22 L42 30 Z" fill="{CHEEK}"/><path d="M92 38 L91 22 L78 30 Z" fill="{CHEEK}"/>'
  + C.format(SLATE) +
  f'<ellipse cx="46" cy="62" rx="8" ry="9" fill="{SAGE}"/><ellipse cx="74" cy="62" rx="8" ry="9" fill="{SAGE}"/>'
  f'<ellipse cx="46" cy="63" rx="3" ry="6" fill="{INK}"/><ellipse cx="74" cy="63" rx="3" ry="6" fill="{INK}"/>'
  f'<path d="M56 74 h8 l-4 4 Z" fill="{CHEEK}" stroke="{CHEEK}" stroke-width="2" stroke-linejoin="round"/>'
  f'<path d="M60 78 q-4 5 -8 2 M60 78 q4 5 8 2" stroke="#e2e8f0" stroke-width="2" fill="none" stroke-linecap="round"/>'
  f'<path d="M22 72 L38 74 M22 80 L38 78 M98 72 L82 74 M98 80 L82 78" stroke="#e2e8f0" stroke-width="1.6" stroke-linecap="round"/>'
)
more["halloween-bat"] = (
  C.format(LAV) +
  f'<path d="M60 56 Q36 40 8 50 Q16 58 14 68 Q24 64 30 72 Q38 64 46 74 Z" fill="{SLATE}" stroke="{SLATE}" stroke-width="2" stroke-linejoin="round"/>'
  f'<path d="M60 56 Q84 40 112 50 Q104 58 106 68 Q96 64 90 72 Q82 64 74 74 Z" fill="{SLATE}" stroke="{SLATE}" stroke-width="2" stroke-linejoin="round"/>'
  f'<path d="M46 50 L48 36 L56 46 Z M74 50 L72 36 L64 46 Z" fill="{SLATE}"/>'
  f'<circle cx="60" cy="64" r="20" fill="{SLATE}"/>'
  f'<circle cx="52" cy="60" r="5" fill="#fff"/><circle cx="68" cy="60" r="5" fill="#fff"/><circle cx="52" cy="61" r="2.6" fill="{INK}"/><circle cx="68" cy="61" r="2.6" fill="{INK}"/>'
  f'<path d="M55 72 l2 4 l2 -4 M61 72 l2 4 l2 -4" fill="#fff" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/>'
  f'<g fill="{CHEEK}" opacity=".8"><circle cx="46" cy="69" r="3"/><circle cx="74" cy="69" r="3"/></g>'
)
more["halloween-witch"] = (
  C.format(SKIN) +
  f'<g CLIP><path d="M0 0 H120 V56 Q104 44 92 54 Q80 42 68 50 L52 50 Q40 42 28 54 Q16 44 0 56 Z" fill="#a78bfa"/></g>'
  f'<path d="M36 34 L58 2 Q66 0 70 8 L76 4 Q74 14 84 34 Z" fill="{PURPLE}" stroke="{PURPLE}" stroke-width="3" stroke-linejoin="round"/>'
  f'<rect x="38" y="26" width="44" height="7" fill="{ORANGE}"/>'
  f'<ellipse cx="60" cy="36" rx="54" ry="8" fill="{PURPLE}"/>'
  + face(64, dx=11, cdx=22)
)
cc_top = "60,24 49.3,50 70.7,50"; cc_mid = "49.3,50 70.7,50 81.3,76 38.7,76"; cc_bot = "38.7,76 81.3,76 92,102 28,102"
more["halloween-candy-corn"] = (
  C.format(LAV) +
  f'<polygon points="{cc_bot}" fill="{GOLDL}" stroke="{GOLDL}" stroke-width="8" stroke-linejoin="round"/>'
  f'<polygon points="{cc_mid}" fill="{ORANGE}"/>'
  f'<polygon points="{cc_top}" fill="{WHITE}" stroke="{WHITE}" stroke-width="8" stroke-linejoin="round"/>'
  + eyes(62, dx=8, r=2.8) + cheeks(69, dx=14, r=3.5) + smile(68, w=4)
)

# ================= BACK TO SCHOOL =================
more["school-apple"] = (
  f'<path d="M60 20 Q58 10 62 4" stroke="{BROWN}" stroke-width="5" fill="none" stroke-linecap="round"/>'
  f'<ellipse cx="74" cy="12" rx="11" ry="5" fill="{TREE}" transform="rotate(-25 74 12)"/>'
  + C.format(PINKRED) +
  f'<ellipse cx="34" cy="54" rx="5" ry="10" fill="#fff" opacity=".55" transform="rotate(25 34 54)"/>'
  + face(64)
)
more["school-pencil"] = (
  C.format(SKY) +
  f'<g transform="rotate(-40 60 64)">'
  f'<rect x="44" y="16" width="32" height="14" rx="6" fill="{PINK}"/><rect x="44" y="28" width="32" height="10" fill="#cbd5e1"/>'
  f'<rect x="44" y="38" width="32" height="50" fill="{GOLDL}"/>'
  f'<path d="M44 88 L76 88 L60 114 Z" fill="#f3d9b1"/><path d="M55 106 L65 106 L60 114 Z" fill="{INK}"/>'
  + eyes(60, dx=7, r=2.8) + cheeks(67, dx=12, r=3.2) + smile(66, w=4) + '</g>'
)
more["school-book"] = (
  C.format(PINK) +
  f'<rect x="32" y="26" width="58" height="76" rx="6" fill="{WHITE}" stroke="{EDGE}" stroke-width="1.5"/>'
  f'<rect x="28" y="24" width="56" height="76" rx="6" fill="{BLUE}"/>'
  f'<rect x="28" y="24" width="10" height="76" rx="4" fill="#7dd3fc"/>'
  f'<rect x="46" y="36" width="30" height="12" rx="3" fill="{WHITE}"/>'
  + eyes(66, dx=9, r=3, cx=61) + cheeks(74, dx=16, r=4, cx=61) + smile(73, w=5, cx=61)
)
more["school-bus"] = (
  C.format(SKY) +
  f'<rect x="32" y="96" width="14" height="14" rx="4" fill="{INK}"/><rect x="74" y="96" width="14" height="14" rx="4" fill="{INK}"/>'
  f'<rect x="24" y="24" width="72" height="78" rx="16" fill="{GOLDL}"/>'
  f'<rect x="32" y="34" width="56" height="26" rx="7" fill="{ICE}"/>'
  + eyes(47, dx=11, r=3.2) +
  f'<circle cx="36" cy="80" r="6" fill="{WHITE}"/><circle cx="84" cy="80" r="6" fill="{WHITE}"/>'
  f'<path d="M48 80 Q60 88 72 80" stroke="{INK}" stroke-width="2.6" stroke-linecap="round" fill="none"/>'
  f'<rect x="24" y="66" width="72" height="4" fill="{GOLD}"/>' + cheeks(54, dx=20, r=3.5)
)
more["school-backpack"] = (
  C.format(MINT) +
  f'<path d="M48 30 Q48 16 60 16 Q72 16 72 30" stroke="#a78bfa" stroke-width="6" fill="none"/>'
  f'<rect x="30" y="28" width="60" height="76" rx="18" fill="{PURPLE}"/>'
  f'<rect x="40" y="70" width="40" height="26" rx="10" fill="#a78bfa"/>'
  f'<path d="M46 78 H74" stroke="{LAV}" stroke-width="2.5" stroke-linecap="round"/>'
  + eyes(50, dx=10, r=3) + cheeks(58, dx=19, r=4) + smile(57, w=5)
)
OWL="#c9a27e"
more["school-owl"] = (
  C.format(OWL) +
  f'<g CLIP><ellipse cx="60" cy="108" rx="34" ry="30" fill="#f3e3cf"/></g>'
  f'<circle cx="45" cy="62" r="13" fill="{WHITE}"/><circle cx="75" cy="62" r="13" fill="{WHITE}"/>'
  f'<circle cx="46" cy="63" r="5" fill="{INK}"/><circle cx="74" cy="63" r="5" fill="{INK}"/>'
  f'<path d="M55 74 L65 74 L60 82 Z" fill="{ORANGE}" stroke="{ORANGE}" stroke-width="2" stroke-linejoin="round"/>'
  f'<path d="M34 30 L60 18 L86 30 L60 42 Z" fill="{INK}"/><rect x="46" y="32" width="28" height="10" rx="2" fill="{INK}"/>'
  f'<path d="M84 30 V44" stroke="#fcd34d" stroke-width="2.5"/><circle cx="84" cy="46" r="3" fill="#fcd34d"/>'
)

# ================= THANKSGIVING =================
feathers = ""
for i,c in enumerate((PINKRED, ORANGE, GOLDL, SAGE, PINKRED, ORANGE, GOLDL, SAGE, PINKRED)):
    a = math.pi + i*math.pi/8; x = 60+30*math.cos(a); y = 70+30*math.sin(a); deg = math.degrees(a)+90
    feathers += f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="11" ry="24" fill="{c}" transform="rotate({deg:.1f} {x:.1f} {y:.1f})"/>'
more["thanks-turkey"] = (
  feathers + f'<circle cx="60" cy="72" r="32" fill="{BROWN}"/>'
  + eyes(66, dx=10, r=3.2) + cheeks(76, dx=19, r=4.5) +
  f'<path d="M54 72 L66 72 L60 80 Z" fill="#fcd34d" stroke="#fcd34d" stroke-width="2" stroke-linejoin="round"/>'
  f'<path d="M62 78 q4 6 0 12 q-3 -6 0 -12 Z" fill="{RED}"/>'
)
more["thanks-pie"] = (
  C.format(TAN) +
  "".join(f'<circle cx="{60+46*math.cos(i*math.pi/12):.1f}" cy="{64+46*math.sin(i*math.pi/12):.1f}" r="3" fill="#d6a46c"/>' for i in range(24))
  + f'<circle cx="60" cy="64" r="38" fill="{ORANGE}"/>'
  + f'<g fill="{WHITE}"><circle cx="60" cy="42" r="10"/><circle cx="52" cy="46" r="7"/><circle cx="68" cy="46" r="7"/><circle cx="60" cy="34" r="6"/></g>'
  + face(70, dx=11, cdx=21, r=3.2)
)
kern = "".join(f'<circle cx="{x}" cy="{y}" r="3" fill="#fcd34d"/>' for y in range(32,96,9) for x in range(48,76,9))
more["thanks-corn"] = (
  C.format(SAGE) +
  f'<clipPath id="__CLIP__k"><ellipse cx="60" cy="60" rx="20" ry="40"/></clipPath>'
  f'<ellipse cx="60" cy="60" rx="20" ry="40" fill="{GOLDL}"/><g clip-path="url(#__CLIP__k)">{kern}</g>'
  f'<path d="M58 112 Q30 96 30 56 Q44 70 52 96 Z" fill="{TREE}"/><path d="M62 112 Q90 96 90 56 Q76 70 68 96 Z" fill="{TREE}"/>'
  f'<ellipse cx="60" cy="62" rx="14" ry="10" fill="{GOLDL}"/>' + eyes(60, dx=7, r=2.8) + smile(65, w=4)
)
more["thanks-leaf"] = (
  C.format(CREAM) +
  f'<path d="M60 108 V96" stroke="{BROWN}" stroke-width="4" stroke-linecap="round"/>'
  f'<path d="M60 20 Q100 46 60 98 Q20 46 60 20 Z" fill="{ORANGE}"/>'
  f'<path d="M60 28 V92 M60 50 l-12 -8 M60 50 l12 -8 M60 74 l-14 -8 M60 74 l14 -8" stroke="#fb923c" stroke-width="2.4" stroke-linecap="round"/>'
  + f'<g fill="{CHEEK}" opacity=".8"><circle cx="46" cy="62" r="4"/><circle cx="74" cy="62" r="4"/></g>'
  + eyes(56, dx=8, r=2.8)
)
more["thanks-acorn"] = (
  C.format(SAGE) +
  f'<path d="M60 26 Q62 18 68 16" stroke="{BROWN}" stroke-width="5" fill="none" stroke-linecap="round"/>'
  f'<path d="M36 58 Q60 98 84 58 Q84 100 60 108 Q36 100 36 58 Z" fill="{TAN}"/>'
  f'<path d="M30 56 Q30 26 60 26 Q90 26 90 56 Z" fill="{BROWN}" stroke="{BROWN}" stroke-width="4" stroke-linejoin="round"/>'
  f'<g stroke="#a47148" stroke-width="2" opacity=".7"><path d="M40 52 L54 32 M54 52 L68 30 M68 52 L80 36"/></g>'
  f'<path d="M36 58 Q60 64 84 58 Q84 96 60 106 Q36 96 36 58 Z" fill="{TAN}"/>'
  + eyes(74, dx=9, r=3) + cheeks(82, dx=16, r=4) + smile(81, w=4)
)
petals = "".join(f'<ellipse cx="{60+36*math.cos(a):.1f}" cy="{64+36*math.sin(a):.1f}" rx="9" ry="16" fill="{GOLDL}" stroke="{GOLD}" stroke-width="1.5" transform="rotate({math.degrees(a)+90:.1f} {60+36*math.cos(a):.1f} {64+36*math.sin(a):.1f})"/>' for a in [i*math.pi/7 for i in range(14)])
more["thanks-sunflower"] = (
  petals + f'<circle cx="60" cy="64" r="26" fill="{BROWN}"/>'
  + "".join(f'<circle cx="{60+18*math.cos(i):.1f}" cy="{64+18*math.sin(i):.1f}" r="1.5" fill="#a47148"/>' for i in range(0,7))
  + eyes(60, dx=9, r=3) + cheeks(68, dx=15, r=4) + smile(67, w=5)
)

xmas_names = {"santa":"Santa","mrs-claus":"Mrs. Claus","elf":"Elf","snowman":"Snowman","reindeer":"Reindeer",
  "gingerbread":"Gingerbread","penguin":"Penguin","polar-bear":"Polar bear","tree":"Tree","ornament":"Ornament",
  "peppermint":"Peppermint","present":"Present"}
ALL = {f"xmas-{k}": v for k, v in icons.items()}
ALL.update(more)
NAMES = {f"xmas-{k}": v for k, v in xmas_names.items()}
nice = {"king-cake":"King cake","fleur":"Fleur-de-lis","candy":"Candy heart","beach-ball":"Beach ball","candy-corn":"Candy corn","hotdog":"Hot dog","hat":"Top hat"}
for k in more:
    n = k.split("-",1)[1]; NAMES[k] = nice.get(n, n.replace("-"," ").capitalize())
for k in ALL: assert len(k) <= 32 and re.fullmatch(r"[a-z0-9-]+", k), k
REPO = Path(__file__).resolve().parents[2]
OUT = sys.argv[1] if len(sys.argv) > 1 else None  # optional folder for standalone .svg files
# careful: body uses "CLIP" placeholder and "__CLIP__x" ids; replace placeholder only when standalone
def inner(k):
    b = re.sub(r'(?<![_A-Za-z])CLIP(?![_A-Za-z])', 'clip-path="url(#__CLIP__)"', ALL[k])
    return '<defs><clipPath id="__CLIP__"><circle cx="60" cy="64" r="50"/></clipPath></defs>' + b
if OUT:
  os.makedirs(OUT, exist_ok=True)
  for k in ALL:
    open(f"{OUT}/{k}.svg","w").write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="120" height="120">' + inner(k).replace("__CLIP__", "c-"+k) + '</svg>')
js = ["/**", " * Holiday icons (original art drawn for this project, no licence needed): flat pastel circles, 120x120 box.",
      " * Generated by tools/holiday-icons/build.py (do not edit by hand); __CLIP__ is replaced with a unique id per use.", " */",
      "export const HOLIDAY_ART = {"]
for k in ALL: js.append(f"  '{k}': {json.dumps(inner(k))},")
js.append("}"); js.append("")
js.append("export const HOLIDAY_NAMES = " + json.dumps(NAMES, indent=2) + "\n")
open(REPO / "frontend/src/holidayArt.js","w").write("\n".join(js))
print(len(ALL))
