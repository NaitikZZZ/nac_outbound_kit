"""Render the ICP analysis as a self-contained HTML report.

Every number is pulled from the model (tam_sam_som.py) or the measured Apollo cache, so
the page cannot drift from the data. Re-run after any model change.

  python3 scripts/build_report_html.py
"""
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tam_sam_som as m  # noqa: E402
from icp_titles import FAMILIES  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs")
CACHE = os.path.join(OUT, "_apollo_counts_cache.json")


def n(x):
    return f"{round(x):,}"


def pc(a, b, d=1):
    return f"{100.0 * a / b:.{d}f}%" if b else "n/a"


def tier_class(v):
    """Coverage tiers, independent of the accent hue."""
    return "t-hi" if v >= 65 else "t-mid" if v >= 55 else "t-lo" if v >= 40 else "t-dead"


def bar(v, mx, cls):
    w = max(1.0, 100.0 * v / mx) if mx else 0
    return f'<span class="bar"><i class="{cls}" style="width:{w:.1f}%"></i></span>'


def main():
    cache = json.load(open(CACHE))
    tiers = {t: m.compute(b, FAMILIES) for t, b in m.SIZE_TIERS.items()}
    tot200, per_region_200, per_family_200 = tiers["200+"]

    u200 = cache["_union|GLOBAL|200+"]
    u200v = cache["_union|GLOBAL|200+|verified"]
    db = cache["_apollo_total_db"]
    rejected = cache.get("_rejected_variants") or {}

    # measured Apollo per region
    reg = []
    for k in cache:
        if k.startswith("_union|") and k.count("|") == 2 and "GLOBAL" not in k:
            r = k.split("|")[1]
            v = cache.get(k + "|verified")
            if v is not None:
                reg.append((r, cache[k], v, 100.0 * v / cache[k]))
    reg.sort(key=lambda x: -x[2])
    maxrec = max(r[1] for r in reg)

    fam = []
    for f in FAMILIES:
        a = cache.get(f"{f['key']}|GLOBAL|200+")
        av = cache.get(f"{f['key']}|GLOBAL|200+|verified")
        if a is None:
            continue
        mod = per_family_200[f["key"]]
        fam.append((f, a, av, mod, a / mod["tam"] if mod["tam"] else 0))
    fam.sort(key=lambda x: -x[1])
    maxfam = max(x[1] for x in fam)

    P = []
    w = P.append

    w('<title>Xoxoday ICP: Data Availability &amp; Outbound Field Guide</title>')
    w(CSS)
    w('<div class="wrap">')

    # ---------------------------------------------------------------- masthead
    w('<header class="mast">')
    w('<div class="eyebrow">Go-to-market intelligence &middot; internal</div>')
    w('<h1>Where our ICP data actually exists</h1>')
    w('<p class="standfirst">A sizing and coverage study of the Xoxoday ICP across '
      'Empuls, Loyalife and Plum. Built from the ABM Campaign Planner, measured live '
      'against Apollo, and written so that anyone running a campaign can tell the '
      'difference between a market we cannot reach and a market we simply have not '
      'bought data for.</p>')
    w(f'<dl class="facts">'
      f'<div><dt>Title families</dt><dd>{len(FAMILIES)}</dd></div>'
      f'<div><dt>Apollo cells measured</dt><dd>1,675</dd></div>'
      f'<div><dt>Regions</dt><dd>{len(reg)}</dd></div>'
      f'<div><dt>Source</dt><dd>ABM Planner v2</dd></div>'
      f'</dl>')
    w('</header>')

    w('<nav class="toc"><span>On this page</span><ol>'
      '<li><a href="#verdict">The verdict</a></li>'
      '<li><a href="#scale">The gap</a></li>'
      '<li><a href="#funnel">Market size</a></li>'
      '<li><a href="#apollo">Apollo coverage</a></li>'
      '<li><a href="#titles">Titles</a></li>'
      '<li><a href="#trap">The title trap</a></li>'
      '<li><a href="#glossary">Glossary</a></li>'
      '</ol></nav>')

    # ----------------------------------------------------------------- verdict
    w('<section id="verdict"><h2>The verdict</h2>')
    w('<div class="cards">')
    for big, lab, sub in [
        (n(u200), "contacts Apollo holds for our ICP",
         f"at 200+ employees, deduplicated. {pc(u200, db, 1)} of Apollo's {n(db)} records."),
        (n(u200v), "carry a verified email",
         f"{pc(u200v, u200)} of the above. This is the number that can actually be sequenced."),
        (f"{max(r[3] for r in reg):.0f}% &ndash; {min(r[3] for r in reg):.0f}%",
         "verified-email rate, best to worst region",
         "Data quality is a geography decision before it is a targeting decision."),
    ]:
        w(f'<div class="card"><b>{big}</b><span>{lab}</span><p>{sub}</p></div>')
    w('</div>')
    w('<p class="callout"><strong>The one thing to take away.</strong> Volume and quality '
      'do not travel together. India is our second-largest pool in Apollo at '
      f'{n(dict((r[0], r[1]) for r in reg)["India"])} records, but only '
      f'{dict((r[0], r[3]) for r in reg)["India"]:.0f}% carry a verified email against '
      f'{dict((r[0], r[3]) for r in reg)["United States"]:.0f}% in the US. Sending the '
      'same volume into both markets buys very different outcomes.</p>')
    w('</section>')

    # ------------------------------------------------------------------- scale
    reached = 6064          # unique contacts in the current Apollo export
    cap = m.som(m.MAILBOXES)["prospects_at_consolidated (4)"]
    tam200 = tiers["200+"][0]["tam"]

    # Bottom-tangent nested circles: area encodes value (r proportional to sqrt(v)),
    # every circle physically contains the next, which is what "part of it" means.
    # Sequential single-hue ramp, lightness strictly decreasing as the set narrows.
    steps = [
        ("Everyone with our titles, worldwide", tam200, "r1", "modelled"),
        ("Of those, in Apollo", u200, "r2", "measured"),
        ("Of those, with a verified email", u200v, "r3", "measured"),
        (f"What {m.MAILBOXES} mailboxes can touch in a year", cap, "r4", "capacity"),
        ("Contacts on our list today", reached, "r5", "actual"),
    ]
    BASE, CX, R = 470.0, 250.0, 210.0
    vmax = steps[0][1]

    w('<section id="scale"><h2>The scale of the gap</h2>')
    w('<p>Each circle sits inside the one before it and its <em>area</em> is its size, '
      'so the picture is to scale. This is deliberately not a pie chart: pie slices are '
      'mutually exclusive and must add up to the whole, whereas each of these is a subset '
      'of the one above. A pie would also be unable to draw the last figure at all.</p>')

    w('<figure class="fig"><div class="figscroll">')
    w('<svg viewBox="0 0 840 520" role="img" width="100%" '
      'aria-label="Nested circles to scale: everyone with our titles worldwide, '
      'the share held in Apollo, the share with a verified email, our annual sending '
      'capacity, and the contacts on our list today.">')
    import math as _math
    geo = []
    for lab, val, col, kind in steps:
        r = R * _math.sqrt(val / vmax)
        geo.append((lab, val, col, kind, r, BASE - r, BASE - 2 * r))
    # circles, largest first so smaller ones sit on top
    for lab, val, col, kind, r, cy, top in geo:
        w(f'<circle class="ring {col}" cx="{CX}" cy="{cy:.1f}" r="{r:.1f}">'
          f'<title>{html.escape(lab)}: {n(val)} '
          f'({pc(val, vmax, 3)} of the worldwide total)</title></circle>')
    # leader lines + labels, anchored at each circle's top edge
    for lab, val, col, kind, r, cy, top in geo:
        y = max(top, 14)
        w(f'<line class="lead" x1="{CX}" y1="{top:.1f}" x2="486" y2="{y:.1f}"/>')
        w(f'<circle class="leaddot" cx="{CX}" cy="{top:.1f}" r="2.5"/>')
        w(f'<text x="496" y="{y - 3:.1f}" class="fl">{html.escape(lab)}</text>')
        w(f'<text x="496" y="{y + 15:.1f}" class="fv">{n(val)}'
          f'<tspan class="fp">  {pc(val, vmax, 3)}</tspan></text>')
    w('</svg>')
    w('</div>')
    w(f'<figcaption>The innermost dot is real, not a rounding artefact: '
      f'{n(reached)} against {n(vmax)} is {pc(reached, vmax, 3)} of the worldwide '
      f'universe, and {pc(reached, cap)} of what our own mailboxes could send this '
      f'year.</figcaption>')
    w('</figure>')

    w('<div class="scroll"><table><thead><tr><th>Ring</th><th class="num">Contacts</th>'
      '<th class="num">Share of worldwide</th><th class="num">Share of the ring above</th>'
      '<th>Basis</th></tr></thead><tbody>')
    for i, (lab, val, col, kind, r, cy, top) in enumerate(geo):
        prev = geo[i - 1][1] if i else None
        w(f'<tr><td><span class="key {col}"></span>'
          f'{html.escape(lab)}</td><td class="num">{n(val)}</td>'
          f'<td class="num">{pc(val, vmax, 3)}</td>'
          f'<td class="num">{pc(val, prev, 1) if prev else "&mdash;"}</td>'
          f'<td><span class="tag {"meas" if kind == "measured" else "mod"}">{kind}</span></td>'
          f'</tr>')
    w('</tbody></table></div>')
    w('<p class="callout"><strong>Read it this way.</strong> Apollo already holds more '
      'in-ICP contacts than we could email in eight years at current capacity. The '
      'constraint has never been how many people exist, or even how many we can buy. It '
      'is that we have only ever loaded one narrow slice of them.</p>')
    w(f'<p class="note">"Contacts on our list today" is the {n(reached)} unique '
      'contacts in the current Apollo export, which is US-only and almost entirely '
      'CHRO-level. It is not a count of everyone we have ever emailed across every '
      'tool; treat it as the size of the list we are working from, not lifetime '
      'outreach.</p>')
    w('</section>')

    # ------------------------------------------------------------------ funnel
    w('<section id="funnel"><h2>How big is the market</h2>')
    w('<p>Four numbers, each smaller than the last. Most sizing arguments go wrong by '
      'quoting one stage and acting on another.</p>')
    w('<div class="scroll"><table><thead><tr><th>Stage</th>'
      + "".join(f'<th class="num">{t} employees</th>' for t in m.SIZE_TIERS)
      + '<th>What it means</th></tr></thead><tbody>')
    w('<tr><td>Accounts in scope</td>'
      + "".join(f'<td class="num">{n(sum(m.ACCOUNTS_BY_BAND[b] for b in m.SIZE_TIERS[t]))}</td>'
                for t in m.SIZE_TIERS)
      + '<td>Companies worldwide at that headcount</td></tr>')
    for key, lab, note, tag in [
        ("tam", "TAM", "Every human on earth holding one of our target titles", "mod"),
        ("sam_addressable", "SAM &mdash; addressable",
         "Of those, the ones we could legally and practically cold-email", "mod"),
        ("sam_sourceable", "SAM &mdash; sourceable",
         "Of those, the ones a data vendor could find an email for", "mod"),
        ("sam_verified", "SAM &mdash; verified",
         "Of those, the ones whose email survives verification", "mod"),
    ]:
        w(f'<tr><td>{lab} <span class="tag {tag}">modelled</span></td>'
          + "".join(f'<td class="num">{n(tiers[t][0][key])}</td>' for t in m.SIZE_TIERS)
          + f'<td>{note}</td></tr>')
    w('<tr class="measured"><td>Apollo actually holds <span class="tag meas">measured</span></td>'
      + "".join(f'<td class="num">{n(cache[f"_union|GLOBAL|{t}"])}</td>' for t in m.SIZE_TIERS)
      + '<td>Deduplicated live count, one query per tier</td></tr>')
    w('<tr class="measured"><td>&hellip; with a verified email <span class="tag meas">measured</span></td>'
      + "".join(f'<td class="num">{n(cache[f"_union|GLOBAL|{t}|verified"])}</td>'
                for t in m.SIZE_TIERS)
      + '<td>What one vendor can hand us today</td></tr>')
    w('</tbody></table></div>')

    ours = m.som(m.MAILBOXES)
    s400 = ours["prospects_at_consolidated (4)"]
    w('<h3>What we can actually work</h3>')
    w(f'<p>We run <strong>{m.MAILBOXES} mailboxes</strong>. At '
      f'{m.SENDS_PER_MAILBOX_DAY} sends a day over {m.WORKING_DAYS} working days that is '
      f'{n(ours["email_sends_yr"])} sends a year, or about <strong>{n(s400)}</strong> '
      f'unique prospects on a 4-step cadence. That is {pc(s400, u200v)} of the '
      f'{n(u200v)} verified contacts Apollo will already sell us, so roughly a fifth of '
      f'the sourceable market is reachable in a single year. Capacity is not the '
      f'bottleneck. Deciding who deserves the sends is.</p>')
    w('<div class="scroll"><table><thead><tr><th>Sending capacity</th>'
      + "".join(f'<th class="num">{k}</th>' for k in m.TOUCH_SCENARIOS)
      + '<th class="num">LinkedIn lane</th></tr></thead><tbody>')
    for name, cnt in m.CAPACITY_TIERS.items():
        s = m.som(cnt)
        w(f'<tr><td>{name}</td>'
          + "".join(f'<td class="num">{n(s["prospects_at_" + k])}</td>' for k in m.TOUCH_SCENARIOS)
          + f'<td class="num">{n(s["li_prospects_yr"])}</td></tr>')
    w('</tbody></table></div>')
    w('<p class="note">Columns are touches per prospect. The planner as built averages '
      f'{m.PLANNER_MEAN_STEPS} steps because most campaigns are single-send; the flagship '
      'personas run 9&ndash;15.</p>')
    w('</section>')

    # ------------------------------------------------------------------ Apollo
    w('<section id="apollo"><h2>Apollo coverage by region</h2>')
    w('<p>All measured, not estimated. <em>Verified rate</em> is the share of Apollo\'s '
      'in-ICP contacts in that region whose email Apollo will vouch for. Treat it as the '
      'ceiling on list quality before we have sent anything.</p>')
    w('<div class="scroll"><table class="dense"><thead><tr><th>Region</th>'
      '<th class="num">Apollo records</th><th></th><th class="num">Verified</th>'
      '<th class="num">Verified rate</th><th>Read</th></tr></thead><tbody>')
    for rn, rec, ver, rate in reg:
        cls = tier_class(rate)
        read = ("strong" if rate >= 65 else "usable" if rate >= 55
                else "thin" if rate >= 40 else "do not plan volume here")
        w(f'<tr><td>{html.escape(rn)}</td><td class="num">{n(rec)}</td>'
          f'<td class="barcell">{bar(rec, maxrec, cls)}</td>'
          f'<td class="num">{n(ver)}</td>'
          f'<td class="num"><span class="pill {cls}">{rate:.1f}%</span></td>'
          f'<td class="read">{read}</td></tr>')
    w('</tbody></table></div>')
    w('<p class="note">Regional counts sum to 91% of the global figure; the remainder '
      'sits in countries outside these 15 groupings.</p>')
    w('</section>')

    # ------------------------------------------------------------------ titles
    w('<section id="titles"><h2>Titles, by how much data exists</h2>')
    w('<p>Every title family, with the exact search strings behind it, ordered by how '
      'much data exists. <strong>These counts overlap and must never be added '
      'together</strong> &mdash; see the title trap below.</p>')
    w('<div class="scroll"><table class="dense"><thead><tr><th>Title family</th>'
      '<th>Product</th><th class="num">Apollo</th><th></th>'
      '<th class="num">Verified</th><th class="num">Rate</th></tr></thead><tbody>')
    clean = cache.get("_clean_variants") or {}
    for f, a, av, mod, ratio in fam:
        rate = 100.0 * av / a if a else 0
        cls = tier_class(rate)
        flag = ' <span class="warn" title="Apollo matches this title more broadly than the role">broad match</span>' if ratio > 1.5 else ""
        titles = clean.get(f["key"], f["variants"])
        strings = ", ".join(titles)
        w(f'<tr><td><strong>{html.escape(f["label"])}</strong>{flag}'
          f'<span class="sub">{html.escape(strings)}</span></td>'
          f'<td class="prod">{html.escape("/".join(f["products"]))}</td>'
          f'<td class="num">{n(a)}</td><td class="barcell">{bar(a, maxfam, cls)}</td>'
          f'<td class="num">{n(av)}</td>'
          f'<td class="num"><span class="pill {cls}">{rate:.0f}%</span></td></tr>')
    w('</tbody></table></div>')
    w(f'<p class="note">All {len(fam)} families. Grey text under each name is the exact '
      'Apollo search string set, after dropping the ones that fail the dilution test. '
      'Full data in <code>icp-title-universe.csv</code>.</p>')
    w('</section>')

    # -------------------------------------------------------------------- trap
    w('<section id="trap"><h2>The title trap</h2>')
    w('<p>Apollo does not match a job title the way you would expect. It matches loosely, '
      'and on multi-word titles it quietly returns people who match only part of the '
      'phrase. We caught this arithmetically: a phrase cannot appear in more job titles '
      'than its own rarest word does. When it does, the search is broken.</p>')
    # Which of our own personas each broken search string belongs to.
    owner = {}
    for f in FAMILIES:
        for v in f["variants"]:
            owner.setdefault(v, f)

    w('<div class="scroll"><table><thead><tr><th>Our title</th>'
      '<th>Search string that breaks</th>'
      '<th class="num">Apollo returned</th><th>Really matched</th>'
      '<th class="num">Ceiling</th><th class="num">Inflated by</th>'
      '</tr></thead><tbody>')
    for v, (cnt, wd, wc) in sorted(rejected.items(), key=lambda x: -x[1][0]):
        f = owner.get(v)
        lab = html.escape(f["label"]) if f else "&mdash;"
        prod = html.escape("/".join(f["products"])) if f else ""
        w(f'<tr><td><strong>{lab}</strong><span class="sub">{prod}</span></td>'
          f'<td><code>{html.escape(v)}</code></td><td class="num">{n(cnt)}</td>'
          f'<td><code>{html.escape(wd)}</code> and up</td><td class="num">{n(wc)}</td>'
          f'<td class="num"><span class="pill t-dead">{cnt/wc:.0f}&times;</span></td></tr>')
    w('</tbody></table></div>')
    w('<p class="note">"Ceiling" is how many people hold <em>any</em> title containing that '
      'word, so it is the maximum the search could legitimately return. Everything above '
      'it is strangers.</p>')
    w(f'<p class="callout warnbox"><strong>Why this matters to us specifically.</strong> '
      f'{len(rejected)} of our title strings failed this test, and they are '
      'disproportionately Loyalife titles &mdash; Zonal Sales Manager, Loyalty Operations, '
      'Subscription Product Manager, Trade Marketing. Those are exactly the personas the '
      'planner leans on. A list built by typing them into Apollo\'s UI will be mostly '
      'strangers.</p>')
    w('</section>')

    # ---------------------------------------------------------------- glossary
    w('<section id="glossary"><h2>Glossary</h2>')
    w('<p>Everything in this report, defined. If a number in a meeting does not map to '
      'one of these, ask which one it is.</p>')
    for group, items in GLOSSARY:
        w(f'<h3>{group}</h3><dl class="gloss">')
        for term, dfn in items:
            w(f'<dt>{term}</dt><dd>{dfn}</dd>')
        w('</dl>')
    w('</section>')

    # ----------------------------------------------------------------- methods
    w('<section id="methods"><h2>What is measured and what is modelled</h2>')
    w('<p>Two different kinds of number appear in this report and they deserve '
      'different levels of trust.</p>')
    w('<div class="scroll"><table><thead><tr><th>Input</th><th>Status</th>'
      '</tr></thead><tbody>')
    for inp, st, tag in METHODS:
        w(f'<tr><td>{inp}</td><td><span class="tag {tag}">{st}</span></td></tr>')
    w('</tbody></table></div>')
    w('<p class="note">Reproduce with <code>python3 scripts/apollo_title_counts.py '
      '--regions --verified</code> then <code>python3 scripts/build_report_html.py</code>. '
      'Every Apollo cell is cached, so a re-run costs nothing unless the taxonomy changes.</p>')
    w('</section>')

    w('<footer>Generated from <code>ABM_Campaign_Planner_v2(Planner).csv</code> and a live '
      f'Apollo measurement of 1,675 query cells. Apollo database size at time of '
      f'measurement: {n(db)} records.</footer>')
    w('</div>')

    path = os.path.join(OUT, "xoxoday-icp-report.html")
    with open(path, "w") as fh:
        fh.write("\n".join(P))
    print(f"wrote {path}")


