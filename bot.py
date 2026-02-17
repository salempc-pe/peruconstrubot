
import os
import asyncio
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters


# --- Configuración ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
PORT = int(os.environ.get("PORT", 8080)) # Render asigna un puerto dinámico

# Configurar Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- Servidor Web "Dummy" para Render ---
# Render necesita un puerto abierto para saber que la app está viva.
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot Ingeniero: ¡Operativo y en Obra! 🏗️"

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

# --- Personalidad del Ingeniero ---
SYSTEM_PROMPT = """
Actúas como un Ingeniero Civil Senior residente de obra con amplia experiencia en construcción en el Perú. Tu comunicación es técnica, precisa y pragmática, orientada a la ejecución en obra y al cumplimiento del Reglamento Nacional de Edificaciones (RNE).

Tono y Estilo:
- Profesional y Directo: "Para esa viga de 5m requerimos un peralte de .50m".
- Terminología Peruana: Usa términos locales como vaciado (hormigonado), tarrajeo (enfoscado), solado (limpieza), afirmado, encofrado, chancado, hormigón (mezcla de arena y piedra), fierro (acero), estribos, zapatas.
- Rigor Normativo: Cita las normas del RNE (E.020, E.030, E.050, E.060, E.070) cuando sea relevante.
- Seguridad: Siempre recuerda que el predimensionamiento es una estimación y no reemplaza el cálculo estructural definitivo de un especialista.

Capacidades Principales:
1. Cuantificación de Materiales (Metrados): Calcula cantidades considerando desperdicios típicos (Concreto 5%, Ladrillo 5-10%).
2. Muros de Albañilería: Ladrillo KK 18 huecos (Soga ~39/m2, Cabeza ~70/m2).
3. Predimensionamiento Estructural (RNE E.060 / E.030):
   - Vigas: Peralte L/10 a L/12. Ancho mín 0.25m.
   - Losas: Espesor L/25.
   - Columnas: Pservicio / (n * f'c). n=0.45 (Interiores), 0.35 (Laterales), 0.25 (Esquineras).

Reglas de Operación:
- Validación: Si faltan datos (dimensiones, f'c), PREGUNTA antes de calcular.
- Seguridad: Advierte si algo suena peligroso.
- Formato: Datos de Entrada -> Cálculos -> Resultados (materiales) -> Notas.
"""

import requests
import json



async def get_gemini_response(user_message):
    clean_key = GEMINI_API_KEY.strip() if GEMINI_API_KEY else ""
    
    # 1. Intentar con gemini-1.5-flash en endpoint v1beta (Más capaz)
    models_to_try = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-pro",
        "gemini-1.0-pro"
    ]

    full_prompt = f"{SYSTEM_PROMPT}\n\nUsuario: {user_message}"

    for model_name in models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={clean_key}"
            payload = {
                "contents": [{"parts": [{"text": full_prompt}]}]
            }
            response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload)
            
            if response.status_code == 200:
                return response.json().get('candidates', [])[0].get('content', {}).get('parts', [])[0].get('text', 'Sin respuesta')
            
            # Si es 404, probamos el siguiente modelo
            if response.status_code != 404:
                logging.error(f"Error {model_name}: {response.text}")
                
        except Exception as e:
            logging.error(f"Excepción {model_name}: {e}")

    # 2. Si todo falla, pedir lista de modelos disponibles para depurar
    try:
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={clean_key}"
        list_resp = requests.get(list_url)
        if list_resp.status_code == 200:
            available = [m['name'] for m in list_resp.json().get('models', [])]
            return f"⚠️ Error de Configuración. Modelos disponibles para tu llave: {', '.join(available[:5])}..."
        else:
            return f"⚠️ Tu API Key no funciona o no tiene permisos. Error: {list_resp.status_code}"
    except:
        return "Error fatal. Verifica tu API Key en Google AI Studio."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text="👷‍♂️ Hola, soy tu Ingeniero Residente Virtual. \n\nEstoy listo para ayudarte con metrados, dosificaciones y consultas del RNE. ¿Qué vamos a construir hoy?"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    ai_response = await get_gemini_response(user_text)
    
    if ai_response:
        if len(ai_response) > 4000:
            for x in range(0, len(ai_response), 4000):
                await context.bot.send_message(chat_id=update.effective_chat.id, text=ai_response[x:x+4000], parse_mode='Markdown')
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=ai_response, parse_mode='Markdown')
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No pude generar una respuesta, intenta de nuevo.")

# --- Main ---
if __name__ == '__main__':
    # 1. Iniciar servidor web en un hilo separado (para Render)
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # 2. Iniciar Bot
    if TELEGRAM_TOKEN and GEMINI_API_KEY:
        print("👷‍♂️ Bot Ingeniero iniciado...")
        application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        application.add_handler(CommandHandler('start', start))
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        application.run_polling()
    else:
        print("Error: Faltan las llaves de API. El bot no puede iniciar.")
