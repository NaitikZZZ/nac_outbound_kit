"""
Export the enriched master CSV in a HubSpot-ready format with campaign tags and data quality flags.

Usage:
  python 08_export_hubspot_csv.py \\
    --master outputs/MASTER_enriched.csv \\
    --campaign-segment-map C1=P1_API_PASSDEAL_IND_EMAIL-LI_naitik_14APR26,C2=P1_API_PASSDEAL_IND_EMAIL_naitik_14APR26 \\
    --smartlead-id-map C1=3178227,C2=3178228 \\
    --heyreach-id-map C1=614694,C2=614695 \\
    --hubspot-record-id 759186512592

If your master CSV doesn't have a 'segment' column, the campaign/smartlead/heyreach ID maps are ignored.
"""
import argparse, os, pandas as pd


def parse_map(s):
    if not s:
        return {}
    d = {}
    for pair in s.split(","):
        if "=" in pair:
            k, v = pair.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def export(master_csv, output_path, seg_map, sl_map, hr_map, hubspot_record_id, enriched_date, campaign_date):
    master = pd.read_csv(master_csv)
    print(f"Loaded {len(master)} rows from {master_csv}")

    out = pd.DataFrame()
    if hubspot_record_id:
        out["Record ID"] = hubspot_record_id

    # Email: prefer send_to_email if present, else email
    if "send_to_email" in master.columns:
        out["Email"] = master.apply(
            lambda r: str(r.get("send_to_email", "")).strip()
            if pd.notna(r.get("send_to_email")) and str(r.get("send_to_email", "")).strip() not in ("", "nan", "None")
            else str(r.get("email", "")).strip(),
            axis=1
        )
    else:
        out["Email"] = master["email"]

    out["Original Email"] = master.get("email", "")
    out["First Name"] = master.get("first_name", "").fillna("") if "first_name" in master.columns else ""
    out["Last Name"] = master.get("last_name", "").fillna("") if "last_name" in master.columns else ""
    out["Company Name"] = master.get("company", master.get("company_name", "")).fillna("") if "company" in master.columns or "company_name" in master.columns else ""

    # Job title - prefer 'title' over 'job_title'
    if "title" in master.columns:
        out["Job Title"] = master.apply(
            lambda r: str(r.get("title", "")).strip()
            if pd.notna(r.get("title")) and str(r.get("title", "")).strip() not in ("", "nan", "None")
            else str(r.get("job_title", "")).strip() if "job_title" in r else "",
            axis=1
        )
    elif "job_title" in master.columns:
        out["Job Title"] = master["job_title"].fillna("")
    else:
        out["Job Title"] = ""

    out["Phone Number"] = master.get("best_phone", "").fillna("") if "best_phone" in master.columns else ""
    out["LinkedIn URL"] = master.get("linkedin_url", "").fillna("") if "linkedin_url" in master.columns else ""
    out["City"] = master.get("city", "").fillna("") if "city" in master.columns else ""
    out["State/Region"] = master.get("state", "").fillna("") if "state" in master.columns else ""
    out["Country"] = master.get("country", "").fillna("") if "country" in master.columns else ""

    # Historic deal name
    if "deal_name" in master.columns:
        out["Deal Name (Historic)"] = master["deal_name"].fillna("")

    # Campaign tracking (if segment column present)
    if "segment" in master.columns and seg_map:
        out["Campaign Segment"] = master["segment"].map(seg_map).fillna("")
    if "segment" in master.columns and sl_map:
        out["Smartlead Campaign ID"] = master["segment"].map(sl_map).fillna("")
    if "segment" in master.columns and hr_map:
        out["HeyReach List ID"] = master["segment"].map(hr_map).fillna("")

    # Data quality
    if "zb_status" in master.columns:
        out["Email Verification Status"] = master["zb_status"].fillna("")
    if "smartlead_ready" in master.columns:
        out["Smartlead Ready"] = master["smartlead_ready"].map({True: "Yes", False: "No"}).fillna("No")
    if "heyreach_ready" in master.columns:
        out["HeyReach Ready"] = master["heyreach_ready"].map({True: "Yes", False: "No"}).fillna("No")
    if "best_phone" in master.columns:
        out["Has Phone"] = master["best_phone"].apply(
            lambda x: "Yes" if pd.notna(x) and str(x).strip() not in ("", "nan", "None") else "No"
        )

    # Enrichment metadata
    out["Enriched Date"] = enriched_date
    out["Outbound Campaign Date"] = campaign_date

    # Sort: Smartlead ready first
    if "Smartlead Ready" in out.columns:
        out = out.sort_values(["Smartlead Ready", "Campaign Segment"] if "Campaign Segment" in out.columns else "Smartlead Ready",
                             ascending=[False, True] if "Campaign Segment" in out.columns else False)

    out.to_csv(output_path, index=False)
    print(f"Saved HubSpot import CSV: {output_path} ({len(out)} rows, {len(out.columns)} columns)")


if __name__ == "__main__":
    from datetime import datetime
    parser = argparse.ArgumentParser()
    parser.add_argument("--master", required=True, help="Enriched master CSV")
    parser.add_argument("--output", default="./outputs/HUBSPOT_IMPORT.csv")
    parser.add_argument("--campaign-segment-map", default="", help="C1=NAME_1,C2=NAME_2")
    parser.add_argument("--smartlead-id-map", default="", help="C1=3178227,C2=3178228")
    parser.add_argument("--heyreach-id-map", default="", help="C1=614694,C2=614695")
    parser.add_argument("--hubspot-record-id", default="", help="Record ID column value")
    parser.add_argument("--enriched-date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--campaign-date", default=datetime.now().strftime("%Y-%m-%d"))
    args = parser.parse_args()

    export(
        args.master, args.output,
        parse_map(args.campaign_segment_map),
        parse_map(args.smartlead_id_map),
        parse_map(args.heyreach_id_map),
        args.hubspot_record_id,
        args.enriched_date, args.campaign_date
    )
