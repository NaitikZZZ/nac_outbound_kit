"""Campaign-name builder for the strict Xoxoday naming convention:
PRIORITY_TEAM_USECASE_REGION_CHANNEL_POCNAME_STARTDATE
(docs/campaign-naming-convention.md in the sibling nac_outbound_kit-main_import kit).

No validation against the full enum tables here -- this just assembles and
formats the pieces the user supplies in the UI; the convention doc is the
source of truth for which codes are valid, and the UI's own dropdowns
constrain most of them already.
"""
import re


def build_campaign_name(priority, team, use_case, region, channel, poc_name, start_date, farming=False):
    """All inputs are already-chosen codes/values from the UI (dropdowns for
    priority/team/region/channel constrain most of these). `start_date` is a
    date string like '2026-08-14' (from an HTML date input); converted to
    DDMMMYY. `farming=True` swaps in the FARMING use-case code, per the
    user's confirmed convention for the excluded-track upload."""
    use_case_code = "FARMING" if farming else use_case.strip().upper()
    poc = "-".join(p.strip().lower() for p in re.split(r"[,+&]", poc_name) if p.strip())

    try:
        year, month, day = start_date.split("-")
        month_names = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
        date_code = f"{int(day):02d}{month_names[int(month) - 1]}{year[2:]}"
    except (ValueError, IndexError):
        date_code = start_date.strip().upper()

    parts = [priority.strip().upper(), team.strip().upper(), use_case_code,
             region.strip().upper(), channel.strip().upper(), poc, date_code]
    return "_".join(p for p in parts if p)
