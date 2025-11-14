import csv
import pandas as pd
import os
from datetime import datetime

def generate_css_styles():
    """Generate CSS styles for the HTML schedule"""
    return """
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header .subtitle {
            margin-top: 10px;
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .schedule-content {
            padding: 30px;
        }
        
        .schedule-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 20px;
            margin: 10px 0;
            background: #f8f9fa;
            border-left: 4px solid #4ECDC4;
            border-radius: 8px;
            transition: all 0.3s ease;
        }
        
        .schedule-item:hover {
            transform: translateX(5px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            background: #e3f2fd;
            border-left-color: #FF6B6B;
        }
        
        .activity-info {
            flex: 1;
        }
        
        .activity-name {
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 2px;
        }
        
        .activity-time {
            font-size: 0.9em;
            color: #7f8c8d;
            font-weight: 500;
        }
        
        .activity-details {
            background: #4ECDC4;
            color: white;
            padding: 8px 15px;
            border-radius: 20px;
            font-weight: 500;
        }
        
        .team-info {
            background: linear-gradient(45deg, #2c3e50, #34495e);
            color: white;
            padding: 20px;
            margin: -30px -30px 30px -30px;
        }
        
        .team-number {
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .team-name {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .generated-info {
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9em;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ecf0f1;
        }
        
        .master-schedule {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .team-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        
        .team-card:hover {
            transform: translateY(-5px);
        }
        
        .team-card h3 {
            margin: 0 0 5px 0;
            color: #2c3e50;
            border-bottom: 2px solid #4ECDC4;
            padding-bottom: 10px;
        }
        
        .room-info {
            font-size: 0.9em;
            color: #7f8c8d;
            font-weight: 500;
            margin-bottom: 15px;
            font-style: italic;
        }
        
        .compact-schedule {
            font-size: 0.9em;
        }
        
        .compact-schedule .schedule-item {
            padding: 8px 15px;
            margin: 5px 0;
        }
        
        .compact-schedule .activity-details {
            padding: 4px 10px;
            font-size: 0.8em;
        }
        
        @media (max-width: 768px) {
            .container {
                margin: 10px;
                border-radius: 10px;
            }
            
            .header {
                padding: 20px;
            }
            
            .header h1 {
                font-size: 2em;
            }
            
            .schedule-content {
                padding: 20px;
            }
            
            .schedule-item {
                flex-direction: column;
                align-items: flex-start;
                gap: 10px;
            }
            
            .activity-details {
                align-self: flex-end;
            }
        }

        /* Print-friendly styles */
        @media print {
            @page {
                margin: 0.5in;
                size: letter;
            }
            
            body {
                background: white !important;
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                color: black !important;
                font-size: 12px;
            }
            
            .container {
                max-width: none !important;
                margin: 0 !important;
                background: white !important;
                border-radius: 0 !important;
                box-shadow: none !important;
                overflow: visible !important;
            }
            
            .header {
                background: white !important;
                color: black !important;
                padding: 8px 0 !important;
                text-align: center;
                border-bottom: 2px solid black;
                margin-bottom: 10px;
            }
            
            .header h1 {
                font-size: 18px !important;
                font-weight: bold !important;
                text-shadow: none !important;
                margin: 0 0 3px 0 !important;
            }
            
            .header .subtitle {
                font-size: 12px !important;
                opacity: 1 !important;
                font-weight: normal;
            }
            
            .schedule-content {
                padding: 0 !important;
            }
            
            .team-info {
                background: white !important;
                color: black !important;
                padding: 8px 0 !important;
                margin: 0 0 10px 0 !important;
                border: 2px solid black;
                text-align: center;
            }
            
            .team-number {
                font-size: 16px !important;
                font-weight: bold !important;
                margin-bottom: 3px !important;
            }
            
            .team-name {
                font-size: 12px !important;
                opacity: 1 !important;
                font-weight: normal;
            }
            
            .schedule-item {
                display: flex !important;
                justify-content: space-between !important;
                align-items: center !important;
                padding: 6px 10px !important;
                margin: 3px 0 !important;
                background: white !important;
                border: 1px solid black !important;
                border-radius: 0 !important;
                transition: none !important;
                page-break-inside: avoid;
                min-height: 35px;
            }
            
            .schedule-item:hover {
                transform: none !important;
                box-shadow: none !important;
                background: white !important;
                border-color: black !important;
            }
            
            .activity-info {
                flex: 1;
            }
            
            .activity-name {
                font-weight: bold !important;
                color: black !important;
                font-size: 10px !important;
                margin-bottom: 1px !important;
                line-height: 1.1;
            }
            
            .activity-time {
                font-size: 9px !important;
                color: black !important;
                font-weight: normal !important;
                line-height: 1.1;
            }
            
            .activity-details {
                background: white !important;
                color: black !important;
                padding: 3px 6px !important;
                border: 1px solid black !important;
                border-radius: 0 !important;
                font-weight: bold !important;
                font-size: 10px !important;
            }
            
            .generated-info {
                text-align: center;
                color: black !important;
                font-size: 8px !important;
                margin-top: 10px !important;
                padding-top: 5px !important;
                border-top: 1px solid black !important;
                page-break-inside: avoid;
            }
            
            .master-schedule {
                display: block !important;
                columns: 3;
                column-gap: 15px;
            }
            
            .team-card {
                background: white !important;
                border: 1px solid black !important;
                border-radius: 0 !important;
                padding: 8px !important;
                box-shadow: none !important;
                transition: none !important;
                margin-bottom: 10px !important;
                page-break-inside: avoid;
                break-inside: avoid;
            }
            
            .team-card:hover {
                transform: none !important;
            }
            
            .team-card h3 {
                margin: 0 0 3px 0 !important;
                color: black !important;
                border-bottom: 1px solid black !important;
                padding-bottom: 3px !important;
                font-size: 10px !important;
                line-height: 1.1;
            }
            
            .room-info {
                font-size: 8px !important;
                color: black !important;
                font-weight: normal !important;
                margin-bottom: 6px !important;
                font-style: italic;
            }
            
            .compact-schedule {
                font-size: 8px !important;
            }
            
            .compact-schedule .schedule-item {
                padding: 3px 5px !important;
                margin: 2px 0 !important;
                min-height: 20px !important;
            }
            
            .compact-schedule .activity-details {
                padding: 2px 4px !important;
                font-size: 7px !important;
            }
            
            .compact-schedule .activity-name {
                font-size: 7px !important;
                line-height: 1.1;
            }
            
            .compact-schedule .activity-time {
                font-size: 6px !important;
                line-height: 1.1;
            }
            
            /* Force page breaks for individual schedules */
            .page-break {
                page-break-before: always;
            }
        }
    </style>
    """

