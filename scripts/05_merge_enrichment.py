"""
Merge Apollo + Clay + ZeroBounce enrichment outputs into a single master CSV.

Inputs (all optional, script detects what exists):
  - apollo_found.csv             (from 01_apollo_bulk_lookup.py)
  - apollo_enriched_new.csv      (from 02_apollo_enrich_missing.py)
  - apollo_phones_final.csv      (from 03_apollo_pull_phones.py)
  - clay_work_email_export.csv   (from Clay work-email waterfall, has "Work Email" column)
  - clay_phone_export.csv        (from Clay phone waterfall, has "Mobile Phone" column)
  - zerobounce_results.csv       (from 04_zerobounce_verify.py)

Output: MASTER_enriched.csv - one row per lead with all enrichment merged.

Usage:
  python 05_merge_enrichment.py --input-dir ./outputs --original leads.csv
"""
import argparse, os, sys, pandas as pd


def merge_all(input_dir, original_csv, output_path):
    # Start with original leads
    master = pd.read_csv(original_csv)
    master["email"] = master["email"].astype(str).str.lower().str.strip()
    print(f"Loaded {len(master)} original leads from {original_csv}")

    # Apollo found
    p = os.path.join(input_dir, "apollo_found.csv")
    if os.path.exists(p):
        apollo = pd.read_csv(p).drop_duplicates(subset="email_original", keep="first")
        apollo["email_original"] = apollo["email_original"].astype(str).str.lower().str.strip()
        apollo = apollo.rename(columns={"email_original": "email"})
        master = master.merge(apollo, on="email", how="left", suffixes=("", "_apollo"))
        print(f"  Merged apollo_found: {len(apollo)} rows")

    # Apollo enrich_missing
    p = os.path.join(input_dir, "apollo_enriched_new.csv")
    if os.path.exists(p):
        enriched = pd.read_csv(p).drop_duplicates(subset="email_original", keep="first")
        enriched["email_original"] = enriched["email_original"].astype(str).str.lower().str.strip()
        enriched = enriched.rename(columns={"email_original": "email"})
        # Fill nulls from enriched
        for _, row in enriched.iterrows():
            idx = master[master["email"] == row["email"]].index
            if len(idx):
                for col in ["first_name", "last_name", "title", "linkedin_url", "organization_name", "best_phone", "city", "country"]:
                    if col in row and pd.notna(row[col]):
                        cur = master.at[idx[0], col] if col in master.columns else None
                        if pd.isna(cur) or str(cur).strip() in ("", "nan", "None"):
                            master.at[idx[0], col] = row[col]
        print(f"  Merged apollo_enriched_new: {len(enriched)} rows")

    # Apollo phones
    p = os.path.join(input_dir, "apollo_phones_final.csv")
    if os.path.exists(p):
        phones = pd.read_csv(p).drop_duplicates(subset="email_original", keep="first")
        phones["email_original"] = phones["email_original"].astype(str).str.lower().str.strip()
        phones = phones.rename(columns={"email_original": "email"})[["email", "best_phone"]].dropna()
        # Only fill where missing
        for _, row in phones.iterrows():
            idx = master[master["email"] == row["email"]].index
            if len(idx) and str(row["best_phone"]).strip() not in ("", "nan"):
                cur = master.at[idx[0], "best_phone"] if "best_phone" in master.columns else None
                if pd.isna(cur) or str(cur).strip() in ("", "nan", "None"):
                    master.at[idx[0], "best_phone"] = row["best_phone"]
        print(f"  Merged apollo_phones: {len(phones)} rows")

    # Clay work email
    p = os.path.join(input_dir, "clay_work_email_export.csv")
    if os.path.exists(p):
        clay = pd.read_csv(p)
        clay["email"] = clay["email"].astype(str).str.lower().str.strip()
        if "Work Email" in clay.columns:
            clay = clay[["email", "Work Email"]].rename(columns={"Work Email": "clay_work_email"})
            master = master.merge(clay, on="email", how="left")
            print(f"  Merged Clay work emails: {clay['clay_work_email'].notna().sum()} valid")

    # Clay phone
    p = os.path.join(input_dir, "clay_phone_export.csv")
    if os.path.exists(p):
        clayp = pd.read_csv(p)
        clayp["email"] = clayp["email"].astype(str).str.lower().str.strip()
        phone_col = "Mobile Phone" if "Mobile Phone" in clayp.columns else None
        if phone_col:
            clayp = clayp[["email", phone_col]].rename(columns={phone_col: "clay_phone"})
            for _, row in clayp.iterrows():
                idx = master[master["email"] == row["email"]].index
                if len(idx) and pd.notna(row["clay_phone"]) and str(row["clay_phone"]).strip() not in ("", "nan"):
                    cur = master.at[idx[0], "best_phone"] if "best_phone" in master.columns else None
                    if pd.isna(cur) or str(cur).strip() in ("", "nan", "None"):
                        master.at[idx[0], "best_phone"] = row["clay_phone"]
            print(f"  Merged Clay phones")

    # ZeroBounce
    p = os.path.join(input_dir, "zerobounce_results.csv")
    if os.path.exists(p):
        zb = pd.read_csv(p)[["email", "zb_status", "zb_sub_status"]]
        zb["email"] = zb["email"].astype(str).str.lower().str.strip()
        master = master.merge(zb, on="email", how="left")
        print(f"  Merged ZeroBounce: {(zb['zb_status']=='valid').sum()} valid")

    # Compute readiness flags
    master["smartlead_ready"] = master["zb_status"].isin(["valid", "catch-all"]) if "zb_status" in master.columns else False
    master["heyreach_ready"] = master["linkedin_url"].notna() & (master["linkedin_url"].astype(str).str.strip() != "") & (master["linkedin_url"].astype(str) != "nan") if "linkedin_url" in master.columns else False

    # Build send_to_email: Clay work email if present and different, else original
    if "clay_work_email" in master.columns:
        master["send_to_email"] = master.apply(
            lambda r: str(r["clay_work_email"]).strip()
            if pd.notna(r.get("clay_work_email")) and str(r.get("clay_work_email", "")).strip() not in ("", "nan", "None")
            else str(r["email"]).strip(),
            axis=1
        )
    else:
        master["send_to_email"] = master["email"]

    master.to_csv(output_path, index=False)
    print(f"\nSaved master to {output_path} ({len(master)} rows, {len(master.columns)} columns)")

    # Summary
    print("\n=== FINAL DATA QUALITY ===")
    print(f"  Total leads:       {len(master)}")
    print(f"  Smartlead ready:   {master['smartlead_ready'].sum()}")
    print(f"  HeyReach ready:    {master['heyreach_ready'].sum()}")
    if "best_phone" in master.columns:
        phone_count = master["best_phone"].notna() & (master["best_phone"].astype(str).str.strip() != "") & (master["best_phone"].astype(str) != "nan")
        print(f"  Has phone:         {phone_count.sum()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="./outputs", help="Folder with enrichment CSVs")
    parser.add_argument("--original", required=True, help="Original leads CSV (must have 'email' column)")
    parser.add_argument("--output", default="./outputs/MASTER_enriched.csv")
    args = parser.parse_args()
    merge_all(args.input_dir, args.original, args.output)
