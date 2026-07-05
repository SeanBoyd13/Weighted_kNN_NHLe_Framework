import sqlite3
import pandas as pd
import math

def get_stats_summary():
    '''
    Gets stats summary for all players from the season stints database.
    '''

    db_path = "sql_data/stints.db"
    conn = sqlite3.connect(db_path)

    df = pd.read_sql_query(
        """
        SELECT season_start, height, weight, age, games, goals, assists, points,
          ROUND(CAST(goals AS REAL) / games, 2) AS goals_per_game,
          ROUND(CAST(assists AS REAL) / games, 2) AS assists_per_game,
          ROUND(CAST(points AS REAL) / games, 2) AS points_per_game
        
        FROM stints
        WHERE season_start IS NOT NULL
          AND height IS NOT NULL
          AND weight IS NOT NULL
          AND age IS NOT NULL
          AND games IS NOT NULL
          AND goals IS NOT NULL
          AND assists IS NOT NULL
          AND points IS NOT NULL
          AND goals_per_game IS NOT NULL
          AND assists_per_game IS NOT NULL
          AND points_per_game IS NOT NULL
    """,
        conn,
    )
    conn.close()

    means = df.mean()
    stds = df.std(ddof=0)

    return means.to_dict(), stds.to_dict()

def get_info(playerid, year, feature):
    '''
    Retrieves non-player vector information from playerid and year.
    '''
    
    db_path = "sql_data/stints.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    query = f"""
        SELECT dy_offset
        FROM stints
        WHERE player_id = {playerid}
        AND season_start = {year};
    """
    cursor.execute(query, ())
    results = cursor.fetchall()

    try:
        return results[0]
    except Exception as e:
        return

def set_weights(
    season_start_w=(10),
    height_w=(10),
    weight_w=(10),
    age_w=(10),
    games_w=(10),
    goals_w=(10),
    assists_w=(10),
    points_w=(10),
    goals_per_game_w=(0),
    assists_per_game_w=(0),
    points_per_game_w=(0),
):
    '''
    Sets weights for similarity scoring system. With potential to include microstats (TBD).
    '''

    weights = {
        "season_start": season_start_w,
        "height": height_w,
        "weight": weight_w,
        "age": age_w,
        "games": games_w,
        "goals": goals_w,
        "assists": assists_w,
        "points": points_w,
        "goals_per_game": goals_per_game_w,
        "assists_per_game": assists_per_game_w,
        "points_per_game": points_per_game_w,
    }

    total = 0
    for k in weights.keys():
        total += weights[k]
    
    for k in weights.keys():
        weights[k] = weights[k]/total

    return weights

def setup_env():
    '''
    Generates current means and standard deviations for all players.
    '''
    weights = set_weights(season_start_w=(0))
    means, stds = get_stats_summary() 
    
    return weights, means, stds

weights, means, stds = setup_env()

def get_player(first=None, last=None, player_id=None, position=None, season=None, league=None, stage=None, dy_offset=None):
    '''
    Retrieves specified player stint based on the information provided.
    '''

    db_path = "sql_data/stints.db"

    if stage == 'regular':
        stage = 2

    if str(dy_offset) == str(0):
        dy_offset = str(dy_offset)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    query = f"""
        SELECT player_id, first, last, position, league, season_start, height, weight, age, games, goals, assists, points,
                ROUND(CAST(goals AS REAL) / games, 2) AS goals_per_game,
                ROUND(CAST(assists AS REAL) / games, 2) AS assists_per_game,
                ROUND(CAST(points AS REAL) / games, 2) AS points_per_game,
                dy_offset
        FROM stints
        WHERE player_id {"IN ('"+str(player_id)+"')" if player_id else 'IS NOT NULL'}
        AND first {"IN ('"+str(first)+"')" if first else 'IS NOT NULL'}
        AND last {"IN ('"+str(last)+"')" if last else 'IS NOT NULL'}
        AND position {"IN ('"+str(position)+"')" if position else 'IS NOT NULL'}
        AND season_start {"IN ('"+str(season)+"')" if season else 'IS NOT NULL'}
        AND stage {"IN ('"+str(stage)+"')" if stage else 'IS NOT NULL'}
        AND league {"IN ('"+str(league)+"')" if league else 'IS NOT NULL'}
        AND dy_offset {"IN ('"+str(dy_offset)+"')" if dy_offset else 'IS NOT NULL'}
        AND goals_per_game IS NOT NULL
        AND assists_per_game IS NOT NULL
        AND points_per_game IS NOT NULL
        ORDER BY season_start DESC, games DESC;
    """
    cursor.execute(query, ())
    results = cursor.fetchall()

    try:
        return results[0]
    except Exception as e:
        return

def get_feature(player, feature):
    '''
    Gets specified feature from a player vector.
    '''
    
    player_indicies = {'player_id': 0,
        'first': 1,
        'last': 2,
        'position': 3,
        'league': 4,
        'season_start': 5,
        'height': 6,
        'weight': 7,
        'age' : 8,
        'games': 9,
        'goals': 10,
        'assists': 11,
        'points': 12,
        'goals_per_game': 13,
        'assists_per_game': 14,
        'points_per_game': 15,
        'translation': 16,
        'next_league': 17}

    index = player_indicies[feature]
    return player[index]

def get_league_set(player, next_league=None, min_gp=10):
    '''
    Gets the entire league set based on minimum gp in current and next league.
    Matches with player position as well.
    '''
    
    db_path = "sql_data/stints.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    league1 = get_feature(player, 'league')
    league2 = next_league
    max_year = get_feature(player, 'season_start')
    position = get_feature(player, 'position')

    if league1 == 'U20 Nationell':
        league1 = 'J20 Nationell'

    query = f"""
        SELECT DISTINCT s1.player_id, s1.first, s1.last, s1.position, s1.league, s1.season_start, s1.height, s1.weight, s1.age, s1.games, s1.goals, s1.assists, s1.points,
            ROUND(CAST(s1.goals AS REAL) / s1.games, 2) AS goals_per_game,
            ROUND(CAST(s1.assists AS REAL) / s1.games, 2) AS assists_per_game,
            ROUND(CAST(s1.points AS REAL) / s1.games, 2) AS points_per_game,
            ROUND((CAST(s2.points AS REAL) / s2.games)/(CAST(s1.points AS REAL) / s1.games),2) AS translation_rate,
            s2.league AS next_league
        FROM stints s1
        JOIN stints s2 ON s1.player_id = s2.player_id
        WHERE s1.stage = 2
        AND s2.stage = 2
        AND s1.league {"= '"+str(league1)+"'" if league1 else 'IS NOT NULL'}
        AND s2.league {"= '"+str(league2)+"'" if league2 else 'IS NOT NULL'}
        AND s1.position IN ({"'C','L','R','F'" if position in ('C','L','R','F') else "'D'"})
        AND s1.season_start < {str(max_year)}
        AND s2.season_start = s1.season_start + 1
        AND s1.games > {str(min_gp)}
        AND s2.games > {str(min_gp)}
        AND goals_per_game IS NOT NULL
        AND assists_per_game IS NOT NULL
        AND points_per_game IS NOT NULL
        AND points_per_game IS NOT NULL
        AND translation_rate IS NOT NULL
        ORDER BY translation_rate DESC;
    """
    cursor.execute(query, ())
    results = cursor.fetchall()

    conn.close()

    return results

def standardize(player):
    """
    Standardizes the stats in a player vector.
    """

    player_indicies = {'player_id': 0,
        'first': 1,
        'last': 2,
        'position': 3,
        'league': 4,
        'season_start': 5,
        'height': 6,
        'weight': 7,
        'age' : 8,
        'games': 9,
        'goals': 10,
        'assists': 11,
        'points': 12,
        'goals_per_game': 13,
        'assists_per_game': 14,
        'points_per_game': 15,
        'translation': 16,
        'next_league': 17}

    player = list(player)
    z_player = player.copy()

    for feature in player_indicies.keys():
        index = player_indicies[feature]

        if feature in weights.keys():
            mean = means[feature]
            stdev = stds[feature]
            value = player[index]

            z = (value - mean) / stdev

            perc = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))

            z_player[index] = round(perc,2)
        
        else:
            try:
                z_player[index] = player[index]
            except:
                continue
            
    return z_player

def similarity(player1, player2):
    """
    Returns similarity score between two z-scored player vectors.
    """
    similarity = 0

    for feature in weights.keys():
        weight = weights[feature]
        p1 = get_feature(player1, feature)
        p2 = get_feature(player2, feature)

        similarity += abs(p1 - p2) * weight

    return similarity

def get_translation(player, next_league='NHL', feature='translation', n=0, dy_sense=False):
    '''
    Gets the weighted-average prediction for the translation rate between a player's
    current league and the next.
    '''

    league_set = get_league_set(player, next_league)
    total_result = 0
    weight_total = 0

    similarity_dict = {}

    for past in league_set:
        if dy_sense:
            if get_info(past[0], past[5], 'dy_offset') == get_info(player[0], player[5], 'dy_offset'):
                continue

        sim = similarity(standardize(player), standardize(past))
        total_result += get_feature(past, feature) * (1-sim)**2
        weight_total += (1-sim)**2

        similarity_dict[past] = (1-sim)**2
    
    sorted_sim_dict = dict(sorted(similarity_dict.items(), key=lambda item: item[1], reverse=True))

    result = round(total_result / weight_total, 2)

    if n > 0:
        comps = []
        sims = {}
        for k, v in list(sorted_sim_dict.items())[:n]:
            #print(k, round(v,3))
            comps.append(k)
            sims[k] = v
        return result, comps, sims
    else:
        return result

def simulate(player, factor, next_league='NHL'):
    '''
    Simulates a player's season and new stats based on a player's translation rate.
    '''
    
    player_indicies = {'player_id': 0,
        'first': 1,
        'last': 2,
        'position': 3,
        'league': 4,
        'season_start': 5,
        'height': 6,
        'weight': 7,
        'age' : 8,
        'games': 9,
        'goals': 10,
        'assists': 11,
        'points': 12,
        'goals_per_game': 13,
        'assists_per_game': 14,
        'points_per_game': 15,
        'translation': 16,
        'next_league': 17}

    simulated_player = list(player).copy()

    simulated_player[player_indicies['age']] = player[player_indicies['age']] + 1
    simulated_player[player_indicies['season_start']] = player[player_indicies['season_start']] + 1
    simulated_player[player_indicies['league']] = next_league

    try:
        simulated_player[player_indicies['games']] = int(get_translation(player, next_league, 'games'))
    except:
        return

    simulated_player[player_indicies['goals_per_game']] = round(player[player_indicies['goals_per_game']] * factor,2)
    simulated_player[player_indicies['assists_per_game']] = round(player[player_indicies['assists_per_game']] * factor,2)
    simulated_player[player_indicies['points_per_game']] = round(player[player_indicies['points_per_game']] * factor,2)

    simulated_player[player_indicies['goals']] = int(simulated_player[player_indicies['goals_per_game']] * simulated_player[player_indicies['games']])
    simulated_player[player_indicies['assists']] = int(simulated_player[player_indicies['assists_per_game']] * simulated_player[player_indicies['games']])
    simulated_player[player_indicies['points']] = int(simulated_player[player_indicies['goals']] + simulated_player[player_indicies['assists']])

    return simulated_player

def get_weighted_paths(player):
    '''
    Provides the most likely next leagues and its corresponding weight likelihood.
    '''

    league_set = get_league_set(player)
    total_result = 0
    weight_total = 0

    paths_dict = {}

    for past in league_set:
        sim = similarity(standardize(player), standardize(past))
        path = get_feature(past, 'next_league')
        try:
            paths_dict[path] += round((1-sim)**2,2)
        except:
            paths_dict[path] = round((1-sim)**2,2)

    return paths_dict

def get_class_ids(draft_year):
    '''
    Retrieves an array of all players from an entire draft class for a specified season.
    '''

    db_path = "sql_data/stints.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = f"""
        SELECT DISTINCT player_id
        FROM stints
        WHERE draft_year = {str(draft_year)}
    """

    cursor.execute(query, ())
    results = cursor.fetchall()

    conn.close()

    draft_class = []

    for r in results:
        draft_class.append(r[0])

    return draft_class

def swat(player, max_depth=1, depth=0, full_path=[]):
    '''
    Recursive similarity-weighted approximate translation function.
    '''

    current_league = get_feature(player, 'league')
    this_path = full_path.copy()
    this_path.append(current_league)

    if depth == max_depth:
        try:
            if current_league == 'NHL':
                return 1 / 1.2**depth
            else:
                return get_translation(player) / 1.2**(depth+1)
        except:
            return 0
    
    paths_dict = get_weighted_paths(player)
    paths_dict = dict(sorted(paths_dict.items(), key=lambda item: item[1], reverse=True))

    total_swat = 0
    total_frequency = 0

    for path in paths_dict.keys():
        frequency = paths_dict[path]
        percentage = frequency/sum(paths_dict.values())

        if percentage <= 0.10 and path != 'NHL':
            continue

        factor = get_translation(player, path)

        new_player = simulate(player, factor, path)

        swat_from_path = swat(new_player, max_depth, depth+1, this_path)

        total_swat += factor * frequency * swat_from_path
        total_frequency += frequency

    return round(total_swat/total_frequency,3)