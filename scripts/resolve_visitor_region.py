"""
Resolve Country (and macro-region, matching the region scheme used throughout
the Plum/Empuls/Loyalife/main-landing-page form-submission analysis) for the
website-visitor deanonymization export, which has City/State but no Country
column.

Zero-cost by design: no API calls, no Apollo/Clay credits. Two layers:
  1. City+State pair lookup (CITY_STATE_OVERRIDES) - built by manually
     checking every non-obviously-Indian row in the 2026-09-15 visitor export
     against its City value. This exists because the State column alone is
     NOT reliable: "GA" is Goa (India) at Panjim/Panaji but Georgia (US) at
     Atlanta in the SAME column, and "LA" turned out to be Lagos (Nigeria) in
     every row it appeared in, not Louisiana (US) or Ladakh (India) as the
     2-letter code alone would suggest. City+State together disambiguates
     correctly; State alone does not.
  2. Fallback: State-code match against INDIA_STATE_CODES (ISO 3166-2:IN),
     with the two proven-ambiguous codes (GA, LA) deliberately excluded from
     this blind fallback - they only resolve via the override layer above,
     or stay Unknown if the override doesn't have that exact City+State pair.

Anything neither layer resolves is left as Country="" / region="Unknown" -
this script does not guess. A residual unresolved slice is expected and
normal; closing it further needs either a HubSpot domain lookup (free, not
yet wired into this script) or paid enrichment (Apollo/Clay), which this kit
gates behind explicit user confirmation for lists over 500 rows (see
CLAUDE.md Critical Rule #5) - not run automatically here.

Usage:
    python3 resolve_visitor_region.py <input_csv> <output_csv> [--city-col City] [--state-col State]
"""
import argparse
import pandas as pd

# ISO 3166-2:IN codes, MINUS "GA" and "LA" - both proven ambiguous in the
# real data (GA = Goa in some rows, Georgia US in others; LA = Lagos,
# Nigeria in every row seen, not a real India match at all despite the
# code's surface resemblance to Ladakh's "LA"). Those two are handled only
# by CITY_STATE_OVERRIDES below, never by this blind fallback.
INDIA_STATE_CODES = {
    'AN', 'AP', 'AR', 'AS', 'BR', 'CH', 'CG', 'CT', 'DN', 'DD', 'DL', 'GJ',
    'HR', 'HP', 'JK', 'JH', 'KA', 'KL', 'LD', 'MP', 'MH', 'MN', 'ML',
    'MZ', 'NL', 'OR', 'OD', 'PY', 'PB', 'RJ', 'SK', 'TN', 'TS', 'TR',
    'UP', 'UT', 'UK', 'WB',
}

# (city, state) -> country, built by hand from the 2026-09-15 export. Keyed
# on the pair (not city alone) because common city names collide across
# countries (Richmond, Paris, Cairo, Madrid, Vienna, Birmingham, London all
# exist in more than one country) - the paired state code is what makes each
# entry here unambiguous. City matching is case-insensitive; state is not
# (state codes in this data are consistently upper-case).
def _ci(city):
    return city.strip().lower()

