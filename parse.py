#!/usr/bin/env python
# -*- coding:utf-8 -*-
import argparse
import configparser
import json
import logging
import os
import pandas as pd
import sys

args = []

def main():
    global args
    args = parse_args()

    # logging
    if args.Debug:
        logging.basicConfig(level=logging.DEBUG)
    
    # read config
    config = read_config()

    df = pd.read_csv(filepath_or_buffer=args.csv, encoding="utf-8", sep=",")
    logging.debug(df)
    
    # columns
    config['defaults']['columns'] = '\n'.join(df.columns.tolist())

    # Matches
    config['defaults']['num_matches'] = str(df.shape[0])

    # Num matches per team
    get_num_match_per_team(config, df)

    # VS per team
    parse_vs_per_team(config, df)

    # export markdown per team
    export_md_per_team(config)

    # export all results as markdown
    export_md_results(config, df)

    # export to parsed.ini
    export_config(config)

    #######
    # df2 = df.sort_values('対戦日は？(省略すると本日)', ascending=False) # sort by date
    # df3 = df2.fillna(' ') # fill NaN

    # # dump team results
    # if args.team:
    #     get_team_results(df3)

    # # dump results
    # get_results(df3)


def get_col(config, idx):
    return config['defaults']['columns'].splitlines()[idx]


def get_date(config):
    return get_col(config, 0)


def get_team1(config):
    return get_col(config, 1)


def get_doubles1(config):
    return get_col(config, 2)


def get_game1(config):
    return get_col(config, 3)


def get_tb1(config):
    return get_col(config, 4)


def get_tb2(config):
    return get_col(config, 5)


def get_game2(config):
    return get_col(config, 6)


def get_doubles2(config):
    return get_col(config, 7)


def get_team2(config):
    return get_col(config, 8)


def get_order(config):
    return get_col(config, 9)


def get_num_match_per_team(config, df):
    # Loop over teams
    teams = config.get('defaults','Teams').splitlines()
    logging.debug(teams)
    team1 = get_team1(config)
    team2 = get_team2(config)
    logging.debug('team1: {}'.format(team1))

    for team in teams:
        name = config[team]['Name']
        logging.debug('Name: {}'.format(name))
        #print(df[team1].str.contains(name))
        num_matches = len(df[df[team1].str.contains(name)])
        num_matches += len(df[df[team2].str.contains(name)])
        config[team]['num_matches'] = str(num_matches)


def parse_vs_per_team(config, df):
    teams = config.get('defaults','Teams').splitlines()
    team1 = get_team1(config)
    team2 = get_team2(config)
    doubles1 = get_doubles1(config)
    doubles2 = get_doubles2(config)
    game1 = get_game1(config)
    game2 = get_game2(config)
    tb1 = get_tb1(config)
    tb2 = get_tb2(config)
    order = get_order(config)

    # Loop over teams
    for team in teams:
        name = config[team]['Name']
        logging.debug('{}: {}'.format(team, name))

        others = get_others(team, teams)
        logging.debug('Others: {}'.format(others))

        df_team1 = df[df[team1].str.contains(name)]
        df_team2 = df[df[team2].str.contains(name)]
        logging.debug('df_team1:')
        logging.debug(df_team1)

        # search others in opposite
        for other in others:
            name = config[other]['Name']
            df_team1_others = df_team1[df_team1[team2].str.contains(name)]
            df_team2_others = df_team2[df_team2[team1].str.contains(name)]
            logging.debug('df_team1_others:')
            logging.debug(df_team1_others)

            num_win = 0
            num_lose = 0
            for index, row in df_team1_others.iterrows():
                logging.debug('row{}: {}'.format(index, row))
                logging.debug('row_game1: {}'.format(row[game1]))
                logging.debug('row_game2: {}'.format(row[game2]))

                nox = row[order]
                key_nox_self = '_'.join(['vs', other, nox, 'self'])
                config[team][key_nox_self] = row[doubles1]
                key_nox_opponent = '_'.join(['vs', other, nox, 'opponent'])
                config[team][key_nox_opponent] = row[doubles2]
                key_nox_score = '_'.join(['vs', other, nox, 'score'])
                score = '-'.join([str(row[game1]), str(row[game2])])
                if not pd.isna(row[tb1]):
                    tb_score = '-'.join([str(int(row[tb1])), str(int(row[tb2]))])
                    tb_score = '(' + tb_score + ')'
                    score = score + tb_score
                config[team][key_nox_score] = score

                if is_win1(config, row):
                    num_win += 1
                else:
                    num_lose += 1

            for index, row in df_team2_others.iterrows():
                nox = row[order]
                key_nox_self = '_'.join(['vs', other, nox, 'self'])
                config[team][key_nox_self] = row[doubles2]
                key_nox_opponent = '_'.join(['vs', other, nox, 'opponent'])
                config[team][key_nox_opponent] = row[doubles1]
                key_nox_score = '_'.join(['vs', other, nox, 'score'])
                score = '-'.join([str(row[game2]), str(row[game1])])
                if not pd.isna(row[tb1]):
                    tb_score = '-'.join([str(int(row[tb2])), str(int(row[tb1]))])
                    tb_score = '(' + tb_score + ')'
                    score = score + tb_score
                config[team][key_nox_score] = score

                if is_win1(config, row):
                    num_lose += 1
                else:
                    num_win += 1
                
            key_num_win = '_'.join(['vs', other, 'num_win'])
            key_num_lose = '_'.join(['vs', other, 'num_lose'])

            config[team][key_num_win] = str(num_win)
            config[team][key_num_lose] = str(num_lose)


