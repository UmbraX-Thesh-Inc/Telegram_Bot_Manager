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
GH_USER = os.getenv('GITHUB_USER') # También te recomiendo poner tu usuario en Render
ALLOWED_IDS = [int(x) for x in os.getenv('ALLOWED_IDS', '').split(',')] if os.getenv('ALLOWED_IDS') else []

# Validación de arranque
if not TOKEN or not GH_TOKEN:
    print("❌ ERROR: Faltan variables de entorno. Revisa el panel de Render.")

bot = telebot.TeleBot(TOKEN)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
app = Flask(__name__)

HEADERS = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}

# Diccionarios temporales para el flujo de trabajo
user_data = {}

# === MENÚS ===
def main_menu():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton("🤖 IA Gemini"), KeyboardButton("📁 Mis Repos"),
        KeyboardButton("🔍 Buscar"), KeyboardButton("➕ Nuevo Repo")
    )
    return markup

# === SEGURIDAD & LOGS ===
@bot.message_handler(func=lambda m: m.from_user.id not in ALLOWED_IDS)
def access_denied(message):
    print(f"⚠️ Intento de acceso no autorizado: ID {message.from_user.id} - @{message.from_user.username}")
    bot.reply_to(message, "🚫 Acceso privado. Tu ID no está en la Whitelist.")

# === INICIO ===
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🛰️ **Sistema GitHub Commander Activo.**\nControl total mediante botones.", 
                     reply_markup=main_menu(), parse_mode="Markdown")

# === GESTIÓN DE ZIP POR LINK DIRECTO ===
@bot.message_handler(func=lambda m: "github.com/" in m.text)
def handle_link_zip(message):
    parts = re.findall(r'github.com/([^/]+/[^/]+)', message.text)
    if parts:
        repo = parts[0].replace('.git', '').strip()
        send_zip(message.chat.id, repo)

# === MANEJADOR DEL MENÚ PRINCIPAL ===
@bot.message_handler(func=lambda message: True)
def menu_handler(message):
    if message.text == "🤖 IA Gemini":
        msg = bot.send_message(message.chat.id, "✨ ¿Qué código o idea necesitas hoy?")
        bot.register_next_step_handler(msg, process_gemini)
    elif message.text == "📁 Mis Repos":
        list_my_repos(message)
    elif message.text == "🔍 Buscar":
        msg = bot.send_message(message.chat.id, "🔎 Escribe el tema a buscar:")
        bot.register_next_step_handler(msg, process_search)
    elif message.text == "➕ Nuevo Repo":
        msg = bot.send_message(message.chat.id, "🏷️ Nombre del nuevo repositorio:")
        bot.register_next_step_handler(msg, process_new_repo)

# === FUNCIONES DE PROCESAMIENTO ===
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
        bot.reply_to(message, f"❌ Error Gemini: {e}")

def process_search(message):
    query = message.text.replace(" ", "+")
    url = f"[https://api.github.com/search/repositories?q=](https://api.github.com/search/repositories?q=){query}&sort=stars&per_page=5"
    res = requests.get(url, headers=HEADERS).json()
    items = res.get('items', [])
    
    if not items:
        return bot.send_message(message.chat.id, "No se encontraron resultados.")

    for repo in items:
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("📥 Descargar ZIP", callback_data=f"zip_{repo['full_name']}"),
            InlineKeyboardButton("🍴 Fork", callback_data=f"fork_{repo['full_name']}")
        )
        bot.send_message(message.chat.id, f"📦 **{repo['full_name']}**\n⭐ {repo['stargazers_count']}\n📝 {repo['description']}", 
                         parse_mode="Markdown", reply_markup=markup)

def list_my_repos(message):
    res = requests.get(f"[https://api.github.com/user/repos?type=owner&sort=updated](https://api.github.com/user/repos?type=owner&sort=updated)", headers=HEADERS).json()
    markup = InlineKeyboardMarkup()
    if isinstance(res, list):
        for r in res[:8]:
            markup.add(InlineKeyboardButton(f"📁 {r['name']}", callback_data=f"manage_{r['name']}"))
        bot.send_message(message.chat.id, "Tus repositorios recientes:", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "❌ Error al listar repos. Revisa tu token.")

