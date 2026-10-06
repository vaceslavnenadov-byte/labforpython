import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Config:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///taxi_web.db")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    PAGE_SIZE = int(os.getenv("PAGE_SIZE", "8"))
    TESTING = False


class TestConfig(Config):
    DATABASE_URL = "sqlite://"
    TESTING = True
    SECRET_KEY = "test"
