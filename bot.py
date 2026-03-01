import os
import requests
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import google.generativeai as genai

# === CONFIGURACIÓN ===
TOKEN = os.getenv('TELEGRAM_TOKEN')
GH_TOKEN = os.getenv('GITHUB_TOKEN')
GH_USER = os.getenv('GITHUB_USER')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
ALLOWED_IDS = [int(x.strip()) for x in os.getenv('ALLOWED_IDS', '').split(',')] if os.getenv('ALLOWED_IDS') else []

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
HEADERS = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}

# Inicialización IA opcional
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

# === MENÚ ===
def main_menu():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton("🤖 IA Gemini"),
        KeyboardButton("📁 Mis Repos"),
        KeyboardButton("🔍 Buscar"),
        KeyboardButton("➕ Nuevo Repo")
    )
    return markup

# === SEGURIDAD ===
@bot.message_handler(func=lambda m: m.from_user.id not in ALLOWED_IDS)
def access_denied(message):
    bot.reply_to(message, "🚫 No tienes permiso para usar este bot.")

# === COMANDOS ===
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🛰️ **Sistema GitHub Commander Activo.**", 
                     reply_markup=main_menu(), parse_mode="Markdown")

# === DETECTAR LINKS DE GITHUB ===
@bot.message_handler(func=lambda m: "github.com/" in m.text)
def handle_link_zip(message):
    parts = m.text.split("github.com/")[-1].split("/")
    if len(parts) >= 2:
        repo = f"{parts[0]}/{parts[1].replace('.git','')}"
        send_zip(message.chat.id, repo)
    else:
        bot.send_message(message.chat.id, "❌ Link de repo inválido.")

# === MENÚ PRINCIPAL ===
@bot.message_handler(func=lambda m: True)
def menu_handler(message):
    text = message.text
    if text == "🤖 IA Gemini" and GEMINI_KEY:
        msg = bot.send_message(message.chat.id, "✨ ¿Qué código o idea necesitas?")
        bot.register_next_step_handler(msg, process_gemini)
    elif text == "📁 Mis Repos":
        list_my_repos(message)
    elif text == "🔍 Buscar":
        msg = bot.send_message(message.chat.id, "🔎 Escribe el tema:")
        bot.register_next_step_handler(msg, process_search)
    elif text == "➕ Nuevo Repo":
        msg = bot.send_message(message.chat.id, "🏷️ Nombre del nuevo repositorio:")
        bot.register_next_step_handler(msg, process_new_repo)
    else:
        bot.send_message(message.chat.id, "⚡ Usa el menú principal.")

# === FUNCIONES ===
def process_gemini(message):
    bot.send_message(message.chat.id, "🧠 Gemini procesando...")
    try:
        res = model.generate_content(message.text)
        markup = InlineKeyboardMarkup()
        if "```" in res.text:
            markup.add(InlineKeyboardButton("💾 Guardar en GitHub", callback_data="gemini_save"))
        bot.send_message(message.chat.id, res.text, reply_markup=markup)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error IA: {e}")

def list_my_repos(message):
    res = requests.get(f"https://api.github.com/user/repos?type=owner&sort=updated", headers=HEADERS).json()
    markup = InlineKeyboardMarkup()
    if isinstance(res, list):
        for r in res[:8]:
            markup.add(InlineKeyboardButton(f"📁 {r['name']}", callback_data=f"zip_{r['full_name']}"))
        bot.send_message(message.chat.id, "Tus repositorios:", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "❌ Error al conectar con GitHub.")

def process_search(message):
    query = message.text.replace(" ", "+")
    url = f"https://api.github.com/search/repositories?q={query}&sort=stars&per_page=5"
    res = requests.get(url, headers=HEADERS).json()
    for repo in res.get('items', []):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📥 ZIP", callback_data=f"zip_{repo['full_name']}"))
        bot.send_message(message.chat.id, f"📦 **{repo['full_name']}**", parse_mode="Markdown", reply_markup=markup)

def process_new_repo(message):
    name = message.text.strip().replace(" ", "-")
    res = requests.post("https://api.github.com/user/repos", headers=HEADERS, json={"name": name})
    bot.send_message(message.chat.id, f"✅ Repo `{name}` creado." if res.status_code==201 else "❌ Error.")

# === ENVIO DE ZIP OPTIMIZADO ===
def send_zip(chat_id, repo_full_name):
    try:
        # Obtener rama por defecto
        repo_info = requests.get(f"https://api.github.com/repos/{repo_full_name}", headers=HEADERS).json()
        branch = repo_info.get('default_branch','main')
        zip_url = f"https://github.com/{repo_full_name}/archive/refs/heads/{branch}.zip"
        # Enviar ZIP directo desde GitHub
        bot.send_message(chat_id, f"⏳ Preparando `{repo_full_name}`...")
        bot.send_document(chat_id, zip_url, visible_file_name=f"{repo_full_name.split('/')[-1]}.zip")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error al descargar ZIP: {e}")

# === CALLBACKS ===
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    if call.data.startswith("zip_"):
        send_zip(call.message.chat.id, call.data.replace("zip_",""))
    elif call.data == "gemini_save":
        bot.send_message(call.message.chat.id, "📝 ¿Nombre del archivo?")

# === FLASK + WEBHOOK PARA RENDER ===
@app.route('/', methods=['GET'])
def health():
    return "🚀 Bot activo", 200

@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook_handler():
    update = request.get_json()
    if update:
        bot.process_new_updates([telebot.types.Update.de_json(update)])
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("🚀 Bot listo para Render Webhook en puerto", port)
    app.run(host='0.0.0.0', port=port)
