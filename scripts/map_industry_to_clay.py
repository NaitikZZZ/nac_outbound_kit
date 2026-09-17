"""
Map the website-visitor export's free-text Industry labels onto Clay Search's
structured `industry` enum (see the clay-search-query skill's field docs -
Clay's own guardrail is explicit: "If an initial (non-refinement) request
names specific subindustries, map them to the closest industry values in
first pass" - broad source labels are expected to map to a SMALL SET of
Clay values, not one value each, when no single enum value covers them.

The source data has two overlapping vintages mixed together (title-case
"Information Technology" style + ALL_CAPS_UNDERSCORE "COMPUTER_SOFTWARE"
style, plus a couple of near-duplicate casings like "RETAIL"/"Retail") -
those are folded into the same target here.

Every value on the right of INDUSTRY_MAP is a real Clay `industry` enum
value, copy-pasted from the skill's field list, not invented - if you add a
new source category, verify the Clay value against that list before adding
it here (Clay enums only support =/!=/in/not_in, so a near-miss string
silently matches nothing rather than erroring).

Usage:
    python3 map_industry_to_clay.py <input_csv> <output_csv> [--industry-col Industry]
"""
import argparse
import pandas as pd

INDUSTRY_MAP = {
    'information technology': ['Information Technology and Services', 'IT Services and IT Consulting',
                                'Technology, Information and Internet', 'Technology, Information and Media'],
    'computer_software': ['Software Development'],
    'computer software': ['Software Development'],
    'education': ['Education'],
    'schools and education': ['Education', 'Primary and Secondary Education'],
    'professional and business services': ['Professional Services', 'Business Consulting and Services'],
    'corporate services': ['Business Consulting and Services'],
    'manufacturing': ['Manufacturing'],
    'industrial manufacturing and services': ['Manufacturing', 'Industrial Machinery Manufacturing'],
    'consumer product manufacturing': ['Consumer Goods'],
    'finance and banking': ['Banking', 'Financial Services'],
    'insurance': ['Insurance'],
    'health and pharmaceuticals': ['Hospitals and Health Care', 'Pharmaceutical Manufacturing'],
    'marketing & advertising': ['Advertising Services', 'Marketing Services'],
    'non-profit and social services': ['Non-profit Organizations', 'Non-profit Organization Management'],
    'retail': ['Retail'],
    'tourism and hospitality': ['Hospitality', 'Leisure, Travel & Tourism'],
    'transportation and logistics': ['Transportation, Logistics, Supply Chain and Storage'],
    'creative arts and entertainment': ['Entertainment', 'Entertainment Providers'],
    'media and publishing': ['Media Production', 'Online Media'],
    'real estate': ['Real Estate'],
    'food and beverage': ['Food & Beverages'],
    'telecommunications': ['Telecommunications'],
    'construction': ['Construction'],
    'construction and building materials': ['Construction', 'Building Materials'],
    'automotive': ['Automotive'],
    'energy': ['Oil and Gas', 'Utilities', 'Renewables & Environment'],
    'utilities': ['Utilities'],
    'agriculture': ['Farming, Ranching, Forestry'],
    'government and public administration': ['Government Administration'],
    'consumer services': ['Consumer Services'],
    'consumer_goods': ['Consumer Goods'],
}


def map_industry(raw):
    if pd.isna(raw):
        return None
    key = str(raw).strip().lower()
    return INDUSTRY_MAP.get(key)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_csv')
    parser.add_argument('output_csv')
    parser.add_argument('--industry-col', default='Industry')
    args = parser.parse_args()

    df = pd.read_csv(args.input_csv)
    mapped = df[args.industry_col].apply(map_industry)
    df['industry_clay_values'] = mapped.apply(lambda v: '; '.join(v) if v else '')
    df['industry_clay_primary'] = mapped.apply(lambda v: v[0] if v else '')

    df.to_csv(args.output_csv, index=False)

    total = len(df)
    mapped_n = (df['industry_clay_primary'] != '').sum()
    print(f"{total} rows: {mapped_n} mapped ({mapped_n/total*100:.1f}%), {total - mapped_n} unmapped")
    print("\nUnmapped source values (fix INDUSTRY_MAP if these matter):")
    unmapped_source = df.loc[df['industry_clay_primary'] == '', args.industry_col]
    print(unmapped_source.value_counts(dropna=False).to_string())
    print(f"\nWrote: {args.output_csv}")


if __name__ == '__main__':
    main()
