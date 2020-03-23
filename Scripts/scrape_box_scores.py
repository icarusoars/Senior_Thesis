from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import pandas as pd
from datetime import date, timedelta
import time
import pickle

# these are replacement strings for unexpected spaces and newlines by our script
text_replacements = {
    # Hustle stats replacement strings
    'SCREEN\nASSISTS': 'SCREEN_ASSISTS',
    'SCREEN ASSISTS' : 'SCREEN_ASSISTS',
    'SCREEN_ASSISTS PTS': 'SCREEN_ASSISTS_PTS',
    'OFF LOOSE BALLS\nRECOVERED': 'OFF_LOOSE_BALLS_RECOVERED',
    'DEF LOOSE BALLS\nRECOVERED': 'DEF_LOOSE_BALLS_RECOVERED',
    'LOOSE BALLS\nRECOVERED': 'LOOSE_BALLS_RECOVERED',
    'CHARGES\nDRAWN': 'CHARGES_DRAWN',
    'CONTESTED\n2PT SHOTS': 'CONTESTED_2PT_SHOTS',
    'CONTESTED\n3PT SHOTS': 'CONTESTED_3PT_SHOTS',
    'CONTESTED\nSHOTS': 'CONTESTED_SHOTS',
    'OFF BOX OUTS' : 'OFF_BOX_OUTS',
    'DEF BOX OUTS' : 'DEF_BOX_OUTS',
    'BOX\nOUTS': 'BOX_OUTS',
    # Advanced stats replacement strings
    ' RATIO': '_RATIO',
    # Defense stats replacement strings
    'DEF\nMIN': 'DEF_MIN',
    'PARTIAL\nPOSS': 'PARTIAL_POSS'
}

# all the options we want to scrape for
options = ['Traditional', 'Advanced', 'Usage', 'Player Tracking', 'Hustle', 'Defense']

# storage location - where pickle files get stored
store_location = '../Pickles/2019_2020'

# specify dates to scrape
start_date = date(2019, 11, 4)
end_date   = date(2019, 11, 8)
delta      = timedelta(days=1)


# instantiate selenium chromedriver
path_to_chromedriver = '/Users/skylershi/Data Science/chromedriver' # Path to access a chrome driver
browser = webdriver.Chrome(executable_path=path_to_chromedriver)


date_scrape = start_date
while date_scrape <= end_date:
    date_str = date_scrape.strftime("%m/%d/%Y")
    date_str_2 = date_scrape.strftime("%Y_%m_%d")
    date_scrape += delta
    
    print("Scraping Games on Date: {}".format(date_str))
    
