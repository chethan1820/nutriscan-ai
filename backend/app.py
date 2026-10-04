"""
AI-Based Food Health Monitoring System
Main Flask Application Entry Point
"""

import os
import sys
import logging
from flask import Flask
from flask_cors import CORS

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.routes import api_blueprint
from api.auth import auth_blueprint
from utils.logger import setup_logger
from utils.database import init_db

# Setup logging
logger = setup_logger("app", "logs/app.log")

def create_app(config_name="development"):
    """Application factory pattern."""
    app = Flask(
        __name__,
        template_folder="../frontend/templates",
        static_folder="../frontend/static"
    )

    # Load configuration
    from config import config
    app.config.from_object(config[config_name])

    # Initialize extensions
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize database
    init_db(app)

    # Register blueprints
    app.register_blueprint(api_blueprint, url_prefix="/api")
    app.register_blueprint(auth_blueprint, url_prefix="/auth")

    # Register main route
    from flask import render_template
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.errorhandler(404)
    def not_found(e):
        return {"error": "Not found", "status": 404}, 404

    @app.errorhandler(500)
    def server_error(e):
        logger.error(f"Server error: {e}")
        return {"error": "Internal server error", "status": 500}, 500

    logger.info(f"App initialized in {config_name} mode")
    return app


if __name__ == "__main__":
    app = create_app(os.getenv("FLASK_ENV", "development"))
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        debug=app.config.get("DEBUG", False)
    )
