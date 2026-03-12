from flask import Flask, send_file, Response
from flask_apscheduler import APScheduler
from datetime import datetime
import os

from os.path import join, dirname
from getdata import *
from getsheet import *

def scheduled_task():
    dayaya, majsoul, player_pool, team_pool, game_pool = loadContestData()
    generateSheet(player_pool, team_pool, game_pool)
    print(f"[{Dayaya.getCurrentTime()}] Scheduled task: updated.")

def generateSheet(player_pool, team_pool, game_pool):
    df_players, df_players_byteam, df_games, team_data = getDf(player_pool, team_pool, game_pool)
    getSheet(player_pool, team_pool, game_pool, df_players, df_players_byteam, df_games, team_data)

class Config:
    SCHEDULER_API_ENABLED = True


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config())

    scheduler = APScheduler()
    scheduler.add_job(id='refresh', func=scheduled_task, trigger='interval', hours=1)

    scheduler.init_app(app)
    scheduler.start()

    @app.route('/')
    def home():
        html = '''<!doctype html><html><head><title>大鸭鸭表格生成工具</title></head>
                <body><h1>大鸭鸭表格生成工具</h1>
                <h3>炽焰天穹ML S1 2025</h3>
                <p><a href="/download">下载</a>（每小时更新）</p>
                <hr><p><a href="https://cn.170045.xyz" target="_blank">实时积分榜</a> | <a href="https://github.com/cyber-mj00/xyz170045" target="_blank">Source code</a></p>
                <p>&copy; 2023-26 <a href="https://mj00.top" target="_blank">Dayaya</a>. All rights reserved.</p>
                </body></html>'''.format()
        return Response(html, content_type='text/html; charset=utf-8')

    @app.route('/download')
    def download_file():
        try:
            with open(join(dirname(__file__), "latest_file.txt"), "r") as f:
                filename = f.read()

            return send_file(join(dirname(__file__), filename), as_attachment=True)
        except Exception as e:
            return f"Error sending file: {str(e)}", 500

    return app



