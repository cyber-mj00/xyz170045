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

env_path = join(dirname(__file__), 'config.env')
dotenv.load_dotenv(env_path)

def fetchContestData(filename: str="dayaya.pkl"):
    file_path = join(dirname(__file__), filename)
    if not os.path.exists(file_path):
        dayaya = generateContestData()
        with open(file_path, "wb") as f:
            pickle.dump(dayaya, f)
    else:
        with open(file_path, "rb") as f:
            dayaya = pickle.load(f)
    return dayaya

def generateContestData():
    print("Logging in to Dayaya Contest Dashboard...")
    dyy_api = DayayaAPI()
    print(f"Locating Dayaya Contest {os.environ.get('dyy_contest_id')}...")
    dayaya = DyyContestManager(os.environ.get('dyy_contest_id'), dyy_api)
    return dayaya

def reloadContestData(filename: str="dayaya.pkl"):
    file_path = join(dirname(__file__), filename)
    if os.path.exists(file_path) and not os.path.isdir(file_path):
        os.remove(file_path)
    fetchContestData(filename)

def fetchMajsoulConnector(filename: str="majsoul.pkl"):
    file_path = join(dirname(__file__), filename)
    if not os.path.exists(file_path):
        majsoul = generateMajsoulConnector()
        with open(file_path, "wb") as f:
            pickle.dump(majsoul, f)
    else:
        with open(file_path, "rb") as f:
            majsoul = pickle.load(f)
    return majsoul

def generateMajsoulConnector():
    print("Logging in to Majsoul Contest Dashboard...")
    mjs_login = TournamentLogin(mjs_email=os.environ.get('mjs_email'), mjs_pw=os.environ.get('mjs_passwd'))
    print(f"Locating Majsoul Contest {os.environ.get('contest_unique_id')}...")
    majsoul = ContestManager(os.environ.get('contest_unique_id'), mjs_login, "Heaven Burns Red")
    return majsoul

def reloadMajsoulConnector(filename: str="dayaya.pkl"):
    file_path = join(dirname(__file__), filename)
    if os.path.exists(file_path) and not os.path.isdir(file_path):
        os.remove(file_path)
    fetchMajsoulConnector(filename)

def getPlayerData(dayaya: DyyContestManager, majsoul: ContestManager):
    players = dayaya.players
    player_pool = Players(dayaya.contest_id)
    player_list = majsoul.get_players(limit=Dayaya.maxIter())
    ranking = {p_data["nickname"]: p_data for p_data in player_list["list"]}
    player_total = player_list["total"]
    print(f"Total number of players: {player_total}")
    if (player_total) > Dayaya.maxIter():
        for i in range(1, Dayaya.ceil(player_total/Dayaya.maxIter())):
            ranking |= {p_data["nickname"]: p_data
                for p_data in majsoul.get_players(offset=i*Dayaya.maxIter(),limit=Dayaya.maxIter())['list']
            }
    
    for j, player in enumerate(players):
        dyyId = player["_id"]
        if (p_nick := player["nickname"]) in ranking:
            mjsId = ranking[p_nick]["account_id"]
            print(f"Adding player {player["nickname"]}[{mjsId}] ({j+1}/{player_total})")
            recent_games, game_stats = dayaya.getPlayerGamesData(dyyId, stats=False)
            player_data = {
                'account_id': mjsId,
                'nickname': player["nickname"],
                'account_data': {
                    'total_game_count': player["gamesPlayed"],
                    'accumulate_point': player["tourneyScore"],
                    'recent_games': recent_games
                },
                'stats': game_stats
                }
            player_pool.addPlayerFromDict(dyyId, player_data)
    return player_pool

def getRankCount(recent_games):
    rank_freq = [int(t['rank']) for t in recent_games]
    rank = {x: rank_freq.count(x) for x in range(1,5)}
    return rank, list(rank.values())

def saveData(pool, filename: str):
    file_path = join(dirname(__file__), filename)
    with open(file_path, "wb") as f:
            pickle.dump(pool, f)

def loadData(filename: str):
    file_path = join(dirname(__file__), filename)
    with open(file_path, "rb") as f:
        pool = pickle.load(f)
    return pool

def deleteData(filename: str):
    file_path = join(dirname(__file__), filename)
    if os.path.exists(file_path) and not os.path.isdir(file_path):
        os.remove(file_path)

def getTeamData(dayaya: DyyContestManager, player_pool: Players):
    teams = dayaya.teams
    print(f"Total number of teams: {len(teams)}")
    team_pool = Teams(dayaya.contest_id)
    for j, team in enumerate(teams):
        print(f"Adding team {team["name"]} ({j+1}/{len(teams)})")
        team_pool.addTeamFromDayaya(team)
    updateTeamScores(dayaya, team_pool)
    updateTeamMatches(dayaya, player_pool, team_pool)
    return team_pool