def get_score(config, row):
    game1 = get_game1(config)
    game2 = get_game2(config)
    tb1 = get_tb1(config)
    tb2 = get_tb2(config)

    score = '-'.join([str(row[game1]), str(row[game2])])
    if not pd.isna(row[tb1]):
        tb_score = '-'.join([str(int(row[tb1])), str(int(row[tb2]))])
        tb_score = '(' + tb_score + ')'
        score = score + tb_score
    
    return score

def is_win1(config, row):
    ''' True if doubles1 win, False if lose
    '''
    game1 = get_game1(config)
    game2 = get_game2(config)
    tb1 = get_tb1(config)
    tb2 = get_tb2(config)

    if int(row[game1]) == 6 and int(row[game2]) == 6:   # Tiebreak
        if row[tb1] > row[tb2]:
            return True
        else:
            return False
    elif int(row[game1]) > 5:
        return True
    else:
        return False



def get_others(self, teams):
    others = []
    for team in teams:
        if team == self:
            continue
        else:
            others.append(team)
    
    return others


def export_md_per_team(config):
    teams = config.get('defaults','Teams').splitlines()
    orders = config.get('defaults','Orders').splitlines()

    # Loop over teams
    for team in teams:
        lines = []
        name = config[team]['Name']
        line = '# {}\n\n'.format(name)
        lines.append(line)

        others = get_others(team, teams)
        for other in others:
            other_name = config[other]['Name']
            logging.debug('vs {}'.format(other_name))

            key_num_win = '_'.join(['vs', other, 'num_win'])
            if key_num_win in config[team]:
                num_win = config[team][key_num_win]
                logging.debug('num_win: {}'.format(num_win)) 
            key_num_lose = '_'.join(['vs', other, 'num_lose'])
            if key_num_lose in config[team]:
                num_lose = config[team][key_num_lose]
                logging.debug('num_lose: {}'.format(num_lose)) 

            line = '## vs {} {}勝{}敗\n\n'.format(other_name, num_win, num_lose)
            lines.append(line)

            # table header is mandatory
            lines.append('|   |   |   |   |\n')
            lines.append('|---|---|---|---|\n')

            for order in orders:
                key_self = '_'.join(['vs', other, order, 'self'])
                if key_self in config[team]:
                    self = config[team][key_self]

                    key_score = '_'.join(['vs', other, order, 'score'])
                    score = config[team][key_score]

                    key_opponent = '_'.join(['vs', other, order, 'opponent'])
                    opponent = config[team][key_opponent]
                
                    logging.debug('| {} | {} | {} |'.format(self, score, opponent))
                    line = '| {} | {} | {} | {} |\n'.format(order, self, score, opponent)
                    lines.append(line)
            
            lines.append('\n')

        fname = team + '.md'
        with open(fname, mode='w') as f:
            f.writelines(lines)