def process_new_repo(message):
    name = message.text.strip().replace(" ", "-")
    res = requests.post("[https://api.github.com/user/repos](https://api.github.com/user/repos)", headers=HEADERS, json={"name": name})
    if res.status_code == 201:
        bot.send_message(message.chat.id, f"✅ Repo `{name}` creado.", reply_markup=main_menu())
    else:
        bot.send_message(message.chat.id, f"❌ Error: {res.json().get('message')}")

# === DESCARGA DE ZIP ===
def send_zip(chat_id, repo_full_name):
    msg = bot.send_message(chat_id, f"⏳ Preparando ZIP de `{repo_full_name}`...")
    try:
        repo_info = requests.get(f"[https://api.github.com/repos/](https://api.github.com/repos/){repo_full_name}", headers=HEADERS).json()
        branch = repo_info.get('default_branch', 'main')
        zip_url = f"[https://github.com/](https://github.com/){repo_full_name}/archive/refs/heads/{branch}.zip"
        
        file_res = requests.get(zip_url, stream=True)
        if file_res.status_code == 200:
            bot.send_document(chat_id, file_res.raw, visible_file_name=f"{repo_full_name.split('/')[-1]}.zip")
            bot.delete_message(chat_id, msg.message_id)
        else:
            bot.edit_message_text("❌ Repositorio privado o no encontrado.", chat_id, msg.message_id)
    except Exception as e:
        bot.send_message(chat_id, f"💥 Error en descarga: {e}")

# === CALLBACKS (BOTONES) ===
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    if call.data.startswith("zip_"):
        repo = call.data.replace("zip_", "")
        send_zip(call.message.chat.id, repo)
    
    elif call.data.startswith("manage_"):
        repo = call.data.replace("manage_", "")
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📥 Descargar ZIP", callback_data=f"zip_{GH_USER}/{repo}"))
        markup.add(InlineKeyboardButton("🚀 Ejecutar Action", callback_data=f"listwf_{repo}"))
        markup.add(InlineKeyboardButton("🗑️ Borrar Repo", callback_data=f"confirm_del_{repo}"))
        bot.edit_message_text(f"Opciones para **{repo}**:", call.message.chat.id, call.message.message_id, 
                              reply_markup=markup, parse_mode="Markdown")

    elif call.data == "gemini_save":
        code = user_data.get(call.message.chat.id, {}).get('last_code', "")
        # Extraer bloques de código
        found_code = re.findall(r'```(?:\w+)?\n(.*?)\n```', code, re.DOTALL)
        final_content = found_code[0] if found_code else code
        user_data[call.message.chat.id]['temp_content'] = final_content
        
        msg = bot.send_message(call.message.chat.id, "📝 ¿Con qué nombre quieres guardarlo? (ej: script.py)")
        bot.register_next_step_handler(msg, save_file_step_2)

def save_file_step_2(message):
    filename = message.text.strip()
    user_data[message.chat.id]['temp_filename'] = filename
    
    res = requests.get(f"[https://api.github.com/user/repos?type=owner&sort=updated](https://api.github.com/user/repos?type=owner&sort=updated)", headers=HEADERS).json()
    markup = InlineKeyboardMarkup()
    for r in res[:6]:
        markup.add(InlineKeyboardButton(f"📁 {r['name']}", callback_data=f"finalsave_{r['name']}"))
    bot.send_message(message.chat.id, f"¿En qué repositorio guardo `{filename}`?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("finalsave_"))
def final_save(call):
    repo = call.data.replace("finalsave_", "")
    data = user_data.get(call.message.chat.id, {})
    
    content_b64 = base64.b64encode(data['temp_content'].encode()).decode()
    url = f"[https://api.github.com/repos/](https://api.github.com/repos/){GH_USER}/{repo}/contents/{data['temp_filename']}"
    
    payload = {"message": "Auto-save via Gemini Bot", "content": content_b64}
    res = requests.put(url, headers=HEADERS, json=payload)
    
    if res.status_code in [200, 201]:
        bot.edit_message_text(f"✅ Archivo guardado en `{repo}`", call.message.chat.id, call.message.message_id)
    else:
        bot.edit_message_text(f"❌ Error al guardar: {res.json().get('message')}", call.message.chat.id, call.message.message_id)

# === FLASK & POLLING ===
@app.route('/')
def health(): return "Bot Running", 200

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.polling(none_stop=True)
