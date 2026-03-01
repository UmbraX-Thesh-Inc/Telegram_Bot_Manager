from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from utils.github_api import (
    create_repository, list_repositories, search_repositories,
    fork_repository, delete_repository, get_repo_info
)
from utils.keyboards import (
    main_menu_keyboard, back_keyboard, visibility_keyboard,
    search_results_keyboard, format_repo_info, repo_actions_keyboard
)
from handlers.states import REPO_NAME, REPO_DESC, REPO_PRIVATE, FORK_URL, SEARCH_QUERY


# ─── CREAR REPO ────────────────────────────────────────────────────────────────

async def create_repo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    state = context.user_data.get('create_state', 'start')

    if query and query.data == 'create_repo':
        await query.answer()
        context.user_data['create_state'] = 'name'
        await query.edit_message_text(
            "➕ *Crear Nuevo Repositorio*\n\n"
            "📝 Escribe el *nombre* del repositorio:\n"
            "_(sin espacios, usa guiones)_",
            parse_mode='Markdown',
            reply_markup=back_keyboard()
        )
        return REPO_NAME

    msg = update.message

    if context.user_data.get('create_state') == 'name':
        context.user_data['repo_name'] = msg.text.strip().replace(' ', '-')
        context.user_data['create_state'] = 'desc'
        await msg.reply_text(
            f"✅ Nombre: `{context.user_data['repo_name']}`\n\n"
            "📄 Escribe la *descripción* del repo\n_(o escribe `skip` para omitir)_",
            parse_mode='Markdown'
        )
        return REPO_DESC

    elif context.user_data.get('create_state') == 'desc':
        desc = msg.text.strip()
        context.user_data['repo_desc'] = '' if desc.lower() == 'skip' else desc
        context.user_data['create_state'] = 'private'
        await msg.reply_text(
            "🔒 ¿El repositorio será *público* o *privado*?",
            parse_mode='Markdown',
            reply_markup=visibility_keyboard()
        )
        return REPO_PRIVATE

    elif query and query.data in ('public', 'private'):
        await query.answer()
        private = query.data == 'private'
        name = context.user_data.get('repo_name', 'mi-repo')
        desc = context.user_data.get('repo_desc', '')

        await query.edit_message_text("⏳ Creando repositorio...")
        result, status = create_repository(name, desc, private)

        if status == 201:
            vis = "🔒 Privado" if private else "🌐 Público"
            url = result.get('html_url', '')
            await query.edit_message_text(
                f"✅ *¡Repositorio creado exitosamente!*\n\n"
                f"📁 Nombre: `{name}`\n"
                f"👁️ Visibilidad: {vis}\n"
                f"🔗 [Abrir en GitHub]({url})",
                parse_mode='Markdown',
                reply_markup=repo_actions_keyboard(result.get('owner', {}).get('login', ''), name)
            )
        else:
            err = result.get('message', 'Error desconocido')
            await query.edit_message_text(
                f"❌ *Error al crear repo:*\n`{err}`",
                parse_mode='Markdown',
                reply_markup=main_menu_keyboard()
            )
        context.user_data.clear()
        return ConversationHandler.END


# ─── LISTAR REPOS ──────────────────────────────────────────────────────────────

async def list_repos_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1):
    query = update.callback_query
    if query:
        await query.answer()

    repos, status = list_repositories(page)

    if status != 200 or not repos:
        text = "❌ No se pudieron obtener los repositorios."
        if query:
            await query.edit_message_text(text, reply_markup=main_menu_keyboard())
        return

    keyboard = []
    for repo in repos:
        name = repo['name']
        private = '🔒' if repo['private'] else '🌐'
        stars = repo.get('stargazers_count', 0)
        keyboard.append([InlineKeyboardButton(
            f"{private} {name} ⭐{stars}",
            callback_data=f'repo_{repo["owner"]["login"]}_{name}'
        )])

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀️", callback_data=f'repos_page_{page-1}'))
    if len(repos) == 10:
        nav.append(InlineKeyboardButton("▶️", callback_data=f'repos_page_{page+1}'))
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("🔙 Menú Principal", callback_data='main_menu')])

    text = f"📁 *Mis Repositorios* — Página {page}"
    markup = InlineKeyboardMarkup(keyboard)

    if query:
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=markup)
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=markup)


# ─── BUSCAR REPOS ──────────────────────────────────────────────────────────────

