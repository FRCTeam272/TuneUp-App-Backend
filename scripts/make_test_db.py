"""Create a SQLite database full of dummy teams, events and scores for testing the frontend.

    python scripts/make_test_db.py                     # writes test.db in the repo root
    python scripts/make_test_db.py other.db --force    # replace an existing file
    python scripts/make_test_db.py --teams 40 --played 5 --date 2025-11-22

Then point the API at it (`database_url=sqlite:///test.db` in .env) and restart the server; a running
server keeps cached responses from the old file.

The data has the same shape load_teams.py produces from schedule.csv (event names are
"<activity>: <details>", judging events contain "Judge"), so /schedule/ and /schedule/rooms work.
It also includes edge cases the pages should handle: teams with no scores, a single score, many
scores, a zero, a tie, no room, and a very long name. The same --seed always gives the same data.
"""
import argparse
import os
import random
import sys
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NAMES = [
    "RoboHatters Black", "RoboHatters Red", "Gear Grinders", "Brick Wizards", "Circuit Breakers",
    "The Lego Legends", "Mindstorm Mavericks", "Torque Titans", "Pixel Pirates", "Byte Bandits",
    "Sprocket Rockets", "Code Crusaders", "Axle Avengers", "Motor Mayhem", "Quantum Bricks",
    "Spike Sparks", "Robo Raptors", "Binary Builders", "Technic Tigers", "Iron Owls",
    "Cog Commanders", "Servo Squad", "Studs & Stacks", "Logic Lynx", "Gyro Gang", "Volt Vikings",
    "Hydraulic Hawks", "Piston Panthers", "Ratchet Rangers", "Widget Wolves",
    "Mega Motors", "Rocket Riggers", "Lego Lab Rats", "Tin Can Titans", "Wrench Warriors",
    "Circuit Cobras", "Drill Drones", "Steel Stompers", "Turbo Tinkerers", "Nexa Nuts",
    "Bolt Brothers", "Metal Moles", "Vector Vanguards", "Micro Mechanics", "Jumper Jacks",
    "Gadget Gators", "Fusion Falcons", "Spark Strikers", "Prime Pilots", "Arcade Assemblers",
    "Turbo Turtles", "Mighty Magnets", "Ruby Rovers", "Orbit Ospreys", "Signal Sleds",
    "Crank Crew", "Rapid Rivets", "Forge Flyers", "Copper Crafters", "Plasma Pioneers",
]
LONG_NAME = "The Extraordinarily Long-Named Robotics Collective of Greater Pennsylvania"

SESSIONS = 6         # morning judging/practice sessions, 30 minutes each from 9:00
ROUNDS = 5           # robot game rounds
MATCHES = 4          # matches per round, 7 minutes apart
PER_MATCH = 6        # tables per match


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("output", nargs="?", default=os.path.join(ROOT, "test.db"),
                        help="SQLite file to create (default: test.db in the repo root)")
    parser.add_argument("--force", action="store_true", help="replace the file if it exists")
    parser.add_argument("--teams", type=int, default=24,
                        help=f"number of teams, at most {MATCHES * PER_MATCH} (default 24)")
    parser.add_argument("--played", type=int, default=3,
                        help=f"robot game rounds that already have scores, 0-{ROUNDS} (default 3)")
    parser.add_argument("--date", type=date.fromisoformat, default=date.today(),
                        help="event day, YYYY-MM-DD (default today, so some events are in the past)")
    parser.add_argument("--seed", type=int, default=2025, help="random seed (default 2025)")
    args = parser.parse_args()
    if not 1 <= args.teams <= MATCHES * PER_MATCH:
        parser.error(f"--teams must be 1-{MATCHES * PER_MATCH}")
    if not 0 <= args.played <= ROUNDS:
        parser.error(f"--played must be 0-{ROUNDS}")
    return args