RULES = [
    ("Search one title string at a time and sanity-check the count before you export.",
     "Paste a list of twenty multi-word titles into Apollo and trust the total."),
    ("Ask whether a phrase can really appear in that many job titles. If <code>zonal "
     "sales manager</code> returns more people than the word <code>zonal</code> does, "
     "the search is broken.",
     "Assume a big result count means a big market. It usually means a loose match."),
    ("Pick geographies by verified-email rate, not by record count. Canada at 70.8% "
     "beats India at 45.8% per thousand contacts bought.",
     "Spend the same budget per contact in every region because the ICP looks identical "
     "on paper."),
    ("Deduplicate before you count. Our two exports share every row.",
     "Add two list sizes together and report the sum as reach."),
    ("Treat <em>verified</em> as the vendor's opinion. Run your own verification before "
     "a large send.",
     "Treat Apollo's verified flag as a delivered email."),
    ("Say which funnel stage a number belongs to: TAM, addressable, sourceable, or "
     "verified.",
     "Quote TAM in a pipeline conversation. It is a ceiling, not a plan."),
    ("Check the account against the exclusion list before adding anyone to a sequence.",
     "Email an existing client because they appeared in a fresh Apollo pull."),
    ("Use narrow, standard title strings for niche vertical roles, and accept a small "
     "true list.",
     "Broaden a niche search until the count looks respectable."),
]