def generate_html_schedule(team_id, schedule, css_styles, time_mapping=None):
    """Generate HTML content for individual team schedule"""
    team_parts = team_id.split(' - ', 1)
    team_number = team_parts[0]
    team_name = team_parts[1] if len(team_parts) > 1 else "Team"
    
    schedule_items = ""
    for activity, details in schedule.items():
        if activity not in ['Team Number', 'Team Name', 'Rm:Num']:
            # Get the time for this activity if available
            time_info = ""
            if time_mapping and activity in time_mapping:
                time_info = f"<div class='activity-time'>{time_mapping[activity]}</div>"
            
            schedule_items += f"""
            <div class="schedule-item">
                <div class="activity-info">
                    <div class="activity-name">{activity}</div>
                    {time_info}
                </div>
                <div class="activity-details">{details}</div>
            </div>
            """
    
    current_time = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Schedule - {team_id}</title>
        {css_styles}
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>FLL Competition Schedule</h1>
                <div class="subtitle">Individual Team Schedule</div>
            </div>
            
            <div class="schedule-content">
                <div class="team-info">
                    <div class="team-number">Team {team_number}</div>
                    <div class="team-name">{team_name}</div>
                </div>
                
                {schedule_items}
                
                <div class="generated-info">
                    Generated on {current_time}
                </div>
            </div>
        </div>
    </body>
    </html>
    """.replace(".0", "")
    
    return html_content

def generate_master_schedule_html(individual_schedules, css_styles, time_mapping=None):
    """Generate master HTML schedule with all teams"""
    current_time = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    
    team_cards = ""
    for team_id, schedule in individual_schedules.items():
        team_parts = team_id.split(' - ', 1)
        team_number = team_parts[0]
        team_name = team_parts[1] if len(team_parts) > 1 else "Team"
        
        # Get room number from schedule
        room_number = schedule.get('Rm:Num', 'N/A')
        
        schedule_items = ""
        for activity, details in schedule.items():
            if activity not in ['Team Number', 'Team Name', 'Rm:Num']:
                # Get the time for this activity if available
                time_info = ""
                if time_mapping and activity in time_mapping:
                    time_info = f"<div class='activity-time'>{time_mapping[activity]}</div>"
                
                schedule_items += f"""
                <div class="schedule-item">
                    <div class="activity-info">
                        <div class="activity-name">{activity}</div>
                        {time_info}
                    </div>
                    <div class="activity-details">{details}</div>
                </div>
                """
        
        team_cards += f"""
        <div class="team-card">
            <h3>Team {team_number} - {team_name}</h3>
            <div class="room-info">{room_number}</div>
            <div class="compact-schedule">
                {schedule_items}
            </div>
        </div>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FLL Competition - Master Schedule</title>
        {css_styles}
    </head>
    <body>
        <div class="container" style="max-width: 1400px;">
            <div class="header">
                <h1>FLL Competition Schedule</h1>
                <div class="subtitle">Master Schedule - All Teams</div>
            </div>
            
            <div class="schedule-content">
                <div class="master-schedule">
                    {team_cards}
                </div>
                
                <div class="generated-info">
                    Generated on {current_time} | Total Teams: {len(individual_schedules)}
                </div>
            </div>
        </div>
    </body>
    </html>
    """.replace(".0", "")
    
    return html_content

def generate_individual_schedules(csv_file_path):
    """
    Read CSV file and generate individual schedules for each participant/team
    """
    try:
        # Read the CSV file
        df = pd.read_csv(csv_file_path)
        
        # Display available columns
        print("Available columns:", df.columns.tolist())
        print(f"Total rows: {len(df)}")
        
        # Filter out columns that are completely empty or only contain NaN/empty strings
        columns_with_values = []
        for col in df.columns:
            # Check if column has any non-null, non-empty values
            has_values = df[col].notna().any() and (df[col].astype(str).str.strip() != '').any()
            if has_values:
                columns_with_values.append(col)
        
        print(f"Columns with values: {columns_with_values}")
        
        # Filter dataframe to only include columns with values
        df_filtered = df[columns_with_values]
        
        # Extract time information from the first row (index 0)
        time_mapping = {}
        first_row = df_filtered.iloc[0] if len(df_filtered) > 0 else None
        if first_row is not None:
            for col in columns_with_values:
                value = first_row[col]
                if pd.notna(value) and str(value).strip() != '' and col not in ['Index:', 'Rm:Num', 'Team Number', 'Team Name']:
                    time_mapping[col] = str(value).strip()
        
        print(f"\nExtracted time mapping: {time_mapping}")
        
        # Generate individual schedules for each team
        individual_schedules = {}
        
        for index, row in df_filtered.iterrows():
            # Skip rows without team information (first row is headers/times)
            team_number = row.get('Team Number', '')
            team_name = row.get('Team Name', '')
            
            if pd.isna(team_number) or str(team_number).strip() == '':
                continue
                
            # Create team identifier
            team_id = f"{team_number} - {team_name}" if team_name and not pd.isna(team_name) else str(team_number)
            
            # Build schedule for this team
            schedule = {}
            for col in columns_with_values:
                value = row[col]
                if pd.notna(value) and str(value).strip() != '':
                    schedule[col] = str(value).strip()
            
            individual_schedules[team_id] = schedule
        
        # Display individual schedules
        print(f"\nGenerated {len(individual_schedules)} individual schedules:")
        for team_id, schedule in individual_schedules.items():
            print(f"\n=== {team_id} ===")
            for activity, details in schedule.items():
                print(f"{activity}: {details}")
        
        # Save individual schedules to separate HTML files
        output_dir = "individual_schedules"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Generate CSS styles
        css_styles = generate_css_styles()
        
        for team_id, schedule in individual_schedules.items():
            # Create safe filename
            safe_filename = "".join(c for c in team_id if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_filename = safe_filename.replace(' ', '_')
            filename = os.path.join(output_dir, f"{safe_filename}_schedule.html")
            
            html_content = generate_html_schedule(team_id, schedule, css_styles, time_mapping)
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
        
        # Generate master schedule HTML
        master_html = generate_master_schedule_html(individual_schedules, css_styles, time_mapping)
        master_filename = os.path.join(output_dir, "master_schedule.html")
        with open(master_filename, 'w', encoding='utf-8') as f:
            f.write(master_html)
        
        print(f"\nIndividual HTML schedule files saved in '{output_dir}' directory")
        print(f"Master schedule saved as '{master_filename}'")
        
        return individual_schedules
        
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return {}

# Main execution
if __name__ == "__main__":
    csv_file = "FLL Schedule.xlsx - Schedule.csv"  # Update with your CSV file path
    individual_schedules = generate_individual_schedules(csv_file)