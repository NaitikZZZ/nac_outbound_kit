"""
Computes the qualitative GTM research columns (value proposition, problem
solved, benefits, ICP/industry/persona, distribution model, workforce
composition, loyalty/gamification fit, GTM summary, product to pitch) for a
leads CSV - via Claude + web search per company, never Apollo's AI Research
field (so never Apollo credits).

Two backends, same precedence as wrapper/backend/app/pipeline/web_scrape.py:
  1. The local Claude Code CLI ($CLAUDE_CODE_EXECPATH), if present - runs on
     your own Claude account/subscription, no Anthropic API credits spent.
  2. The Anthropic API (ANTHROPIC_API_KEY) with the web_search_20250305 tool,
     if the CLI isn't available - spends Claude API credits per call.

One Claude call per company (not the multi-field-stacking design used for the
Apollo prompts drafted earlier) - that split existed only to work around
Apollo's per-field billing; it doesn't apply here, so one combined web-search
call producing all fields as JSON is both simpler and cheaper.

Usage:
    python3 gtm_research_fields.py <input_csv> <output_csv> \
        [--company-col "Company Name"] [--domain-col Website] \
        [--limit N] [--model claude-sonnet-4-5]

ALWAYS run with --limit 3-5 first to sanity-check quality and see real
per-call cost/latency before scaling to a full list - each row is one Claude
call with web search enabled, real (small, or subscription-covered if
CLI-backed) cost per row.
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time

from dotenv import load_dotenv

load_dotenv()
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
MODEL = 'claude-sonnet-4-5'
CLI_TIMEOUT = 180

NEW_COLUMNS = [
    'gtm_value_proposition', 'gtm_problem_solved', 'gtm_product_benefits',
    'gtm_icp_industry', 'gtm_icp_persona', 'gtm_distribution_model',
    'gtm_named_partners', 'gtm_workforce_composition',
    'gtm_loyalty_gamification_fit', 'gtm_summary', 'gtm_product_to_pitch',
]

# Static Xoxoday product framework (same content used in the Apollo "Product
# to Pitch" AI field prompt drafted earlier) - own material, safe to embed
# directly rather than treat as something to "research".
PRODUCT_FRAMEWORK = """Xoxoday sells four products:
- Plum: rewards/incentives payout API, 10M+ reward catalog across 175+ countries. Fits any team running rewards/incentive programs (marketing, HR, sales ops, CX, research) - self-serve, API-first, strong for multi-country or consumer/channel-facing use cases.
- Empuls: employee recognition, rewards and engagement for HR/People teams at 200+ FTE companies - sales-led.
- Compass: sales commission and incentive automation for Sales Ops/RevOps/Finance teams with a distributed or channel sales force.
- Loyalife: enterprise customer or channel loyalty programs for consumer or B2B2C brands with repeat-purchase customers - sales-led, longer cycle."""


def _build_prompt(company_name: str, domain: str, partner_tech_match: str = '',
                   partner_suggested_products: str = '') -> str:
    partner_signal = ''
    if partner_tech_match and partner_suggested_products:
        partner_signal = f"""

Xoxoday's own CRM records a real signal for this company: its technology stack includes \
confirmed Xoxoday integration/channel partners ({partner_tech_match}), and Xoxoday's own \
GTM playbook records that {partner_suggested_products} is the product actually pitched \
through those specific partner relationships. Treat this as a strong, recorded fact - weigh \
it alongside (not instead of) the sales-org/channel/workforce signals you find below when \
deciding product_to_pitch. If it conflicts with what you find (e.g. a strong sales-org signal \
pointing to Compass while the partner record says Plum), answer "Multiple" and explain both \
angles in gtm_summary rather than silently picking one."""

    return f"""You are a B2B GTM research analyst. Research the company "{company_name}" \
(website: {domain}) using web search: its homepage, product/solutions pages, pricing page, \
about/company page, careers/jobs page, and its LinkedIn page.

{PRODUCT_FRAMEWORK}{partner_signal}