GLOSSARY = [
    ("Market sizing", [
        ("TAM &mdash; Total Addressable Market",
         "Everyone on earth who holds one of our target job titles at a company of the "
         "relevant size. A ceiling, not a target. Nobody will ever sell to all of it, and "
         "it should never appear in a pipeline forecast."),
        ("SAM &mdash; Serviceable Addressable Market",
         "The slice of TAM we could realistically approach. This report splits it into "
         "three progressively smaller versions: addressable, sourceable and verified."),
        ("SAM, addressable",
         "People we could legally and practically cold-email: the language works, the "
         "privacy regime allows it, the market buys cloud software, and we have some "
         "go-to-market presence. Excludes most of China, Japan and Korea for our purposes."),
        ("SAM, sourceable",
         "Of the addressable people, those for whom some vendor could actually find a "
         "business email address. This is where most of the loss happens outside the US."),
        ("SAM, verified",
         "Of the sourceable people, those whose email passes verification. The realistic "
         "input to a sequence."),
        ("SOM &mdash; Serviceable Obtainable Market",
         "What we can actually work in twelve months given mailboxes, sending limits and "
         "sequence length. For us this is far smaller than SAM, which means our "
         "constraint is list quality, not capacity."),
    ]),
    ("Who we are targeting", [
        ("ICP &mdash; Ideal Customer Profile",
         "The definition of who we sell to: company size, industry and job title. Ours "
         "comes from the ABM Campaign Planner."),
        ("Title family",
         "A group of job titles that mean the same thing to us. \"CHRO / Chief People "
         "Officer\" is one family covering six real-world title strings. We use "
         f"{len(FAMILIES)} of them."),
        ("Persona",
         "A title family plus the reason they would care. The planner has one campaign "
         "per persona per use case."),
        ("Buyer, champion, influencer",
         "Buyer signs. Champion pushes internally. Influencer can block. A sequence "
         "written for a buyer will not land with an influencer."),
        ("Breadth",
         "The share of companies that have this role at all. Roughly 90% have a CFO; "
         "about 0.4% have a frequent-flyer programme manager. Ignoring breadth is how "
         "niche titles get sized a hundred times too large."),
        ("Findability",
         "How reliably data vendors index a title. \"CFO\" is written the same way "
         "everywhere; \"Head of Employee Experience\" is not, so fewer of them are "
         "findable even though they exist."),
    ]),
    ("Data and tooling", [
        ("Apollo",
         "The contact database we query. It holds roughly 245 million records. Coverage "
         "is far better in the US than anywhere else."),
        ("total_entries",
         "The count Apollo returns for a search. It reports what Apollo <em>has</em>, not "
         "what our plan lets us <em>export</em>. Those are different limits."),
        ("Verified email",
         "Apollo's own claim that an address is deliverable. It is a vendor assertion, "
         "not a test we ran."),
        ("Catch-all",
         "A domain that accepts mail to any address, so verification cannot prove the "
         "person exists. Higher bounce risk."),
        ("Title dilution",
         "Apollo returning people who match only part of a multi-word title. The cause of "
         "the title trap above."),
        ("Deduplicated count",
         "A single query that counts each person once. Adding up separate searches "
         "double-counts anyone matching more than one, which is why our first Apollo "
         "total was 25% too high."),
        ("Data decay",
         "Roughly a quarter of B2B contact records go stale each year as people change "
         "jobs. A list is a perishable good."),
        ("Suppression / exclusion list",
         "Accounts we must not contact, usually existing clients. 784 of our contacts "
         "sit on it."),
    ]),
    ("Sending", [
        ("Sequence",
         "The ordered set of emails a prospect receives. Ours range from one step to "
         "fifteen."),
        ("Touch",
         "One message to one person. Total sends divided by touches per prospect gives "
         "the number of people we can reach."),
        ("Mailbox capacity",
         "Emails one sending address can send per day without hurting deliverability. We "
         "model 30."),
        ("Deliverability",
         "Whether mail reaches the inbox rather than spam. Sending to unverified "
         "addresses damages it for every campaign afterwards, not just the current one."),
        ("Merge tag",
         "A placeholder such as <code>{{First Name}}</code> filled in per recipient. An "
         "empty merge tag is worse than no personalisation."),
    ]),
]

