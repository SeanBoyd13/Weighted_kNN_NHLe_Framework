import pandas as pd
from IPython.display import display
from Code.swat_functions import setup_env, get_player, get_feature, get_translation, get_class_ids, swat

weights, means, stds = setup_env()

drafts = [2024,2025,2026]

for draft in drafts:
    excel_dict = {}
    print(f'\n\nDraft: {draft}')
    ids = get_class_ids(draft)
    
    total = 2026 - draft
    offsets = list(range(0, total + 1))

    print(f'{draft}: {offsets}')

    for offset in offsets:
        rows = []
        print(f'\nOffset: {offset}')

        for id in ids:
            try:
                player = get_player(player_id=id, dy_offset=offset)
                name = f"{get_feature(player, 'first')} {get_feature(player, 'last')}"
                print(name)
            except:
                continue

            row = {}
            row['Player'] = name
            row['Position'] = get_feature(player, 'position')
            row['League'] = get_feature(player, 'league')
            row['Year'] = get_feature(player, 'season_start')
            row['Height'] = get_feature(player, 'height')
            row['Weight'] = get_feature(player, 'weight')
            row['Age'] = get_feature(player, 'age')
            row['Games'] = get_feature(player, 'games')
            row['Goals'] = get_feature(player, 'goals')
            row['Assists'] = get_feature(player, 'assists')
            row['Points'] = get_feature(player, 'points')

            try:
                nhle = round(
                    get_feature(player, 'points_per_game') *
                    swat(player) *
                    82,
                    1
                )
            except:
                nhle = 0

            row['SWAT'] = round(nhle,1)
            # try:
            #     _, c, _ = get_translation(player, n=10, dy_sense=True)
            #     if len(c) > 5:
            #         c = c[0]
            #         comp = f"{get_feature(c,'first')} {get_feature(c,'last')} ({get_feature(c,'league')} - {get_feature(c,'season_start')})"
            #     else:
            #         _, c, _ = get_translation(player, next_league=None, n=10, dy_sense=True)
            #         c = c[0]
            #         comp = f"{get_feature(c,'first')} {get_feature(c,'last')} ({get_feature(c,'league')} - {get_feature(c,'season_start')})*"
            # except:
            #     comp = ''
            # row['Comparable'] = comp
            rows.append(row)

        df = pd.DataFrame(rows)

        if offset < 0:
            sheet = f"DY{offset}"
        elif offset == 0:
            sheet = "DY"
        else:
            sheet = f"DY+{offset}"

        excel_dict[sheet] = (df)
        
    with pd.ExcelWriter(f"Data/{draft}_Draft.xlsx", engine="openpyxl") as writer:
        for sheetname in excel_dict.keys():
            df = excel_dict[sheetname]
            df = df.sort_values(by='SWAT', ascending=False)
            display(df)
            df.to_excel(writer, index=False, sheet_name=sheetname)