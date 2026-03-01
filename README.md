# 🤖 GitHub Manager Bot para Telegram

Bot completo de Telegram para gestionar GitHub con IA integrada (Gemini).

## ✨ Funciones

| Función | Descripción |
|---------|-------------|
| 📁 Mis Repos | Lista y navega tus repositorios |
| ➕ Crear Repo | Crea repos públicos o privados |
| 🔍 Buscar | Busca repositorios en GitHub |
| 🍴 Fork | Haz fork de cualquier repositorio |
| 📤 Subir | Sube archivos o ZIPs completos |
| 📥 Descargar ZIP | Descarga repos directamente al chat |
| ✏️ Editar | Edita archivos, descripciones, branches |
| 🗑️ Eliminar | Elimina repositorios con confirmación |
| 🤖 IA Gemini | Chat inteligente para ayuda técnica |
| 🌐 Descargar URL | Descarga archivos por enlace directo |
| 👤 Perfil | Ver info de tu cuenta GitHub |

## 📁 Estructura del Proyecto

```
telegram-github-bot/
├── main.py              # Punto de entrada
├── requirements.txt     # Dependencias
├── render.yaml          # Configuración Render.com
├── .env.example         # Template de variables
├── config/
│   ├── __init__.py
│   └── settings.py      # Configuración y variables
├── handlers/
│   ├── __init__.py
│   ├── states.py        # Estados de conversación
│   ├── start.py         # /start y /help
│   ├── callbacks.py     # Router de callbacks
│   ├── github_repos.py  # Crear/listar/buscar/fork/delete
│   ├── github_upload.py # Subir archivos
│   ├── github_download.py # Descargar ZIP y archivos
│   ├── github_edit.py   # Editar repos y archivos
│   ├── ai_handler.py    # Chat con Gemini
│   └── url_download.py  # Descarga por URL
└── utils/
    ├── __init__.py
    ├── github_api.py    # Wrapper de la API de GitHub
    └── keyboards.py     # Teclados y mensajes UI
```

## 🚀 Deploy en Render.com

### Paso 1: Obtener las Keys

**Telegram Bot Token:**
1. Habla con [@BotFather](https://t.me/BotFather)
2. `/newbot` → elige nombre y username
3. Copia el token

**Tu ID de Telegram:**
1. Habla con [@userinfobot](https://t.me/userinfobot)
2. Copia tu ID numérico

**GitHub Token:**
1. GitHub.com → Settings → Developer settings
2. Personal access tokens → Tokens (classic)
3. Generate new token con permisos: `repo`, `delete_repo`, `user`

**Gemini API Key:**
1. Ve a [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create API Key

### Paso 2: Deploy en Render

1. Sube el proyecto a GitHub
2. Ve a [render.com](https://render.com) → New → Web Service
3. Conecta tu repo de GitHub
4. Configura las variables de entorno:

```
BOT_TOKEN=tu_token
USER_ID_1=tu_id
USER_ID_2=id_del_segundo_usuario
GITHUB_TOKEN=ghp_...
GITHUB_USERNAME=tu_usuario
GEMINI_API_KEY=AIza...
```

5. Build Command: `pip install -r requirements.txt`
6. Start Command: `python main.py`
7. Click **Create Web Service**

### Paso 3: Verificar

Escribe `/start` en tu bot de Telegram. ¡Listo!

## 🔒 Seguridad

- Solo los 2 IDs configurados pueden usar el bot
- Todos los intentos no autorizados son bloqueados
- Los tokens nunca se exponen en los mensajes

## 📦 Instalación Local

```bash
git clone <tu-repo>
cd telegram-github-bot
pip install -r requirements.txt
cp .env.example .env
# Edita .env con tus valores
python main.py
```
