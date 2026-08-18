"""TAM / SAM / SOM model for the Xoxoday ICP defined in ABM_Campaign_Planner_v2.

Model chain
-----------
  account universe        Zipf firm-size distribution anchored on Statista's ~380k
                          companies worldwide at 250+ employees (2023)
  x industry fit          share of large companies where the product has a use case
  x seats per account     buying-center headcount per title family (icp_titles.py)
  = contact TAM           every human on earth who holds an in-ICP title

  x ICP reachability      cold-email addressable: language, GDPR posture, cloud-tech
                          adoption, Xoxoday GTM presence
  = SAM (addressable)

  x data availability     profile exists x business email findable x email verifiable
  = SAM (sourceable)      what any vendor stack could actually hand you

  capacity-bound          mailboxes x sends/day x working days / touches per prospect
  = SOM                   what you can work in 12 months

Coverage rates are MODELLED, anchored on published benchmarks:
  - Apollo: ~88% accuracy US, 60-73% international
  - Surfe 5k-contact benchmark: email find rate 65% US -> 35% global
  - LinkedIn 2026: 1.2B members, APAC 277M / Europe 257M / NA 233M, 72% ex-US
They are not measured. Apollo-measured numbers come from apollo_title_counts.py.
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from icp_titles import FAMILIES, SIZE_MULT  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs")

# --------------------------------------------------------------- account universe
# Statista: ~380,000 companies worldwide with 250+ employees (2023 est.).
ANCHOR_N, ANCHOR_SIZE = 380_000, 250
# Firm-size distribution follows a Zipf tail; 1.06 is the standard fitted exponent.
ZIPF = 1.06


def n_at_least(size):
    return ANCHOR_N * (size / ANCHOR_SIZE) ** -ZIPF


BAND_EDGES = [("200-499", 200, 500), ("500-999", 500, 1000), ("1000-4999", 1000, 5000),
              ("5000-9999", 5000, 10000), ("10000+", 10000, None)]

ACCOUNTS_BY_BAND = {}
for name, lo, hi in BAND_EDGES:
    ACCOUNTS_BY_BAND[name] = n_at_least(lo) - (n_at_least(hi) if hi else 0.0)

# Regional share of the 250+ universe. Anchored on Statista's regional split
# (Asia ~225k, North America ~41k of ~380k) then split down to GTM-relevant units.
# profile   - person has a discoverable professional profile
# email     - a business email can be found for them
# verified  - that email survives verification / is safe to send
# icp_fit   - fraction that is genuinely cold-email addressable for Xoxoday
REGIONS = {
    "United States":            dict(share=8.8,  profile=0.95, email=0.75, verified=0.85, icp_fit=0.95),
    "Canada":                   dict(share=2.0,  profile=0.92, email=0.70, verified=0.83, icp_fit=0.90),
    "UK & Ireland":             dict(share=3.0,  profile=0.92, email=0.62, verified=0.80, icp_fit=0.90),
    "DACH / Benelux / France":  dict(share=8.5,  profile=0.85, email=0.45, verified=0.75, icp_fit=0.55),
    "Nordics":                  dict(share=2.0,  profile=0.88, email=0.50, verified=0.78, icp_fit=0.70),
    "S. & E. Europe":           dict(share=8.5,  profile=0.75, email=0.35, verified=0.70, icp_fit=0.40),
    "India":                    dict(share=7.1,  profile=0.85, email=0.55, verified=0.75, icp_fit=0.95),
    "SEA":                      dict(share=6.6,  profile=0.75, email=0.42, verified=0.72, icp_fit=0.75),
    "Middle East":              dict(share=2.5,  profile=0.70, email=0.40, verified=0.70, icp_fit=0.80),
    "Australia & NZ":           dict(share=1.5,  profile=0.90, email=0.62, verified=0.82, icp_fit=0.85),
    "LatAm":                    dict(share=4.0,  profile=0.68, email=0.32, verified=0.68, icp_fit=0.35),
    "Africa":                   dict(share=2.6,  profile=0.55, email=0.25, verified=0.62, icp_fit=0.45),
    "China":                    dict(share=32.6, profile=0.25, email=0.10, verified=0.55, icp_fit=0.05),
    "Japan":                    dict(share=7.1,  profile=0.45, email=0.18, verified=0.65, icp_fit=0.15),
    "South Korea":              dict(share=3.6,  profile=0.40, email=0.15, verified=0.62, icp_fit=0.15),
}
_tot = sum(r["share"] for r in REGIONS.values())
for r in REGIONS.values():
    r["w"] = r["share"] / _tot

# Data vendors cover large enterprises materially better than 200-person firms:
# more web footprint, more press, more scraped org charts, more email-pattern signal.
BAND_COVERAGE_LIFT = {
    "200-499": 0.80,
    "500-999": 0.90,
    "1000-4999": 1.00,
    "5000-9999": 1.10,
    "10000+": 1.15,
}

# Share of large companies where each product has a live use case.
INDUSTRY_FIT = {"Empuls": 0.75, "Loyalife": 0.20, "Plum": 0.55}

SIZE_TIERS = {
    "200+":  ["200-499", "500-999", "1000-4999", "5000-9999", "10000+"],
    "1000+": ["1000-4999", "5000-9999", "10000+"],
    "5000+": ["5000-9999", "10000+"],
}


def fit_for(family):
    """Share of accounts that have this role at all.

    Per-TITLE breadth, not per-product industry fit: a Head of Cards exists in ~4% of
    large companies regardless of the fact that Loyalife nominally addresses 20% of them.
    """
    return family["breadth"]


def compute(bands, families, region_filter=None):
    """Return the full funnel for a set of size bands x title families x regions."""
    out = dict(tam=0.0, sam_addressable=0.0, sam_sourceable=0.0, sam_verified=0.0)
    per_region, per_family = {}, {}
    for rname, r in REGIONS.items():
        if region_filter and rname not in region_filter:
            continue
        acct = sum(ACCOUNTS_BY_BAND[b] * r["w"] for b in bands)
        row = dict(tam=0.0, sam_addressable=0.0, sam_sourceable=0.0, sam_verified=0.0,
                   accounts=acct)
        for f in families:
            fit = fit_for(f)
            tam = addr = src = ver = 0.0
            for b in bands:
                seats = ACCOUNTS_BY_BAND[b] * r["w"] * f["seats"] * SIZE_MULT[b]
                b_tam = seats * fit
                b_addr = b_tam * r["icp_fit"]
                # coverage lift is capped so a band can never exceed a perfect find rate
                find = min(1.0, r["profile"] * r["email"] * BAND_COVERAGE_LIFT[b]
                           * f["findability"])
                b_src = b_addr * find
                tam += b_tam
                addr += b_addr
                src += b_src
                ver += b_src * r["verified"]
            row["tam"] += tam
            row["sam_addressable"] += addr
            row["sam_sourceable"] += src
            row["sam_verified"] += ver
            pf = per_family.setdefault(f["key"], dict(label=f["label"], role=f["role"],
                                                      products="/".join(f["products"]),
                                                      breadth=f["breadth"],
                                                      findability=f["findability"],
                                                      tam=0.0, sam_addressable=0.0,
                                                      sam_sourceable=0.0, sam_verified=0.0))
            pf["tam"] += tam
            pf["sam_addressable"] += addr
            pf["sam_sourceable"] += src
            pf["sam_verified"] += ver
        per_region[rname] = row
        for k in out:
            out[k] += row[k]
    return out, per_region, per_family


# ------------------------------------------------------------------------- SOM
# Measured from the planner: 475 campaigns carry a sequence length, mean 1.87 steps.
# 357 are single-step (one use case = one send), but the P1 flagship personas run
# 9-15 steps. Touch count per PROSPECT is what bounds SOM, so show a sensitivity grid.
PLANNER_MEAN_STEPS = 1.87
TOUCH_SCENARIOS = {"planner as-built (1.9)": 1.87, "consolidated (4)": 4.0,
                   "full nurture (8)": 8.0}
WORKING_DAYS = 250
SENDS_PER_MAILBOX_DAY = 30
LI_TOUCHES = 3.0
LI_ACTIONS_PER_SEAT_DAY = 22

MAILBOXES = 400  # actual estate
CAPACITY_TIERS = {"100 mailboxes": 100, "200 mailboxes": 200,
                  "400 mailboxes (ours)": MAILBOXES}


def som(mailboxes, li_seats=None):
    li_seats = li_seats if li_seats is not None else max(1, mailboxes // 5)
    email_sends = mailboxes * SENDS_PER_MAILBOX_DAY * WORKING_DAYS
    li_actions = li_seats * LI_ACTIONS_PER_SEAT_DAY * WORKING_DAYS
    return dict(mailboxes=mailboxes, li_seats=li_seats,
                email_sends_yr=email_sends, li_actions_yr=li_actions,
                li_prospects_yr=li_actions / LI_TOUCHES,
                **{f"prospects_at_{k}": email_sends / v for k, v in TOUCH_SCENARIOS.items()})


def main():
    report = dict(model=dict(anchor_250plus=ANCHOR_N, zipf=ZIPF,
                             accounts_by_band={k: round(v) for k, v in ACCOUNTS_BY_BAND.items()},
                             industry_fit=INDUSTRY_FIT,
                             band_coverage_lift=BAND_COVERAGE_LIFT,
                             planner_mean_steps=PLANNER_MEAN_STEPS,
                             touch_scenarios=TOUCH_SCENARIOS))

    # --- headline funnel at each size tier, every title family
    report["tiers"] = {}
    for tier, bands in SIZE_TIERS.items():
        tot, per_region, per_family = compute(bands, FAMILIES)
        report["tiers"][tier] = dict(
            accounts=round(sum(ACCOUNTS_BY_BAND[b] for b in bands)),
            **{k: round(v) for k, v in tot.items()},
            per_region={k: {kk: round(vv) for kk, vv in v.items()} for k, v in per_region.items()},
        )

    # --- per product at the 200+ tier
    report["by_product"] = {}
    for prod in INDUSTRY_FIT:
        fams = [f for f in FAMILIES if prod in f["products"]]
        tot, _, _ = compute(SIZE_TIERS["200+"], fams)
        report["by_product"][prod] = dict(families=len(fams),
                                          **{k: round(v) for k, v in tot.items()})

    # --- per title family at the 200+ tier
    _, _, per_family = compute(SIZE_TIERS["200+"], FAMILIES)
    report["by_family"] = {k: {kk: (round(vv) if isinstance(vv, float) else vv)
                               for kk, vv in v.items()} for k, v in per_family.items()}

    # --- SOM
    report["som"] = {name: {k: round(v) for k, v in som(n).items()}
                     for name, n in CAPACITY_TIERS.items()}

    with open(os.path.join(OUT, "tam-sam-som-model.json"), "w") as f:
        json.dump(report, f, indent=1)

    # --- CSV: per-title-family funnel
    with open(os.path.join(OUT, "icp-title-universe.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Title family", "Products", "Buying role", "% of accounts with role",
                    "Findability index", "TAM (global holders)", "SAM addressable",
                    "SAM sourceable", "SAM verified-email", "Global data availability %"])
        for k, v in sorted(per_family.items(), key=lambda x: -x[1]["tam"]):
            avail = 100.0 * v["sam_verified"] / v["tam"] if v["tam"] else 0.0
            w.writerow([v["label"], v["products"], v["role"],
                        f"{v['breadth'] * 100:.1f}", f"{v['findability']:.2f}",
                        round(v["tam"]), round(v["sam_addressable"]),
                        round(v["sam_sourceable"]), round(v["sam_verified"]),
                        f"{avail:.1f}"])

    # --- CSV: per-region funnel at 200+
    with open(os.path.join(OUT, "icp-region-coverage.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Region", "Accounts 200+", "TAM contacts", "SAM addressable",
                    "SAM sourceable", "SAM verified-email", "Data availability %",
                    "profile %", "email-find %", "verify %", "ICP reachability %"])
        _, per_region, _ = compute(SIZE_TIERS["200+"], FAMILIES)
        for rname, row in sorted(per_region.items(), key=lambda x: -x[1]["tam"]):
            r = REGIONS[rname]
            avail = 100.0 * row["sam_verified"] / row["tam"] if row["tam"] else 0.0
            w.writerow([rname, round(row["accounts"]), round(row["tam"]),
                        round(row["sam_addressable"]), round(row["sam_sourceable"]),
                        round(row["sam_verified"]), f"{avail:.1f}",
                        int(r["profile"] * 100), int(r["email"] * 100),
                        int(r["verified"] * 100), int(r["icp_fit"] * 100)])

    # --- console summary
    print("ACCOUNTS BY BAND (global)")
    for k, v in ACCOUNTS_BY_BAND.items():
        print(f"  {k:>10}  {round(v):>9,}")
    print(f"  {'TOTAL 200+':>10}  {round(sum(ACCOUNTS_BY_BAND.values())):>9,}\n")

    print(f"FUNNEL BY SIZE TIER (all {len(FAMILIES)} title families)")
    hdr = f"  {'tier':<7}{'accounts':>10}{'TAM':>12}{'SAM addr':>12}{'SAM src':>12}{'SAM verif':>12}{'avail%':>8}"
    print(hdr)
    for tier in SIZE_TIERS:
        t = report["tiers"][tier]
        avail = 100.0 * t["sam_verified"] / t["tam"]
        print(f"  {tier:<7}{t['accounts']:>10,}{t['tam']:>12,}{t['sam_addressable']:>12,}"
              f"{t['sam_sourceable']:>12,}{t['sam_verified']:>12,}{avail:>7.1f}%")

    print("\nBY PRODUCT (200+ tier)")
    for p, v in report["by_product"].items():
        print(f"  {p:<9} {v['families']:>2} families  TAM {v['tam']:>10,}  "
              f"addr {v['sam_addressable']:>9,}  verif {v['sam_verified']:>9,}")

    print("\nSOM: unique email prospects reachable per 12 months")
    print(f"  {'capacity':<14}" + "".join(f"{k:>26}" for k in TOUCH_SCENARIOS)
          + f"{'LinkedIn lane':>16}")
    for name, v in report["som"].items():
        cells = "".join(f"{v['prospects_at_' + k]:>26,}" for k in TOUCH_SCENARIOS)
        print(f"  {name:<14}{cells}{v['li_prospects_yr']:>16,}")

    print("\nwrote outputs/tam-sam-som-model.json, icp-title-universe.csv, icp-region-coverage.csv")


if __name__ == "__main__":
    main()
