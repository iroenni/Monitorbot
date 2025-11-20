import requests
from datetime import datetime
from database import DatabaseManager
from config import Config

class ServiceMonitor:
    def __init__(self):
        self.db = DatabaseManager()
        self.timeout = Config.REQUEST_TIMEOUT
    
    def check_service(self, service):
        """Verifica el estado de un servicio individual"""
        try:
            # Realizar petición HEAD para mayor eficiencia
            response = requests.head(
                service.url, 
                timeout=self.timeout,
                allow_redirects=True
            )
            is_up = response.status_code < 400
            status_code = response.status_code
        except requests.exceptions.SSLError:
            # Si falla SSL, intentar con HTTP
            try:
                http_url = service.url.replace('https://', 'http://')
                response = requests.head(
                    http_url, 
                    timeout=self.timeout,
                    allow_redirects=True
                )
                is_up = response.status_code < 400
                status_code = response.status_code
            except Exception:
                is_up = False
                status_code = 0
        except Exception:
            is_up = False
            status_code = 0
        
        # Actualizar base de datos
        self.db.update_service_status(service.id, is_up, datetime.now())
        
        return is_up, status_code
    
    def check_all_services(self, bot=None):
        """Verifica todos los servicios y envía notificaciones si es necesario"""
        services = self.db.get_all_services()
        results = []
        
        for service in services:
            try:
                previous_status = service.last_status
                current_status, status_code = self.check_service(service)
                
                # Enviar notificación si el estado cambió
                if bot and previous_status is not None and previous_status != current_status:
                    self.send_status_notification(bot, service, current_status, status_code)
                
                results.append({
                    'service': service,
                    'status': current_status,
                    'status_code': status_code
                })
                
            except Exception as e:
                print(f"Error checking service {service.name}: {e}")
                results.append({
                    'service': service,
                    'status': False,
                    'status_code': 0,
                    'error': str(e)
                })
        
        return results
    
    def send_status_notification(self, bot, service, current_status, status_code):
        """Envía notificación de cambio de estado"""
        chat_id = service.chat_id
        
        if current_status:
            message = (
                f"✅ **SERVICIO RECUPERADO**\n"
                f"**Nombre:** {service.name}\n"
                f"**URL:** {service.url}\n"
                f"**Código de estado:** {status_code}\n"
                f"**Hora:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            message = (
                f"🚨 **SERVICIO CAÍDO**\n"
                f"**Nombre:** {service.name}\n"
                f"**URL:** {service.url}\n"
                f"**Código de estado:** {status_code if status_code else 'N/A'}\n"
                f"**Hora:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        
        try:
            bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
        except Exception as e:
            print(f"Error sending notification to {chat_id}: {e}")