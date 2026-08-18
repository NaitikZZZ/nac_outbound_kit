"""ICP clusters + one senior-only Clay search query per cluster, from the ABM planner.

The planner (data/ABM_Campaign_Planner_v2.csv) is organised at job-title level: one row
per persona x region x send date. This script rolls those rows up into one cluster per
distinct `Persona (Job Title)` value and emits a Clay people query for each.

Deliberately NOT a taxonomy. icp_titles.py collapses the planner's 206 raw persona
strings into 60 canonical families; this script keeps all 206 exactly as the sheet
writes them, because the sheet's cluster == campaign == one Clay list. Junk-looking
titles ("site", "manager") are kept and flagged in `title_quality` instead of dropped,
so the emitted query set stays 1:1 with the planner's campaign set.

Every query is gated to senior people via the experience `seniority` enum. Titles go in
as `job_title is_similar_to (...)` because Clay expands a title into its own synonyms
and abbreviations, so no hand-written variant lists here.

Outputs:
  outputs/icp-clusters.csv               one row per cluster, query in the last column
  outputs/icp-clusters-clay-queries.md   the same queries, grouped for copy-paste
"""
import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLANNER = ROOT / "data" / "ABM_Campaign_Planner_v2.csv"
OUT = ROOT / "outputs"

# Row 0 of the planner is a one-cell preamble blurb; row 1 is the real header.
HEADER_ROW = 1

# Experience-seniority enum values that count as senior. Order is fixed so the emitted
# queries are byte-stable across runs. These are Clay's exact enum strings: the field
# only supports = / != / in / not_in, so they must match verbatim.
SENIORITY = ["Founder", "Owner", "Board Member", "Partner", "C-suite", "VP", "Head",
             "Director", "Senior"]

# Clay company table the queries scope to. Overridable with --table.
DEFAULT_TABLE = "t_0tjls37SF4EdmKRoZfK:gv_0tjls39M4MbywSYCvtR:f_0tjls68msVKDPjEgeUQ"

PRIORITY_RANK = {"P1": 0, "P2": 1, "P3": 2}

# Titles the sheet's own parsing left behind as fragments rather than real job titles.
# Advisory only: these clusters are still emitted, just flagged.
TITLE_FRAGMENTS = {"site", "manager", "admin", "panel", "brand", "retailer", "payroll"}

COL_REGION = "Region"
COL_GEO = "Target Geography (this send)"
COL_PERSONA = "Persona (Job Title)"
COL_PRIORITY = "Priority"
COL_STREAM = "Stream"
COL_USECASES = "Use Cases Covered (Buyer / Champion / Influencer-User)"
COL_CAMPAIGN = "Campaign Name"
REQUIRED = [COL_REGION, COL_GEO, COL_PERSONA, COL_PRIORITY, COL_STREAM, COL_USECASES,
            COL_CAMPAIGN]


def load_rows(path):
    """Read the planner into dicts keyed by the row-1 header. Exits on a bad file."""
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            raw = list(csv.reader(f))
    except FileNotFoundError:
        sys.exit(f"planner not found: {path}")
    except OSError as exc:
        sys.exit(f"cannot read {path}: {exc}")
    except UnicodeDecodeError as exc:
        sys.exit(f"{path} is not utf-8 text: {exc}")

    if len(raw) <= HEADER_ROW + 1:
        sys.exit(f"{path} has no data rows below the header")
    header = [h.strip() for h in raw[HEADER_ROW]]
    missing = [c for c in REQUIRED if c not in header]
    if missing:
        sys.exit(f"{path} header is missing expected columns: {', '.join(missing)}")

    rows = []
    for cells in raw[HEADER_ROW + 1:]:
        if not any(c.strip() for c in cells):
            continue
        # Short rows are padded rather than skipped; trailing Notes cells are often blank.
        cells = cells + [""] * (len(header) - len(cells))
        rows.append(dict(zip(header, cells)))
    return rows


def parse_persona(text):
    """'Head of Total Rewards (Plum)' -> ('Head of Total Rewards', 'Plum')."""
    m = re.match(r"^(.*?)\(([^()]*)\)\s*$", text.strip())
    if not m:
        return " ".join(text.split()), ""
    return " ".join(m.group(1).split()), " ".join(m.group(2).split())


def use_case_names(cell):
    """Pull bare use-case names out of the multi-line Use Cases cell.

    Each line reads '3. Service milestone & anniversary rewards - Buyer: CHRO | ...'.
    Drop the numbering and everything from ' - Buyer:' on, keeping just the name.
    """
    names = []
    for line in cell.splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^\d+\.\s*", "", line)
        line = line.split(" - Buyer:", 1)[0]
        name = " ".join(line.split())
        if name:
            names.append(name)
    return names


def slugify(text):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def title_quality(title):
    """Advisory flag. Nothing is dropped on the strength of this."""
    if title.lower() in TITLE_FRAGMENTS:
        return "low"
    if not any(c.isupper() for c in title):
        return "low"
    return "ok"


