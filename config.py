import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///monitored_services.db')
    ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')
    PORT = int(os.getenv('PORT', 10000))
    
    # Configuración de monitoreo
    DEFAULT_CHECK_INTERVAL = 300  # 5 minutos en segundos
    REQUEST_TIMEOUT = 10  # segundos