def updateTeamScores(dayaya: DyyContestManager, team_pool: Teams):
    phases = dayaya.phases
    for phase in phases:
        phase_index = phase["index"]
        # Record phase in Teams
        team_pool.addPhase(phase_index, phase["name"])
        # Update aggregate
        foo = phase_index - dayaya.current_phase
        print(f"Setting teams' aggregate score from previous phase.")
        for team_id, total in dayaya.start_points[phase_index].items():
            team_pool.teams[team_id].setAggregate(phase_index, total)
        # Update latest score
        print(f"Updating teams' current score.")
        if foo < 0:
            last_session = sorted(dayaya.sessions[phase_index], key=lambda x:x["scheduledTime"])[-1]
            for team_id, total in last_session["aggregateTotals"].items():
                team_pool.teams[team_id].setScore(phase_index, total)
        elif foo == 0:
            this_session = dayaya.current_session
            for team_id, total in this_session["aggregateTotals"].items():
                team_pool.teams[team_id].setScore(phase_index, total)

def updateTeamMatches(dayaya: DyyContestManager, player_pool: Players, team_pool: Teams):
    phases = dayaya.phases
    for team_id, team in team_pool.teams.items():
        # Update number of matches played
        print(f"Updating number of matches played for team {team.name}.")
        team_stats = dayaya.getTeamStats(team_id)[team_id]
        getGamesPlayed = lambda x: [min(x,Dayaya.maxMatches(0)), 
                                    max(min(x-Dayaya.maxMatches(0),Dayaya.maxMatches(1)), 0), 
                                    max(min(x-Dayaya.maxMatches(0)-Dayaya.maxMatches(1),Dayaya.maxMatches(2)), 0)]
        team_gamesPlayed = getGamesPlayed(team_stats["stats"]["gamesPlayed"])
        team_phasesPlayed = sum([gp > 0 for gp in team_gamesPlayed])
        for i, gp in enumerate(team_gamesPlayed):
            if gp > 0:
                team_pool.teams[team_id].setGamesPlayed(i, gp)
        # Update team rank count by phase
        rank_count = {a: [0,0,0,0] for a in range(team_phasesPlayed)}
        print("Updating team rank count by phase and allocating players to teams...")
        for player in team.players:
            player_pointer = player_pool.players[player["_id"]]
            player_pointer.setTeam(team.name)
            for i in range(team_phasesPlayed):
                player_games = [g for g in player_pointer.games if g["phase_index"] == i]
                _, player_rank = getRankCount(player_games)
                rank_count[i] = [a+b for a,b in zip(rank_count[i], player_rank)]
        team_pool.teams[team_id].ranks = rank_count

def loadContestData(
        players_filename: str = "players.pkl",
        teams_filename: str = "teams.pkl",
        games_filename: str = "games.pkl"):
    dayaya = fetchContestData()
    majsoul = fetchMajsoulConnector()

    player_pool, team_pool, game_pool = refreshContestData(dayaya, majsoul, players_filename, teams_filename, games_filename)
    return dayaya, majsoul, player_pool, team_pool, game_pool

def resetContestData(
        players_filename: str = "players.pkl",
        teams_filename: str = "teams.pkl",
        games_filename: str = "games.pkl"):
    dayaya = reloadContestData()
    majsoul = reloadMajsoulConnector()

    player_pool, team_pool, game_pool = refreshContestData(dayaya, majsoul, players_filename, teams_filename, games_filename)
    return dayaya, majsoul, player_pool, team_pool, game_pool

def refreshContestData(dayaya: DyyContestManager, 
                       majsoul: ContestManager,
                       players_filename: str = "players.pkl",
                       teams_filename: str = "teams.pkl",
                       games_filename: str = "games.pkl"):
    
    print("Refreshing Dayaya Contest Data...")
    dayaya.update()
    
    print("Fetching players list...")
    player_pool = getPlayerData(dayaya, majsoul)

    print("Fetching teams list...")
    team_pool = getTeamData(dayaya, player_pool)
    saveData(team_pool, teams_filename)
    
    saveData(player_pool, players_filename)
    game_pool = getGameLogs(dayaya)

    saveData(game_pool, games_filename)
    print("Setup completed.")

    return player_pool, team_pool, game_pool

def getGameLogs(dayaya: DyyContestManager):
    print("Fetching game logs...")
    games = dayaya.getContestGames()
    game_pool = Games(dayaya.contest_id)
    for game_data in games:
        game_pool.addGameFromDict(game_data)
    return game_pool



def main():
    pass

if __name__ == "__main__":
    main()