Return ONLY a JSON object with these exact keys (use "Not found" for anything you can't \
confidently determine from real sources - never invent specifics):
- "value_proposition": what the company sells and its core value proposition, 1-2 sentences.
- "problem_solved": the primary problem/pain point their product solves, 1 sentence.
- "product_benefits": top 3 concrete benefits/outcomes their product claims, comma-separated.
- "icp_industry": the industries and company sizes they primarily sell into, 1 sentence.
- "icp_persona": the job titles/functions of their target buyer, 1 sentence.
- "distribution_model": how they go to market - direct sales, self-serve/API-first, channel \
partners, dealers/resellers, marketplace, or a mix, 1-2 sentences.
- "named_partners": any specific partners, dealers, resellers, or influencer programs \
mentioned by name, comma-separated, or "None found".
- "workforce_composition": evidence of white-collar/office vs blue-collar/frontline staff, \
citing where you found it (careers page, job listings, LinkedIn, news), 1 sentence.
- "loyalty_gamification_fit": one sentence on whether this company's own end customers show \
repeat-purchase/recurring-engagement behavior a loyalty/gamification program could be built \
on, ending with exactly one word: HIGH, MEDIUM, LOW, or UNCLEAR.
- "gtm_summary": a 3-4 sentence GTM briefing paragraph for a Xoxoday rep about to reach out - \
what they sell, who they sell to, how they go to market, any workforce signal. Plain prose.
- "product_to_pitch": exactly one of Plum, Empuls, Loyalife, Compass, Multiple, or Unclear - \
the best-fit Xoxoday product(s) for THIS company as a Xoxoday customer.

Before answering product_to_pitch, you MUST explicitly check for all of these signals \
(don't skip straight to Empuls just because a company has no obvious blue-collar workforce) - \
search their careers page / job listings for evidence of each:
1. A dedicated quota-carrying sales org (titles like "Account Executive", "Regional Sales \
   Manager", "Sales Development Rep", territory/quota language, CRM mentions like Salesforce) \
   -> this is a Compass (sales commission automation) signal, not just Empuls.
2. A distributor, reseller, wholesaler, franchise, or dealer network (per-order/per-unit \
   channel sales, "distributor", "channel partner") -> this is a Plum (channel incentives) or \
   Loyalife (channel loyalty) signal.
3. A B2C or B2B2C customer base with repeat purchases (subscriptions, repeat transactions, \
   existing points/rewards program) -> this is a Loyalife signal.
4. General employee headcount/engagement need (200+ FTE, no other signal) -> Empuls.
If 2 or more signals apply, answer "Multiple" and name which products in \
gtm_summary. Only answer a single product when just one signal clearly applies.

Output the JSON object and nothing else - no markdown fences, no commentary."""


def _extract_json(text: str) -> dict:
    match = re.search(r'\{.*\}', text or '', re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def _research_via_cli(prompt: str) -> str:
    """Headless local Claude Code CLI call - uses the user's own Claude
    account/subscription, no ANTHROPIC_API_KEY or API credits needed. Same
    mechanism as wrapper/backend/app/pipeline/web_scrape.py's _extract_via_cli."""
    execpath = os.environ.get('CLAUDE_CODE_EXECPATH')
    proc = subprocess.run(
        [execpath, '-p', prompt, '--allowedTools', 'WebFetch,WebSearch'],
        capture_output=True, text=True, timeout=CLI_TIMEOUT,
    )
    out = (proc.stdout or '').strip()
    if 'Not logged in' in out or (proc.returncode != 0 and not out):
        raise ValueError(f"Claude CLI call failed (exit {proc.returncode}): {(proc.stderr or '')[:300]}")
    return out


def _research_via_api(prompt: str) -> str:
    from anthropic import Anthropic
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        tools=[{'type': 'web_search_20250305', 'name': 'web_search'}],
        messages=[{'role': 'user', 'content': prompt}],
    )
    return ''.join(getattr(b, 'text', '') for b in response.content if getattr(b, 'type', None) == 'text')


def research_company(company_name: str, domain: str, partner_tech_match: str = '',
                      partner_suggested_products: str = '') -> dict:
    prompt = _build_prompt(company_name, domain, partner_tech_match, partner_suggested_products)
    if os.environ.get('CLAUDE_CODE_EXECPATH'):
        text = _research_via_cli(prompt)
    elif ANTHROPIC_API_KEY:
        text = _research_via_api(prompt)
    else:
        raise ValueError('Neither CLAUDE_CODE_EXECPATH nor ANTHROPIC_API_KEY is available.')
    data = _extract_json(text)
    return {
        'gtm_value_proposition': data.get('value_proposition', ''),
        'gtm_problem_solved': data.get('problem_solved', ''),
        'gtm_product_benefits': data.get('product_benefits', ''),
        'gtm_icp_industry': data.get('icp_industry', ''),
        'gtm_icp_persona': data.get('icp_persona', ''),
        'gtm_distribution_model': data.get('distribution_model', ''),
        'gtm_named_partners': data.get('named_partners', ''),
        'gtm_workforce_composition': data.get('workforce_composition', ''),
        'gtm_loyalty_gamification_fit': data.get('loyalty_gamification_fit', ''),
        'gtm_summary': data.get('gtm_summary', ''),
        'gtm_product_to_pitch': data.get('product_to_pitch', ''),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input_csv')
    ap.add_argument('output_csv')
    ap.add_argument('--company-col', default='Company Name')
    ap.add_argument('--domain-col', default='Website')
    ap.add_argument('--limit', type=int, default=None,
                     help='Only process the first N rows - ALWAYS test with 3-5 before scaling.')
    ap.add_argument('--model', default=MODEL)
    args = ap.parse_args()

    if not os.environ.get('CLAUDE_CODE_EXECPATH') and not ANTHROPIC_API_KEY:
        sys.exit('Neither the local Claude Code CLI ($CLAUDE_CODE_EXECPATH) nor ANTHROPIC_API_KEY '
                  'is available - one of the two is required for web-search-backed research.')
    print(f"Research backend: {'Claude Code CLI (your subscription, no API credits)' if os.environ.get('CLAUDE_CODE_EXECPATH') else 'Anthropic API (spends credits)'}")

    with open(args.input_csv, encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []
    if args.limit:
        rows = rows[:args.limit]

    if args.company_col not in fieldnames or args.domain_col not in fieldnames:
        sys.exit(f"ERROR: need columns '{args.company_col}' and '{args.domain_col}'. "
                  f"Available: {fieldnames}")

    out_fieldnames = fieldnames + [c for c in NEW_COLUMNS if c not in fieldnames]
    errors = []
    start = time.time()

    has_partner_signal = 'partner_tech_match' in fieldnames and 'partner_suggested_products' in fieldnames
    if has_partner_signal:
        print("Found partner_tech_match/partner_suggested_products columns (from "
              "apollo_gtm_columns.py) - feeding that real signal into each research prompt.")

    for i, row in enumerate(rows):
        company = row.get(args.company_col, '') or ''
        domain = row.get(args.domain_col, '') or ''
        print(f"[{i + 1}/{len(rows)}] researching {company!r} ({domain})...", flush=True)
        try:
            facts = research_company(
                company, domain,
                partner_tech_match=row.get('partner_tech_match', '') if has_partner_signal else '',
                partner_suggested_products=row.get('partner_suggested_products', '') if has_partner_signal else '',
            )
            row.update(facts)
            print(f"  -> product_to_pitch={facts['gtm_product_to_pitch']!r}, "
                  f"loyalty_fit={facts['gtm_loyalty_gamification_fit']!r}")
        except Exception as e:
            errors.append(f"{company}: {e}")
            print(f"  ERROR: {e}")
            for c in NEW_COLUMNS:
                row.setdefault(c, '')

    elapsed = time.time() - start
    with open(args.output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=out_fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} rows to {args.output_csv} in {elapsed:.1f}s "
          f"({elapsed / max(len(rows), 1):.1f}s/company).")
    if errors:
        print(f"{len(errors)} errors:")
        for e in errors[:10]:
            print(f"  - {e}")


if __name__ == '__main__':
    main()
