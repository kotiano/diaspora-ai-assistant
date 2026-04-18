import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

_DEFAULT_SQLITE = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'diaspora.db')}"


def _get_db_uri():

    uri = os.environ.get("DATABASE_URI") or os.environ.get("DATABASE_URL")
    if not uri:
        return _DEFAULT_SQLITE


    if uri.startswith("sqlite:///") and not uri.startswith("sqlite:////"):
        relative_part = uri[len("sqlite:///"):]        
        absolute_path = os.path.join(BASE_DIR, relative_part)
        return f"sqlite:///{absolute_path}"

    return uri


class Config:
    SECRET_KEY                     = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    AI_PROVIDER    = os.environ.get("AI_PROVIDER", "gemini").lower()
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL   = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
    GROQ_API_KEY   = os.environ.get("GROQ_API_KEY", "")
    GROQ_MODEL     = os.environ.get("GROQ_MODEL", "llama3-8b-8192")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = _get_db_uri()


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = _get_db_uri()


config_map = {
    "development": DevelopmentConfig,
    "testing":     TestingConfig,
    "production":  ProductionConfig,
}


def get_config():
    env = os.environ.get("FLASK_ENV", "development")
    cfg = config_map.get(env, DevelopmentConfig)
    print(f"[INFO] Database: {cfg.SQLALCHEMY_DATABASE_URI}")
    return cfg