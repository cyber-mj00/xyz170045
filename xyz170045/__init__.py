# A very simple Flask Hello World app for you to get started with...

from flask import Flask, send_file, Response
import os

from os.path import join, dirname
from getdata import *

app = Flask(__name__)

@app.route('/')
def home():
    html = '''<!doctype html><html><head><title>大鸭鸭表格生成工具</title></head>
              <body><h1>大鸭鸭表格生成工具</h1>
              <h3>炽焰天穹ML S1 2025  常规赛</h3>
              <p><a href="/download">下载</a>（每小时更新）</p>
              <hr><p><a href="https://cn.170045.xyz" target="_blank">实时积分榜</a> | <a href="https://github.com/cyber-mj00/xyz170045" target="_blank">Source code</a></p>
              <p>&copy; 2023-25 <a href="https://cyber.mj00.top" target="_blank">Dayaya</a>. All rights reserved.</p>
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

