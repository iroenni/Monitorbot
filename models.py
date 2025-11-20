from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
from config import Config

engine = create_engine(Config.DATABASE_URL)
Base = declarative_base()
Session = sessionmaker(bind=engine)

class MonitoredService(Base):
    __tablename__ = 'services'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    chat_id = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    check_interval = Column(Integer, default=300)  # segundos
    last_checked = Column(DateTime)
    last_status = Column(Boolean)
    created_at = Column(DateTime, default=func.now())
    
    def __repr__(self):
        return f"<Service(name='{self.name}', url='{self.url}', active={self.is_active})>"

class UserSession(Base):
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(String(100), nullable=False)
    current_action = Column(String(100))
    temp_data = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

# Crear tablas
def init_db():
    Base.metadata.create_all(engine)

if __name__ == '__main__':
    init_db()
    print("Base de datos inicializada correctamente.")