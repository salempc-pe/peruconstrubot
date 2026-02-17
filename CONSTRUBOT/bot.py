
import os
import asyncio
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from google import genai
from google.genai import types

# --- Configuración ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Configurar Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

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

# --- Cliente de Gemini ---
client = genai.Client(api_key=GEMINI_API_KEY)

async def get_gemini_response(user_message):
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.3, # Baja temperatura para ser preciso
            ),
            contents=[user_message]
        )
        return response.text
    except Exception as e:
        logging.error(f"Error en Gemini API: {e}")
        return "Disculpa, hubo un error técnico calculando tu respuesta. Intenta de nuevo."

# --- Handlers de Telegram ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text="👷‍♂️ Hola, soy tu Ingeniero Residente Virtual. \n\nEstoy listo para ayudarte con metrados, dosificaciones y consultas del RNE. ¿Qué vamos a construir hoy?"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    # Mostrar que está "escribiendo..."
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Obtener respuesta de Gemini
    ai_response = await get_gemini_response(user_text)
    
    # Enviar respuesta
    if ai_response:
        # Dividir mensajes largos si exceden el límite de Telegram (4096 caracteres)
        if len(ai_response) > 4000:
            for x in range(0, len(ai_response), 4000):
                await context.bot.send_message(chat_id=update.effective_chat.id, text=ai_response[x:x+4000], parse_mode='Markdown')
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=ai_response, parse_mode='Markdown')
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No pude generar una respuesta, intenta de nuevo.")

# --- Main ---
if __name__ == '__main__':
    if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
        print("Error: Faltan las variables de entorno TELEGRAM_TOKEN o GEMINI_API_KEY")
        # No salimos con exit(1) para evitar crash loop en local si solo estamos probando, pero en prod es necesario.
        # En este caso, imprimimos advertencia.
    
    # Usamos ApplicationBuilder con el token
    if TELEGRAM_TOKEN:
        application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

        start_handler = CommandHandler('start', start)
        message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)

        application.add_handler(start_handler)
        application.add_handler(message_handler)

        print("👷‍♂️ Bot Ingeniero iniciado...")
        application.run_polling()
    else:
        print("No se pudo iniciar el bot: Falta TELEGRAM_TOKEN")
