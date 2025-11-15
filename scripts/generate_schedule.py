import sqlite3
import os
from datetime import datetime
from weasyprint import HTML

# Connect to the database
db_path = os.path.join(os.path.dirname(__file__), '..', 'team.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Fetch schedule data
cursor.execute("""
    SELECT e.name, e.date, e.team_id, t.name as team_name
    FROM event e
    LEFT JOIN team t ON e.team_id = t.id
    ORDER BY e.date, e.team_id
""")

# Fetch all results
results = cursor.fetchall()

# Generate HTML table
html = """
<!DOCTYPE html>
<html>
<head>
    <title>Schedule</title>
    <style>
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid black; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>Event Schedule</h1>
    <table>
        <tr>
            <th>Event Name</th>
            <th>Date</th>
            <th>Team ID</th>
            <th>Team Name</th>
        </tr>
"""

for row in results:
    date_obj = datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S.%f')
    time_str = date_obj.strftime('%I:%M %p')
    html += f"""
        <tr>
            <td>{row[0]}</td>
            <td>{time_str}</td>
            <td>{row[2] if row[2] else 'N/A'}</td>
            <td>{row[3] if row[3] else 'N/A'}</td>
        </tr>
"""

html += """
    </table>
</body>
</html>
"""

# Write to file

output_path = os.path.join(os.path.dirname(__file__), "generated_schedules", 'schedule.html')
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, 'w') as f:
    f.write(html)

# Close database connection

print(f"Schedule generated: {output_path}")

# Generate individual team schedule files
cursor = conn.cursor()
cursor.execute("SELECT DISTINCT team_id FROM event WHERE team_id IS NOT NULL ORDER BY team_id")
team_ids = [row[0] for row in cursor.fetchall()]

for team_id in team_ids:
    cursor.execute("""
        SELECT e.name, e.date
        FROM event e
        WHERE e.team_id = ?
        ORDER BY e.date
    """, (team_id,))
    
    team_results = cursor.fetchall()
    
    # Get team name
    cursor.execute("SELECT name FROM team WHERE id = ?", (team_id,))
    team_name_row = cursor.fetchone()
    team_name = team_name_row[0] if team_name_row else f"Team {team_id}"
    
    team_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Schedule - {team_name}</title>
    <style>
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid black; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>{team_name} : {team_id}</h1>
    <table>
        <tr>
            <th>Event Name</th>
            <th>Time</th>
        </tr>
"""
    
    for row in team_results:
        date_obj = datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S.%f')
        time_str = date_obj.strftime('%I:%M %p')
        team_html += f"""
        <tr>
            <td>{row[0]}</td>
            <td>{time_str}</td>
        </tr>
"""
    
    team_html += """
    </table>
</body>
</html>
"""
    team_output_path = os.path.join(os.path.dirname(__file__), 'generated_schedules', 'teams', f'schedule_team_{team_id}.html')
    os.makedirs(os.path.dirname(team_output_path), exist_ok=True)
    with open(team_output_path, 'w') as f:
        f.write(team_html)
    
    print(f"Team schedule generated: {team_output_path}")

    # Generate PDF version of team schedule
    pdf_output_path = os.path.join(os.path.dirname(__file__), 'generated_schedules', 'teams', f'{team_id}_schedule_team.pdf')
    HTML(string=team_html).write_pdf(pdf_output_path)
    print(f"Team schedule PDF generated: {pdf_output_path}")