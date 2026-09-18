"""
Post a summary note to a HubSpot Project record (portal 6512810, object type
0-970 / "projects"). This is the ONE scoped write exception to this kit's
HubSpot read-only rule (see CLAUDE.md Critical Rule #2) - every other write
path stays prohibited.

Uses HUBSPOT_PRIVATE_APP_TOKEN / HUBSPOT_API_KEY from .env.

Usage:
  python3 hubspot_post_project_note.py --project-id 851440115432 --body-file note.html
"""
import argparse
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

HUBSPOT_TOKEN = os.environ.get('HUBSPOT_PRIVATE_APP_TOKEN') or os.environ.get('HUBSPOT_API_KEY')
NOTES_URL = 'https://api.hubapi.com/crm/v3/objects/notes'
ASSOC_URL = 'https://api.hubapi.com/crm/v4/objects/notes/{note_id}/associations/default/0-970/{project_id}'


def _headers():
    return {'Authorization': f'Bearer {HUBSPOT_TOKEN}', 'Content-Type': 'application/json'}


def post_note(project_id, body_html):
    payload = {
        'properties': {
            'hs_note_body': body_html,
            'hs_timestamp': str(int(time.time() * 1000)),
        }
    }
    r = requests.post(NOTES_URL, headers=_headers(), json=payload, timeout=15)
    r.raise_for_status()
    note_id = r.json()['id']

    r2 = requests.put(ASSOC_URL.format(note_id=note_id, project_id=project_id),
                       headers=_headers(), timeout=15)
    r2.raise_for_status()
    return note_id


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-id', required=True)
    parser.add_argument('--body-file', required=True)
    args = parser.parse_args()

    with open(args.body_file) as f:
        body = f.read()

    note_id = post_note(args.project_id, body)
    print(f'Note {note_id} created and associated to Project {args.project_id}')
    print(f'https://app-na2.hubspot.com/contacts/6512810/record/0-970/{args.project_id}')
