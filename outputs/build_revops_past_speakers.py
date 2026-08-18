"""Build CSV of PRIOR-edition speakers for recurring Revenue Operations Alliance
summits, recovered from Wayback Machine snapshots (these lineups were overwritten
on the live site when the next year's edition went up).

Coverage note: archived pages only render the static "a snapshot of our speakers"
subset (not the full 150+ roster), and not every prior edition was archived.
Captured 2026-06-25.
"""
import csv

PAST = [
    {
        "event": "Revenue Operations Summit - San Francisco (2025 edition)",
        "edition_date": "2025-09-16", "location": "San Francisco",
        "snapshot": "https://web.archive.org/web/20250620103331/https://events.revenueoperationsalliance.com/location/sanfrancisco/speakers",
        "speakers": [
            ("Tom Germack", "SVP, Revenue Operations", "Oracle"),
            ("Jiaxi Zhu", "Head, Analytics & Insights", "Google"),
            ("Mike Lee", "Senior Director, Global Revenue Operations, Reality Labs", "Meta"),
            ("Jan Foo", "Senior Director, GTM Operations", "ServiceNow"),
            ("Fidel Rodriguez", "Senior Director, GTM Tech & Analytics", "LinkedIn"),
            ("Tana Jackson", "VP, Operations", "Upright Labs"),
            ("Joe Aurilia, Jr", "SVP of Operations", "Cyware"),
            ("Meltem Zando", "Sales Operations Lead", "AWS"),
            ("Erin Myers", "Director, Revenue Operations", "Cisco"),
            ("Andrew Kodner", "VP, Revenue Operations & Enablement", "Bazaarvoice"),
            ("Naoki Suzuki Cartes", "Lead, Sales Operations & Strategy", "Uber"),
            ("Stephen Daniels", "VP, Revenue Operations", "Cresta"),
            ("Olga Traskova", "VP, Revenue Operations", "Birdeye"),
            ("Aneet Narang", "Former Head, Global Revenue Enablement", "PayPal"),
            ("Tanvir Gopal", "Director, Sales Operations", "Cast & Crew"),
            ("Akansha Aggarwal", "Senior Director, Americas GTM Strategy & Operations", "NetApp"),
            ("Kunal Pathak", "Director, Deal Strategy & Operations", "ServiceNow"),
        ],
    },
    {
        "event": "Revenue Operations Summit - London (2025 edition)",
        "edition_date": "2025-12-03", "location": "London",
        "snapshot": "https://web.archive.org/web/20251114204544/https://events.revenueoperationsalliance.com/location/london/speakers",
        "speakers": [
            ("Simon Mitchell", "Head of EMEA Sales Strategy and Operations - Startups", "Amazon Web Services"),
            ("Amr ElGabry", "Head of International GTM", "LinkedIn"),
            ("James Matthews", "Head of Consumption & Revenue Strategy, EMEA", "Google"),
            ("Michelle Hulse", "Director of Revenue Operations EMEA", "Pax8"),
            ("Daniel Silbereisen", "Senior Director, Product Strategy, Operations & Performance", "Visa"),
            ("Geoff Smith", "Head of Sales Operations", "The Economist"),
            ("David Woodcock", "Corporate VP, Client Services", "WNS (Part of Capgemini)"),
            ("Alexey Nekhaenko", "Senior Director Sales Operations, Europe", "IDC"),
            ("Mary Sajni Joseph", "Head of Sales Operations & Enablement", "TransUnion"),
            ("Robert Smith", "Senior Director Sales Operations", "Flexera"),
            ("Ian Matthews", "VP of WW GTM Strategy, Field Operations & Renewals", "Teradata"),
            ("Maria Randall", "Head of UK Revenue Operations", "Ekco"),
            ("Fiona NicChoiligh", "Director of Enablement - APAC & EMEA", "Gong"),
            ("Emilie Leblanc", "VP Commercial Operations", "Disguise"),
            ("Tibaut Meulemans", "Head of Revenue Operations", "Intact"),
            ("Cristian Rinceanu", "Associate Director, Sales Operations Europe", "Illumina"),
            ("Anna Luisa Fisher-Jeffes", "Director of Sales Operations", "Prometheus"),
            ("Molly Sestak", "Head of Revenue Enablement & Operations", "Sedna"),
            ("Ben Austen", "VP of Revenue Operations & Growth", "Find.co"),
        ],
    },
    {
        "event": "Revenue Operations Summit - Austin (Feb 2026 edition)",
        "edition_date": "2026-02-11", "location": "Austin",
        "snapshot": "https://web.archive.org/web/20250810071814/https://events.revenueoperationsalliance.com/location/austin/speakers",
        "speakers": [
            ("Josh Hoffman", "Chief Revenue Officer", "ControlCase"),
            ("Ian Lazarus", "VP of Business Operations", "Zippy"),
            ("Zeeshan Hafeez", "Chief Revenue Officer", "Chirok Health"),
            ("Brian Cannatelli", "VP of Sales Operations", "Lighthouse"),
            ("Raoul Hingle", "Head of Sales - US", "OOD Houses"),
            ("Tiffany Gonzalez", "Head of Revenue Operations and Growth Programs", "Microsoft"),
            ("Sai Karthik Ramakuru", "Director Sales Productivity, Strategy & Analytics", "MongoDB"),
            ("Ethan Lippman", "Senior Director, Revenue Operations", "Alkami Technology"),
            ("Imani Chopin", "Senior Director, Revenue Operations & Enablement", "Brinks Home"),
            ("Sandy Robinson", "VP of Revenue Operations & Client Growth", "Quavo Fraud & Disputes"),
            ("Danny Lenz", "Senior Director of Revenue Operations", "Dell"),
            ("Sandeep Singh", "CEO and GTM Advisor", ""),
            ("Everett Kimball", "VP, Global Revenue Operations", "SailPoint"),
            ("Allie Moore", "Marketing Operations Manager", "Alkami Technology"),
            ("Altaf Mohammed", "Head of Global Programs - Sales Strategy", "Indeed"),
            ("Elizabeth Ferguson", "VP of Revenue Operations", "Maxor"),
            ("Benjamin Zeitz", "Head of Revenue Operations", "Sweep"),
            ("Philip Lakin", "Head of Enterprise Innovation", "Zapier"),
            ("Christine Maxey", "Director of Revenue Operations", "LeanData"),
            ("Phil Russell", "SVP of Sales", "Creatio"),
        ],
    },
]


def main():
    rows = []
    for ev in PAST:
        for name, title, company in ev["speakers"]:
            rows.append({
                "Event": ev["event"],
                "Edition Date": ev["edition_date"],
                "Location": ev["location"],
                "Speaker": name,
                "Job Title": title,
                "Company": company,
                "Archive Snapshot": ev["snapshot"],
            })

    path = "outputs/revenueops-past-speakers.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "Event", "Edition Date", "Location", "Speaker",
            "Job Title", "Company", "Archive Snapshot"])
        w.writeheader()
        w.writerows(rows)

    print(f"Past editions: {len(PAST)}")
    print(f"Past speaker rows: {len(rows)}")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
