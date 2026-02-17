
# ⚠️ IMPORTANTE: Sigue esto para desplegar GRATIS

> **NOTA SOBRE TARJETAS**: Es posible que Render pida una tarjeta **solo para verificar que eres humano**, incluso para el plan gratuito ("Web Service"). 
> - Si te pide tarjeta, **asegúrate de que en la pantalla de pago el precio diga "Free" o "$0.00/mo"**.
> - Si dice "$7.00/mo", cámbialo a **Free** en la configuración de la instancia.

## Pasos RÁPIDOS

1.  **Sube estos cambios a GitHub** (bot.py, render.yaml, requirements.txt).
2.  Ve a Render Dashboard -> **New** -> **Blueprint**.
3.  Conecta el repo.
4.  Render leerá automáticamente el archivo `render.yaml` que ahora dice `type: web` y `plan: free`.
5.  Introduce tus variables (`TELEGRAM_TOKEN`, `GEMINI_API_KEY`).
6.  ¡Dale a **Apply**!

Tu bot arrancará. Recuerda que la versión gratuita "duerme" si no se usa por 15 minutos, pero debería responder cuando lo despiertes.
