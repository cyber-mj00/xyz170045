import asyncio
import aiohttp
import json
import re
import os
import dotenv
import pandas as pd
import xlsxwriter
import datetime

from os.path import join, dirname
from getdata import *

from mahjongsoul.helper import *
from mahjongsoul.manager import *
from mahjongsoul.dayaya import *


env_path = join(dirname(__file__), 'config.env')
dotenv.load_dotenv(env_path)
DAYS = ["一","二","三","四","五","六","日"]
CUTOFF = [6,4,1]

MAX_ITER = 100 # Max number of logs Majsoul can GET at one time

def delFile(filename):
    try:
        file_path = join(dirname(__file__), filename)
        if os.path.exists(file_path) and not os.path.isdir(file_path):
            os.remove(file_path)
    except:
        print(f"File {filename} not found!")

def color_strtoint(color_str):
    try:
        assert len(color_str) == 6
    except:
        return -1, -1, -1
    return int(color_str[0:2], 16), int(color_str[2:4], 16), int(color_str[4:6], 16)

def getDf(player_pool: Players,
          team_pool: Teams, 
          game_pool: Games):
    df_players = pd.DataFrame(data=player_pool.exportToDict())
    df_players = df_players.round({'平顺': 2, 'TOP率': 4, '连对率': 4, '避四率': 4})
    df_games = pd.DataFrame(data=game_pool.exportToDict())
    team_data = team_pool.exportToDict()
    for i in range(len(team_data)):
        team_data[i]["df"] = pd.DataFrame(data=team_data[i]["data"]).sort_values(by='总积分', ascending=False).reset_index(drop=True)
        team_data[i]["df"].index.name = '排名'
    
    print("Generating individual stats")
    df_players['队伍'] = pd.Categorical(df_players['队伍'], [team.name for team in team_pool.teams.values()])
    df_players = df_players.sort_values(by='积分', ascending=False).reset_index(drop=True)
    df_players.index = df_players.index + 1
    print("Generating team stats by player")
    df_players_byteam = df_players.sort_values(by=['队伍', '积分'], ascending=[True, False]).reset_index(names='排名')
    df_players.index.name = '排名'
    print("Generating team scores")
    for i in range(len(team_data)):
        df_pointer = team_data[i]["df"]
        df_pointer.insert(2,"差值",-df_pointer['总积分'].diff())

        cutoff = df_pointer['总积分'].copy()
        cutoff.iloc[:CUTOFF[i]] = df_pointer['总积分'].iloc[:CUTOFF[i]] - df_pointer.loc[CUTOFF[i], '总积分']
        cutoff.iloc[CUTOFF[i]:] = df_pointer['总积分'].iloc[CUTOFF[i]:] - df_pointer.loc[CUTOFF[i]-1, '总积分']
        df_pointer.insert(3, "晋级线", cutoff)

        df_pointer.index = df_pointer.index + 1
        df_pointer.index.name = '排名'
    
    print("Generating logs")
    df_games.insert(4,"1位队伍",df_games['1位ID'].apply(lambda x: player_pool.getPlayerTeam(x)))
    df_games.insert(9,"2位队伍",df_games['2位ID'].apply(lambda x: player_pool.getPlayerTeam(x)))
    df_games.insert(14,"3位队伍",df_games['3位ID'].apply(lambda x: player_pool.getPlayerTeam(x)))
    df_games.insert(19,"4位队伍",df_games['4位ID'].apply(lambda x: player_pool.getPlayerTeam(x)))
    df_games = df_games.drop(columns=[f'{w}位ID' for w in range(1,5)])

    return df_players, df_players_byteam, df_games, team_data




