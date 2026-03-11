import hmac
import hashlib
import asyncio
import requests
from datetime import datetime, tzinfo, timedelta, UTC
import logging
import time
from typing import *
from websockets.exceptions import ConnectionClosed, ConnectionClosedError, InvalidStatusCode

# MS_MANAGER_WSS_ENDPOINT: `__MJ_DHS_WS__` from https://www.maj-soul.com/dhs/js/config.js
# MS_MANAGER_WSS_ENDPOINT = "wss://common-v2.maj-soul.com/contest_ws_gateway"
EAST = 0
SOUTH = 1
WEST = 2
NORTH = 3
MAX_TIMESTAMP = 2147483647000

class DayayaAPI:
    def __init__(self, endpoint = "", log_messages=False, logger_name="Dayaya Manager"):
        self.logger = logging.getLogger(logger_name)
        self.log_messages = log_messages
        self.endpoint = endpoint or "http://web.170045.xyz:8008/api"
        self.headers = {
            "Referer": "https://170045.xyz/",
            "Accept": "application/json, */*",
            "Content-Type": "application/json",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/123.0",
        }

    def get(self, method: str, endpoint: str = "", headers: Dict = {}, second_try: bool = False, **params):
        try:
            return requests.get((endpoint or self.endpoint) + method, params=params, headers=headers or self.headers).json()
        except Exception as e:
            if not second_try:
                self.logger.info("Attempting to log in again in order to resend the request...")
                self.login()
                return self.get(method=method, endpoint=endpoint, second_try=True, **params)
            else:
                self.logger.info("Relog failed, not trying again")
    def delete(self, method: str, endpoint: str = "", second_try: bool = False, **params):
        try:
            return requests.delete((endpoint or self.endpoint) + method, params=params, headers=self.headers).json()
        except Exception as e:
            if not second_try:
                self.logger.info("Attempting to log in again in order to resend the request...")
                self.login()
                return self.get(method=method, endpoint=endpoint, second_try=True, **params)
            else:
                self.logger.info("Relog failed, not trying again")
    def put(self, method: str, params: Dict = {}, endpoint: str = "", second_try: bool = False, **data):
        try:
            return requests.put((endpoint or self.endpoint) + method, params=params, headers=self.headers, json=data).json()
        except Exception as e:
            if not second_try:
                self.logger.info("Attempting to log in again in order to resend the request...")
                self.login()
                return self.post(method=method, params=params, endpoint=endpoint, second_try=True, **data)
            else:
                self.logger.info("Relog failed, not trying again")
    def patch(self, method: str, params: Dict = {}, endpoint: str = "", second_try: bool = False, **data):
        try:
            return requests.patch((endpoint or self.endpoint) + method, params=params, headers=self.headers, json=data).json()
        except Exception as e:
            if not second_try:
                self.logger.info("Attempting to log in again in order to resend the request...")
                self.login()
                return self.post(method=method, params=params, endpoint=endpoint, second_try=True, **data)
            else:
                self.logger.info("Relog failed, not trying again")
    def login(self):
        pass

class DayayaLogin(DayayaAPI):
    def __init__(self, username: str, password: str, log_messages=False, logger_name="Contest Manager"):
        super().__init__(log_messages, logger_name)
        self.username = username
        self.password = password
        self.login()
    def login(self):
        self.login_token = self.get_new_login_token()
        self.headers["Authorization"] = "Bearer " + self.login_token
    def get_login_token(self):
        return self.login_token
    def get_new_login_token(self):
        try:
            login_header = dict(self.headers)
            login_header["Username"] = self.username
            login_header["Password"] = self.password
            login_token = self.get("rigging/token", headers=login_header)
        except Exception as e:
            print("Error: " + str(e))
            print("login result: " + str(login_token))
        if self.log_messages:
            self.logger.info("Login token: " + login_token)
        return login_token

class DyyContestManager:
    def __init__(self, contest_id: str, api: DayayaAPI):
        self.contest_id = contest_id
        self.api = api
        self.update()
        
    def update(self):
        self.__fetch_contest()
        self.contest_name = self.contest_info["name"]
        self.logger = logging.getLogger(self.contest_name)
        self.teams = self.contest_info["teams"]
        self.players = self.api.get(method=f"contests/{self.contest_id}/players")
        self.phases = self.contest_info["phases"]
        self.start_points, self.sessions = self.__getDataByPhase()
        self.current_phase = self.api.get(method=f"contests/{self.contest_id}/phases/active")["index"]
        self.current_session = self.api.get(method=f"contests/{self.contest_id}/sessions/active")

    def __fetch_contest(self):
        self.contest_info = self.api.get(method=f"contests/{self.contest_id}")
    def __getCurrenttime(timezone=UTC):
        return datetime.now(timezone)
    def __getDataByPhase(self):
        aggregateTotals = dict()
        sessions = dict()
        for i in range(len(self.phases)):
            data = self.api.get(f"contests/{self.contest_id}/phases/{i}")
            aggregateTotals[i] = data["aggregateTotals"]
            sessions[i] = data["sessions"]
        return aggregateTotals, sessions

    def getPlayerDyyId(self, nickname: str, limit: int=1):
        return self.api.get(method="players", name=nickname, limit=limit)["_id"]
    def getPlayerGames(self, player_dyyId: str):
        return self.api.get(method=f"contests/{self.contestId}/players/{player_dyyId}/games")
    def getPlayerStats(self, player: str):
        """
        player: dyyId
        """
        return self.api.get(method=f"contests/{self.contestId}/stats", player=player)
    def getTeamStats(self, team: str):
        """
        team: dyyId
        """
        return self.api.get(method=f"contests/{self.contestId}/stats", team=team)
    def getAllPlayerStats(self):
        return self.api.get(method=f"contests/{self.contestId}/stats", players=None)
    def getPlayerGames(self, id, start_time: int=None, end_time: int=None):
        """
        "start_time" and "end_time" defines range of games to be recorded based on START_TIME of games.
        Type is int - Unix timestamp in milliseconds.
        """
        games_raw = [game for game in self.api.get(method=f"contests/{self.contestId}/players/{id}/games", players=None)
                     if game["start_time"] >= (start_time or 0) and game["start_time"] <= (end_time or MAX_TIMESTAMP)]
        recent_games = []
        for game in games_raw:
            # Returns the index if found, or -1 if not
            index = next((i for i, item in enumerate(game["players"]) if item.get("_id") == id), -1)
            point = game["finalScore"][index]["uma"]
            rank = sorted([sc["uma"] for sc in game["finalScore"]], reverse=True).index(point) +1
            recent_games.append({"rank": rank, "total_point": point})


        
        