def export_md_results(config, df):
    date = get_date(config)
    team1 = get_team1(config)
    team2 = get_team2(config)
    doubles1 = get_doubles1(config)
    doubles2 = get_doubles2(config)
    game1 = get_game1(config)
    game2 = get_game2(config)
    tb1 = get_tb1(config)
    tb2 = get_tb2(config)
    order = get_order(config)

    # Loop over df
    lines = []
    lines.append('# 試合結果\n')
    lines.append('\n')
    lines.append('| 対戦日 | チーム | ペア   | スコア | 相手ペア | 相手チーム | オーダー |\n')
    lines.append('| :---- | ----: | ----: | :---: | :------ | :------- | :------ |\n')

    for index, row in df.iterrows():
        score = get_score(config, row)

        line = '| {} | {} | {} | {} | {} | {} | {} |\n'.format(
            row[date],
            row[team1],
            row[doubles1],
            score,
            row[doubles2],
            row[team2],
            row[order]
        )
        lines.append(line)

        fname = 'results.md'
        with open(fname, mode='w') as f:
            f.writelines(lines)


def export_config(config):
    dst = 'parsed.ini'
    with open(dst, mode='w') as f:
        config.write(f)


def read_config():
    """Read config (INI)
    """

    basename = os.path.basename(__file__)
    basename_wo_ext = os.path.splitext(basename)[0]
    ini = basename_wo_ext + '.ini'

    if not os.path.isfile(ini):
        raise Exception(ini + ' does not exist.')
    
    config = configparser.ConfigParser()
    config.read(ini, encoding='utf-8')

    show_config(config)
    return config

def show_config(config):
    sections = config.sections()

    if sections :
        logging.debug('config.sections:')
        for key in config.sections():
            logging.debug('  {}'.format(key))
            for key2 in config[key]:
                logging.debug('    {} = {}'.format(key2, config[key][key2]))


#####
def get_teams():

    teams = []
    teams.append('チーム徳川家康')
    teams.append('東京シティBoys')
    teams.append('TUBE')
    teams.append('お上品関西軍団')
    teams.append('チーム桃太郎')
    teams.append('チームNAHANAHA')
    logging.debug(teams)

    return teams

