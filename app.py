from flask import Flask, request, jsonify
from bot import MonitoringBot
from monitoring import ServiceMonitor
from database import DatabaseManager
from config import Config
import threading
import time
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
bot = MonitoringBot()
monitor = ServiceMonitor()
db = DatabaseManager()

# Configurar el scheduler para monitoreo periódico
scheduler = BackgroundScheduler()

def scheduled_monitoring():
    """Tarea programada para monitorear servicios"""
    with app.app_context():
        try:
            print("🔍 Ejecutando monitoreo programado...")
            if bot.application:
                monitor.check_all_services(bot.application.bot)
            else:
                print("Bot no inicializado, omitiendo monitoreo...")
        except Exception as e:
            print(f"Error en monitoreo programado: {e}")

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "service": "Telegram Monitoring Bot",
        "message": "Bot de monitoreo de servicios ejecutándose correctamente"
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook para Telegram (opcional, si se usa webhook en lugar de polling)"""
    update = request.get_json()
    if bot.application:
        bot.application.update_queue.put(update)
    return jsonify({"status": "ok"})

@app.route('/check-now', methods=['POST'])
def check_now():
    """Endpoint para forzar verificación inmediata"""
    try:
        results = monitor.check_all_services(bot.application.bot if bot.application else None)
        return jsonify({
            "status": "success",
            "checked_services": len(results),
            "results": [{
                "service": result['service'].name,
                "status": result['status'],
                "status_code": result.get('status_code', 0)
            } for result in results]
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def start_bot():
    """Inicia el bot de Telegram en un hilo separado"""
    print("🤖 Iniciando bot de Telegram...")
    bot.run()

def start_scheduler():
    """Inicia el scheduler para monitoreo periódico"""
    print("⏰ Iniciando scheduler de monitoreo...")
    
    # Verificar servicios cada minuto
    scheduler.add_job(
        func=scheduled_monitoring,
        trigger='interval',
        minutes=1,
        id='service_monitoring'
    )
    
    scheduler.start()
    print("✅ Scheduler iniciado correctamente")

if __name__ == '__main__':
    # Inicializar base de datos
    from models import init_db
    init_db()
    print("✅ Base de datos inicializada")
    
    # Iniciar scheduler
    start_scheduler()
    
    # Iniciar bot en un hilo separado
    bot_thread = threading.Thread(target=start_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Iniciar servidor Flask
    print(f"🌐 Iniciando servidor web en puerto {Config.PORT}...")
    app.run(host='0.0.0.0', port=Config.PORT, debug=False)