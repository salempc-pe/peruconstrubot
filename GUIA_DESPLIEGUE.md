# Plan de Despliegue: Construction Bot (Render + Google Gemini)

## 1. Obtener Credenciales

Necesitas dos "llaves" secretas. Guárdalas bien, no las compartas:

1.  **Telegram Bot Token**:
    *   Abre Telegram y busca al usuario `@BotFather`.
    *   Escribe el comando `/newbot`.
    *   Ponle un nombre (ej. "Ingeniero Civil Bot") y un usuario (ej. `mi_ingeniero_bot`).
    *   Te dará un token largo que empieza con `7...`. **Cópialo**.

2.  **Google Gemini API Key**:
    *   Ve a [Google AI Studio](https://aistudio.google.com/).
    *   Clic en "Get API key" -> "Create API key in new project".
    *   **Copia la clave** (empieza con `AIza...`).

---

## 2. Preparar el Código

Ya tienes los archivos necesarios en esta carpeta:
*   `bot.py`: El cerebro del bot.
*   `requirements.txt`: Las librerías necesarias.
*   `render.yaml`: La configuración para la nube.

---

## 3. Subir a GitHub y Render

1.  Sube esta carpeta a un **repositorio de GitHub**.
2.  Entra a [Render.com](https://render.com/) y crea una cuenta.
3.  Haz clic en "New" -> "Blueprint".
4.  Conecta tu repositorio.
5.  Render detectará el archivo `render.yaml`.
6.  **IMPORTANTE**: Te pedirá las "Environment Variables" (Variables de Entorno). Introduce tus llaves:
    *   `TELEGRAM_TOKEN`
    *   `GEMINI_API_KEY`
7.  Haz clic en "Apply". ¡Tu bot estará vivo en unos minutos!
