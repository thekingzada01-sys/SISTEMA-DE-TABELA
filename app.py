from flask import Flask, render_template, request, redirect, send_file
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

import os
import re
import json

app = Flask(__name__)

DB_FILE = "database.json"
RESULTADOS_DIR = "resultados"
FONT_PATH = "arial.ttf"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ==========================================
# CRIAR DATABASE
# ==========================================

if not os.path.exists(DB_FILE):

    with open(DB_FILE, "w", encoding="utf-8") as f:

        json.dump({

            "times": {},
            "players": {},
            "processados": []

        }, f, indent=4, ensure_ascii=False)

# ==========================================
# LOAD DB
# ==========================================

def load_db():

    with open(DB_FILE, "r", encoding="utf-8") as f:

        return json.load(f)

# ==========================================
# SAVE DB
# ==========================================

def save_db(db):

    with open(DB_FILE, "w", encoding="utf-8") as f:

        json.dump(
            db,
            f,
            indent=4,
            ensure_ascii=False
        )

# ==========================================
# PROCESSAR LOGS
# ==========================================

def process_logs():

    db = load_db()

    if not os.path.exists(RESULTADOS_DIR):
        os.makedirs(RESULTADOS_DIR)

    for arquivo in os.listdir(RESULTADOS_DIR):

        if not arquivo.endswith(".log"):
            continue

        if arquivo in db["processados"]:
            continue

        caminho = os.path.join(
            RESULTADOS_DIR,
            arquivo
        )

        with open(
            caminho,
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as f:

            conteudo = f.read()

        # ==================================
        # TIMES
        # ==================================

        teams = re.findall(

            r"TeamName:\s*(.*?)\s+Rank:\s*(\d+)\s+KillScore:\s*(\d+)\s+RankScore:\s*(\d+)\s+TotalScore:\s*(\d+)",

            conteudo,
            re.MULTILINE
        )

        for team in teams:

            nome = re.sub(
                r"\s+",
                " ",
                team[0]
            ).strip().upper()

            kills = int(team[2])
            pontos = int(team[4])

            if nome not in db["times"]:

                db["times"][nome] = {

                    "kills": 0,
                    "pontos": 0,
                    "quedas": 0

                }

            db["times"][nome]["kills"] += kills
            db["times"][nome]["pontos"] += pontos
            db["times"][nome]["quedas"] += 1

        # ==================================
        # PLAYERS
        # ==================================

        players = re.findall(

            r"NAME:\s*(.*?)\s+ID:\s*(\d+)\s+KILL:\s*(\d+)",

            conteudo,
            re.MULTILINE
        )

        for player in players:

            nome = player[0].strip()
            pid = player[1]
            kills = int(player[2])

            if nome not in db["players"]:

                db["players"][nome] = {

                    "id": pid,
                    "kills": 0,
                    "quedas": 0,
                    "kd": 0

                }

            db["players"][nome]["kills"] += kills
            db["players"][nome]["quedas"] += 1

            quedas = db["players"][nome]["quedas"]

            if quedas > 0:

                db["players"][nome]["kd"] = round(

                    db["players"][nome]["kills"] / quedas,
                    2
                )

        db["processados"].append(arquivo)

    save_db(db)

# ==========================================
# HOME
# ==========================================

@app.route("/")
def home():

    process_logs()

    db = load_db()

    teams = sorted(

        db["times"].items(),

        key=lambda x: x[1]["pontos"],

        reverse=True
    )

    players = sorted(

        db["players"].items(),

        key=lambda x: x[1]["kills"],

        reverse=True
    )

    mvp = players[0] if players else None

    return render_template(

        "index.html",

        teams=teams,
        players=players,
        mvp=mvp
    )

# ==========================================
# UPLOAD
# ==========================================

@app.route("/upload", methods=["POST"])
def upload():

    arquivos = request.files.getlist("log")

    if not os.path.exists(RESULTADOS_DIR):
        os.makedirs(RESULTADOS_DIR)

    for arquivo in arquivos:

        if arquivo.filename == "":
            continue

        if not arquivo.filename.endswith(".log"):
            continue

        caminho = os.path.join(
            RESULTADOS_DIR,
            arquivo.filename
        )

        arquivo.save(caminho)

    return redirect("/")

# ==========================================
# RESET
# ==========================================

@app.route("/reset")
def reset():

    db = {

        "times": {},
        "players": {},
        "processados": []

    }

    save_db(db)

    if os.path.exists(RESULTADOS_DIR):

        for arquivo in os.listdir(RESULTADOS_DIR):

            if arquivo.endswith(".log"):

                os.remove(

                    os.path.join(
                        RESULTADOS_DIR,
                        arquivo
                    )
                )

    return redirect("/")

# ==========================================
# PEGAR BACKGROUND SEM ESTICAR
# ==========================================

def get_background(largura, altura):

    background_path = os.path.join(
        BASE_DIR,
        "background.png"
    )

    # Fundo padrão caso não exista imagem
    fundo_final = Image.new(
        "RGB",
        (largura, altura),
        (5, 5, 5)
    )

    # Verifica se existe
    if not os.path.exists(background_path):
        return fundo_final

    # Abre imagem
    background = Image.open(background_path).convert("RGB")

    # Tamanho original
    bg_w, bg_h = background.size

    # Escala proporcional
    escala = max(
        largura / bg_w,
        altura / bg_h
    )

    # Novo tamanho mantendo proporção
    novo_w = int(bg_w * escala)
    novo_h = int(bg_h * escala)

    # Redimensiona sem perder qualidade
    background = background.resize(
        (novo_w, novo_h),
        Image.LANCZOS
    )

    # Centraliza imagem
    pos_x = (largura - novo_w) // 2
    pos_y = (altura - novo_h) // 2

    # Cola imagem centralizada
    fundo_final.paste(
        background,
        (pos_x, pos_y)
    )

    return fundo_final

# ==========================================
# EXPORTAR CLASSIFICAÇÃO
# ==========================================

@app.route("/export")
def export():

    try:

        db = load_db()

        teams = sorted(

            db["times"].items(),

            key=lambda x: x[1]["pontos"],

            reverse=True
        )

        largura = 2200
        altura = 300 + (len(teams) * 78)

        imagem = get_background(
            largura,
            altura
        )

        draw = ImageDraw.Draw(imagem)

        # FONTES

        try:

            fonte_titulo = ImageFont.truetype(
                FONT_PATH,
                60
            )

            fonte_header = ImageFont.truetype(
                FONT_PATH,
                28
            )

            fonte = ImageFont.truetype(
                FONT_PATH,
                32
            )

        except:

            fonte_titulo = ImageFont.load_default()
            fonte_header = ImageFont.load_default()
            fonte = ImageFont.load_default()

        # TITULO

        draw.text(

            (40, 20),

            "CLASSIFICACAO GERAL",

            fill=(255,255,255),

            font=fonte_titulo
        )

        # HEADER

        header_y = 150

        colunas = [

            ("#", 20, 180),
            ("TIME", 180, 980),
            ("KILLS", 980, 1280),
            ("PONTOS", 1280, 1630),
            ("QUEDAS", 1630, 1980)

        ]

        for titulo, x1, x2 in colunas:

            draw.rectangle(

                (x1, header_y, x2, header_y + 55),

                fill=(180,0,0)
            )

            largura_texto = draw.textlength(
                titulo,
                font=fonte_header
            )

            centro_x = ((x1 + x2) / 2) - (largura_texto / 2)

            draw.text(

                (centro_x, header_y + 12),

                titulo,

                fill=(255,255,255),

                font=fonte_header
            )

        # TABELA

        y = 220

        for i, (team, data) in enumerate(teams):

            fundo = (10,10,10)
            texto = (255,255,255)

            if i == 0:

                fundo = (255,215,0)
                texto = (0,0,0)

            elif i == 1:

                fundo = (210,210,210)
                texto = (0,0,0)

            elif i == 2:

                fundo = (205,127,50)

            col_data = [

                (str(i+1), 20, 180),
                (team, 180, 980),
                (str(data["kills"]), 980, 1280),
                (str(data["pontos"]), 1280, 1630),
                (str(data["quedas"]), 1630, 1980)

            ]

            for valor, x1, x2 in col_data:

                draw.rectangle(

                    (x1, y, x2, y + 65),

                    fill=fundo
                )

                largura_texto = draw.textlength(
                    valor,
                    font=fonte
                )

                centro_x = ((x1 + x2) / 2) - (largura_texto / 2)

                if x1 == 180:
                    centro_x = x1 + 20

                draw.text(

                    (centro_x, y + 14),

                    valor,

                    fill=texto,

                    font=fonte
                )

            y += 75

        buffer = BytesIO()

        imagem.save(buffer, format="PNG")

        buffer.seek(0)

        return send_file(

            buffer,

            mimetype="image/png",

            as_attachment=True,

            download_name="classificacao_geral.png"
        )

    except Exception as e:

        return f"ERRO AO EXPORTAR TABELA: {str(e)}"

# ==========================================
# EXPORTAR MVP
# ==========================================

@app.route("/export_mvp")
def export_mvp():

    try:

        db = load_db()

        players = sorted(

            db["players"].items(),

            key=lambda x: x[1]["kills"],

            reverse=True
        )

        if not players:
            return "Nenhum player encontrado"

        largura = 2200
        altura = 300 + (len(players[:5]) * 78)

        imagem = get_background(
            largura,
            altura
        )

        draw = ImageDraw.Draw(imagem)

        # FONTES

        try:

            fonte_titulo = ImageFont.truetype(
                FONT_PATH,
                60
            )

            fonte_header = ImageFont.truetype(
                FONT_PATH,
                28
            )

            fonte = ImageFont.truetype(
                FONT_PATH,
                32
            )

        except:

            fonte_titulo = ImageFont.load_default()
            fonte_header = ImageFont.load_default()
            fonte = ImageFont.load_default()

        # TITULO

        draw.text(

            (40, 20),

            "TOP 5 MVP PLAYERS",

            fill=(255,255,255),

            font=fonte_titulo
        )

        # HEADER

        header_y = 150

        colunas = [

            ("#", 20, 180),
            ("PLAYER", 180, 1180),
            ("KILLS", 1180, 1480),
            ("KD", 1480, 1780),
            ("QUEDAS", 1780, 2080)

        ]

        for titulo, x1, x2 in colunas:

            draw.rectangle(

                (x1, header_y, x2, header_y + 55),

                fill=(180,0,0)
            )

            largura_texto = draw.textlength(
                titulo,
                font=fonte_header
            )

            centro_x = ((x1 + x2) / 2) - (largura_texto / 2)

            draw.text(

                (centro_x, header_y + 12),

                titulo,

                fill=(255,255,255),

                font=fonte_header
            )

        # TABELA

        y = 220

        top_players = players[:5]

        for i, (player, data) in enumerate(top_players):

            fundo = (10,10,10)
            texto = (255,255,255)

            if i == 0:

                fundo = (255,215,0)
                texto = (0,0,0)

            elif i == 1:

                fundo = (210,210,210)
                texto = (0,0,0)

            elif i == 2:

                fundo = (205,127,50)

            kd = data.get("kd", 0)

            col_data = [

                (str(i+1), 20, 180),
                (player, 180, 1180),
                (str(data["kills"]), 1180, 1480),
                (str(kd), 1480, 1780),
                (str(data["quedas"]), 1780, 2080)

            ]

            for valor, x1, x2 in col_data:

                draw.rectangle(

                    (x1, y, x2, y + 65),

                    fill=fundo
                )

                largura_texto = draw.textlength(
                    valor,
                    font=fonte
                )

                centro_x = ((x1 + x2) / 2) - (largura_texto / 2)

                if x1 == 180:
                    centro_x = x1 + 20

                draw.text(

                    (centro_x, y + 14),

                    valor,

                    fill=texto,

                    font=fonte
                )

            y += 75

        buffer = BytesIO()

        imagem.save(buffer, format="PNG")

        buffer.seek(0)

        return send_file(

            buffer,

            mimetype="image/png",

            as_attachment=True,

            download_name="top5_mvp.png"
        )

    except Exception as e:

        return f"ERRO AO EXPORTAR MVP: {str(e)}"

# ==========================================
# TEXTO TABELA
# ==========================================

@app.route("/texto_tabela")
def texto_tabela():

    db = load_db()

    teams = sorted(

        db["times"].items(),

        key=lambda x: x[1]["pontos"],

        reverse=True
    )

    texto = "🏆 CLASSIFICACAO GERAL 🏆\n\n"

    for i, (team, data) in enumerate(teams):

        texto += (
            f"{i+1}º {team} | "
            f"KILLS: {data['kills']} | "
            f"PONTOS: {data['pontos']} | "
            f"QUEDAS: {data['quedas']}\n"
        )

    return texto

# ==========================================
# TEXTO MVP
# ==========================================

@app.route("/texto_mvp")
def texto_mvp():

    db = load_db()

    players = sorted(

        db["players"].items(),

        key=lambda x: x[1]["kills"],

        reverse=True
    )

    if not players:
        return "Nenhum MVP encontrado"

    player, data = players[0]

    texto = (
        "🔥 MVP PLAYER 🔥\n\n"
        f"PLAYER: {player}\n"
        f"KILLS: {data['kills']}\n"
        f"KD: {data['kd']}\n"
        f"QUEDAS: {data['quedas']}"
    )

    return texto

# ==========================================
# START
# ==========================================

# ==========================================
# COPIAR TABELA TEXTO
# ==========================================

@app.route("/copiar_tabela")
def copiar_tabela():

    db = load_db()

    teams = sorted(
        db["times"].items(),
        key=lambda x: x[1]["pontos"],
        reverse=True
    )

    linhas = []

    linhas.append("POS\tEQUIPE\tABATES\tPONTOS\tQUEDAS")

    for i, (team, data) in enumerate(teams):

        linhas.append(
            f"'{i+1}\t"
            f"{team}\t"
            f"'{data['kills']}\t"
            f"'{data['pontos']}\t"
            f"'{data['quedas']}"
        )

    return "\n".join(linhas)

# ==========================================
# COPIAR MVP TEXTO
# ==========================================

@app.route("/copiar_mvp")
def copiar_mvp():

    db = load_db()

    players = sorted(
        db["players"].items(),
        key=lambda x: x[1]["kills"],
        reverse=True
    )

    linhas = []

    linhas.append("POS\tPLAYER\tKILLS\tKD\tQUEDAS")

    for i, (player, data) in enumerate(players[:5]):

        linhas.append(
            f"'{i+1}\t"
            f"{player}\t"
            f"'{data['kills']}\t"
            f"'{data['kd']}\t"
            f"'{data['quedas']}"
        )

    return "\n".join(linhas)

import os
from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return "Aplicação rodando!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)