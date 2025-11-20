from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, MonitoredService, UserSession
from config import Config

class DatabaseManager:
    def __init__(self):
        self.engine = create_engine(Config.DATABASE_URL)
        self.Session = sessionmaker(bind=self.engine)
        
    def add_service(self, name, url, chat_id, check_interval=300):
        session = self.Session()
        try:
            service = MonitoredService(
                name=name,
                url=url,
                chat_id=str(chat_id),
                check_interval=check_interval
            )
            session.add(service)
            session.commit()
            return service
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_user_services(self, chat_id):
        session = self.Session()
        try:
            services = session.query(MonitoredService).filter(
                MonitoredService.chat_id == str(chat_id)
            ).all()
            return services
        finally:
            session.close()
    
    def delete_service(self, service_id, chat_id):
        session = self.Session()
        try:
            service = session.query(MonitoredService).filter(
                MonitoredService.id == service_id,
                MonitoredService.chat_id == str(chat_id)
            ).first()
            if service:
                session.delete(service)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def update_service_interval(self, service_id, chat_id, new_interval):
        session = self.Session()
        try:
            service = session.query(MonitoredService).filter(
                MonitoredService.id == service_id,
                MonitoredService.chat_id == str(chat_id)
            ).first()
            if service:
                service.check_interval = new_interval
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_all_services(self):
        session = self.Session()
        try:
            services = session.query(MonitoredService).all()
            return services
        finally:
            session.close()
    
    def update_service_status(self, service_id, status, last_checked):
        session = self.Session()
        try:
            service = session.query(MonitoredService).filter(
                MonitoredService.id == service_id
            ).first()
            if service:
                service.last_status = status
                service.last_checked = last_checked
                service.is_active = status
                session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def set_user_action(self, chat_id, action, temp_data=None):
        session = self.Session()
        try:
            session_obj = session.query(UserSession).filter(
                UserSession.chat_id == str(chat_id)
            ).first()
            
            if not session_obj:
                session_obj = UserSession(chat_id=str(chat_id))
                session.add(session_obj)
            
            session_obj.current_action = action
            session_obj.temp_data = temp_data
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_user_session(self, chat_id):
        session = self.Session()
        try:
            session_obj = session.query(UserSession).filter(
                UserSession.chat_id == str(chat_id)
            ).first()
            return session_obj
        finally:
            session.close()
    
    def clear_user_session(self, chat_id):
        session = self.Session()
        try:
            session_obj = session.query(UserSession).filter(
                UserSession.chat_id == str(chat_id)
            ).first()
            if session_obj:
                session.delete(session_obj)
                session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()