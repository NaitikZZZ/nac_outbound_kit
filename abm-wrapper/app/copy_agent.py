"""Step 10 -- Copy Agent: segments uploaded leads by persona (reusing the
repo's own scripts/icp_titles.py taxonomy) and generates tailored email +
LinkedIn copy per segment via Claude.

Modeled directly on the reference "Xoxoday ABM Wrapper" tool (seen in a
screen recording, 2026-07-23): its sidebar describes this exact step as
"Segment leads, generate email & LinkedIn copy", and it degrades to a clean
skip when ANTHROPIC_API_KEY isn't set rather than failing -- same pattern
used elsewhere in this app (domain_resolver_ai.py).

Writing constraints applied to every generated message, per standing
feedback for this project: no em/en dashes, and the sign-off uses a
hardcoded sender name (the run's POC name from Step 7) rather than a
{{Sender First Name}} merge tag, since sends go out from multiple mailboxes
with inconsistent sender profiles.
"""
import json

from . import skills_bridge
from .config import ANTHROPIC_API_KEY

MAX_SEGMENTS = 8


def _match_family(title, families):
    if not title:
        return None
    lowered = title.strip().lower()
    if not lowered:
        return None
    for family in families:
        for variant in family.get("variants", []):
            if variant in lowered or lowered in variant:
                return family
    return None


def segment_leads(rows, title_col):
    """Buckets rows by matched ICP family. Returns a list of
    {family, leads} dicts, most populous first, plus the unmatched leads
    under a synthetic "general" bucket -- sorted last since it has no
    specific persona to write to."""
    families = skills_bridge.icp_families()
    buckets = {}
    unmatched = []

    for row in rows:
        title = (row.get(title_col) or "").strip() if title_col else ""
        family = _match_family(title, families)
        if family is None:
            unmatched.append(row)
            continue
        buckets.setdefault(family["key"], {"family": family, "leads": []})["leads"].append(row)

    segments = sorted(buckets.values(), key=lambda b: len(b["leads"]), reverse=True)
    if unmatched:
        segments.append({
            "family": {"key": "general", "label": "General / unmatched title", "products": [], "role": "unknown"},
            "leads": unmatched,
        })
    return segments


_COPY_TOOL = {
    "name": "emit_copy",
    "description": "Return the generated outbound copy for this persona segment.",
    "input_schema": {
        "type": "object",
        "properties": {
            "email_subject": {"type": "string"},
            "email_body": {"type": "string", "description": "Initial cold email body, plain text, using {{First Name}}/{{Company}}/{{Job Title}} merge tags where natural."},
            "email_followup_subject": {"type": "string"},
            "email_followup_body": {"type": "string", "description": "Short follow-up email body, sent a few days later."},
            "linkedin_connect_note": {"type": "string", "description": "LinkedIn connection request note, under 300 characters."},
            "linkedin_followup_dm": {"type": "string", "description": "LinkedIn DM sent after connection is accepted."},
        },
        "required": ["email_subject", "email_body", "email_followup_subject", "email_followup_body", "linkedin_connect_note", "linkedin_followup_dm"],
    },
}


def _generate_copy_for_segment(family, lead_count, poc_name):
    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    products = ", ".join(family.get("products", [])) or "Xoxoday's rewards & incentives platform"
    role = family.get("role", "unknown")
    label = family.get("label", "this persona")
    sender = poc_name.strip() if poc_name and poc_name.strip() else "The Xoxoday Team"

    prompt = (
        f"Write cold outbound copy for a B2B sales sequence targeting the persona "
        f'"{label}" (a {role} in the buying process) for {products}. This segment has '
        f"{lead_count} contact(s).\n\n"
        "Requirements:\n"
        "- Use {{First Name}}, {{Company}}, and {{Job Title}} as literal merge tags "
        "(do not resolve them to real values) wherever personalization is natural.\n"
        f"- Sign every message with exactly this name, written out plainly (not a merge tag): {sender}\n"
        "- Never use an em dash or en dash character anywhere in the copy. Use periods, "
        "commas, or separate sentences instead.\n"
        "- Keep the tone direct and specific to this persona's role, not generic.\n"
        "- The LinkedIn connection note must be under 300 characters.\n"
        "- Call the emit_copy tool with the result -- do not write prose outside the tool call."
    )

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        tools=[_COPY_TOOL],
        tool_choice={"type": "tool", "name": "emit_copy"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "emit_copy":
            return block.input
    return None


def run(rows, cols, poc_name):
    """OK track only, after Step 9's upload. Returns None if ANTHROPIC_API_KEY
    isn't configured -- caller treats that as a clean skip, matching the
    reference tool's exact behavior rather than raising an error."""
    if not ANTHROPIC_API_KEY:
        return None

    title_col = cols.get("title")
    segments = segment_leads(rows, title_col)

    dropped = segments[MAX_SEGMENTS:]
    segments = segments[:MAX_SEGMENTS]

    results = []
    for seg in segments:
        family = seg["family"]
        lead_count = len(seg["leads"])
        try:
            copy = _generate_copy_for_segment(family, lead_count, poc_name)
        except Exception as exc:
            copy = None
            error = str(exc)
        else:
            error = None if copy else "Claude did not return structured copy for this segment."

        results.append({
            "key": family["key"],
            "label": family["label"],
            "role": family.get("role", "unknown"),
            "products": family.get("products", []),
            "lead_count": lead_count,
            "copy": copy,
            "error": error,
        })

    return {
        "segments": results,
        "dropped_segment_count": len(dropped),
        "dropped_lead_count": sum(len(s["leads"]) for s in dropped),
        "total_leads": len(rows),
    }


def to_markdown(result, campaign_name):
    """Renders the Copy Agent's output as a downloadable Markdown report."""
    lines = [f"# Campaign copy: {campaign_name}", ""]
    for seg in result["segments"]:
        lines.append(f"## {seg['label']} ({seg['lead_count']} lead(s), role: {seg['role']})")
        if seg.get("products"):
            lines.append(f"Products: {', '.join(seg['products'])}")
        lines.append("")
        copy = seg.get("copy")
        if not copy:
            lines.append(f"_Copy generation failed: {seg.get('error', 'unknown error')}_")
            lines.append("")
            continue
        lines += [
            "**Email 1 (initial)**", f"Subject: {copy['email_subject']}", "", copy["email_body"], "",
            "**Email 2 (follow-up)**", f"Subject: {copy['email_followup_subject']}", "", copy["email_followup_body"], "",
            "**LinkedIn connection note**", copy["linkedin_connect_note"], "",
            "**LinkedIn follow-up DM**", copy["linkedin_followup_dm"], "",
            "---", "",
        ]
    if result["dropped_segment_count"]:
        lines.append(
            f"_{result['dropped_segment_count']} smaller segment(s) "
            f"({result['dropped_lead_count']} lead(s) total) were not generated -- "
            f"top {MAX_SEGMENTS} segments by size only._"
        )
    return "\n".join(lines)
