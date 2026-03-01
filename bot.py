import os
import requests
import base64
import threading
import re
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import google.generativeai as genai

# === CONFIGURACIÓN (Vía Variables de Entorno) ===
TOKEN = os.getenv('TELEGRAM_TOKEN')
GH_TOKEN = os.getenv('GITHUB_TOKEN')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
GH_USER = os.getenv('GITHUB_USER') 
# Convertir string de IDs "123,456" a lista de enteros
ALLOWED_IDS = [int(x.strip()) for x in os.getenv('ALLOWED_IDS', '').split(',')] if os.getenv('ALLOWED_IDS') else []

# Inicialización
bot = telebot.TeleBot(TOKEN)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
app = Flask(__name__)

HEADERS = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
user_data = {}

# === RUTAS PARA RENDER (FLASK) ===
@app.route('/')
def health():
    # Esta ruta permite que Render detecte que el puerto está abierto
    return "🚀 Bot GitHub Commander está en línea", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    # Aquí recibirás notificaciones de GitHub Actions si lo configuraste
    return "OK", 200

# === MENÚS ===
def main_menu():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton("🤖 IA Gemini"), KeyboardButton("📁 Mis Repos"),
        KeyboardButton("🔍 Buscar"), KeyboardButton("➕ Nuevo Repo")
    )
    return markup

# === SEGURIDAD ===
#@bot.message_handler(func=lambda m: m.from_user.id not in ALLOWED_IDS)
#def access_denied(message):
 #   print(f"⚠️ Bloqueado: {message.from_user.id}")
#    bot.reply_to(message, "🚫 No tienes permiso para usar este bot.")

# === COMANDOS Y LOGICA ===
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🛰️ **Sistema GitHub Commander Activo.**", 
                     reply_markup=main_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: "github.com/" in m.text)
def handle_link_zip(message):
    parts = re.findall(r'github.com/([^/]+/[^/]+)', message.text)
    if parts:
        repo = parts[0].replace('.git', '').strip()
        send_zip(message.chat.id, repo)

@bot.message_handler(func=lambda message: True)
def menu_handler(message):
    if message.text == "🤖 IA Gemini":
        msg = bot.send_message(message.chat.id, "✨ ¿Qué código o idea necesitas?")
        bot.register_next_step_handler(msg, process_gemini)
    elif message.text == "📁 Mis Repos":
        list_my_repos(message)
    elif message.text == "🔍 Buscar":
        msg = bot.send_message(message.chat.id, "🔎 Escribe el tema:")
        bot.register_next_step_handler(msg, process_search)
    elif message.text == "➕ Nuevo Repo":
        msg = bot.send_message(message.chat.id, "🏷️ Nombre del nuevo repositorio:")
        bot.register_next_step_handler(msg, process_new_repo)

# --- (Las funciones process_gemini, process_search, list_my_repos se mantienen igual) ---

def process_gemini(message):
    m = bot.send_message(message.chat.id, "🧠 Gemini procesando...")
    try:
        res = model.generate_content(message.text)
        user_data[message.chat.id] = {'last_code': res.text}
        markup = InlineKeyboardMarkup()
        if "```" in res.text:
            markup.add(InlineKeyboardButton("💾 Guardar en GitHub", callback_data="gemini_save"))
        bot.send_message(message.chat.id, res.text, reply_markup=markup)
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

def list_my_repos(message):
    res = requests.get("[https://api.github.com/user/repos?type=owner&sort=updated](https://api.github.com/user/repos?type=owner&sort=updated)", headers=HEADERS).json()
    markup = InlineKeyboardMarkup()
    if isinstance(res, list):
        for r in res[:8]:
            markup.add(InlineKeyboardButton(f"📁 {r['name']}", callback_data=f"manage_{r['name']}"))
        bot.send_message(message.chat.id, "Tus repositorios:", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "❌ Error de conexión con GitHub.")

def process_search(message):
    query = message.text.replace(" ", "+")
    url = f"[https://api.github.com/search/repositories?q=](https://api.github.com/search/repositories?q=){query}&sort=stars&per_page=5"
    res = requests.get(url, headers=HEADERS).json()
    for repo in res.get('items', []):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📥 ZIP", callback_data=f"zip_{repo['full_name']}"))
        bot.send_message(message.chat.id, f"📦 **{repo['full_name']}**", parse_mode="Markdown", reply_markup=markup)

def process_new_repo(message):
    name = message.text.strip().replace(" ", "-")
    res = requests.post("[https://api.github.com/user/repos](https://api.github.com/user/repos)", headers=HEADERS, json={"name": name})
    bot.send_message(message.chat.id, f"✅ Repo `{name}` creado." if res.status_code == 201 else "❌ Error.")

def send_zip(chat_id, repo_full_name):
    bot.send_message(chat_id, f"⏳ Comprimiendo `{repo_full_name}`...")
    try:
        repo_info = requests.get(f"[https://api.github.com/repos/](https://api.github.com/repos/){repo_full_name}", headers=HEADERS).json()
        branch = repo_info.get('default_branch', 'main')
        zip_url = f"[https://github.com/](https://github.com/){repo_full_name}/archive/refs/heads/{branch}.zip"
        file_res = requests.get(zip_url, stream=True)
        bot.send_document(chat_id, file_res.raw, visible_file_name=f"{repo_full_name.split('/')[-1]}.zip")
    except:
        bot.send_message(chat_id, "❌ Error al descargar.")

# === CALLBACKS ===
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    if call.data.startswith("zip_"):
        send_zip(call.message.chat.id, call.data.replace("zip_", ""))
    elif call.data.startswith("manage_"):
        repo = call.data.replace("manage_", "")
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("📥 ZIP", callback_data=f"zip_{GH_USER}/{repo}"))
        bot.edit_message_text(f"Gestionando: {repo}", call.message.chat.id, call.message.message_id, reply_markup=markup)
    elif call.data == "gemini_save":
        bot.send_message(call.message.chat.id, "📝 ¿Nombre del archivo?")
        # (Lógica simplificada para el ejemplo)

# === ARRANCADOR DUAL (FLASK + POLLING) ===
def start_polling():
    print("🤖 Bot de Telegram escuchando...")
    bot.infinity_polling()

if __name__ == "__main__":
    # 1. Lanzamos el bot en un hilo secundario (Daemon para que muera con el principal)
    threading.Thread(target=start_polling, daemon=True).start()
    
    # 2. El hilo principal ejecuta Flask para que Render detecte el puerto
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
