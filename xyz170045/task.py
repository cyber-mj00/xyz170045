from getdata import *
from getsheet import *

def main():
    print(f"[{Dayaya.getCurrentTime()}] Scheduled task: started.")
    dayaya, majsoul, player_pool, team_pool, game_pool = loadContestData()
    generateSheet(player_pool, team_pool, game_pool)
    print(f"[{Dayaya.getCurrentTime()}] Scheduled task: updated.")

def generateSheet(player_pool, team_pool, game_pool):
    df_players, df_players_byteam, df_games, team_data = getDf(player_pool, team_pool, game_pool)
    getSheet(player_pool, team_pool, game_pool, df_players, df_players_byteam, df_games, team_data)

if __name__ == "__main__":
    main()