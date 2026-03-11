import asyncio
import aiohttp
import json
import re
import os
import dotenv
import pandas as pd
import xlsxwriter
import datetime
import pickle

from os.path import join, dirname

from mahjongsoul.helper import *
from mahjongsoul.manager import *
from mahjongsoul.dayaya import *

MAX_ITER = 100 # Max number of logs Majsoul can GET at one time
MAX_MATCHES = [120, 20, 16]

def fetchContestData(filename: str="dayaya.pkl"):
    file_path = join(dirname(__file__), filename)
    if not os.path.exists(file_path):
        dyy_api = DayayaAPI()
        dayaya = DyyContestManager(os.environ.get('dyy_contest_id'), dyy_api)
        with open(file_path, "wb") as f:
            pickle.dump(dayaya, f)
    else:
        with open(file_path, "rb") as f:
            dayaya = pickle.load(f)
    return dayaya

def fetchMajsoulConnector(filename: str="majsoul.pkl"):
    file_path = join(dirname(__file__), filename)
    if not os.path.exists(file_path):
        mjs_login = TournamentLogin(mjs_email=os.environ.get('mjs_email'), mjs_pw=os.environ.get('mjs_passwd'))
        majsoul = ContestManager(os.environ.get('contest_unique_id'), mjs_login, "Heaven Burns Red")
        with open(file_path, "wb") as f:
            pickle.dump(majsoul, f)
    else:
        with open(file_path, "rb") as f:
            majsoul = pickle.load(f)
    return majsoul

def getPlayerData(dayaya: DyyContestManager, majsoul: ContestManager):
    players = dayaya.players
    player_pool = Players(dayaya.contest_id)
    rank_stats = majsoul.get_player_rank_stats(limit=MAX_ITER)
    ranking = rank_stats["rank"]
    if (player_total := rank_stats["total"]) > MAX_ITER:
        for i in range(1, player_total//MAX_ITER+1):
            ranking.append(rank_stats = majsoul.get_player_rank_stats(offset=i*MAX_ITER,limit=MAX_ITER))
    
    for player in players:
        dyyId = player["_id"]
        p_data = [r for r in ranking if r["nickname"] == player["nickname"]]
        if len(p_data) > 0:
            player_data = {
                'account_id': p_data["account_id"],
                'nickname': player["nickname"],
                'account_data': {
                    'total_game_count': player["gamesPlayed"],
                    'accumulate_point': player["tourneyScore"],
                    'recent_games': dayaya.getPlayerGames()
                },
                "rank_count": [p_data["rank_1_count"], p_data["rank_2_count"], p_data["rank_3_count"], p_data["rank_4_count"]]
                }
            player_pool.addPlayerFromDict(dyyId, player_data)
    return player_pool

def saveData(pool, filename: str):
    file_path = join(dirname(__file__), filename)
    with open(file_path, "wb") as f:
            pickle.dump(pool, f)

def loadData(filename: str):
    file_path = join(dirname(__file__), filename)
    with open(file_path, "wb") as f:
        pool = pickle.load(f)
    return pool

def getTeamData(dayaya: DyyContestManager):
    teams = dayaya.teams
    team_pool = Teams(dayaya.contest_id)
    for team in teams:
        team_pool.addTeamFromDayaya(team)
    return team_pool

def updateTeamScores(dayaya: DyyContestManager, team_pool: Teams):
    phases = dayaya.phases
    for phase in phases:
        phase_index = phase["index"]
        foo = phase_index - dayaya.current_phase
        for team_id, total in phase["aggregateTotals"].items():
            team_pool.teams[team_id].setAggregate(phase_index, total)
        if foo < 0:
            last_session = sorted(phase["sessions"], key=lambda x:x["scheduledTime"])[-1]
            for team_id, total in last_session["aggregateTotals"].items():
                team_pool.teams[team_id].setScore(phase_index, total)
        elif foo == 0:
            this_session = dayaya.current_session
            for team_id, total in this_session["aggregateTotals"].items():
                team_pool.teams[team_id].setScore(phase_index, total)
    for team_id in team_pool.teams.keys():
        team_stats = dayaya.getTeamStats(team_id)["team_id"]
        getGamesPlayed = lambda x: [min(x,MAX_MATCHES[0]), 
                                    max(min(x-MAX_MATCHES[0],MAX_MATCHES[1]), 0), 
                                    max(min(x-MAX_MATCHES[0]-MAX_MATCHES[1],MAX_MATCHES[2]), 0)]
        team_gamesPlayed = getGamesPlayed(team_stats["stats"]["gamesPlayed"])
        for i, gp in enumerate(team_gamesPlayed):
            if gp > 0:
                team_pool.teams[team_id].games_played[i] = gp
        

        


        

def updateContestData():
    pass



def main():
    pass

if __name__ == "__main__":
    main()