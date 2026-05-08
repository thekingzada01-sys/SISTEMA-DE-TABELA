# app.py - versão final pronta para Railway

import os
import re
import json
from io import BytesIO
from flask import Flask, render_template, request, redirect, send_file
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

DB_FILE = "database.json"
RESULTADOS_DIR = "resultados"
FONT_PATH = "arial.ttf"  # substitua se não tiver
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Inicializar database
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump({"times": {}, "players": {}, "processados": []}, f, indent=4, ensure_ascii=False)

# Load/save
def load_db():
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

# Processar logs
def process_logs():
    db = load_db()
    if not os.path.exists(RESULTADOS_DIR):
        os.makedirs(RESULTADOS_DIR)
    for arquivo in os.listdir(RESULTADOS_DIR):
        if not arquivo.endswith(".log") or arquivo in db["processados"]:
            continue
        caminho = os.path.join(RESULTADOS_DIR, arquivo)
        with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
            conteudo = f.read()

        # TIMES
        teams = re.findall(
            r"TeamName:\s*(.*?)\s+Rank:\s*(\d+)\s+KillScore:\s*(\d+)\s+RankScore:\s*(\d+)\s+TotalScore:\s*(\d+)",
            conteudo,
            re.MULTILINE
        )
        for team in teams:
            nome = re.sub(r"\s+", " ", team[0]).strip().upper()
            kills = int(team[2])
            pontos = int(team[4])
            if nome not in db["times"]:
                db["times"][nome] = {"kills": 0, "pontos": 0, "quedas": 0}
            db["times"][nome]["kills"] += kills
            db["times"][nome]["pontos"] += pontos
            db["times"][nome]["quedas"] += 1

        # PLAYERS
        players = re.findall(r"NAME:\s*(.*?)\s+ID:\s*(\d+)\s+KILL:\s*(\d+)", conteudo, re.MULTILINE)
        for player in players:
            nome = player[0].strip()
            pid = player[1]
            kills = int(player[2])
            if nome not in db["players"]:
                db["players"][nome] = {"id": pid, "kills": 0, "quedas": 0, "kd": 0}
            db["players"][nome]["kills"] += kills
            db["players"][nome]["quedas"] += 1
            db["players"][nome]["kd"] = round(db["players"][nome]["kills"] / max(db["players"][nome]["quedas"], 1), 2)

        db["processados"].append(arquivo)
    save_db(db)

# Background
def get_background(largura, altura):
    fundo_final = Image.new("RGB", (largura, altura), (5,5,5))
    background_path = os.path.join(BASE_DIR, "background.png")
    if not os.path.exists(background_path):
        return fundo_final
    background = Image.open(background_path).convert("RGB")
    bg_w, bg_h = background.size
    escala = max(largura / bg_w, altura / bg_h)
    novo_w = int(bg_w * escala)
    novo_h = int(bg_h * escala)
    background = background.resize((novo_w, novo_h), Image.LANCZOS)
    pos_x = (largura - novo_w) // 2
    pos_y = (altura - novo_h) // 2
    fundo_final.paste(background, (pos_x, pos_y))
    return fundo_final

# Rotas
@app.route("/")
def home():
    process_logs()
    db = load_db()
    teams = sorted(db["times"].items(), key=lambda x: x[1]["pontos"], reverse=True)
    players = sorted(db["players"].items(), key=lambda x: x[1]["kills"], reverse=True)
    mvp = players[0] if players else None
    return render_template("index.html", teams=teams, players=players, mvp=mvp)

@app.route("/upload", methods=["POST"])
def upload():
    arquivos = request.files.getlist("log")
    if not os.path.exists(RESULTADOS_DIR):
        os.makedirs(RESULTADOS_DIR)
    for arquivo in arquivos:
        if arquivo.filename.endswith(".log"):
            arquivo.save(os.path.join(RESULTADOS_DIR, arquivo.filename))
    return redirect("/")

@app.route("/reset")
def reset():
    db = {"times": {}, "players": {}, "processados": []}
    save_db(db)
    if os.path.exists(RESULTADOS_DIR):
        for f in os.listdir(RESULTADOS_DIR):
            if f.endswith(".log"):
                os.remove(os.path.join(RESULTADOS_DIR, f))
    return redirect("/")

# ==========================
# NÃO USAR app.run()
# Railway usa gunicorn
# ==========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)