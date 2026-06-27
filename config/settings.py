import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.serpapi_api_key = os.getenv("SERPAPI_API_KEY")
        
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///linkedin_posts.db")
        
        self.enable_fact_checking = os.getenv("ENABLE_FACT_CHECKING", "True") == "True"
        self.enable_analytics = os.getenv("ENABLE_ANALYTICS", "True") == "True"
        self.enable_scheduling = os.getenv("ENABLE_SCHEDULING", "True") == "True"
        self.enable_multi_language = os.getenv("ENABLE_MULTI_LANGUAGE", "True") == "True"
        
        self.default_tone = os.getenv("DEFAULT_TONE", "professional")
        self.default_length = os.getenv("DEFAULT_LENGTH", "medium")
        self.default_audience = os.getenv("DEFAULT_AUDIENCE", "professionals")
        self.default_num_posts = int(os.getenv("DEFAULT_NUM_POSTS", "3"))
        self.temperature = float(os.getenv("TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("MAX_TOKENS", "2000"))

_settings = None

def get_settings():
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