#     time.sleep(6)
    date_url = 'https://stats.nba.com/scores/{}'.format(date_str)
    browser.get(date_url)
    time.sleep(5)
    
    
    # get all boxscore links
    box_score_links = browser.find_elements_by_partial_link_text('Box Score')

    for i in range(len(box_score_links)):

        browser.find_elements_by_partial_link_text('Box Score')[i].click()
        time.sleep(3)

        # browser is within boxscore page now

        # keep track of all stats with a list of dfs
        team1_stats_dfs = []
        team2_stats_dfs = []
        team1 = browser.find_elements_by_class_name('nba-stat-table__caption')[0].text
        team2 = browser.find_elements_by_class_name('nba-stat-table__caption')[1].text

        # scrape multiple options designated above
        for i, option in enumerate(options):
            # only select new options item if not first-time loading page
            if i != 0:
                browser.find_element_by_partial_link_text(option).click()
                time.sleep(3)


            # scrape 2 boxscore tables
            table1 = browser.find_element_by_xpath('/html/body/main/div[2]/div/div/div[4]/div/div[2]/div/nba-stat-table[1]')
            table2 = browser.find_element_by_xpath('/html/body/main/div[2]/div/div/div[4]/div/div[2]/div/nba-stat-table[2]')



            # scrape tables for both teams
            for table_idx, table in enumerate([table1, table2]):
                column_names = []
                player_stats = []
                temp_player_stat = []

                # replace all the unexpected spaces and newlines strings by our script
                table_text = table.text
                for orig_str, replace_str in text_replacements.items():
                    table_text = table_text.replace(orig_str, replace_str)

                # read table text into python list of lists
                for line_id, line in enumerate(table_text.split('\n')):
                    if line_id == 0:
                        column_names = line.split(' ')[1:]
                        column_names.insert(0,'PLAYER')
                    else:
                        # stop reading once we see totals or DNP/DND line
                        if ('Totals' in line) or ('DNP' in line) or ('DND' in line):
                            break

                        if line_id % 2 == 1:
                            line_cleaned = line[:-2] + line[-2:].replace(' F', '').replace(' C', '').replace(' G', '')
                            temp_player_stat.append(line_cleaned)
                        if line_id % 2 == 0:
                            temp_player_stat.extend(line.split(' '))
                            # only append if formatting is correct
                            if (len(temp_player_stat) == len(column_names)):
                                player_stats.append(temp_player_stat)
                            temp_player_stat = []

                # convert list of lists into pandas df
                df = pd.DataFrame(player_stats, columns = column_names)
                if table_idx == 0:
                    team1_stats_dfs.append(df)
                else:
                    team2_stats_dfs.append(df)


            # open the options menu
            browser.find_element_by_partial_link_text(option).click()
            time.sleep(2)

        # combine all the stats and write to a pickle file
        team1_df = pd.merge(team1_stats_dfs[0], team1_stats_dfs[1].drop(columns = ['MIN']),
                            how = 'outer', left_on = 'PLAYER', right_on = 'PLAYER')
        team1_df = pd.merge(team1_df, team1_stats_dfs[2].drop(columns = ['MIN', 'USG%']),
                            how = 'outer', left_on = 'PLAYER', right_on = 'PLAYER')
        team1_df = pd.merge(team1_df, team1_stats_dfs[3].drop(columns = ['MIN', 'AST', 'FG%']),
                            how = 'outer', left_on = 'PLAYER', right_on = 'PLAYER')
        team1_df = pd.merge(team1_df, team1_stats_dfs[4].drop(columns = ['MIN']),
                            how = 'outer', left_on = 'PLAYER', right_on = 'PLAYER')
        team1_stats_dfs[5] = team1_stats_dfs[5].rename(columns = {
            'PTS' : 'ALLOWED_PTS',
            'AST' : 'ALLOWED_AST',
            'TOV' : 'FORCED_TOV'
        })
        team1_df = pd.merge(team1_df, team1_stats_dfs[5].drop(columns = ['DREB', 'STL', 'BLK', 'DFGM', 'DFGA', 'DFG%']),
                            how = 'outer', left_on = 'PLAYER', right_on = 'PLAYER')
        # team 2
        team2_df = pd.merge(team2_stats_dfs[0], team2_stats_dfs[1].drop(columns = ['MIN']),
                            how = 'outer', left_on = 'PLAYER', right_on = 'PLAYER')
        team2_df = pd.merge(team2_df, team2_stats_dfs[2].drop(columns = ['MIN', 'USG%']),
                            how = 'outer', left_on = 'PLAYER', right_on = 'PLAYER')
        team2_df = pd.merge(team2_df, team2_stats_dfs[3].drop(columns = ['MIN', 'AST', 'FG%']),
                            how = 'outer', left_on = 'PLAYER', right_on = 'PLAYER')
        team2_df = pd.merge(team2_df, team2_stats_dfs[4].drop(columns = ['MIN']),
                            how = 'outer', left_on = 'PLAYER', right_on = 'PLAYER')
        team2_stats_dfs[5] = team2_stats_dfs[5].rename(columns = {
            'PTS' : 'ALLOWED_PTS',
            'AST' : 'ALLOWED_AST',
            'TOV' : 'FORCED_TOV'
        })
        team2_df = pd.merge(team2_df, team2_stats_dfs[5].drop(columns = ['DREB', 'STL', 'BLK', 'DFGM', 'DFGA', 'DFG%']),
                            how = 'outer', left_on = 'PLAYER', right_on = 'PLAYER')
        team1_df.insert(0, 'TEAM', team1)
        team2_df.insert(0, 'TEAM', team2)

        teams_df = pd.concat([team1_df, team2_df], ignore_index=True)
        teams_df.to_pickle('{}/{}_{}_{}'.format(store_location, date_str_2, team1.replace(' ','-'), team2.replace(' ','-')))

        # finish scraping the stats from all the options, go back to the previous page listing all games in one day
        browser.get(date_url)
        time.sleep(5)
    
    