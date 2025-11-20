from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from database import DatabaseManager
from monitoring import ServiceMonitor
from config import Config
import re

class MonitoringBot:
    def __init__(self):
        self.db = DatabaseManager()
        self.monitor = ServiceMonitor()
        self.application = None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start - Mensaje de bienvenida"""
        chat_id = update.effective_chat.id
        self.db.clear_user_session(chat_id)
        
        keyboard = [
            ["➕ Agregar Servicio", "📋 Mis Servicios"],
            ["⚙️ Configurar Intervalo", "🗑️ Eliminar Servicio"],
            ["🔍 Verificar Ahora", "ℹ️ Ayuda"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        welcome_text = (
            "🤖 **Bot de Monitoreo de Servicios**\n\n"
            "Puedo monitorear el estado de tus servicios web y notificarte "
            "cuando estén caídos o se recuperen.\n\n"
            "**Comandos disponibles:**\n"
            "• ➕ Agregar Servicio: Añade una nueva URL para monitorear\n"
            "• 📋 Mis Servicios: Lista todos tus servicios monitoreados\n"
            "• ⚙️ Configurar Intervalo: Cambia el tiempo de verificación\n"
            "• 🗑️ Eliminar Servicio: Elimina un servicio del monitoreo\n"
            "• 🔍 Verificar Ahora: Verifica el estado actual de todos los servicios\n\n"
            "¡Selecciona una opción del menú para comenzar!"
        )
        
        await update.message.reply_text(
            welcome_text, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def handle_add_service(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inicia el proceso para agregar un servicio"""
        chat_id = update.effective_chat.id
        self.db.set_user_action(chat_id, 'awaiting_service_name')
        
        await update.message.reply_text(
            "📝 **Agregar Nuevo Servicio**\n\n"
            "Por favor, envía el **nombre** para tu servicio:\n"
            "(Ejemplo: 'Mi API Principal')"
        )
    
    async def handle_my_services(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Muestra la lista de servicios del usuario"""
        chat_id = update.effective_chat.id
        services = self.db.get_user_services(chat_id)
        
        if not services:
            await update.message.reply_text(
                "📭 No tienes servicios monitoreados.\n"
                "Usa '➕ Agregar Servicio' para comenzar."
            )
            return
        
        message = "📋 **Tus Servicios Monitoreados:**\n\n"
        for service in services:
            status_emoji = "✅" if service.is_active else "❌"
            message += (
                f"{status_emoji} **{service.name}**\n"
                f"🔗 {service.url}\n"
                f"⏰ Intervalo: {service.check_interval // 60} minutos\n"
                f"📅 Última verificación: {service.last_checked.strftime('%Y-%m-%d %H:%M') if service.last_checked else 'Nunca'}\n\n"
            )
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def handle_check_now(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Verifica todos los servicios inmediatamente"""
        chat_id = update.effective_chat.id
        
        await update.message.reply_text("🔍 Verificando el estado de tus servicios...")
        
        # Verificar servicios del usuario
        user_services = self.db.get_user_services(chat_id)
        if not user_services:
            await update.message.reply_text("No tienes servicios para verificar.")
            return
        
        for service in user_services:
            status, status_code = self.monitor.check_service(service)
            
            if status:
                message = f"✅ **{service.name}** - ACTIVO (Código: {status_code})"
            else:
                message = f"❌ **{service.name}** - INACTIVO"
            
            await update.message.reply_text(message, parse_mode='Markdown')
    
    async def handle_configure_interval(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Configura el intervalo de verificación para un servicio"""
        chat_id = update.effective_chat.id
        services = self.db.get_user_services(chat_id)
        
        if not services:
            await update.message.reply_text(
                "No tienes servicios para configurar.\n"
                "Primero agrega un servicio con '➕ Agregar Servicio'."
            )
            return
        
        # Crear teclado inline con los servicios
        keyboard = []
        for service in services:
            keyboard.append([
                InlineKeyboardButton(
                    f"{service.name} ({service.check_interval // 60} min)", 
                    callback_data=f"config_{service.id}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⚙️ **Configurar Intervalo de Verificación**\n\n"
            "Selecciona el servicio que quieres configurar:",
            reply_markup=reply_markup
        )
    
    async def handle_delete_service(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Elimina un servicio del monitoreo"""
        chat_id = update.effective_chat.id
        services = self.db.get_user_services(chat_id)
        
        if not services:
            await update.message.reply_text(
                "No tienes servicios para eliminar.\n"
                "Primero agrega un servicio con '➕ Agregar Servicio'."
            )
            return
        
        # Crear teclado inline con los servicios
        keyboard = []
        for service in services:
            keyboard.append([
                InlineKeyboardButton(
                    f"🗑️ {service.name}", 
                    callback_data=f"delete_{service.id}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🗑️ **Eliminar Servicio**\n\n"
            "Selecciona el servicio que quieres eliminar:",
            reply_markup=reply_markup
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja mensajes de texto normales"""
        chat_id = update.effective_chat.id
        user_message = update.message.text
        session = self.db.get_user_session(chat_id)
        
        if not session:
            await self.show_main_menu(update)
            return
        
        if session.current_action == 'awaiting_service_name':
            self.db.set_user_action(chat_id, 'awaiting_service_url', user_message)
            await update.message.reply_text(
                "👍 Nombre guardado.\n\n"
                "Ahora envía la **URL** del servicio:\n"
                "(Ejemplo: https://mi-servicio.com)"
            )
        
        elif session.current_action == 'awaiting_service_url':
            service_name = session.temp_data
            url = user_message.strip()
            
            # Validar URL
            if not self.is_valid_url(url):
                await update.message.reply_text(
                    "❌ URL inválida. Por favor, envía una URL válida:\n"
                    "(Ejemplo: https://mi-servicio.com)"
                )
                return
            
            try:
                # Agregar servicio a la base de datos
                service = self.db.add_service(
                    name=service_name,
                    url=url,
                    chat_id=chat_id,
                    check_interval=300  # 5 minutos por defecto
                )
                
                self.db.clear_user_session(chat_id)
                
                await update.message.reply_text(
                    f"✅ **Servicio agregado exitosamente!**\n\n"
                    f"**Nombre:** {service.name}\n"
                    f"**URL:** {service.url}\n"
                    f"**Intervalo:** {service.check_interval // 60} minutos\n\n"
                    f"Ahora monitorearé este servicio cada {service.check_interval // 60} minutos.",
                    parse_mode='Markdown'
                )
                
            except Exception as e:
                await update.message.reply_text(
                    f"❌ Error al agregar el servicio: {str(e)}"
                )
        
        elif session.current_action == 'awaiting_interval':
            try:
                service_id = int(session.temp_data)
                interval_minutes = int(user_message)
                interval_seconds = interval_minutes * 60
                
                if interval_seconds < 60:
                    await update.message.reply_text(
                        "❌ El intervalo mínimo es 1 minuto."
                    )
                    return
                
                success = self.db.update_service_interval(service_id, chat_id, interval_seconds)
                
                if success:
                    self.db.clear_user_session(chat_id)
                    await update.message.reply_text(
                        f"✅ Intervalo actualizado a {interval_minutes} minutos."
                    )
                else:
                    await update.message.reply_text(
                        "❌ No se pudo actualizar el intervalo."
                    )
                    
            except ValueError:
                await update.message.reply_text(
                    "❌ Por favor, envía un número válido de minutos."
                )
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja las acciones de los botones inline"""
        query = update.callback_query
        await query.answer()
        
        chat_id = query.message.chat_id
        data = query.data
        
        if data.startswith('config_'):
            service_id = int(data.split('_')[1])
            self.db.set_user_action(chat_id, 'awaiting_interval', str(service_id))
            
            await query.edit_message_text(
                "⏰ **Configurar Intervalo**\n\n"
                "Envía el nuevo intervalo en **minutos**:\n"
                "(Ejemplo: 5 para 5 minutos)"
            )
        
        elif data.startswith('delete_'):
            service_id = int(data.split('_')[1])
            success = self.db.delete_service(service_id, chat_id)
            
            if success:
                await query.edit_message_text("✅ Servicio eliminado exitosamente.")
            else:
                await query.edit_message_text("❌ Error al eliminar el servicio.")
    
    async def show_main_menu(self, update: Update):
        """Muestra el menú principal"""
        keyboard = [
            ["➕ Agregar Servicio", "📋 Mis Servicios"],
            ["⚙️ Configurar Intervalo", "🗑️ Eliminar Servicio"],
            ["🔍 Verificar Ahora", "ℹ️ Ayuda"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "Selecciona una opción del menú:",
            reply_markup=reply_markup
        )
    
    def is_valid_url(self, url):
        """Valida si una URL tiene formato válido"""
        regex = re.compile(
            r'^(?:http|ftp)s?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return re.match(regex, url) is not None
    
    def setup_handlers(self):
        """Configura todos los manejadores del bot"""
        # Comandos
        self.application.add_handler(CommandHandler("start", self.start))
        
        # Handlers para botones del teclado
        self.application.add_handler(MessageHandler(filters.Text("➕ Agregar Servicio"), self.handle_add_service))
        self.application.add_handler(MessageHandler(filters.Text("📋 Mis Servicios"), self.handle_my_services))
        self.application.add_handler(MessageHandler(filters.Text("⚙️ Configurar Intervalo"), self.handle_configure_interval))
        self.application.add_handler(MessageHandler(filters.Text("🗑️ Eliminar Servicio"), self.handle_delete_service))
        self.application.add_handler(MessageHandler(filters.Text("🔍 Verificar Ahora"), self.handle_check_now))
        self.application.add_handler(MessageHandler(filters.Text("ℹ️ Ayuda"), self.start))
        
        # Handler para callbacks de botones inline
        self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))
        
        # Handler para mensajes de texto
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    def run(self):
        """Inicia el bot"""
        self.application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
        self.setup_handlers()
        self.application.run_polling()