def schedule_for(index, day):
    """(datetime, event name) pairs for the team at `index`, laid out like the real schedule CSV."""
    at = lambda hour, minute: datetime.combine(day, datetime.min.time()).replace(hour=hour, minute=minute)
    group = index // SESSIONS % MATCHES + 1      # teams in the same session get different groups
    judge_session = index % SESSIONS
    practice_session = (judge_session + SESSIONS // 2) % SESSIONS
    match = index % MATCHES
    table = index // MATCHES % PER_MATCH + 1

    events = [(at(8, 30), "Coach Meeting in Gym: Coach Meeting in Gym")]
    session_start = lambda s: at(9, 0) + timedelta(minutes=30 * s)
    events.append((session_start(judge_session), f"Morning Session {judge_session + 1}: Judge Grp {group}"))
    events.append((session_start(practice_session), f"Morning Session {practice_session + 1}: Table {table}"))
    events.append((at(12, 0), "Opening Ceremony: Opening Ceremony"))
    for game_round in range(ROUNDS):
        start = at(12, 15) + timedelta(minutes=7 * (game_round * MATCHES + match))
        events.append((start, f"Round {game_round + 1} Match {match + 1}: Table {table}"))
    events.append((at(15, 0), "Closing Ceremony: Closing Ceremony"))
    return events


def scores_for(index, team_count, played, rng):
    """Scores for the team at `index`; a few positions are reserved for edge cases."""
    if index == 1:
        return []                       # registered, never played
    if index == 2:
        return [0] * min(played, 1)     # one round, scored zero
    if index == team_count - 1 and played:
        return [rng.randint(100, 300)]  # only one round so far
    skill = rng.uniform(0.3, 1.0)
    scores = [max(0, min(600, round(rng.gauss(400 * skill, 60)))) for _ in range(played)]
    if index == 0 and played:
        scores += [rng.randint(150, 450) for _ in range(3)]  # replayed rounds: more than five scores
    return scores


def main():
    args = parse_args()
    output = os.path.abspath(args.output)
    if os.path.exists(output):
        if not args.force:
            sys.exit(f"{output} already exists; pass --force to replace it.")
        os.remove(output)

    # database_setup connects (and creates the tables) on import. load_dotenv() won't override this.
    os.environ["database_url"] = f"sqlite:///{output}"
    sys.path.insert(0, ROOT)
    from database.database_setup import ROSTER, SCORES, Event, Score, Session, Team, bump_cache_versions, engine

    rng = random.Random(args.seed)
    names = NAMES[:]
    rng.shuffle(names)
    team_ids = rng.sample(range(1000, 99999), args.teams)

    with Session() as session:
        teams = []
        for index, team_id in enumerate(team_ids):
            name = LONG_NAME if index == 3 else names[index % len(names)]
            room = None if index == 4 else f"RM:{101 + index // 2}-{'i' * (index % 2 + 1)}"
            teams.append(Team(id=team_id, name=name, room=room))
        session.add_all(teams)
        session.flush()

        for index, team in enumerate(teams):
            for when, name in schedule_for(index, args.date):
                session.add(Event(name=name, date=when, team_id=team.id))

        # Scores are inserted round by round, the order they'd be entered during an event.
        score_lists = [scores_for(index, args.teams, args.played, rng) for index in range(args.teams)]
        if args.teams > 6 and score_lists[5] and score_lists[6]:
            score_lists[6] = list(score_lists[5])  # an exact tie on average
        for position in range(max(map(len, score_lists))):
            for team, scores in zip(teams, score_lists):
                if position < len(scores):
                    session.add(Score(team_id=team.id, score=scores[position]))

        bump_cache_versions(session, ROSTER, SCORES)
        team_names = [team.name for team in teams]  # committing expires the objects
        session.commit()

        event_count = session.query(Event).count()
        score_count = session.query(Score).count()

    engine.dispose()

    team = lambda index: f"#{team_ids[index]} {team_names[index]}"
    edge_cases = [
        (0, lambda: f"{team(0)}: {len(score_lists[0])} scores" if score_lists[0] else None),
        (1, lambda: f"{team(1)}: no scores"),
        (2, lambda: f"{team(2)}: {'a single 0' if score_lists[2] else 'no scores'}"),
        (3, lambda: f"#{team_ids[3]}: very long name"),
        (4, lambda: f"{team(4)}: no room"),
        (6, lambda: f"#{team_ids[5]} and #{team_ids[6]}: tied" if score_lists[5] else None),
    ]
    print(f"Wrote {output}")
    print(f"  {args.teams} teams, {event_count} events on {args.date}, {score_count} scores "
          f"({args.played} of {ROUNDS} rounds played)")
    lines = [line for index, describe in edge_cases if index < args.teams and (line := describe())]
    if lines:
        print("Edge cases:\n  " + "\n  ".join(lines))
    inside_repo = os.path.commonpath([output, ROOT]) == ROOT
    print(f"\nUse it: database_url=sqlite:///{os.path.relpath(output, ROOT) if inside_repo else output} "
          "in .env, then restart the server.")


if __name__ == "__main__":
    main()