async def search_repos_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query and query.data == 'search_repo':
        await query.answer()
        await query.edit_message_text(
            "🔍 *Buscar Repositorios en GitHub*\n\n"
            "Escribe tu búsqueda:\n_(ej: python bot, machine learning, etc.)_",
            parse_mode='Markdown',
            reply_markup=back_keyboard()
        )
        return SEARCH_QUERY

    msg = update.message
    search_text = msg.text.strip()
    await msg.reply_text("⏳ Buscando...")

    results, status = search_repositories(search_text)

    if status != 200:
        await msg.reply_text("❌ Error en la búsqueda.", reply_markup=main_menu_keyboard())
        return ConversationHandler.END

    items = results.get('items', [])
    if not items:
        await msg.reply_text("🔍 No se encontraron resultados.", reply_markup=main_menu_keyboard())
        return ConversationHandler.END

    total = results.get('total_count', 0)
    await msg.reply_text(
        f"🔍 *Resultados para:* `{search_text}`\n"
        f"📊 Total encontrados: `{total}`\n\n"
        f"*Top 10 resultados:*",
        parse_mode='Markdown',
        reply_markup=search_results_keyboard(items)
    )
    return ConversationHandler.END


# ─── FORK REPO ─────────────────────────────────────────────────────────────────

async def fork_repo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query and query.data == 'fork_repo':
        await query.answer()
        await query.edit_message_text(
            "🍴 *Forkear Repositorio*\n\n"
            "Envía la URL o `owner/repo`:\n"
            "_(ej: microsoft/vscode)_",
            parse_mode='Markdown',
            reply_markup=back_keyboard()
        )
        return FORK_URL

    msg = update.message
    text = msg.text.strip()

    # Parse owner/repo from URL or direct input
    if 'github.com/' in text:
        parts = text.rstrip('/').split('github.com/')[-1].split('/')
        owner, repo = parts[0], parts[1] if len(parts) > 1 else ''
    elif '/' in text:
        owner, repo = text.split('/', 1)
    else:
        await msg.reply_text("❌ Formato inválido. Usa `owner/repo`", parse_mode='Markdown')
        return FORK_URL

    await msg.reply_text(f"⏳ Forkeando `{owner}/{repo}`...")
    result, status = fork_repository(owner, repo)

    if status in (202, 200):
        url = result.get('html_url', '')
        await msg.reply_text(
            f"✅ *¡Fork creado exitosamente!*\n\n"
            f"📁 Repo: `{owner}/{repo}`\n"
            f"🔗 [Abrir Fork]({url})",
            parse_mode='Markdown',
            reply_markup=main_menu_keyboard()
        )
    else:
        err = result.get('message', 'Error desconocido')
        await msg.reply_text(
            f"❌ Error al forkear:\n`{err}`",
            parse_mode='Markdown',
            reply_markup=main_menu_keyboard()
        )
    return ConversationHandler.END


# ─── INFO REPO ─────────────────────────────────────────────────────────────────

async def repo_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, owner: str, repo: str):
    query = update.callback_query
    if query:
        await query.answer()

    result, status = get_repo_info(owner, repo)

    if status != 200:
        text = f"❌ No se pudo obtener info de `{owner}/{repo}`"
        if query:
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=main_menu_keyboard())
        return

    text = format_repo_info(result)
    markup = repo_actions_keyboard(owner, repo)

    if query:
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=markup)
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=markup)


# ─── DELETE REPO ───────────────────────────────────────────────────────────────

async def delete_repo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, repo: str = None):
    query = update.callback_query
    if query:
        await query.answer()

    if repo is None:
        repos, _ = list_repositories()
        keyboard = []
        for r in repos:
            keyboard.append([InlineKeyboardButton(
                f"🗑️ {r['name']}",
                callback_data=f'delconfirm_{r["name"]}'
            )])
        keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data='main_menu')])
        await query.edit_message_text(
            "🗑️ *Eliminar Repositorio*\n\n"
            "⚠️ Selecciona el repo a eliminar:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    status = delete_repository(repo)
    if status == 204:
        await query.edit_message_text(
            f"✅ Repositorio `{repo}` eliminado correctamente.",
            parse_mode='Markdown',
            reply_markup=main_menu_keyboard()
        )
    else:
        await query.edit_message_text(
            f"❌ Error al eliminar `{repo}`. Código: `{status}`",
            parse_mode='Markdown',
            reply_markup=main_menu_keyboard()
        )
