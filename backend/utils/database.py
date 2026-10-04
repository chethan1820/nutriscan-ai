"""
Database Models and Initialization
Uses SQLAlchemy with SQLite (development) or PostgreSQL (production).
"""

import json
import logging
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

logger = logging.getLogger("utils.database")
db = SQLAlchemy()


class FoodLog(db.Model):
    """Records of food items analyzed by users."""
    __tablename__ = "food_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(64), nullable=False, index=True)
    food_name = db.Column(db.String(256), nullable=False)
    input_type = db.Column(db.String(20), default="text")  # "text" or "image"
    calories = db.Column(db.Float, default=0)
    protein = db.Column(db.Float, default=0)
    carbs = db.Column(db.Float, default=0)
    fats = db.Column(db.Float, default=0)
    health_score = db.Column(db.Float, default=0)
    health_label = db.Column(db.String(20), default="unknown")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "food_name": self.food_name,
            "input_type": self.input_type,
            "calories": self.calories,
            "protein": self.protein,
            "carbs": self.carbs,
            "fats": self.fats,
            "health_score": self.health_score,
            "health_label": self.health_label,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


class UserProfile(db.Model):
    """User health profile for personalized recommendations."""
    __tablename__ = "user_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(64), unique=True, nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    weight_kg = db.Column(db.Float)
    height_cm = db.Column(db.Float)
    activity_level = db.Column(db.String(50))  # sedentary, light, moderate, active, very_active
    health_conditions = db.Column(db.Text)  # JSON list
    dietary_preferences = db.Column(db.Text)  # JSON list
    allergies = db.Column(db.Text)  # JSON list
    goal = db.Column(db.String(100))  # weight_loss, muscle_gain, maintenance, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        def parse_json_field(field):
            if not field:
                return []
            try:
                return json.loads(field)
            except Exception:
                return field

        return {
            "user_id": self.user_id,
            "age": self.age,
            "gender": self.gender,
            "weight_kg": self.weight_kg,
            "height_cm": self.height_cm,
            "activity_level": self.activity_level,
            "health_conditions": parse_json_field(self.health_conditions),
            "dietary_preferences": parse_json_field(self.dietary_preferences),
            "allergies": parse_json_field(self.allergies),
            "goal": self.goal,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


def init_db(app):
    """Initialize the database with the app context."""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        logger.info("Database initialized")