def build_clusters(rows):
    """One cluster per distinct persona string, rolled up across its source rows."""
    acc = {}
    for row in rows:
        persona = row[COL_PERSONA].strip()
        if not persona:
            continue  # 134 planner rows carry no persona (calendar spacers, notes)
        c = acc.setdefault(persona, dict(persona=persona, regions=set(), geographies=set(),
                                         streams=set(), campaign_names=set(),
                                         use_cases=set(), priorities=set(), count=0))
        c["count"] += 1
        for key, col in (("regions", COL_REGION), ("geographies", COL_GEO),
                         ("streams", COL_STREAM), ("campaign_names", COL_CAMPAIGN)):
            val = row[col].strip()
            if val:
                c[key].add(val)
        priority = row[COL_PRIORITY].strip()
        if priority:
            c["priorities"].add(priority)
        c["use_cases"].update(use_case_names(row[COL_USECASES]))

    clusters = []
    for c in acc.values():
        title, product = parse_persona(c["persona"])
        # Highest priority wins: a persona worked as P1 in any send is a P1 cluster.
        prio = sorted(c["priorities"], key=lambda p: PRIORITY_RANK.get(p, 99))
        clusters.append(dict(
            title=title,
            product=product,
            priority=prio[0] if prio else "",
            regions="|".join(sorted(c["regions"])),
            geographies="|".join(sorted(c["geographies"])),
            streams="|".join(sorted(c["streams"])),
            campaign_count=c["count"],
            campaign_names="|".join(sorted(c["campaign_names"])),
            use_cases="|".join(sorted(c["use_cases"])),
            use_case_count=len(c["use_cases"]),
            title_quality=title_quality(title),
        ))

    clusters.sort(key=lambda c: (c["product"].lower(),
                                 PRIORITY_RANK.get(c["priority"], 99),
                                 c["title"].lower()))

    # Slugs are assigned after the sort so collision suffixes are deterministic.
    seen = {}
    for c in clusters:
        base = slugify(f"{c['product']}-{c['title']}") or "cluster"
        seen[base] = seen.get(base, 0) + 1
        c["cluster_id"] = base if seen[base] == 1 else f"{base}-{seen[base]}"
    return clusters


def clay_query(title, table, limit):
    """Senior-gated people query for one title, scoped to the Clay company table.

    clay.filter_to_companies stays at the TOP level: it means "currently at one of these
    companies", so nesting it inside experiences.any(...) would be wrong. The second
    experiences.count clause keeps anyone without a current role out of the result.
    """
    seniority = ", ".join(f'"{s}"' for s in SENIORITY)
    safe_title = title.replace('"', '\\"')
    return (
        "select from people\n"
        f"where experiences.count(is_current = true and seniority in ({seniority}) "
        f'and job_title is_similar_to ("{safe_title}")) >= 1\n'
        "  and experiences.count(is_current = true) >= 1\n"
        f'  and clay.filter_to_companies(@table("{table}"))\n'
        f"limit {limit} by clay_company_id"
    )


CSV_COLUMNS = ["cluster_id", "title", "product", "priority", "regions", "geographies",
               "streams", "campaign_count", "use_case_count", "title_quality",
               "use_cases", "campaign_names", "clay_query"]


def write_csv(clusters, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(CSV_COLUMNS)
        for c in clusters:
            w.writerow([c[col] for col in CSV_COLUMNS])


def write_markdown(clusters, path, table, limit):
    lines = ["# ICP clusters: Clay search queries", ""]
    lines.append(f"{len(clusters)} clusters from the ABM planner, one query each. "
                 "Every query is gated to senior people only, via the experience "
                 "seniority enum: " + ", ".join(SENIORITY) + ".")
    lines.append("")
    lines.append(f"Company scope: `@table(\"{table}\")`. Per-company cap: {limit}.")
    lines.append("")

    # Clusters arrive sorted product > priority > title, so a product heading plus the
    # per-cluster metadata line is enough grouping; priority stays out of the heading
    # tree so every cluster heading sits at the same level.
    product = None
    for c in clusters:
        if c["product"] != product:
            product = c["product"]
            lines += [f"## {product or 'No product'}", ""]
        lines.append(f"### {c['title']} - {c['product']}")
        lines.append(f"Priority {c['priority'] or 'unset'} | regions "
                     f"{c['regions'] or 'none'} | geographies "
                     f"{c['geographies'] or 'none'} | {c['use_case_count']} use cases "
                     f"| {c['campaign_count']} planner rows")
        lines += ["", "```", c["clay_query"], "```", ""]

    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--planner", default=str(PLANNER), help="path to the ABM planner CSV")
    ap.add_argument("--table", default=DEFAULT_TABLE,
                    help="Clay company table reference to scope every query to")
    ap.add_argument("--limit", type=int, default=10,
                    help="per-company people cap (limit N by clay_company_id)")
    args = ap.parse_args()

    if args.limit < 1:
        sys.exit("--limit must be at least 1")

    rows = load_rows(Path(args.planner))
    clusters = build_clusters(rows)
    if not clusters:
        sys.exit("no persona rows found in the planner, nothing to cluster")
    for c in clusters:
        c["clay_query"] = clay_query(c["title"], args.table, args.limit)

    OUT.mkdir(exist_ok=True)
    csv_path = OUT / "icp-clusters.csv"
    md_path = OUT / "icp-clusters-clay-queries.md"
    write_csv(clusters, csv_path)
    write_markdown(clusters, md_path, args.table, args.limit)

    # --- console summary
    by_product = {}
    for c in clusters:
        p = by_product.setdefault(c["product"] or "(none)",
                                  dict(n=0, p1=0, low=0, ucs=0))
        p["n"] += 1
        p["p1"] += 1 if c["priority"] == "P1" else 0
        p["low"] += 1 if c["title_quality"] == "low" else 0
        p["ucs"] += c["use_case_count"]

    print(f"planner rows read: {len(rows)}  clusters built: {len(clusters)}")
    print(f"  {'product':<10}{'clusters':>10}{'P1':>6}{'low-qual title':>16}{'use-case links':>16}")
    for name, p in sorted(by_product.items()):
        print(f"  {name:<10}{p['n']:>10}{p['p1']:>6}{p['low']:>16}{p['ucs']:>16}")
    print(f"senior-only seniority gate: {', '.join(SENIORITY)}")
    print(f"wrote {csv_path.relative_to(ROOT)}, {md_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