def get_team_results(df):

    teams = get_teams()

    # page header
    print('# チーム勝敗')
    print('')

    # Header
    win_loss_str = "| {} | {} | {} | {} | {} | {} | {} | {} | {}|".format(
        '---',
        teams[0],
        teams[1],
        teams[2],
        teams[3],
        teams[4],
        teams[5],
        'チーム勝敗(得失ゲーム)',
        'チーム順位'
    )
    print(win_loss_str)
    win_loss_str = "| {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
        '----:',
        ':---:',
        ':---:',
        ':---:',
        ':---:',
        ':---:',
        ':---:',
        ':---:',
        ':---:',
    )
    print(win_loss_str)

    for team in teams:
        logging.debug(team)

        win_loss = []
        team_win = 0
        team_loss = 0
        team_win_games = 0
        team_loss_games = 0
        for oteam in teams:
            if team == oteam:
                win_loss.append('---')
                continue

            # Extract wins and losses
            # df_win = df[(df['あなたのチームは？'] == team) & (df['対戦相手は？'] == oteam)]
            # df_win = df_win[df_win['ダブルスの結果 [あなた]'] == 6]
            df_win = df[(df['あなたのチームは？'] == team) & (df['対戦相手は？'] == oteam) & (df['ダブルスの結果 [あなた]'] == 6)]
            logging.debug(df_win)
            num_win = len(df_win)
            logging.debug("num_win: {}".format(num_win))
            num_loss = len(df[(df['あなたのチームは？'] == team) & (df['対戦相手は？'] == oteam) & (df['ダブルスの結果 [対戦相手]'] == 6)])
            num_win_alt = len(df[(df['あなたのチームは？'] == oteam) & (df['対戦相手は？'] == team) & (df['ダブルスの結果 [対戦相手]'] == 6)])
            num_loss_alt = len(df[(df['あなたのチームは？'] == oteam) & (df['対戦相手は？'] == team) & (df['ダブルスの結果 [あなた]'] == 6)])
            num_win = num_win + num_win_alt
            num_loss = num_loss + num_loss_alt

            win_loss_str = "{}-{}".format(num_win, num_loss)

            df_games = df[(df['あなたのチームは？'] == team) & (df['対戦相手は？'] == oteam)].sum()
            num_games = df_games['ダブルスの結果 [あなた]']
            num_ogames = df_games['ダブルスの結果 [対戦相手]']
            logging.debug('num_games: {}'.format(num_games))

            df_games_alt = df[(df['あなたのチームは？'] == oteam) & (df['対戦相手は？'] == team)].sum()
            num_games_alt = df_games_alt['ダブルスの結果 [対戦相手]']
            num_ogames_alt = df_games_alt['ダブルスの結果 [あなた]']
            logging.debug('num_games_alt: {}'.format(num_games_alt))

            num_games = num_games + num_games_alt
            num_ogames = num_ogames + num_ogames_alt

            team_win_games += num_games
            team_loss_games += num_ogames

            # count games if even
            if num_win == num_loss:
                win_loss_str = "{} ({}-{})".format(win_loss_str, int(num_games), int(num_ogames))
                
            win_loss.append(win_loss_str)

            # calc team win loss
            if (num_win + num_loss) > 2:
                if num_win > num_loss:
                    team_win += 1
                if num_win < num_loss:
                    team_loss += 1
            
            # case: 2-2
            if (num_win == 2) and (num_loss == 2):
                if num_games > num_ogames:
                    team_win +=1
                if num_games < num_ogames:
                    team_loss += 1

        #team_win_loss = "{}-{}".format(team_win, team_loss)
        team_win_loss = "{}-{} ({}-{})".format(team_win, team_loss, int(team_win_games), int(team_loss_games))
        if team == 'チーム桃太郎':
            team_rank = '1'
        elif team == '東京シティBoys':
            team_rank = '2'
        elif team == 'お上品関西軍団':
            team_rank = '3'
        elif team == 'TUBE':
            team_rank = '4'
        elif team == 'チームNAHANAHA':
            team_rank = '5'
        elif team == 'チーム徳川家康':
            team_rank = '6'
        else:
            team_rank = '--'

        #logging.debug(df[df['あなたのチームは？'] == team])
        win_loss_str = "| {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            team,
            win_loss[0],
            win_loss[1],
            win_loss[2],
            win_loss[3],
            win_loss[4],
            win_loss[5],
            team_win_loss,
            team_rank
        )
        print(win_loss_str)

    print('')
    print('* 勝敗が同数の場合: 勝利数-敗北数 (得ゲーム数-失ゲーム数)')
    print('')

    sys.exit()

def get_results(df):
    # table header
    title_str = "| {} | {} ({}) | {} | {} ({}) | {} |".format(
        '対戦日',
        'チーム',
        'ペア',
        'スコア',
        'チーム',
        'ペア',
        'コメント'
    )
    print(title_str)
    
    title_str = "| {} | {} | {} | {} | {} |".format(
        ':---:',
        '----:',
        ':---:',
        ':----',
        ':----'
    )
    print(title_str)
    
    # format results
    md_rows = []
    for index, row in df.iterrows():
        # print("index: {}".format(index))
        # print("row: {}".format(row))
        mteam = row[1]
        oteam = row[2]
        mgames = row[3]
        ogames = row[4]
        mpair = row[5]
        opair = row[6]
        comment = row[7]
        gday = row[8]
    
        row_str = "| {} | {} ({}) | {}-{} | {} ({}) | {} |".format(
            gday,
            mteam,
            mpair,
            mgames,
            ogames,
            oteam,
            opair,
            comment 
        )
        md_rows.append(row_str)
        print(row_str)

def parse_args():
    parser = argparse.ArgumentParser(
        description = '''
        Parse raw csv for SDC 5th and output results
        '''
    )
    parser.add_argument(
        'csv',
        help='CSV input'
    )
    parser.add_argument(
        '-i', '--ini',
        help='Use optional config (INI) file'
    )
    parser.add_argument(
        '-t', '--team',
        action='store_true',
        help='Output team results'
    )
    parser.add_argument(
        '-D', '--Debug',
        action='store_true',
        help='Debug mode'
    )

    args = parser.parse_args()

    if not os.path.isfile(args.csv):
        raise Exception('{} does not exist.'.format(args.csv))
    
    return args

if __name__ == '__main__':
    main()
