import base64
import io
import os
import re
from datetime import datetime
from html import escape

import qrcode
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from weasyprint import HTML

SCRIPT_DIR = os.path.dirname(__file__)

# QR codes printed at the bottom of every team schedule
SITE_URL = "tuneupinpa.netlify.app"
SITE_QR_PATH = os.path.join(SCRIPT_DIR, "tuneupinpa.netlify.app_home.png")
WIFI_SSID = "LC-lego-robotics"
WIFI_PASSWORD = "LC-lego@2026"


def png_data_uri(png_bytes):
    return "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")


def wifi_escape(value):
    """Escape the characters that are special in the WIFI: QR format."""
    for ch in '\\;,:"':
        value = value.replace(ch, "\\" + ch)
    return value


def qr_data_uri(payload):
    img = qrcode.make(payload, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return png_data_uri(buf.getvalue())


def wifi_qr_data_uri(ssid, password):
    return qr_data_uri(f"WIFI:T:WPA;S:{wifi_escape(ssid)};P:{wifi_escape(password)};;")


with open(SITE_QR_PATH, "rb") as f:
    SITE_QR = png_data_uri(f.read())
WIFI_QR = wifi_qr_data_uri(WIFI_SSID, WIFI_PASSWORD)


def team_app_qr(team_id):
    """(QR data URI, label without https://) for the team's own page in the app."""
    label = f"{SITE_URL}/team/?id={team_id}"
    return qr_data_uri(f"https://{label}"), label


def qr_footer(team_id=None):
    """QR codes for the bottom of a page: the team's own page when team_id is given, else the site home.

    Embedded as data URIs so the HTML files and PDFs are self-contained.
    """
    if team_id is None:
        site_qr, site_label, site_title = SITE_QR, SITE_URL, "Live scores &amp; schedule"
    else:
        site_qr, site_label = team_app_qr(team_id)
        site_title = "Your team's live scores &amp; schedule"
    return f"""
    <div class="qr-row">
        <div class="qr">
            <img src="{site_qr}" alt="QR code for {site_label}">
            <div class="qr-title">{site_title}</div>
            <div>{site_label}</div>
        </div>
        <div class="qr">
            <img src="{WIFI_QR}" alt="Wi-Fi QR code">
            <div class="qr-title">Wi-Fi</div>
            <div>Network: <strong>{WIFI_SSID}</strong></div>
            <div>Password: <strong>{WIFI_PASSWORD}</strong></div>
        </div>
    </div>
"""

QR_STYLES = """
        @page { size: letter; margin: 0.6in; }
        body { font-family: sans-serif; }
        h1 { margin: 0 0 12px; }
        .qr-row { display: flex; justify-content: space-around; margin-top: 24px; page-break-inside: avoid; }
        .qr { text-align: center; font-size: 13px; line-height: 1.4; }
        .qr img { width: 1.8in; height: 1.8in; }
        .qr-title { font-weight: bold; font-size: 15px; margin-top: 4px; }
        .room { font-size: 20px; margin: 0 0 12px; }
        .team-page + .team-page { break-before: page; }
        /* Empty box to tick off by hand on the judge and table schedules */
        th.check, td.check { width: 0.5in; text-align: center; }
        /* Only team names may wrap, so the extra column doesn't split times and sessions over two lines */
        .group-page th, .group-page td:not(.name) { white-space: nowrap; }
        .checkbox { display: inline-block; width: 12px; height: 12px; border: 1.5px solid black; vertical-align: middle; }
        /* Table schedules have up to ~31 rows (5 rounds x 5 matches + 6 morning sessions);
           tighter rows and smaller QR codes keep each on one page, with room for a few more rows */
        .compact h1 { margin-bottom: 8px; }
        .compact th, .compact td { padding: 2px 8px; font-size: 12px; line-height: 1.2; }
        .compact .qr-row { margin-top: 10px; }
        .compact .qr { font-size: 12px; line-height: 1.3; }
        .compact .qr img { width: 1.2in; height: 1.2in; }
"""

# Connect to the database named by database_url in the backend's .env (same as the API)
REPO_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
load_dotenv(os.path.join(REPO_DIR, '.env'))
database_url = os.getenv("database_url", "")
if not database_url:
    raise SystemExit("database_url is not set (check the .env file in the backend folder)")
# Heroku hands out "postgres://" URLs, but SQLAlchemy only accepts "postgresql://".
if database_url.startswith("postgres://"):
    database_url = "postgresql://" + database_url[len("postgres://"):]
# Relative SQLite paths (sqlite:///team.db) are relative to the backend folder, not the cwd.
if database_url.startswith("sqlite:///") and not database_url.startswith("sqlite:////"):
    database_url = "sqlite:///" + os.path.join(REPO_DIR, database_url[len("sqlite:///"):])
print(f"Reading from {database_url.split('://')[0]} database")
engine = create_engine(database_url)
conn = engine.connect()

OUTPUT_DIR = os.path.join(SCRIPT_DIR, "generated_schedules")
TEAMS_DIR = os.path.join(OUTPUT_DIR, "teams")  # team PDFs
HTML_DIR = os.path.join(TEAMS_DIR, "HTML")     # team HTML output
JUDGES_DIR = os.path.join(OUTPUT_DIR, "judges")      # judge group PDFs
JUDGES_HTML_DIR = os.path.join(JUDGES_DIR, "HTML")   # judge group HTML output
TABLES_DIR = os.path.join(OUTPUT_DIR, "tables")      # robot game table PDFs
TABLES_HTML_DIR = os.path.join(TABLES_DIR, "HTML")   # robot game table HTML output
os.makedirs(HTML_DIR, exist_ok=True)
os.makedirs(JUDGES_HTML_DIR, exist_ok=True)
os.makedirs(TABLES_HTML_DIR, exist_ok=True)


def as_datetime(event_date):
    """SQLite returns strings, Postgres returns datetimes."""
    if isinstance(event_date, str):
        return datetime.fromisoformat(event_date)
    return event_date


def format_room(room):
    """'RM:207-i' -> '207-i'; missing -> 'TBD'."""
    if not room:
        return "TBD"
    room = str(room).strip()
    if room.upper().startswith("RM:"):
        room = room[3:].strip()
    return room or "TBD"


def html_document(title, body):
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{escape(title)}</title>
    <style>
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid black; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        {QR_STYLES}
    </style>
</head>
<body>
{body}
</body>
</html>
"""


def team_page(team_id, team_name, room, events):
    rows = ""
    for event_name, event_date in events:
        time_str = as_datetime(event_date).strftime('%I:%M %p')
        rows += f"""
        <tr>
            <td>{escape(event_name)}</td>
            <td>{time_str}</td>
        </tr>"""
    return f"""
<div class="team-page">
    <h1>{escape(team_name)} : {team_id}</h1>
    <div class="room">Room: <strong>{escape(format_room(room))}</strong></div>
    <table>
        <tr>
            <th>Event Name</th>
            <th>Time</th>
        </tr>{rows}
    </table>
    {qr_footer(team_id)}
</div>
"""


teams = conn.execute(text("""
    SELECT DISTINCT e.team_id, t.name, t.room
    FROM event e
    LEFT JOIN team t ON e.team_id = t.id
    WHERE e.team_id IS NOT NULL
    ORDER BY e.team_id
""")).all()

pages = []
documents = []
for team_id, team_name, room in teams:
    team_name = team_name or f"Team {team_id}"
    events = conn.execute(
        text("SELECT name, date FROM event WHERE team_id = :team_id ORDER BY date"),
        {"team_id": team_id},
    ).all()
    page = team_page(team_id, team_name, room, events)
    pages.append(page)

    team_html = html_document(f"Schedule - {team_name}", page)
    team_output_path = os.path.join(HTML_DIR, f'schedule_team_{team_id}.html')
    with open(team_output_path, 'w') as f:
        f.write(team_html)
    print(f"Team schedule generated: {team_output_path}")

    document = HTML(string=team_html).render()
    documents.append(document)
    pdf_output_path = os.path.join(TEAMS_DIR, f'{team_id}_schedule_team.pdf')
    document.write_pdf(pdf_output_path)
    print(f"Team schedule PDF generated: {pdf_output_path}")

# Every team event, for the judge group ("<Session>: Judge Grp N") and table ("<Round>: Table N") schedules
group_events = conn.execute(text("""
    SELECT e.name, e.date, e.team_id, t.name, t.room
    FROM event e
    LEFT JOIN team t ON e.team_id = t.id
    WHERE e.team_id IS NOT NULL
    ORDER BY e.date, e.team_id
""")).all()

conn.close()
engine.dispose()

# Full schedule: every team page, one team per page
output_path = os.path.join(HTML_DIR, 'schedule.html')
with open(output_path, 'w') as f:
    f.write(html_document("Schedule", "".join(pages)))
print(f"Schedule generated: {output_path}")

if documents:
    all_pages = [p for document in documents for p in document.pages]
    pdf_output_path = os.path.join(OUTPUT_DIR, 'schedule.pdf')
    documents[0].copy(all_pages).write_pdf(pdf_output_path)
    print(f"Schedule PDF generated: {pdf_output_path} ({len(all_pages)} pages)")

# Team signs: one landscape page per team with name, number and room in large type
SIGN_STYLES = """
    @page { size: letter landscape; margin: 0.5in; }
    body { font-family: sans-serif; margin: 0; }
    .sign { height: 7.4in; display: flex; flex-direction: column; justify-content: center;
            align-items: center; text-align: center; break-after: page; }
    .sign:last-child { break-after: auto; }
    .sign-name { font-size: 60px; font-weight: bold; line-height: 1.15; margin-bottom: 0.4in; }
    .sign-label { font-size: 24px; color: #555; text-transform: uppercase; letter-spacing: 2px; }
    .sign-value { font-size: 96px; font-weight: bold; line-height: 1.1; margin-bottom: 0.25in; }
    .sign-qr { display: flex; align-items: center; gap: 0.25in; margin-top: 0.1in; text-align: left; }
    .sign-qr img { width: 1.5in; height: 1.5in; }
    .sign-qr-title { font-size: 22px; font-weight: bold; white-space: nowrap; }
    .sign-qr-url { font-size: 16px; color: #555; }
"""


def team_sign(team_id, team_name, room):
    qr, label = team_app_qr(team_id)
    return f"""
<div class="sign">
    <div class="sign-name">{escape(team_name or f"Team {team_id}")}</div>
    <div class="sign-label">Team Number</div>
    <div class="sign-value">{team_id}</div>
    <div class="sign-label">Room</div>
    <div class="sign-value">{escape(format_room(room))}</div>
    <div class="sign-qr">
        <img src="{qr}" alt="QR code for {label}">
        <div>
            <div class="sign-qr-title">Scan for live scores &amp; schedule</div>
            <div class="sign-qr-url">{label}</div>
        </div>
    </div>
</div>"""


signs = "".join(team_sign(team_id, team_name, room) for team_id, team_name, room in teams)

signs_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Team Signs</title>
    <style>{SIGN_STYLES}</style>
</head>
<body>
{signs}
</body>
</html>
"""
signs_pdf_path = os.path.join(OUTPUT_DIR, 'team_signs.pdf')
HTML(string=signs_html).write_pdf(signs_pdf_path)
print(f"Team signs PDF generated: {signs_pdf_path} ({len(teams)} teams)")

def group_visits(prefix):
    """Events whose detail starts with `prefix` ("Judge", "Table"), grouped by that detail.

    Event names look like "Morning Session 1: Judge Grp 2" or "Round 3 Match 1: Table 4".
    Names are compared ignoring spaces and case, so "Table7" and "Table 7" are the same group
    (shown with the space).
    """
    def squash(value):
        return "".join(value.split()).lower()

    groups = {}  # squashed name -> (display name, visits)
    for event_name, event_date, team_id, team_name, room in group_events:
        slot_name, _, detail = event_name.partition(":")
        detail = " ".join(detail.split())
        if not squash(detail).startswith(squash(prefix)):
            continue
        key = squash(detail)
        display, visits = groups.get(key, (detail, []))
        # Prefer the spelling with the most spaces ("Table 7" over "Table7"), and add one before a trailing number
        display = max(display, detail, key=lambda name: name.count(" "))
        display = re.sub(r"(?<=\D)\s*(\d+)$", r" \1", display)
        visits.append(
            (as_datetime(event_date), slot_name.strip(), team_id, team_name or f"Team {team_id}", room)
        )
        groups[key] = (display, visits)
    return dict(groups.values())


def group_sort_key(group_name):
    """Sort 'Judge Grp 10' after 'Judge Grp 2'."""
    match = re.search(r"(\d+)\s*$", group_name)
    return (int(match.group(1)), group_name) if match else (float("inf"), group_name)


def group_page(group_name, visits, slot_heading, show_room, compact):
    rows = "".join(f"""
        <tr>
            <td class="check"><span class="checkbox"></span></td>
            <td>{visit_date.strftime('%I:%M %p')}</td>
            <td>{escape(slot_name)}</td>
            <td>{team_id}</td>
            <td class="name">{escape(team_name)}</td>{f'''
            <td>{escape(format_room(room))}</td>''' if show_room else ''}
        </tr>""" for visit_date, slot_name, team_id, team_name, room in
        sorted(visits, key=lambda visit: visit[:3]))
    room_heading = """
            <th>Room</th>""" if show_room else ""
    return f"""
<div class="team-page group-page{' compact' if compact else ''}">
    <h1>{escape(group_name)}</h1>
    <table>
        <tr>
            <th class="check">Done</th>
            <th>Time</th>
            <th>{slot_heading}</th>
            <th>Team Number</th>
            <th>Team Name</th>{room_heading}
        </tr>{rows}
    </table>
    {qr_footer()}
</div>
"""


def write_group_schedules(groups, kind, slot_heading, show_room, pdf_dir, html_dir, combined_name, compact=False):
    """One HTML + PDF per group, plus every group in one HTML/PDF (one group per page)."""
    pages = []
    documents = []
    for group_name in sorted(groups, key=group_sort_key):
        page = group_page(group_name, groups[group_name], slot_heading, show_room, compact)
        pages.append(page)

        group_slug = group_name.replace(" ", "_").lower()
        group_html = html_document(f"Schedule - {group_name}", page)
        group_html_path = os.path.join(html_dir, f'schedule_{group_slug}.html')
        with open(group_html_path, 'w') as f:
            f.write(group_html)
        print(f"{kind} schedule generated: {group_html_path}")

        document = HTML(string=group_html).render()
        documents.append(document)
        group_pdf_path = os.path.join(pdf_dir, f'{group_slug}_schedule.pdf')
        document.write_pdf(group_pdf_path)
        print(f"{kind} schedule PDF generated: {group_pdf_path}")

    if not documents:
        print(f"No {kind.lower()} events found - no {kind.lower()} schedules generated")
        return

    combined_html_path = os.path.join(html_dir, f'{combined_name}.html')
    with open(combined_html_path, 'w') as f:
        f.write(html_document(f"{kind} Schedules", "".join(pages)))
    print(f"{kind} schedules generated: {combined_html_path}")

    all_pages = [p for document in documents for p in document.pages]
    combined_pdf_path = os.path.join(OUTPUT_DIR, f'{combined_name}.pdf')
    documents[0].copy(all_pages).write_pdf(combined_pdf_path)
    print(f"{kind} schedules PDF generated: {combined_pdf_path} ({len(all_pages)} pages)")


# Judge group schedules: one page per judge group listing its teams in time order.
write_group_schedules(group_visits("Judge"), "Judge group", "Session", True,
                      JUDGES_DIR, JUDGES_HTML_DIR, "judge_schedules")

# Table schedules: one page per robot game table listing which team plays which round there.
# Includes the morning-session table slots as well as the scored rounds.
table_groups = group_visits("Table")
write_group_schedules(table_groups, "Table", "Round", False,
                      TABLES_DIR, TABLES_HTML_DIR, "table_schedules", compact=True)

# Queueing schedule: one row per time slot, one column per table, showing which team is due where.
QUEUE_STYLES = """
    @page { size: letter landscape; margin: 0.4in; }
    body { font-family: sans-serif; margin: 0; }
    h1 { margin: 0 0 8px; }
    table { border-collapse: collapse; width: 100%; table-layout: fixed; }  /* equal-width table columns */
    th.time { width: 0.8in; }
    th.slot { width: 1.25in; }
    thead { display: table-header-group; }  /* repeat the header row on every page */
    tr { break-inside: avoid; }
    th, td { border: 1px solid black; padding: 3px 5px; text-align: left; vertical-align: middle; font-size: 12px; }
    th { background-color: #f2f2f2; }
    td.time, td.slot { white-space: nowrap; }
    th.check, td.check { width: 0.45in; text-align: center; }
    .checkbox { display: inline-block; width: 12px; height: 12px; border: 1.5px solid black; vertical-align: middle; }
    .team-number { font-weight: bold; font-size: 14px; }
    .team-name { font-size: 10px; line-height: 1.15; }
    .queue-page + .queue-page { break-before: page; }  /* one page per round */
"""


def queue_block_title(slot_names):
    """'Round 2' for a round; 'Morning Session 1-6' for the morning sessions."""
    first = slot_names[0]
    if first.startswith("Round"):
        return first.split(" Match")[0]
    first_match = re.match(r"(.*?)\s*(\d+)$", first)
    last_match = re.match(r"(.*?)\s*(\d+)$", slot_names[-1])
    if first_match and last_match and first_match.group(1) == last_match.group(1):
        if first_match.group(2) == last_match.group(2):
            return first
        return f"{first_match.group(1)} {first_match.group(2)}-{last_match.group(2)}"
    return "Morning Sessions"


def queue_schedule_html(table_groups):
    tables = sorted(table_groups, key=group_sort_key)
    slots = {}  # (time, slot name) -> {table: (team_id, team_name)}
    for table, visits in table_groups.items():
        for visit_date, slot_name, team_id, team_name, _room in visits:
            slots.setdefault((visit_date, slot_name), {})[table] = (team_id, team_name)

    header = "".join(f"<th>{escape(table)}</th>" for table in tables)
    # Rows grouped into one page per round; the morning sessions share one page
    blocks = []  # [[round key, [slot names], rows html]]
    for (visit_date, slot_name), teams_at in sorted(slots.items()):
        # "Round 2 Match 3" -> "Round 2"
        round_key = slot_name.split(" Match")[0] if slot_name.startswith("Round") else "Morning"
        if not blocks or blocks[-1][0] != round_key:
            blocks.append([round_key, [], ""])
        if slot_name not in blocks[-1][1]:
            blocks[-1][1].append(slot_name)
        cells = ""
        for table in tables:
            if table in teams_at:
                team_id, team_name = teams_at[table]
                cells += (f'<td><div class="team-number">{team_id}</div>'
                          f'<div class="team-name">{escape(team_name)}</div></td>')
            else:
                cells += "<td></td>"
        blocks[-1][2] += f"""
        <tr>
            <td class="check"><span class="checkbox"></span></td>
            <td class="time">{visit_date.strftime('%I:%M %p')}</td>
            <td class="slot">{escape(slot_name)}</td>
            {cells}
        </tr>"""
    pages = "".join(f"""
<div class="queue-page">
    <h1>Queueing Schedule - {escape(queue_block_title(slot_names))}</h1>
    <table>
        <thead>
        <tr>
            <th class="check">Done</th>
            <th class="time">Time</th>
            <th class="slot">Round</th>
            {header}
        </tr>
        </thead>
        <tbody>{rows}
        </tbody>
    </table>
</div>""" for _round_key, slot_names, rows in blocks)

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>Queueing Schedule</title>
    <style>{QUEUE_STYLES}</style>
</head>
<body>{pages}
</body>
</html>
"""


if table_groups:
    queue_html = queue_schedule_html(table_groups)
    queue_html_path = os.path.join(TABLES_HTML_DIR, 'queue_schedule.html')
    with open(queue_html_path, 'w') as f:
        f.write(queue_html)
    print(f"Queueing schedule generated: {queue_html_path}")

    queue_document = HTML(string=queue_html).render()
    queue_pdf_path = os.path.join(OUTPUT_DIR, 'queue_schedule.pdf')
    queue_document.write_pdf(queue_pdf_path)
    print(f"Queueing schedule PDF generated: {queue_pdf_path} ({len(queue_document.pages)} pages)")
