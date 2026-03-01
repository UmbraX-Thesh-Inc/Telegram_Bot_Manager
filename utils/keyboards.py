from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📁 Mis Repos", callback_data='list_repos'),
            InlineKeyboardButton("➕ Crear Repo", callback_data='create_repo')
        ],
        [
            InlineKeyboardButton("🔍 Buscar Repos", callback_data='search_repo'),
            InlineKeyboardButton("🍴 Forkear Repo", callback_data='fork_repo')
        ],
        [
            InlineKeyboardButton("📤 Subir Archivos", callback_data='upload_repo'),
            InlineKeyboardButton("📥 Descargar ZIP", callback_data='download_zip')
        ],
        [
            InlineKeyboardButton("✏️ Editar Repo", callback_data='edit_repo'),
            InlineKeyboardButton("🗑️ Eliminar Repo", callback_data='delete_repo_menu')
        ],
        [
            InlineKeyboardButton("🤖 IA Gemini", callback_data='ai_chat'),
            InlineKeyboardButton("🌐 Descargar URL", callback_data='url_download')
        ],
        [
            InlineKeyboardButton("👤 Mi Perfil GitHub", callback_data='gh_profile'),
            InlineKeyboardButton("❓ Ayuda", callback_data='help')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def back_keyboard(back_data='main_menu'):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menú Principal", callback_data=back_data)]])


def repo_actions_keyboard(owner: str, repo: str):
    keyboard = [
        [
            InlineKeyboardButton("📥 Descargar ZIP", callback_data=f'zip_{owner}_{repo}'),
            InlineKeyboardButton("📄 Ver Archivos", callback_data=f'files_{owner}_{repo}')
        ],
        [
            InlineKeyboardButton("✏️ Editar Desc", callback_data=f'editdesc_{repo}'),
            InlineKeyboardButton("🌿 Branches", callback_data=f'branches_{owner}_{repo}')
        ],
        [InlineKeyboardButton("🔙 Menú Principal", callback_data='main_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)


def visibility_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🌐 Público", callback_data='public'),
            InlineKeyboardButton("🔒 Privado", callback_data='private')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def confirm_keyboard(action: str):
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirmar", callback_data=f'confirm_{action}'),
            InlineKeyboardButton("❌ Cancelar", callback_data='main_menu')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def paginate_keyboard(items: list, page: int, total_pages: int, prefix: str):
    keyboard = []
    for item in items:
        keyboard.append([InlineKeyboardButton(f"📁 {item}", callback_data=f'{prefix}_{item}')])
    
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀️ Anterior", callback_data=f'page_{prefix}_{page-1}'))
    if page < total_pages:
        nav.append(InlineKeyboardButton("▶️ Siguiente", callback_data=f'page_{prefix}_{page+1}'))
    if nav:
        keyboard.append(nav)
    
    keyboard.append([InlineKeyboardButton("🔙 Menú Principal", callback_data='main_menu')])
    return InlineKeyboardMarkup(keyboard)


def search_results_keyboard(repos: list):
    keyboard = []
    for repo in repos[:10]:
        name = repo.get('full_name', 'Unknown')
        stars = repo.get('stargazers_count', 0)
        keyboard.append([
            InlineKeyboardButton(
                f"⭐{stars} {name}",
                callback_data=f'repoinfo_{name.replace("/", "_")}'
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 Menú Principal", callback_data='main_menu')])
    return InlineKeyboardMarkup(keyboard)


def format_repo_info(repo: dict) -> str:
    name = repo.get('full_name', 'N/A')
    desc = repo.get('description', 'Sin descripción') or 'Sin descripción'
    stars = repo.get('stargazers_count', 0)
    forks = repo.get('forks_count', 0)
    lang = repo.get('language', 'N/A') or 'N/A'
    private = '🔒 Privado' if repo.get('private') else '🌐 Público'
    url = repo.get('html_url', '')
    updated = repo.get('updated_at', 'N/A')[:10]
    size = repo.get('size', 0)

    return (
        f"╔══════════════════════╗\n"
        f"  📁 *{name}*\n"
        f"╚══════════════════════╝\n\n"
        f"📝 {desc}\n\n"
        f"⭐ Stars: `{stars}` | 🍴 Forks: `{forks}`\n"
        f"💻 Lenguaje: `{lang}`\n"
        f"👁️ Visibilidad: {private}\n"
        f"📦 Tamaño: `{size} KB`\n"
        f"📅 Actualizado: `{updated}`\n"
        f"🔗 [Abrir en GitHub]({url})"
    )
