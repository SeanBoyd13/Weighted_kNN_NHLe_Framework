import requests
import sqlite3
import os

def season_start_age(player_json, season_start):
    '''
    Takes a player json and season start age to determine a player's age at the NHL Draft cutoff date of a specific season.

    Args:
        player_json (dict): Player JSON from NHL API.
        season_start (integer): Date year at start of a season (ex. 2024 for 2024-25 season).

    Returns:
        float: A player's exact age at the NHL draft cutoff date (Sept. 15th in specified season).
    '''

    bd_year, bd_month, bd_day = player_json['birthDate'].split('-')
    age = (int(season_start)-int(bd_year)) + (1-((int(bd_month)-9)/12 + (int(bd_day)-15)/365))
    return round(age-1,2)


def get_player_ids(draft_years):
    '''
    Takes list of draft years and returns all unique player ids in order of first drafted.

    Args:
        draft_years (list): List of draft years to be included.

    Returns:
        list: All unique player ids (for NHL.com), in order of first drafted, from the draft years provided as a dictionary containing
        their respective draft information (Drafted by Team, Draft Year, Draft Overall).
    '''

    players_drafted = {}
    for draft in draft_years:
        draft_json = requests.get('https://records.nhl.com/site/api/draft?include=draftProspect.id&cayenneExp=%20draftYear%20=%20'+str(draft)).json()

        for pick in draft_json['data']:
            id = pick.get('playerId')
            draft_team = pick.get('triCode')
            overall = pick.get('overallPickNumber')

            if (id is None):
                continue

            players_drafted[id] = (draft_team, draft, overall)
    
    return players_drafted


def get_player_stints(player_id, draft_info, season_starts_array):
    '''
    Takes Player ID, Draft Info, and Year to provide all stints from various leagues and stages from specified season.
    Stints include the following data:
        - Player ID
        - First
        - Last
        - Position Code
        - Season Start Year
        - Drafted by Team
        - Draft Year
        - Draft Overall
        - Draft Year Offset
        - Height (in)
        - Weight (lbs)
        - Age at Season Start
        - League
        - Season Stage
        - Games Played
        - Goals
        - Assists
        - Points
        - Points-per-Game

    Args:
        player_id (int): NHL.com provided Player ID.
        draft_info (list): [Drafted by Team, Draft Year, Overall Pick].
        season_start (int): Start of season calendar year (in YYYY format).

    Returns:
        list: A list of the player's stints from various teams and stages in the specified season.
    '''

    print(f'Trying: https://www.nhl.com/player/{str(player_id)}')
    player = requests.get(f'https://api-web.nhle.com/v1/player/{str(player_id)}/landing').json()
    season_stints = []

    first = player['firstName']['default']
    last = player['lastName']['default']
    position = player['position']
    height = player['heightInInches']
    weight = player['weightInPounds']
    
    for season_start in season_starts_array:
        age = season_start_age(player, season_start)
        draft_team, draft_year, draft_overall = draft_info
        dy_offset = int(age) - int(17)

        for stint in player['seasonTotals']:
            year = (round(stint['season']/10000))
            
            if year != season_start:
                continue
            
            try:
                stage = stint['gameTypeId']
                league = stint['leagueAbbrev']
                games = stint['gamesPlayed']
                goals = stint['goals']
                assists = stint['assists']
                points = stint['points']
            except:
                stage = -1
                league = '-'
                games = -1
                goals = -1
                assists = -1
                points = -1

            stint_metrics = [player_id, first, last, position, season_start, draft_team, draft_year, draft_overall, dy_offset, height, weight, age, league, stage, games, goals, assists, points]
            season_stints.append(stint_metrics)

    return season_stints


def create_db():
    '''
    Creates SQL database 'season_stints' to store player's stints.
    
    Args:
        None.

    Returns:
        None.
    '''

    db_path='sql_data/stints.db'

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    schema = '''
    CREATE TABLE IF NOT EXISTS stints (
        player_id INTEGER,
        first TEXT,
        last TEXT,
        position TEXT,
        season_start INTEGER,
        draft_team TEXT,
        draft_year INTEGER,
        draft_overall INTEGER,
        dy_offset INTEGER,
        height INTEGER,
        weight INTEGER,
        age FLOAT,
        league TEXT,
        stage INTEGER,
        games INTEGER,
        goals INTEGER,
        assists INTEGER,
        points INTEGER,
        PRIMARY KEY (player_id, season_start, league, stage)
    );
    '''

    cursor.executescript(schema)
    conn.commit()
    conn.close()


def populate_with_draft(draft):
    '''
    Populates SQL database with a single draft year full of data for all selected offset range. (Typically DY: -1 to current)

    Args:
        draft (int): NHL Entry Draft.

    Returns:
        None.
    '''
    
    db_path='sql_data/stints.db'

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()


    players = get_player_ids([draft])
    current_year = 2025

    all_stints = []

    for player_id, draft_info in players.items():
        years_to_add = []
        for year in range(draft - 2, current_year + 1):
            years_to_add.append(year)
        stints = get_player_stints(player_id, draft_info, years_to_add)
        for stint in stints:
            print(stint)
            all_stints.append(stint)

    if all_stints:
        cursor.executemany('''
                INSERT OR REPLACE INTO stints (player_id, first, last, position, season_start, draft_team, draft_year, draft_overall, dy_offset, height, weight, age, league, stage, games, goals, assists, points)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', all_stints)
    conn.commit()
    conn.close()


def main():
    create_db()

    years = list(range(2026, 2008, -1)) # Every draft back to '07

    for year in years:
        populate_with_draft(year)


if __name__ == "__main__":
    main()