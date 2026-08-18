# Event Outreach - 1-Step Email Template

> Use this for event-based campaigns where a Xoxoday exec (CRO, VP Sales, etc.) is attending and wants to meet prospects at the venue or over coffee.

## Smartlead Sequence Config (JSON)

```json
{
  "sequences": [
    {
      "seq_number": 1,
      "seq_delay_details": { "delay_in_days": 0 },
      "seq_variants": [
        {
          "subject": "{{first_name}}, let's connect at [EVENT NAME]",
          "email_body": "<p>Hey {{first_name}},</p><p>Noticed you're at the [EVENT NAME] event - so is our [TITLE], [FIRST NAME].</p><p>[HE/SHE]'d love to meet you in person on-site or grab a quick coffee to chat about what's top of mind for your team this year.</p><p>If you're open to it, just reply here and we'll coordinate a time that works on the go.</p><p>No formal agenda needed - just a conversation.</p><p>Talk soon,<br/>{{sender_first_name}}<br/>Xoxoday | [PRODUCT]</p>",
          "variant_label": "A"
        },
        {
          "subject": "Coffee at [EVENT NAME]? {{first_name}}",
          "email_body": "<p>Hey {{first_name}},</p><p>Noticed you're at the [EVENT NAME] event - so is our [TITLE], [FIRST NAME].</p><p>[HE/SHE]'d love to meet you in person on-site or grab a quick coffee to chat about what's top of mind for your team this year.</p><p>If you're open to it, just reply here and we'll coordinate a time that works on the go.</p><p>No formal agenda needed - just a conversation.</p><p>Talk soon,<br/>{{sender_first_name}}<br/>Xoxoday | [PRODUCT]</p>",
          "variant_label": "B"
        }
      ]
    }
  ]
}
```

## Placeholders to Fill

Before using, replace:
- `[EVENT NAME]` - e.g. "Quirks", "SaaStr", "HR Tech"
- `[TITLE]` - e.g. "CRO", "VP Sales", "Head of Partnerships"
- `[FIRST NAME]` - the exec's first name
- `[HE/SHE]` - pronoun
- `[PRODUCT]` - "Plum", "Empuls", or "Loyalife"

## Recommended Settings

| Setting | Value |
|---------|-------|
| Schedule | Match event timezone, weekdays only |
| Sending window | Before event opens, e.g. 6am-9am local |
| Min time between emails | 5-8 min (event is time-sensitive) |
| Max new leads per day | All of them (single-day blast) |
| Stop on reply | Yes |

## Campaign Naming

```
P1_EVENTS_PREEVENT_<REGION>_EMAIL_<POC>_<DDMMMYY>
```

Example: `P1_EVENTS_PREEVENT_US_EMAIL_naitik_16APR26`

For post-event follow-up, use `POSTEVENT` in place of `PREEVENT`.