def getSheet(player_pool: Players,
             team_pool: Teams,
             game_pool: Games,
             df_players: pd.DataFrame, 
             df_players_byteam: pd.DataFrame, 
             df_games: pd.DataFrame, 
             team_data: Dict[str,int|str|pd.DataFrame|Dict[str,str|int]],
             delete_previous: bool = True):

    print("Writing to spreadsheet...")
    time_now = Dayaya.getCurrentTime()
    ContrastColor = lambda r,g,b: "000000" if (0.299 * r + 0.587 * g + 0.114 * b)/255 > 0.5 else "ffffff"
    teams_list = team_pool.teams.values()

    if delete_previous:
        with open(join(dirname(__file__), "latest_file.txt"), "r") as f:
            delFile(old_filename := f.read())
    
    output_filename = os.environ.get('output_filename')+time_now.strftime("_%Y%m%d_%H%M%S")+".xlsx"
    with pd.ExcelWriter(join(dirname(__file__), output_filename), engine='xlsxwriter', engine_kwargs={"options": {'strings_to_formulas': False}}) as writer:
        df_players_byteam.to_excel(writer, index=False, sheet_name='团体个人表', startrow=1)
        df_players.to_excel(writer, index=True, sheet_name='个人积分表', startrow=1)
        for i in range(len(team_data)):
            team_data[i]["df"].to_excel(writer, index=True, sheet_name=f'队伍积分表-{team_data[i]["name"]}', startrow=1)
        df_games.to_excel(writer, index=False, sheet_name='牌谱数据')

        # Future step forward: automatic formatting
        formats = {}
        workbook = writer.book
        formats["score"] = workbook.add_format({"bg_color": "#FAF0CE", "font_color": "#000000", "align": "center"})
        formats["score_red"] = workbook.add_format({"bg_color": "#FAF0CE", "font_color": "#FF0000", "align": "center"})
        formats["simple_red"] = workbook.add_format({"font_color": "#FF0000", "align": "center"})
        formats["top"] = workbook.add_format({"bg_color": "#FF66CC", "font_color": "#000000", "align": "center"})
        formats["title"] = workbook.add_format({"bold": True, "align": "center"})
        formats["title_red"] = workbook.add_format({"bold": True, "align": "center", "font_color": "#FF0000"})
        formats["noteL"] = workbook.add_format({"bold": True, "align": "left"})
        formats["noteR"] = workbook.add_format({"bold": True, "align": "right"})
        formats["center"] = workbook.add_format({"align": "center", "valign": "vcenter"})
        formats["center_percent"] = workbook.add_format({"align": "center", "valign": "vcenter", 'num_format': '0.00%'})
        for team in teams_list:
            r,g,b = color_strtoint(team_color := team.color)
            formats[team.name] = workbook.add_format({"bg_color": f"#{team_color}", "font_color": f"#{ContrastColor(r,g,b)}", "align": "center"})
        worksheet_activeSession = workbook.add_worksheet("每日试合")

        worksheet_players = writer.sheets['个人积分表']
        worksheet_players.set_column(0, 0, 8, formats["title"])
        worksheet_players.set_column(1, 2, 30, formats["center"])
        worksheet_players.set_column(3, 5, 8, formats["center"])
        worksheet_players.set_column(6, 9, 6, formats["center"])
        worksheet_players.set_column(10, 12, 8, formats["center_percent"])
        worksheet_players.set_column(13, 13, 8, formats["center"])
        worksheet_players.set_row(1, None, formats["title"])

        worksheet_players.merge_range("A1:N1", "炽焰天穹ML S1 2025  个人成绩顺位表", formats["title"])
        row1, _ = df_players.shape
        worksheet_players.merge_range(f"A{row1+3}:F{row1+3}", "★常规赛各选手出场数最少12个半庄、最多60个半庄", formats["noteL"])
        worksheet_players.merge_range(f"A{row1+4}:F{row1+4}", "★半决赛各选手出场数最少2个半庄、最多10个半庄", formats["noteL"])
        worksheet_players.merge_range(f"A{row1+5}:F{row1+5}", "★决赛各选手出场数最少1个半庄、最多8个半庄", formats["noteL"])
        worksheet_players.merge_range(f"G{row1+3}:N{row1+3}", f'{time_now.strftime("%m月%d日")} 终了时点', formats["noteR"])

        for team in teams_list:
            worksheet_players.conditional_format(
                f"B3:C{row1+2}", {"type": "formula", "criteria": f'=$B3="{team.name}"', "format": formats[team.name]}
            )

        worksheet_players.conditional_format(
            f"D3:D{row1+2}", {"type": "cell", "criteria": "<", "value": 0, "format": formats["score_red"]}
        )
        worksheet_players.conditional_format(
            f"D3:D{row1+2}", {"type": "cell", "criteria": ">=", "value": 0, "format": formats["score"]}
        )
        
        for a in ['G', 'K', 'L', 'M', 'N']:
             worksheet_players.conditional_format(
                f"{a}3:{a}{row1+2}", {"type": "top", "value": 1, "format": formats["top"]}
            )

        worksheet_players_byteam = writer.sheets['团体个人表']
        worksheet_players_byteam.set_column(0, 0, 8, formats["title"])
        worksheet_players_byteam.set_column(1, 2, 30, formats["center"])
        worksheet_players_byteam.set_column(3, 5, 8, formats["center"])
        worksheet_players_byteam.set_column(6, 9, 6, formats["center"])
        worksheet_players_byteam.set_column(10, 12, 8, formats["center_percent"])
        worksheet_players_byteam.set_column(13, 13, 8, formats["center"])
        worksheet_players_byteam.set_row(1, None, formats["title"])
        
        worksheet_players_byteam.merge_range("A1:N1", "炽焰天穹ML S1 2025  个人成绩顺位表（按队伍）", formats["title"])
        row2, _ = df_players_byteam.shape
        worksheet_players_byteam.merge_range(f"A{row2+3}:F{row2+3}", "★常规赛各选手出场数最少12个半庄、最多60个半庄", formats["noteL"])
        worksheet_players_byteam.merge_range(f"A{row2+4}:F{row2+4}", "★半决赛各选手出场数最少2个半庄、最多10个半庄", formats["noteL"])
        worksheet_players_byteam.merge_range(f"A{row2+5}:F{row2+5}", "★决赛各选手出场数最少1个半庄、最多8个半庄", formats["noteL"])
        worksheet_players_byteam.merge_range(f"G{row2+3}:N{row2+3}", f'{time_now.strftime("%m月%d日")} 终了时点', formats["noteR"])

        for team in teams_list:
            worksheet_players_byteam.conditional_format(
                f"B3:C{row2+2}", {"type": "formula", "criteria": f'=$B3="{team.name}"', "format": formats[team.name]}
            )

        worksheet_players_byteam.conditional_format(
            f"D3:D{row2+2}", {"type": "cell", "criteria": "<", "value": 0, "format": formats["score_red"]}
        )
        worksheet_players_byteam.conditional_format(
            f"D3:D{row2+2}", {"type": "cell", "criteria": ">=", "value": 0, "format": formats["score"]}
        )

        worksheet_team = {}
        for i in range(len(team_data)):
            phase_name = team_data[i]["name"]
            worksheet_tmp = writer.sheets[f'队伍积分表-{phase_name}']
            worksheet_team[phase_name] = worksheet_tmp
            worksheet_team[phase_name].set_column(0, 0, 8, formats["title"])
            worksheet_team[phase_name].set_column(1, 1, 30, formats["center"])
            worksheet_team[phase_name].set_column(2, 7, 8, formats["center"])
            worksheet_team[phase_name].set_column(8, 11, 6, formats["center"])
            worksheet_team[phase_name].set_row(1, None, formats["title"])
            
            worksheet_team[phase_name].merge_range("A1:J1", f"炽焰天穹ML S1 2025  {phase_name}  队伍积分顺位表", formats["title"])
            row3, _ = team_data[i]["df"].shape
            worksheet_team[phase_name].merge_range(f"D{row3+3}:L{row3+3}", f'{time_now.strftime("%m月%d日")} 终了时点', formats["noteR"])

            for team in teams_list:
                worksheet_team[phase_name].conditional_format(
                    f"B3:B{row3+2}", {"type": "cell", "criteria": "==", "value": f'"{team.name}"', "format": formats[team.name]}
                )

            worksheet_team[phase_name].conditional_format(
                f"C3:C{row3+2}", {"type": "cell", "criteria": "<", "value": 0, "format": formats["score_red"]}
            )
            worksheet_team[phase_name].conditional_format(
                f"C3:C{row3+2}", {"type": "cell", "criteria": ">=", "value": 0, "format": formats["score"]}
            )
            worksheet_team[phase_name].conditional_format(
                f"E3:E{row3+2}", {"type": "cell", "criteria": "<", "value": 0, "format": formats["simple_red"]}
            )

        worksheet_paifu = writer.sheets['牌谱数据']
        worksheet_paifu.set_column(0, 1, 18, formats["center"])
        worksheet_paifu.set_row(0, None, formats["title"])
        for i in range(2,17,4):
            worksheet_paifu.set_column(i, i, 20, formats["center"])
            worksheet_paifu.set_column(i+1, i+1, 30, formats["center"])
            worksheet_paifu.set_column(i+2, i+3, 12, formats["center"])
        worksheet_paifu.set_column(18, 18, 72, formats["center"])
        row4, _ = df_games.shape
        
        for team in teams_list:
            worksheet_paifu.conditional_format(
                f"C2:F{row4+1}", {"type": "formula", "criteria": f'=$D2="{team.name}"', "format": formats[team.name]}
            )
            worksheet_paifu.conditional_format(
                f"G2:J{row4+1}", {"type": "formula", "criteria": f'=$H2="{team.name}"', "format": formats[team.name]}
            )
            worksheet_paifu.conditional_format(
                f"K2:N{row4+1}", {"type": "formula", "criteria": f'=$L2="{team.name}"', "format": formats[team.name]}
            )
            worksheet_paifu.conditional_format(
                f"O2:R{row4+1}", {"type": "formula", "criteria": f'=$P2="{team.name}"', "format": formats[team.name]}
            )
        
        
        last_games = game_pool.getGameFromTime(last_gametime := game_pool.getGameTime())[::-1]
        worksheet_activeSession.set_column(0, 4, 30)
        worksheet_activeSession.write('A1', f'{last_gametime.strftime("%m/%d")} (周{Dayaya.getDays(last_gametime.weekday())})', formats["title_red"])
        teams = set([player_pool.getPlayerTeam(p["_id"]) for x in last_games for p in x.players])
        teams_game = [set([player_pool.getPlayerTeam(p["_id"]) for p in last_games[0].players])]
        if (len(teams) > 4):
            teams_game.append(teams - teams_game[0])
        
        for i in range(len(teams_game)):
            i_0 = 10*i+2
            x = 0
            teams_game_tmp = list(teams_game[i])
            for k in range(4):
                teamname_tmp = teams_game_tmp[k]
                worksheet_activeSession.write(i_0-2, k+1, teamname_tmp, formats[teamname_tmp])
            worksheet_activeSession.write(f'A{i_0}', "第1半庄", formats["title"])
            worksheet_activeSession.write(f'A{i_0+4}', "第2半庄", formats["title"])
            for j in range(2):
                worksheet_activeSession.write(f'A{i_0+4*j+1}', "马点", formats["title"])
                worksheet_activeSession.write(f'A{i_0+4*j+2}', "分数", formats["title"])
                worksheet_activeSession.write(f'A{i_0+4*j+3}', "赛事牌谱", formats["title"])
            
            for u in range(n_last_games := len(last_games)):
                if player_pool.getPlayerTeam(last_games[u].players[0]["_id"]) in teams_game_tmp:
                    players_team = [player_pool.getPlayerTeam(p["_id"]) for p in last_games[u].players]
                    players_idx = [teams_game_tmp.index(p) for p in players_team]
                    for y in range(len(players_idx)):
                        worksheet_activeSession.write(i_0-1+4*x, players_idx[y]+1, last_games[u].players[y]["nickname"], formats[players_team[y]])
                        worksheet_activeSession.write(i_0+4*x, players_idx[y]+1, last_games[u].players[y]["score"], formats[players_team[y]])
                        worksheet_activeSession.write(i_0+1+4*x, players_idx[y]+1, last_games[u].players[y]["uma"] / 1000, formats[players_team[y]])
                    worksheet_activeSession.merge_range(f"B{i_0+3+4*x}:E{i_0+3+4*x}", "https://game.maj-soul.com/1/?paipu="+last_games[u].uuid, formats["score"])
                    x += 1
                    
    
    with open(join(dirname(__file__), "latest_file.txt"), "w") as f:
        f.write(output_filename)

def main():
    pass

if __name__ == "__main__":
    main()