CITY_STATE_OVERRIDES = {
    (_ci('Panjim'), 'GA'): 'India',
    (_ci('Panaji'), 'GA'): 'India',
    (_ci('Atlanta'), 'GA'): 'United States',
    (_ci('Lagos'), 'LA'): 'Nigeria',
    (_ci('Quezon City'), '00'): 'Philippines',
    (_ci('Dubai'), 'DU'): 'United Arab Emirates',
    (_ci('Cape Town'), 'WC'): 'South Africa',
    (_ci('Wakefield'), 'ENG'): 'United Kingdom',
    (_ci('London'), 'ENG'): 'United Kingdom',
    (_ci('Birmingham'), 'ENG'): 'United Kingdom',
    (_ci('Calgary'), 'AB'): 'Canada',
    (_ci('Brampton'), 'ON'): 'Canada',
    (_ci('Araripina'), 'PE'): 'Brazil',
    (_ci('Sungai Buloh'), '10'): 'Malaysia',
    (_ci('Kuala Lumpur'), '14'): 'Malaysia',
    (_ci('Lake Elsinore'), 'CA'): 'United States',
    (_ci('Torrance'), 'CA'): 'United States',
    (_ci('Lake Forest'), 'CA'): 'United States',
    (_ci('Los Angeles'), 'CA'): 'United States',
    (_ci('Stockton'), 'CA'): 'United States',
    (_ci('Richmond'), 'TX'): 'United States',
    (_ci('Houston'), 'TX'): 'United States',
    (_ci('Phnom Penh'), '12'): 'Cambodia',
    (_ci('Aba'), 'AB'): 'Nigeria',
    (_ci('Hamilton'), 'WKO'): 'New Zealand',
    (_ci('Lahug'), '07'): 'Philippines',
    (_ci('Carmona'), '40'): 'Philippines',
    (_ci('City of Muntinlupa'), '40'): 'Philippines',
    (_ci('Sakhnin'), 'Z'): 'Israel',
    (_ci('Tel Aviv'), 'TA'): 'Israel',
    (_ci('rebro'), 'T'): 'Sweden',  # "Örebro" with a mangled leading character in the export
    (_ci('Oslo'), '03'): 'Norway',
    (_ci('Tultitln de Mariano Escobedo'), 'MEX'): 'Mexico',
    (_ci('Taipei'), 'TPE'): 'Taiwan',
    (_ci('Hanoi'), 'HN'): 'Vietnam',
    (_ci('Vinh'), '22'): 'Vietnam',
    (_ci('Boonton'), 'NJ'): 'United States',
    (_ci('Cabimas'), 'V'): 'Venezuela',
    (_ci('Addis Ababa'), 'AA'): 'Ethiopia',
    (_ci('Riyadh'), '01'): 'Saudi Arabia',
    (_ci('Hong Kong'), ''): 'Hong Kong',
    (_ci('Lisbon'), '11'): 'Portugal',
    (_ci('Silver Spring'), 'MD'): 'United States',
    (_ci('South Tangerang'), 'BT'): 'Indonesia',
    (_ci('The Bronx'), 'NY'): 'United States',
    (_ci('Paris'), 'IDF'): 'France',
    (_ci('Singapore'), '01'): 'Singapore',
    (_ci('Budapest'), 'BU'): 'Hungary',
    (_ci('Tokyo'), '13'): 'Japan',
    (_ci('Vienna'), '9'): 'Austria',
    (_ci('Oran'), '31'): 'Algeria',
    (_ci('Johannesburg'), 'GP'): 'South Africa',
    (_ci('Karachi'), 'SD'): 'Pakistan',
    (_ci('Zagazig'), 'SHR'): 'Egypt',
    (_ci('Cairo'), 'C'): 'Egypt',
    (_ci('Rolla'), 'MO'): 'United States',
    (_ci('Guangzhou'), 'GD'): 'China',
    (_ci('Aiken'), 'SC'): 'United States',
    (_ci('Madrid'), 'MD'): 'Spain',
    (_ci('Grayslake'), 'IL'): 'United States',
    (_ci('Kallithea'), 'I'): 'Greece',
}

# Same macro-region rollup used throughout the Plum/Empuls/Loyalife/
# main-landing-page analysis, for direct consistency with that work.
REGION_MAP = {
    'India': 'India',
    'United Arab Emirates': 'GCC', 'Saudi Arabia': 'GCC',
    'Egypt': 'MENA (non-GCC)', 'Algeria': 'MENA (non-GCC)', 'Israel': 'MENA (non-GCC)',
    'United States': 'North America', 'Canada': 'North America', 'Mexico': 'LatAm',
    'United Kingdom': 'UK/EU', 'Sweden': 'UK/EU', 'Norway': 'UK/EU', 'Portugal': 'UK/EU',
    'Hungary': 'UK/EU', 'Austria': 'UK/EU', 'France': 'UK/EU', 'Spain': 'UK/EU', 'Greece': 'UK/EU',
    'Philippines': 'SEA', 'Malaysia': 'SEA', 'Singapore': 'SEA', 'Indonesia': 'SEA', 'Vietnam': 'SEA',
    'Cambodia': 'SEA',
    'China': 'East Asia', 'Japan': 'East Asia', 'Taiwan': 'East Asia', 'Hong Kong': 'East Asia',
    'South Africa': 'Africa', 'Nigeria': 'Africa', 'Ethiopia': 'Africa',
    'Pakistan': 'South Asia (non-India)',
    'Brazil': 'LatAm', 'Venezuela': 'LatAm',
    'New Zealand': 'ANZ', 'Australia': 'ANZ',
}


def resolve_row(city, state):
    city_key = _ci(str(city)) if pd.notna(city) else ''
    state_key = str(state).strip() if pd.notna(state) else ''

    override = CITY_STATE_OVERRIDES.get((city_key, state_key))
    if override:
        return override, 'city+state override'

    if state_key in INDIA_STATE_CODES:
        return 'India', 'state code (India)'

    return '', 'unresolved'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_csv')
    parser.add_argument('output_csv')
    parser.add_argument('--city-col', default='City')
    parser.add_argument('--state-col', default='State')
    args = parser.parse_args()

    df = pd.read_csv(args.input_csv)
    resolved = df.apply(lambda r: resolve_row(r.get(args.city_col), r.get(args.state_col)), axis=1)
    df['Country'] = [r[0] for r in resolved]
    df['country_resolution_method'] = [r[1] for r in resolved]
    df['Region'] = df['Country'].map(REGION_MAP).fillna(df['Country'].apply(lambda c: 'Rest of World' if c else 'Unknown'))

    df.to_csv(args.output_csv, index=False)

    total = len(df)
    resolved_n = (df['Country'] != '').sum()
    print(f"{total} rows: {resolved_n} resolved ({resolved_n/total*100:.1f}%), {total - resolved_n} unresolved")
    print("\nBy resolution method:")
    print(df['country_resolution_method'].value_counts().to_string())
    print("\nBy region:")
    print(df['Region'].value_counts().to_string())
    print(f"\nWrote: {args.output_csv}")


if __name__ == '__main__':
    main()
