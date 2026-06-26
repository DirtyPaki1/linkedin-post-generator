from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, JSON, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
from config import get_settings
from utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

Base = declarative_base()

class Post(Base):
    """Model for generated posts."""
    __tablename__ = 'posts'
    
    id = Column(Integer, primary_key=True)
    topic = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    tone = Column(String(50))
    length = Column(String(20))
    audience = Column(String(100))
    language = Column(String(10), default='en')
    hashtags = Column(JSON)
    metadata = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    analytics = relationship("PostAnalytics", back_populates="post", uselist=False)
    fact_checks = relationship("FactCheckResult", back_populates="post")

class PostAnalytics(Base):
    """Model for post analytics and performance."""
    __tablename__ = 'post_analytics'
    
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('posts.id'))
    engagement_score = Column(Float)
    word_count = Column(Integer)
    character_count = Column(Integer)
    readability_score = Column(Float)
    sentiment_score = Column(Float)
    predicted_views = Column(Integer)
    predicted_likes = Column(Integer)
    predicted_comments = Column(Integer)
    metadata = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    post = relationship("Post", back_populates="analytics")

class FactCheckResult(Base):
    """Model for fact-checking results."""
    __tablename__ = 'fact_check_results'
    
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('posts.id'))
    status = Column(String(20))  # verified, unverified, inaccurate, no_claims
    claims_checked = Column(JSON)
    summary = Column(Text)
    confidence_score = Column(Float)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    post = relationship("Post", back_populates="fact_checks")

class ScheduledPost(Base):
    """Model for scheduled posts."""
    __tablename__ = 'scheduled_posts'
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String(100), unique=True)
    topic = Column(String(500))
    tone = Column(String(50))
    length = Column(String(20))
    audience = Column(String(100))
    interval_hours = Column(Integer)
    next_run = Column(DateTime)
    last_run = Column(DateTime)
    is_active = Column(Boolean, default=True)
    metadata = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

class User(Base):
    """Model for users (for future authentication)."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)
    email = Column(String(100), unique=True)
    password_hash = Column(String(255))
    api_key = Column(String(100), unique=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    last_login = Column(DateTime)
    preferences = Column(JSON)

def init_db():
    """Initialize database."""
    try:
        engine = create_engine(settings.database_url)
        Base.metadata.create_all(engine)
        logger.info(f"Database initialized: {settings.database_url}")
        return engine
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

def get_db():
    """Get database session."""
    engine = init_db()
    Session = sessionmaker(bind=engine)
    return Session()