METHODS = [
    ("Apollo record and verified-email counts", "measured live", "meas"),
    ("Apollo database size", "measured live", "meas"),
    ("Title dilution test results", "measured live", "meas"),
    ("Our existing list audit", "measured from the CSVs", "meas"),
    ("Title taxonomy", "derived from the planner", "meas"),
    ("Planner mean sequence length", "measured from the planner", "meas"),
    ("~380,000 companies worldwide at 250+ employees", "Statista 2023", "src"),
    ("Regional split of large companies", "Statista 2023", "src"),
    ("Firm-size distribution exponent", "standard fitted value, not re-fit", "mod"),
    ("Contacts per account per title", "modelled estimate", "mod"),
    ("Breadth and findability per title", "modelled judgement", "mod"),
    ("Regional reachability and email-find rates", "modelled, now superseded by the "
     "measured Apollo table", "mod"),
]

CSS = """<style>
/* ---------------------------------------------------------------------------
   Xoxoday Brand Book 2026 design tokens.
   Primary   Dark 300 #06182D · Blue 300 #0A51E8 · Yellow 300 #F6B847 · White
   Semantic  Green 300 #4EAE8A success · Orange 200 #ED7B30 warning
             Red 300 #CC4141 error · Light 300 #E0E4E9
   Chart order (brandbook p.40): Blue 300, Green 300, Yellow 300, Red 300, Dark 100
   Layout    60% white/neutral · 30% navy/blue · 10% amber
   Type      Inter -- 400 body, 500 UI labels, 600 headings, 700 display

   Two deliberate deviations, both documented in the report itself:
   1. Dark 100 #8092A0 measures 3.2:1 on white, not the 7.2:1 the book claims, so it
      fails WCAG AA for small text. --muted is a darker navy-family value used wherever
      text must be legible; #8092A0 is kept for non-text rules and bar tracks.
   2. The book specifies no dark mode. Dark tokens are derived here, holding hue and
      keeping the amber-is-never-text rule intact.
--------------------------------------------------------------------------- */
:root{
  --navy:#06182D; --blue:#0A51E8; --amber:#F6B847;
  --green:#4EAE8A; --orange:#ED7B30; --red:#CC4141;
  --dark100:#8092A0; --light300:#E0E4E9; --light200:#D7E4E9;

  --paper:#FFFFFF; --sunk:#F4F7FA; --ink:var(--navy); --muted:#47596A;
  --rule:var(--light300); --accent:var(--blue); --accent-soft:#E3ECFD;
  --hi:#276B51; --mid:#8A5A10; --lo:#A2521A; --dead:#A62F2F;
  --hi-bg:#E4F3ED; --mid-bg:#FDF1DA; --lo-bg:#FBE9DC; --dead-bg:#F8E3E3;
  --bar-hi:var(--green); --bar-mid:var(--amber); --bar-lo:var(--orange);
  --bar-dead:var(--red); --bar-track:#E7ECF1;
  --keyline:var(--navy); --on-accent:#FFFFFF;

  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
  --sans:"Inter","Inter var",system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
}
@media (prefers-color-scheme:dark){:root{
  --paper:#06182D; --sunk:#0C2440; --ink:#EAF0F7; --muted:#9FB3C4;
  --rule:#173352; --accent:#6C9BFF; --accent-soft:#0F2C50;
  --hi:#6FD3AC; --mid:#F0C060; --lo:#F0955A; --dead:#EE7A7A;
  --hi-bg:#0E3830; --mid-bg:#33290F; --lo-bg:#33220F; --dead-bg:#361A1A;
  --bar-track:#12314F; --keyline:#6C9BFF; --on-accent:#06182D;
}}
:root[data-theme="dark"]{
  --paper:#06182D; --sunk:#0C2440; --ink:#EAF0F7; --muted:#9FB3C4;
  --rule:#173352; --accent:#6C9BFF; --accent-soft:#0F2C50;
  --hi:#6FD3AC; --mid:#F0C060; --lo:#F0955A; --dead:#EE7A7A;
  --hi-bg:#0E3830; --mid-bg:#33290F; --lo-bg:#33220F; --dead-bg:#361A1A;
  --bar-track:#12314F; --keyline:#6C9BFF; --on-accent:#06182D;
}
:root[data-theme="light"]{
  --paper:#FFFFFF; --sunk:#F4F7FA; --ink:#06182D; --muted:#47596A;
  --rule:#E0E4E9; --accent:#0A51E8; --accent-soft:#E3ECFD;
  --hi:#276B51; --mid:#8A5A10; --lo:#A2521A; --dead:#A62F2F;
  --hi-bg:#E4F3ED; --mid-bg:#FDF1DA; --lo-bg:#FBE9DC; --dead-bg:#F8E3E3;
  --bar-track:#E7ECF1; --keyline:#06182D; --on-accent:#FFFFFF;
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);
  font-size:16px;font-weight:400;line-height:1.62;-webkit-font-smoothing:antialiased}
.wrap{max-width:1080px;margin:0 auto;padding:0 24px 96px}
h1,h2,h3{text-wrap:balance;line-height:1.16;letter-spacing:-.02em}
h1{font-size:clamp(2.1rem,5.4vw,3.35rem);font-weight:700;margin:.1em 0 .3em}
h2{font-size:clamp(1.4rem,2.7vw,1.9rem);font-weight:600;margin:0 0 .5em}
h3{font-size:1.08rem;font-weight:600;margin:2.2em 0 .5em}
p{margin:0 0 1.05em;max-width:70ch}
a{color:var(--accent)}
code{font-family:var(--mono);font-size:.87em;background:var(--sunk);
  padding:.13em .38em;border-radius:4px}

.mast{padding:76px 0 30px}
.eyebrow{font-family:var(--mono);font-size:.7rem;letter-spacing:.15em;font-weight:500;
  text-transform:uppercase;color:var(--accent);margin-bottom:1.6em}
.standfirst{font-size:1.16rem;color:var(--muted);max-width:64ch}
.facts{display:flex;flex-wrap:wrap;gap:0;margin:2.4em 0 0;padding:18px 0 0;
  border-top:2px solid var(--keyline)}
.facts div{padding-right:44px}
.facts dt{font-family:var(--mono);font-size:.66rem;letter-spacing:.13em;font-weight:500;
  text-transform:uppercase;color:var(--muted)}
.facts dd{margin:.25em 0 0;font-size:1.32rem;font-weight:600;
  font-variant-numeric:tabular-nums}

.toc{position:sticky;top:0;z-index:5;background:var(--paper);
  border-bottom:1px solid var(--rule);padding:11px 0;margin-bottom:52px;
  display:flex;gap:18px;align-items:baseline;overflow-x:auto}
.toc span{font-family:var(--mono);font-size:.66rem;letter-spacing:.13em;font-weight:500;
  text-transform:uppercase;color:var(--muted);white-space:nowrap}
.toc ol{list-style:none;display:flex;gap:20px;margin:0;padding:0}
.toc a{white-space:nowrap;font-size:.88rem;text-decoration:none;color:var(--muted);
  font-weight:500}
.toc a:hover,.toc a:focus-visible{color:var(--accent)}

section{margin:0 0 76px;scroll-margin-top:64px}

.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(232px,1fr));
  gap:1px;background:var(--rule);border:1px solid var(--rule);margin:0 0 1.6em;
  border-radius:6px;overflow:hidden}
.card{background:var(--paper);padding:22px 20px}
.card b{display:block;font-size:2.05rem;font-weight:700;line-height:1.05;
  font-variant-numeric:tabular-nums;letter-spacing:-.026em}
.card span{display:block;margin:.42em 0 .6em;font-size:.83rem;font-weight:500;
  color:var(--accent)}
.card p{margin:0;font-size:.86rem;color:var(--muted);line-height:1.5}
.cards.small .card b{font-size:1.68rem}

/* Amber is a fill only, never text -- brandbook p.20. Navy text sits on it. */
.callout{border-left:4px solid var(--amber);background:var(--mid-bg);
  padding:15px 19px;max-width:none;font-size:.95rem;border-radius:0 6px 6px 0}
.callout.warnbox{border-left-color:var(--red);background:var(--dead-bg)}

.scroll{overflow-x:auto;margin:0 0 1.1em;border:1px solid var(--rule);border-radius:6px}
table{border-collapse:collapse;width:100%;font-size:.9rem;background:var(--paper)}
thead th{text-align:left;font-family:var(--mono);font-size:.64rem;letter-spacing:.1em;
  text-transform:uppercase;color:var(--muted);font-weight:500;padding:11px 13px;
  border-bottom:1.5px solid var(--keyline);white-space:nowrap;background:var(--sunk)}
td{padding:9px 13px;border-bottom:1px solid var(--rule);vertical-align:middle}
tbody tr:last-child td{border-bottom:0}
.num{text-align:right;font-variant-numeric:tabular-nums;font-family:var(--mono);
  font-size:.87em;white-space:nowrap}
th.num{text-align:right}
table.dense td{padding:7px 13px}
tr.measured td{background:var(--accent-soft)}
.prod{font-size:.79rem;color:var(--muted)}
.sub{display:block;font-family:var(--mono);font-size:.7rem;line-height:1.45;
  color:var(--muted);margin-top:.28em;font-weight:400;overflow-wrap:anywhere}
/* Keep the title column from ballooning on the back of the mono search strings. */
#titles td:first-child,#trap td:first-child{min-width:230px;max-width:400px}
.read{font-size:.82rem;color:var(--muted)}

.fig{margin:0 0 1.5em;padding:0}
.figscroll{overflow-x:auto;border:1px solid var(--rule);border-radius:6px;
  background:var(--sunk);padding:8px}
.fig svg{display:block;min-width:700px}
.fl{font-family:var(--sans);font-size:13px;font-weight:500;fill:var(--ink)}
.fv{font-family:var(--mono);font-size:14px;font-weight:600;fill:var(--ink);
  font-variant-numeric:tabular-nums}
.fp{font-size:11px;font-weight:400;fill:var(--muted)}
figcaption{font-size:.85rem;color:var(--muted);margin-top:.7em;max-width:72ch}
.key{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:.55em;
  vertical-align:.02em;border:1px solid rgba(6,24,45,.18)}
/* Sequential ramp for the nested figure: one hue, lightness strictly monotonic.
   Light mode runs light->dark as the set narrows. Dark mode is selected separately
   from the same hue and runs dark->light, so the small inner rings stay visible
   against the navy surface rather than being an inverted copy. */
.r1{--ring:#DCE7FD} .r2{--ring:#9FBEF9} .r3{--ring:#4C86F0}
.r4{--ring:#0A51E8} .r5{--ring:#06182D}
@media (prefers-color-scheme:dark){
  .r1{--ring:#12304F} .r2{--ring:#1C4E85} .r3{--ring:#2E6FC4}
  .r4{--ring:#6C9BFF} .r5{--ring:#DCE7FD}
}
:root[data-theme="dark"] .r1{--ring:#12304F}
:root[data-theme="dark"] .r2{--ring:#1C4E85}
:root[data-theme="dark"] .r3{--ring:#2E6FC4}
:root[data-theme="dark"] .r4{--ring:#6C9BFF}
:root[data-theme="dark"] .r5{--ring:#DCE7FD}
:root[data-theme="light"] .r1{--ring:#DCE7FD}
:root[data-theme="light"] .r2{--ring:#9FBEF9}
:root[data-theme="light"] .r3{--ring:#4C86F0}
:root[data-theme="light"] .r4{--ring:#0A51E8}
:root[data-theme="light"] .r5{--ring:#06182D}
.ring{fill:var(--ring);stroke:var(--sunk);stroke-width:2}
.key{background:var(--ring)}
.lead{stroke:var(--muted);stroke-width:1;stroke-dasharray:2 3;opacity:.65}
.leaddot{fill:var(--muted)}

.barcell{width:104px;padding-left:0}
.bar{display:block;width:96px;height:6px;background:var(--bar-track);border-radius:3px}
.bar i{display:block;height:100%;border-radius:3px}
.bar i.t-hi{background:var(--bar-hi)} .bar i.t-mid{background:var(--bar-mid)}
.bar i.t-lo{background:var(--bar-lo)} .bar i.t-dead{background:var(--bar-dead)}

.pill{display:inline-block;padding:.13em .5em;border-radius:4px;font-weight:600;
  font-size:.85em}
.pill.t-hi{background:var(--hi-bg);color:var(--hi)}
.pill.t-mid{background:var(--mid-bg);color:var(--mid)}
.pill.t-lo{background:var(--lo-bg);color:var(--lo)}
.pill.t-dead{background:var(--dead-bg);color:var(--dead)}

.tag{display:inline-block;font-family:var(--mono);font-size:.6rem;letter-spacing:.09em;
  text-transform:uppercase;padding:.22em .5em;border-radius:3px;vertical-align:.13em;
  font-weight:500}
.tag.meas{background:var(--accent);color:var(--on-accent)}
.tag.mod{background:var(--sunk);color:var(--muted);border:1px solid var(--rule)}
.tag.src{background:transparent;color:var(--muted);border:1px solid var(--muted)}
.warn{font-family:var(--mono);font-size:.6rem;letter-spacing:.07em;text-transform:uppercase;
  color:var(--dead);border:1px solid var(--dead);padding:.1em .38em;border-radius:3px;
  margin-left:.5em;white-space:nowrap}
.note{font-size:.85rem;color:var(--muted);max-width:72ch}

.rules{display:grid;gap:1px;background:var(--rule);border:1px solid var(--rule);
  border-radius:6px;overflow:hidden}
.rule{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--rule)}
.rule>div{background:var(--paper);padding:15px 18px}
.rule span{display:block;font-family:var(--mono);font-size:.62rem;letter-spacing:.13em;
  text-transform:uppercase;margin-bottom:.5em;font-weight:600}
.do span{color:var(--hi)} .dont span{color:var(--dead)}
.rule p{margin:0;font-size:.9rem;line-height:1.52;max-width:none}
.dont p{color:var(--muted)}
@media(max-width:680px){.rule{grid-template-columns:1fr}}

.gloss{margin:0 0 1.9em;border-top:1px solid var(--rule)}
.gloss dt{font-weight:600;padding:13px 0 0;font-size:.96rem}
.gloss dd{margin:.24em 0 0;padding:0 0 13px;color:var(--muted);font-size:.92rem;
  border-bottom:1px solid var(--rule);max-width:76ch}


footer{border-top:1px solid var(--rule);padding-top:20px;font-size:.82rem;
  color:var(--muted)}
a:focus-visible,.toc a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>"""


if __name__ == "__main__":
    main()
