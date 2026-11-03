import csv, json, re, sys, urllib.parse, os

SRC = "https://freeafricanamericans.com/halifax.htm"
HAL = "Halifax Co., NC, "; KG = "King George Co., VA, "
BOOKS = {"1": HAL + "Will Book Vol. 1 (1758-1774)", "2": HAL + "Will Book Vol. 2 (1775-1779)",
         "3": HAL + "Will Book Vol. 3 (1781-1824)", "4": HAL + "Will Book Vol. 4 (1825-1854)",
         "KGA": KG + "Will Book A-1 (1721-1752)", "KG1": KG + "Will Book 1 (1752-1780)",
         "KG2": KG + "Will Book 2 (1780-1804)", "KG3": KG + "Will Book 3 (1804-1846)",
         "KG4": KG + "Will Book 4 (1847-1901)"}
ORDER = list(BOOKS)
import json as _j
FAMILY = re.compile(r"\b(son|daughter|wife|brother|sister|grandson|granddaughter|grandchild|grandchildren|mother|father|nephew|niece|child|children|sons|daughters)\b", re.I)
SUFFIX = {"senr", "jnr", "junr", "senior", "sr", "jr", "junior"}

here = os.path.dirname(os.path.abspath(__file__))
wills, names = [], []

def surname(full):
    toks = [t for t in re.split(r"\s+", full.strip()) if t.strip(".").lower() not in SUFFIX]
    return toks[-1] if toks else ""

REV = {}
USED = set()
_cur = None
if os.path.exists(os.path.join(here, "reviews.txt")):
    for _l in open(os.path.join(here, "reviews.txt"), encoding="utf-8"):
        _l = _l.rstrip("\n")
        if not _l.strip() or _l.startswith("#"): continue
        if _l.startswith("@"):
            _cur = tuple(x.strip() for x in _l[1:].split("|")); REV[_cur] = []
        else: REV[_cur].append(_l.strip())

def apply_review(key, testator, date, recips, ens, notes):
    """returns testator, date, recips, ens, notes, alias, extras, drops"""
    USED.add(key); ds = REV[key]; rl = [x.strip() for x in recips.split(";") if x.strip()]; el = [x.strip() for x in ens.split(";") if x.strip()]
    extras, drops, t0 = [], [], testator
    for d in ds:
        op, _, arg = d.partition(" "); arg = arg.strip()
        if op == "T": testator = arg
        elif op == "D": date = arg
        elif op == "N": notes = arg
        elif op == "-R": rl = [x for x in rl if (x.lower() if "(" in arg else re.sub(r"\s*\(.*$", "", x).lower()) != arg.lower()]
        elif op == "+R": rl.append(arg)
        elif op == "-E": el = [x for x in el if x.lower() != arg.lower()]
        elif op == "+E": el.append(arg)
        elif op == "+B": extras.append(arg)
        elif op == "-B": drops.append(arg)
    return testator, date, "; ".join(rl), "; ".join(el), notes, t0, extras, drops

ALIAS = {}
EXTRA = {}
DROP = {}

