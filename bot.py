
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

# --- Lista de Precios Base (Referenciales Lima 2025 - Soles) ---
# Puedes editar estos valores directamente aquí cuando cambien los precios en el mercado.
PRECIOS_BASE = """
- Cemento (Bolsa 42.5kg): S/ 28.50
- Arena Gruesa (m3): S/ 60.00
- Piedra Chancada 1/2" (m3): S/ 65.00
- Hormigón (m3): S/ 50.00
- Ladrillo KK 18 huecos (unidad): S/ 0.95
- Ladrillo Pandereta (unidad): S/ 0.70
- Ladrillo Techo 15x30x30 (unidad): S/ 2.80
- Fierro 3/8" (varilla 9m): S/ 18.00
- Fierro 1/2" (varilla 9m): S/ 32.00
- Fierro 5/8" (varilla 9m): S/ 52.00
- Alambre recocido #16 (kg): S/ 5.50
- Agua (m3 cisterna): S/ 15.00
- Mano de Obra (Operario + Peón / día global - ref): S/ 250.00
"""

# --- Personalidad del Ingeniero ---
SYSTEM_PROMPT = f"""
Actúas como un Ingeniero Civil Senior residente de obra con amplia experiencia en construcción en el Perú. Tu misión es calcular metrados exactos, estimar costos y dar recomendaciones técnicas según el Reglamento Nacional de Edificaciones (RNE).

Tono y Estilo:
- Profesional y Directo: "Para esa columna de 30x30, el acero es insuficiente".
- Terminología Peruana: Usa términos locales (vaciado, tarrajeo, solado, afirmado, encofrado, chancado, hormigón, fierro, estribos).
- Formato de Salida: SIEMPRE usa tablas Markdown para metrados y presupuestos.

--- CONOCIMIENTO TÉCNICO (RNE) ---

1. CONCRETO (Dosificación por m3 - f'c 210 kg/cm2):
   - Cemento: 9.7 bolsas (aprox 9-10)
   - Arena Gruesa: 0.52 m3
   - Piedra Chancada: 0.53 m3
   - Agua: 0.186 m3
   - Desperdicio sugerido: 5%

2. MUROS DE ALBAÑILERÍA (Ladrillo KK 18 huecos - 9x13x24):
   - Soga (espesor 13cm): 39 ladrillos/m2 | Mortero 1:5: 0.025 m3/m2
   - Cabeza (espesor 24cm): 70 ladrillos/m2 | Mortero 1:5: 0.050 m3/m2
   - Desperdicio sugerido: Ladrillo 5%, Mortero 10%

3. ACERO (Cuantías referenciales):
   - Zapatas: ~45 kg/m3
   - Vigas: ~90 kg/m3
   - Columnas: ~110-140 kg/m3
   - Losas Aligeradas: ~5-7 kg/m2
   - Losa Maciza: ~60 kg/m3

4. PRECIOS REFERENCIALES (Soles - Lima 2025):
   {PRECIOS_BASE}
   *Nota: Advierte siempre que estos precios son referenciales y pueden variar por zona/proveedor.*

--- REGLAS DE RESPUESTA ---

1. **Si te piden cantidad de material**:
   - Calcula el volumen/área real.
   - Aplica el desperdicio (indícalo).
   - Muestra la tabla de materiales con: [Item, Cantidad, Unidad, Precio Unit, Parcial].
   - Suma el Costo Total Estimado.

2. **Si te piden predimensionamiento**:
   - Viga: Peralte H = L/10 a L/12. Base B >= 0.25m (o H/2).
   - Losa Aligerada: H = L/25.
   - Columna: Área = P_servicio / (n * f'c).
   - Zapatas: Area = P_servicio / Q_admisible.
   - *DISCLAIMER OBLIGATORIO*: "⚠️ Esto es un predimensionamiento. El diseño final debe ser realizado por un Ingeniero Estructural colegiado."

3. **Si faltan datos**:
   - Asume valores estándar del RNE (f'c 210, H=2.40m, Sobrecarga vivienda 200kg/m2) pero AVÍSALO.
"""

import requests
import json




async def get_gemini_response(user_message):
    clean_key = GEMINI_API_KEY.strip() if GEMINI_API_KEY else ""
    
    # Lista de modelos confirmados en tu cuenta (Rotación para evitar límites)
    models = [
        "gemini-2.5-flash",
        "gemini-2.0-flash-001", 
        "gemini-2.0-flash",
        "gemini-2.0-flash-exp"  # Respaldo experimental
    ]
    
    full_prompt = f"{SYSTEM_PROMPT}\n\nUsuario: {user_message}"
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {"temperature": 0.3},
        # Configuramos seguridad permisiva para evitar bloqueos falsos en temas técnicos
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }
    
    last_error = ""

    for model in models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={clean_key}"
            # Timeout de 15 segundos para no colgar a Telegram
            response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                # Verificar si hay candidatos válidos
                if 'candidates' in data and data['candidates']:
                    candidate = data['candidates'][0]
                    # Verificar si fue bloqueado
                    if candidate.get('finishReason') == 'SAFETY':
                        last_error = "⚠️ Respuesta bloqueada por filtro de seguridad de Google."
                        continue # Intentar otro modelo
                        
                    content_parts = candidate.get('content', {}).get('parts', [])
                    if content_parts:
                        return content_parts[0].get('text', 'Sin texto.')
                
                last_error = "La IA devolvió una respuesta vacía (posible error interno)."
                logging.warning(f"{model} respuesta vacía: {data}")

            elif response.status_code == 429:
                logging.warning(f"Quota {model} excedida.")
                last_error = "Tráfico alto (429). Intentando otro servidor..."
                continue
            else:
                logging.error(f"Error {model} ({response.status_code}): {response.text}")
                last_error = f"Error {response.status_code}."
                
        except requests.exceptions.Timeout:
            logging.error(f"Timeout en {model}")
            last_error = "Tiempo de espera agotado."
        except Exception as e:
            logging.error(f"Excepción {model}: {e}")
            last_error = str(e)

    return f"⚠️ No pude responder. Causa: {last_error}\nPrueba reformular la pregunta."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text="👷‍♂️ **Ingeniero Residente v2.0**\n\nListo para metrados y costos (Lima 2025).\nEjemplo: _'Costo de muro soga 3x2m'_"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_text = update.message.text
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        ai_response = await get_gemini_response(user_text)
        
        if ai_response:
            # Cortar mensajes muy largos
            if len(ai_response) > 4000:
                for x in range(0, len(ai_response), 4000):
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=ai_response[x:x+4000], parse_mode='Markdown')
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=ai_response, parse_mode='Markdown')
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Error crítico: Respuesta nula.")
            
    except Exception as e:
        logging.error(f"Error en handler: {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Ocurrió un error interno en el bot. Intenta más tarde.")

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
