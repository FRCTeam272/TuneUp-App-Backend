import base64
import io
import os
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


def wifi_qr_data_uri(ssid, password):
    payload = f"WIFI:T:WPA;S:{wifi_escape(ssid)};P:{wifi_escape(password)};;"
    img = qrcode.make(payload, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return png_data_uri(buf.getvalue())


with open(SITE_QR_PATH, "rb") as f:
    SITE_QR = png_data_uri(f.read())
WIFI_QR = wifi_qr_data_uri(WIFI_SSID, WIFI_PASSWORD)

# Embedded as data URIs so the HTML files and PDFs are self-contained.
QR_FOOTER = f"""
    <div class="qr-row">
        <div class="qr">
            <img src="{SITE_QR}" alt="QR code for {SITE_URL}">
            <div class="qr-title">Live scores &amp; schedule</div>
            <div>{SITE_URL}</div>
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
HTML_DIR = os.path.join(TEAMS_DIR, "HTML")     # all HTML output
os.makedirs(HTML_DIR, exist_ok=True)


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
        if isinstance(event_date, str):  # SQLite returns strings, Postgres returns datetimes
            event_date = datetime.fromisoformat(event_date)
        time_str = event_date.strftime('%I:%M %p')
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
    {QR_FOOTER}
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
"""

signs = "".join(f"""
<div class="sign">
    <div class="sign-name">{escape(team_name or f"Team {team_id}")}</div>
    <div class="sign-label">Team Number</div>
    <div class="sign-value">{team_id}</div>
    <div class="sign-label">Room</div>
    <div class="sign-value">{escape(format_room(room))}</div>
</div>""" for team_id, team_name, room in teams)

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
