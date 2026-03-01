from telegram import Update
from telegram.ext import ContextTypes
from utils.keyboards import main_menu_keyboard
from utils.github_api import get_user_info
from config.settings import GITHUB_USERNAME


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    gh_info, _ = get_user_info()
    gh_name = gh_info.get('login', GITHUB_USERNAME)
    gh_repos = gh_info.get('public_repos', 0)
    
    text = (
        f"╔══════════════════════════╗\n"
        f"  🤖 *GitHub Manager Bot*\n"
        f"╚══════════════════════════╝\n\n"
        f"👋 ¡Hola, *{user.first_name}*!\n\n"
        f"🐙 GitHub: `@{gh_name}`\n"
        f"📁 Repositorios: `{gh_repos}`\n\n"
        f"*¿Qué deseas hacer hoy?*"
    )
    
    await update.message.reply_text(
        text,
        parse_mode='Markdown',
        reply_markup=main_menu_keyboard()
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "╔══════════════════════════╗\n"
        "  ❓ *Ayuda - GitHub Bot*\n"
        "╚══════════════════════════╝\n\n"
        "📋 *Funciones disponibles:*\n\n"
        "📁 *Mis Repos* — Lista tus repositorios\n"
        "➕ *Crear Repo* — Crea un nuevo repositorio\n"
        "🔍 *Buscar Repos* — Busca en GitHub\n"
        "🍴 *Forkear* — Haz fork de cualquier repo\n"
        "📤 *Subir Archivos* — Sube archivos a un repo\n"
        "📥 *Descargar ZIP* — Descarga repos como ZIP\n"
        "✏️ *Editar* — Edita archivos de tus repos\n"
        "🗑️ *Eliminar* — Elimina repositorios\n"
        "🤖 *IA Gemini* — Chat con inteligencia artificial\n"
        "🌐 *Descargar URL* — Descarga archivos por link\n\n"
        "💡 Usa /start para volver al menú principal"
    )
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=main_menu_keyboard())