def load(fname, origs, auto):
    k = 0
    for line in open(os.path.join(here, fname), encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        assert len(parts) == 7, line
        vol, pages, date, testator, recips, ens, notes = [p.strip() for p in parts]
        orig = origs[k]; k += 1
        key0 = (vol, pages, testator); reviewed = auto and key0 in REV
        if reviewed:
            testator, date, recips, ens, notes, t0, ex, dr = apply_review(key0, testator, date, recips, ens, notes)
            ALIAS[key0] = (vol, pages, testator); EXTRA[key0] = ex; DROP[key0] = dr; auto = False
        wid = len(wills) + 1
        cite = f"{BOOKS[vol]}, {pages}"
        q = (testator if not auto else orig.split("...")[0][:60]).replace("...", "").strip()
        link = SRC + "#:~:text=" + urllib.parse.quote(q)
        w = dict(id=wid, vol=vol, county=("King George County, VA" if vol.startswith("KG") else "Halifax County, NC"),
                 book=BOOKS[vol], pages=pages, citation=cite, date=date,
                 testator=testator, notes=notes, link=link, orig=orig, auto=auto, recipients=[], unnamed=[], enslaved=[])
        wills.append(w)
        yield w, recips, ens
        auto = fname.startswith("auto")

def firstpage(p):
    m = re.search(r"\d+", p); return int(m.group()) if m else 0
raw = []
raw += list(load("wills.txt", _j.load(open(os.path.join(here, "orig_curated.json"), encoding="utf-8")), False))
raw += list(load("auto_wills.txt", _j.load(open(os.path.join(here, "orig_auto.json"), encoding="utf-8")), True))
# order by book, then page, then file order (stable); renumber ids
order = sorted(range(len(raw)), key=lambda i: (ORDER.index(raw[i][0]["vol"]), firstpage(raw[i][0]["pages"]), i))
raw = [raw[i] for i in order]; wills[:] = [r[0] for r in raw]
for n, w in enumerate(wills, 1): w["id"] = n
for w, recips, ens in raw:
    wid = w["id"]
    tsur = surname(w["testator"])
    names.append(dict(will=wid, name=w["testator"], written=w["testator"], role="Testator", rel="", inferred=False))
    for r in [x.strip() for x in recips.split(";") if x.strip()]:
        if r.startswith("~"):
            w["unnamed"].append(r[1:].strip())
            continue
        m = re.match(r"^(.*?)\s*\(([^()]*)\)\s*$", r)
        nm, rel = (m.group(1).strip(), m.group(2).strip()) if m else (r, "")
        full, inferred = nm, False
        if len(nm.split()) == 1 and rel and FAMILY.search(rel) and "not stated" not in rel and tsur:
            full, inferred = f"{nm} {tsur}", True
        w["recipients"].append(dict(name=full, written=nm, rel=rel, inferred=inferred))
        names.append(dict(will=wid, name=full, written=nm, role="Recipient", rel=rel, inferred=inferred))
    for e in [x.strip() for x in ens.split(";") if x.strip()]:
        w["enslaved"].append(e)
        names.append(dict(will=wid, name=e, written=e, role="Enslaved person named", rel="", inferred=False))

# ---- bequests ----
from collections import defaultdict, deque
keyq = defaultdict(deque)
for w in wills:
    w["bequests"] = []
    keyq[(w["vol"], w["pages"], w["testator"])].append(w)
for _k0, _k1 in ALIAS.items():
    if _k0 != _k1: keyq[_k0] = keyq[_k1]
cur = None
unmatched = []
def _lines():
    yield from open(os.path.join(here, "bequests.txt"), encoding="utf-8")
    key = None
    for l in open(os.path.join(here, "auto_bequests.txt"), encoding="utf-8"):
        if l.startswith("@"):
            if key in EXTRA: yield from (x + "\n" for x in EXTRA[key])
            key = tuple(x.strip() for x in l[1:].rstrip("\n").split("|")); yield l; continue
        if key in DROP and any(d in l for d in DROP[key]): continue
        yield l
    if key in EXTRA: yield from (x + "\n" for x in EXTRA[key])
for line in _lines():
    line = line.rstrip("\n")
    if not line.strip() or line.startswith("#"):
        continue
    if line.startswith("@"):
        k = tuple(x.strip() for x in line[1:].split("|"))
        cur = keyq[k].popleft() if keyq[k] else None
        if cur is None: unmatched.append(k)
        continue
    if cur is None: continue
    parts = [x.strip() for x in line.split("|")]
    while len(parts) < 4: parts.append("")
    who, verb, what, cond = parts[:4]
    verb = verb.upper()
    # link enslaved names appearing in "what" (longest first, consume spans)
    text = what; linked = []
    for i, e in sorted(enumerate(cur["enslaved"]), key=lambda t: -len(t[1])):
        base = e
        pat = re.compile(r"(?<![A-Za-z])" + "[" + base[0].upper() + base[0].lower() + "]" + re.escape(base[1:]) + r"(?![A-Za-z])")
        m = pat.search(text)
        if m:
            linked.append(i)
            text = text[:m.start()] + "#" * (m.end() - m.start()) + text[m.end():]
    # also "who" may itself be an enslaved person (FREED/HIRED/CHOICE)
    if verb in ("FREED", "HIRED", "CHOICE"):
        for i, e in enumerate(cur["enslaved"]):
            if re.search(r"(?<![A-Za-z])" + re.escape(e) + r"(?![A-Za-z])", who) and i not in linked:
                linked.append(i)
    # link recipients by written name in "who"
    whoname = re.sub(r"\([^)]*\)", "", who.replace("(?)", ""))
    whorel = " ".join(re.findall(r"\(([^)]*)\)", who)).lower()
    cands = []
    for i, r in enumerate(cur["recipients"]):
        if re.search(r"(?<![A-Za-z])" + re.escape(r["written"].replace("(?)", "")) + r"(?![A-Za-z])", whoname):
            cands.append(i)
    if len(cands) > 1 and whorel:
        relfit = [i for i in cands if cur["recipients"][i]["rel"] and cur["recipients"][i]["rel"].split(",")[0].split()[0].lower() in whorel]
        if relfit: cands = relfit
    # drop shorter names contained in a longer matched name (e.g. "Mary" inside "Mary Ann Butler")
    cnames = [cur["recipients"][i]["written"] for i in cands]
    cands = [i for i in cands if not any(cur["recipients"][i]["written"] != n and re.search(r"(?<![A-Za-z])" + re.escape(cur["recipients"][i]["written"]) + r"(?![A-Za-z])", n) for n in cnames)]
    cur["bequests"].append(dict(who=who, verb=verb, what=what, cond=cond, ens=sorted(linked), rec=cands))
print("UNUSED review keys:", [k for k in REV if k not in USED])
missing = [w for w in wills if not w["bequests"]]
print("unmatched bequest headers:", unmatched)
print("wills without bequests:", [(w["vol"], w["pages"], w["testator"]) for w in missing])

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
byid = {w["id"]: w for w in wills}
with open(os.path.join(out, "halifax-wills-names.csv"), "w", newline="", encoding="utf-8") as f:
    cw = csv.writer(f)
    cw.writerow(["name", "name_as_written", "role", "relationship_as_stated", "surname_inferred_from_testator",
                 "testator", "county", "citation", "will_book", "pages", "date", "extraction", "will_notes", "source_link"])
    for n in names:
        w = byid[n["will"]]
        cw.writerow([n["name"], n["written"], n["role"], n["rel"], "yes" if n["inferred"] else "",
                     w["testator"], w["county"], w["citation"], w["book"], w["pages"], w["date"], "auto-extracted" if w["auto"] else "AI-reviewed", w["notes"], w["link"]])
with open(os.path.join(out, "halifax-wills.csv"), "w", newline="", encoding="utf-8") as f:
    cw = csv.writer(f)
    cw.writerow(["testator", "county", "citation", "will_book", "pages", "date", "extraction", "recipients", "unnamed_recipients",
                 "enslaved_people_named", "notes", "original_text", "source_link"])
    for w in wills:
        cw.writerow([w["testator"], w["county"], w["citation"], w["book"], w["pages"], w["date"], "auto-extracted" if w["auto"] else "AI-reviewed",
                     "; ".join(f'{r["name"]} ({r["rel"]})' if r["rel"] else r["name"] for r in w["recipients"]),
                     "; ".join(w["unnamed"]), "; ".join(w["enslaved"]), w["notes"], w["orig"], w["link"]])
with open(os.path.join(out, "halifax-wills-bequests.csv"), "w", newline="", encoding="utf-8") as f:
    cw = csv.writer(f)
    cw.writerow(["testator", "county", "action", "recipient", "what", "condition", "enslaved_people_named", "citation", "date", "extraction", "source_link"])
    for w in wills:
        for b in w["bequests"]:
            cw.writerow([w["testator"], w["county"], b["verb"].lower(), b["who"], b["what"], b["cond"],
                         "; ".join(w["enslaved"][i] for i in b["ens"]), w["citation"], w["date"], "auto-extracted" if w["auto"] else "AI-reviewed", w["link"]])
json.dump(wills, open(os.path.join(out, "wills.json"), "w"), ensure_ascii=False, separators=(",", ":"))

tpl = open(os.path.join(here, "page.html"), encoding="utf-8").read()
page = tpl.replace("/*__DATA__*/[]", json.dumps(wills, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))
open(os.path.join(out, "halifax-wills-index.html"), "w", encoding="utf-8").write(page)
# standalone version (full document) for static hosting
head_end = page.index("</style>") + len("</style>")
standalone = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
              '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
              + page[:head_end] + "\n</head>\n<body>\n" + page[head_end:].replace("<!--DOWNLOADS-->", '<p>Download the data: <a href="halifax-wills-names.csv">every name (CSV)</a>, <a href="halifax-wills-bequests.csv">every bequest (CSV)</a>, <a href="halifax-wills.csv">every will (CSV)</a>.</p>') + "\n</body>\n</html>\n")
open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(standalone)
print(len(wills), "wills;", len(names), "name entries;",
      sum(1 for n in names if n["role"] == "Recipient"), "recipients;",
      sum(1 for n in names if n["role"] == "Enslaved person named"), "enslaved;",
      sum(1 for n in names if n["inferred"]), "inferred surnames")
nr = [(w["testator"], w["pages"], r["name"]) for w in wills for i, r in enumerate(w["recipients"]) if not any(i in b["rec"] for b in w["bequests"])]
ne = [(w["testator"], w["pages"], e) for w in wills for i, e in enumerate(w["enslaved"]) if not any(i in b["ens"] for b in w["bequests"])]
print("recipients with no bequest:", len(nr)); print(nr[:60])
print("enslaved with no bequest:", len(ne)); print(ne[:80])
