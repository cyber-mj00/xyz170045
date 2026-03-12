import asyncio
import json
import typing
import pandas as pd

from datetime import datetime, tzinfo, timedelta
from os.path import join, dirname

class CNTZ(tzinfo):
    def utcoffset(self, dt):
        return timedelta(hours=8)
    def dst(self, dt):
        return timedelta(0)
    def tzname(self,dt):
        return "+08:00"
    def  __repr__(self):
        return f"{self.__class__.__name__}()"

class Dayaya:
    @staticmethod
    def ceil(n):
        return int(-1 * n // 1 * -1)
    
    @staticmethod
    def maxIter():
        return 100
    
    @staticmethod
    def maxTimestamp(ms = True):
        return 2147483647000 if ms else 2147483647
    
    @staticmethod
    def getDays(n):
        days = ["一","二","三","四","五","六","日"]
        return days[n]
    
    @staticmethod
    def maxMatches(phase_index):
        limit = [120, 20, 16]
        return limit[phase_index]
    
    @staticmethod
    def getCurrentTime(timezone :tzinfo =CNTZ()):
        return datetime.now(tz=timezone)

class Player:
    def __init__(self, dyyId, player_data, team = None):
        self.dyyId = dyyId
        self.mjsId = player_data['account_id']
        self.nickname = player_data['nickname']
        self.team = team or ""
        self.total_game_count = player_data['account_data']['total_game_count']
        self.games = player_data['account_data']['recent_games']
        self.rank_pt = player_data["account_data"]['accumulate_point']
        self.rank_count = player_data["rank_count"]
        self.rank = {}
        for i, r in enumerate(self.rank_count):
            self.rank[i+1] = r
    
    def setDyyId(self, dyyId):
        self.dyyId = dyyId
    
    def setTeam(self, team_name):
        self.team = team_name
    
    def getHighestGamePoints(self):
        return max([game["raw_score"] for game in self.games]) if len(self.games) != 0 else 0
    
    def getTop(self):
        return (self.rank_count[0]) / self.total_game_count if self.total_game_count != 0 else 0
    
    def getRentai(self):
        return (self.rank_count[0]+self.rank_count[1]) / self.total_game_count if self.total_game_count != 0 else 0
    
    def get4thAvoidance(self):
        return (self.rank_count[0]+self.rank_count[1]+self.rank_count[2]) / self.total_game_count if self.total_game_count != 0 else 0
    
    def getAvgPlacement(self):
        return sum([a*b for a,b in zip([1,2,3,4], self.rank_count)]) / self.total_game_count if self.total_game_count != 0 else 0
    
    def __str__(self):
        return str({'nickname': self.nickname})
    
    def __repr__(self):
        return str({'_id': self.dyyId, 'mahjongSoulId': self.mjsId, 'nickname': self.nickname})

class Players:
    def __init__(self, contestId):
        self.contestId = contestId
        self.players: dict[str, Player] = {}
    
    def addPlayer(self, player: Player):
        self.players[player.dyyId] = player
    
    def addPlayerFromDict(self, dyyId, player_data):
        self.players[dyyId] = Player(dyyId, player_data)
    
    def getPlayerTeam(self, dyyId):
        return self.players[dyyId].team
    
    def exportToDict(self):
        data_cols = ["队伍","选手","积分","试合数","平顺","1着","2着","3着","4着","TOP率","连对率","避四率","最高分"]
        data = {a: [] for a in data_cols}

        for player in self.players.values():
            data["队伍"].append(player.team)
            data["选手"].append(player.nickname)
            data["积分"].append(player.rank_pt / 1000)
            data["试合数"].append(player.total_game_count)
            data["平顺"].append(player.getAvgPlacement())
            data["1着"].append(player.rank_count[0])
            data["2着"].append(player.rank_count[1])
            data["3着"].append(player.rank_count[2])
            data["4着"].append(player.rank_count[3])
            data["TOP率"].append(player.getTop())
            data["连对率"].append(player.getRentai())
            data["避四率"].append(player.get4thAvoidance())
            data["最高分"].append(player.getHighestGamePoints())
        
        return data


class Team:
    def __init__(self, dyyId, name, players, color=None):
        self.dyyId = dyyId
        self.name = name
        self.players: list[dict] = players
        self.color = color
        # Key of following dicts is phase index
        self.games_played: dict[int, int] = {}
        self.aggregate: dict[int, int] = {}
        self.score: dict[int, int] = {}
        self.ranks: dict[int, list[int]] = {}
    
    def inTeam(self, dyyId):
        return dyyId in [p["_id"] for p in self.players]
    
    def setColor(self, color):
        self.color = color
    
    def playsIn(self, phase_index):
        return phase_index in self.aggregate
    
    def setAggregate(self, phase_index, aggregate_total):
        self.aggregate[phase_index] = aggregate_total
    
    def setScore(self, phase_index, score):
        self.score[phase_index] = score
    
    def setGamesPlayed(self, phase_index, games_played):
        self.games_played[phase_index] = games_played

    def __str__(self):
        return str({"name": self.name, "players": self.players})
    
    def __repr__(self):
        return str({"_id": self.dyyId, "name": self.name, "players": self.players, "color": self.color})

class Teams:
    def __init__(self, contestId):
        self.contestId = contestId
        self.teams: dict[str, Team] = {}
        self.phases: dict[int, str] = {}
    
    def addTeamFromDayaya(self, team_dict):
        team = Team(dyyId := team_dict["_id"], team_dict["name"], team_dict["players"])
        if "color" in team_dict:
            team.setColor(team_dict["color"])
        self.teams[dyyId] = team

    def addTeamFromMajsoul(self, team_dict):
        # Soon
        pass

    def addPhase(self, index, phase_name):
        self.phases[index] = phase_name
    
    def exportToDict(self):
        data_cols = ["队伍","总积分","继承","阶段","试合数","1着","2着","3着","4着"]
        data = [{"index": index, "name": phase_name, "data": {a: [] for a in data_cols}} for index, phase_name in self.phases.items()]

        for index in self.phases.keys():
            for team in self.teams.values():
                data[index]["data"]["队伍"].append(team.name)
                data[index]["data"]["继承"].append(team.aggregate[index] / 1000)
                data[index]["data"]["阶段"].append((team.score[index]-team.aggregate[index]) / 1000)
                data[index]["data"]["总积分"].append(team.score[index] / 1000)
                data[index]["data"]["试合数"].append(team.games_played[index])
                data[index]["data"]["1着"].append(team.ranks[index][0])
                data[index]["data"]["2着"].append(team.ranks[index][1])
                data[index]["data"]["3着"].append(team.ranks[index][2])
                data[index]["data"]["4着"].append(team.ranks[index][3])
        
        return data

class Game:
    def __init__(self, game_data, tz: tzinfo = None):
        self.dyyId = game_data["_id"]
        self.uuid = game_data['majsoulId']
        self.tz = tz or CNTZ()
        self.players = [player | score for player, score in zip(game_data["players"], game_data["finalScore"])]
        self.start_time = datetime.fromtimestamp(game_data['start_time'] // 1000, tz=self.tz)
        self.end_time = datetime.fromtimestamp(game_data['end_time'] // 1000, tz=self.tz)
    
    def getPlayerData(self, dyyId):
        return [p for p in self.players if p['_id'] == dyyId]
    
    def hasPlayed(self, dyyId):
        return len(self.getPlayerData(dyyId)) == 1
    
    def hasSameDate(self, time: datetime):
        return self.start_time.date() == time.date()

class Games:
    def __init__(self, contestId):
        self.contestId = contestId
        self.games: dict[str, Game] = {}
    
    def addGame(self, game: Game):
        self.games[game.dyyId] = game
    
    def addGameFromDict(self, game_data):
        self.games[game_data["_id"]] = Game(game_data)
    
    def getGameFromUuid(self, uuid):
        return [g for g in self.games.values() if g.uuid == uuid]
    
    def getPlayerGames(self, dyyId):
        return [g for g in self.games.values() if g.hasPlayed(dyyId)]
    
    def getGameFromTime(self, time: datetime):
        return [g for g in self.games.values() if g.hasSameDate(time)]
    
    def getGameTime(self, last=0):
        """
        last: 0 for most recent, 1 for 2nd most recent, etc.
        """
        return sorted([game.start_time for game in self.games.values()], reverse=True)[last]
    
    def exportToDict(self, games = None):
        data_cols = ["开始时间","结束时间", "1位玩家","1位ID","1位分数","1位终局点数","2位玩家","2位ID","2位分数","2位终局点数","3位玩家","3位ID","3位分数","3位终局点数","4位玩家","4位ID","4位分数","4位终局点数","牌谱链接"]
        data = {a: [] for a in data_cols}
        games = games or self.games
        #beijing_time = CNTZ()

        for game in games.values():
            game_data = sorted(game.players, key=lambda x:x["uma"], reverse=True)
            data["开始时间"].append(game.start_time.strftime("%Y-%m-%d %H:%M:%S"))
            data["结束时间"].append(game.end_time.strftime("%Y-%m-%d %H:%M:%S"))
            data["1位玩家"].append(game_data[0]["nickname"])
            data["1位ID"].append(game_data[0]["_id"])
            data["1位分数"].append(game_data[0]["score"])
            data["1位终局点数"].append(game_data[0]["uma"] / 1000)
            data["2位玩家"].append(game_data[1]["nickname"])
            data["2位ID"].append(game_data[1]["_id"])
            data["2位分数"].append(game_data[1]["score"])
            data["2位终局点数"].append(game_data[1]["uma"] / 1000)
            data["3位玩家"].append(game_data[2]["nickname"])
            data["3位ID"].append(game_data[2]["_id"])
            data["3位分数"].append(game_data[2]["score"])
            data["3位终局点数"].append(game_data[2]["uma"] / 1000)
            data["4位玩家"].append(game_data[3]["nickname"])
            data["4位ID"].append(game_data[3]["_id"])
            data["4位分数"].append(game_data[3]["score"])
            data["4位终局点数"].append(game_data[3]["uma"] / 1000)
            data["牌谱链接"].append("https://game.maj-soul.com/1/?paipu="+game.uuid)
        
        return data