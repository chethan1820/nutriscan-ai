"""
Configuration settings for different environments.
"""

import os
from datetime import timedelta


class BaseConfig:
    """Base configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = False
    TESTING = False

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///food_health.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

    # ML Model settings
    MODEL_PATH = os.getenv("MODEL_PATH", "../models/food_classifier.pth")
    MODEL_CLASSES_PATH = os.getenv("MODEL_CLASSES_PATH", "../models/classes.json")
    NUTRITION_DB_PATH = os.getenv("NUTRITION_DB_PATH", "../dataset/nutrition_database.json")

    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # Rate limiting
    RATELIMIT_DEFAULT = "100 per hour"

    # Logging
    LOG_LEVEL = "INFO"
    LOG_FILE = "logs/app.log"


class DevelopmentConfig(BaseConfig):
    """Development configuration."""
    DEBUG = True
    LOG_LEVEL = "DEBUG"


class ProductionConfig(BaseConfig):
    """Production configuration."""
    DEBUG = False
    SECRET_KEY = os.getenv("SECRET_KEY")  # Must be set in production
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/food_health")


class TestingConfig(BaseConfig):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig
}
