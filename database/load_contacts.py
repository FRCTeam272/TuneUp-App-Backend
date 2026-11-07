"""Load team contact people (name, email, phone) from contacts.csv into the team_contact table.

Run from database/ after load_teams.py (contacts are matched to teams by team number):

    python load_contacts.py [contacts.csv]

With no argument, a file dialog asks for the CSV (e.g. the registration receipts.csv).

load_teams.py also calls this automatically when contacts.csv exists, because wiping the teams
has to wipe their contacts too.

The CSV needs a header row. Headers are matched case-insensitively and ignoring spaces/punctuation;
any of these names work for each column:
    team number:  Team Number, Team #, Team, Number, Team ID
    contact name: Contact Name, Contact, Coach, Coach Name, Name
    email:        Email, Contact Email, Coach Email, E-mail
    phone:        Phone, Phone Number, Phone #, Contact Phone, Contact Phone #, Coach Phone, Cell, Mobile
Only the team number is required. Rows whose team isn't in the database are skipped with a warning.

contacts.csv holds personal data, so it is gitignored - don't commit it.
"""
import os
import re
import sys

import pandas as pd

from database_setup import Session, Team, TeamContact
from file_picker import pick_csv

COLUMN_ALIASES = {
    "team_id": ["teamnumber", "team", "teamno", "number", "teamid", "team#"],
    "name": ["contactname", "contact", "coach", "coachname", "name", "contactperson"],
    "email": ["email", "contactemail", "coachemail", "emailaddress"],
    "phone": ["phone", "phonenumber", "contactphone", "coachphone", "cell", "mobile", "cellphone",
              "phone#", "contactphone#", "coachphone#"],
}


def _normalize(header):
    return re.sub(r"[^a-z0-9#]", "", str(header).lower())


def _find_columns(columns):
    normalized = {_normalize(col): col for col in columns}
    found = {}
    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                found[field] = normalized[alias]
                break
    return found


def _clean(value):
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _team_number(value):
    text = _clean(value)
    if text is None:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def load_contacts(session, csv_file_path="contacts.csv"):
    """Replace all contacts with the ones in the CSV. Adds to `session`; the caller commits."""
    df = pd.read_csv(csv_file_path, dtype=str)  # dtype=str keeps phone numbers' formatting/leading zeros
    columns = _find_columns(df.columns)
    if "team_id" not in columns:
        raise ValueError(f"{csv_file_path} has no team number column (headers: {list(df.columns)})")
    missing = [field for field in ("name", "email", "phone") if field not in columns]
    if missing:
        print(f"Warning: no column found for {', '.join(missing)} (headers: {list(df.columns)})")

    team_ids = {team_id for (team_id,) in session.query(Team.id)}
    session.query(TeamContact).delete()

    contacts = {}
    for index, row in df.iterrows():
        team_id = _team_number(row[columns["team_id"]])
        if team_id is None:
            continue
        if team_id not in team_ids:
            print(f"Warning: row {index + 2}: team {team_id} is not in the database, skipped")
            continue
        if team_id in contacts:
            print(f"Warning: row {index + 2}: team {team_id} listed again, keeping the later row")
        contacts[team_id] = TeamContact(
            team_id=team_id,
            **{field: _clean(row[col]) for field, col in columns.items() if field != "team_id"},
        )
    session.add_all(contacts.values())

    without = len(team_ids) - len(contacts)
    print(f"Loaded {len(contacts)} contacts from {csv_file_path}"
          + (f" ({without} teams have no contact)" if without else ""))
    return len(contacts)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else pick_csv(
        "Select the contacts CSV (e.g. receipts.csv)",
        initialdir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "CSV_Imports"),
    )
    if not path:
        sys.exit("No contacts file selected - nothing loaded")
    with Session() as session:
        load_contacts(session, path)
        # Contacts aren't in any cached response, so no bump_cache_versions() is needed.
        session.commit()
