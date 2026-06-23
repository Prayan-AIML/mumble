#!/usr/bin/env python3
import os, sys, threading, time

# Run from the app's own directory so server.py finds index.html and .env.local
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import server

def run_server():
    server.start()

t = threading.Thread(target=run_server, daemon=True)
t.start()
time.sleep(1.5)  # wait for server to be ready

import webview
window = webview.create_window(
    'Mumble',
    'http://localhost:3456',
    width=390,
    height=820,
    resizable=False,
    min_size=(390, 600),
)
webview.start()
