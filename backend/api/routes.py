"""
API Routes for Food Health Monitoring System
Endpoints:
  POST /api/predict  - Image-based food recognition
  POST /api/analyze  - Text-based food analysis
  GET  /api/history  - User food history
  POST /api/profile  - Update user profile
  GET  /api/nutrients/<food> - Get nutrition info
"""

import os
import json
import uuid
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.utils import secure_filename

from utils.image_utils import preprocess_image, validate_image
from utils.nutrition import NutritionAnalyzer
from utils.health_scorer import HealthScorer
from utils.recommendations import RecommendationEngine
from utils.database import db, FoodLog, UserProfile
from models.inference import FoodClassifier

logger = logging.getLogger("api.routes")

api_blueprint = Blueprint("api", __name__)

# Initialize components (lazy loaded)
_classifier = None
_nutrition_analyzer = None
_health_scorer = None
_recommendation_engine = None


def get_classifier():
    global _classifier
    if _classifier is None:
        _classifier = FoodClassifier()
    return _classifier


def get_nutrition_analyzer():
    global _nutrition_analyzer
    if _nutrition_analyzer is None:
        _nutrition_analyzer = NutritionAnalyzer()
    return _nutrition_analyzer


def get_health_scorer():
    global _health_scorer
    if _health_scorer is None:
        _health_scorer = HealthScorer()
    return _health_scorer


def get_recommendation_engine():
    global _recommendation_engine
    if _recommendation_engine is None:
        _recommendation_engine = RecommendationEngine()
    return _recommendation_engine


def allowed_file(filename):
    """Check if file extension is allowed."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in current_app.config["ALLOWED_EXTENSIONS"]
    )


@api_blueprint.route("/predict", methods=["POST"])
def predict():
    """
    Endpoint: POST /api/predict
    Input: multipart/form-data with 'image' file and optional 'user_id'
    Output: JSON with food name, nutrition, health score, recommendations
    """
    try:
        # Validate image upload
        if "image" not in request.files:
            return jsonify({"error": "No image file provided"}), 400

        file = request.files["image"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file type. Use PNG, JPG, JPEG, GIF, or WEBP"}), 400

        # Validate image content
        is_valid, error_msg = validate_image(file)
        if not is_valid:
            return jsonify({"error": error_msg}), 400

        # Save uploaded file
        upload_dir = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_dir, exist_ok=True)
        filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)

        # Get user profile if provided
        user_id = request.form.get("user_id","anonymous")
        user_profile = _get_user_profile(user_id)

        # Run food classification
        classifier = get_classifier()
        classification_result = classifier.predict(filepath)

        food_name = classification_result["food_name"]
        confidence = classification_result["confidence"]
        top_predictions = classification_result["top_k"]

        # Get nutrition data
        nutrition_analyzer = get_nutrition_analyzer()
        nutrition_data = nutrition_analyzer.get_nutrition(food_name)

        # Calculate health score
        health_scorer = get_health_scorer()
        health_result = health_scorer.score(nutrition_data, user_profile)

        # Get personalized recommendations
        rec_engine = get_recommendation_engine()
        recommendations = rec_engine.get_recommendations(
            food_name, nutrition_data, health_result, user_profile
        )

        # Log to database
        _log_food_entry(user_id, food_name, nutrition_data, health_result, "image")

        # Build response
        response = {
            "status": "success",
            "input_type": "image",
            "food_name": food_name,
            "confidence": round(confidence * 100, 2),
            "top_predictions": top_predictions,
            "nutrition": nutrition_data,
            "health_score": health_result,
            "recommendations": recommendations,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Cleanup uploaded file
        try:
            os.remove(filepath)
        except Exception:
            pass

        logger.info(f"Predict: {food_name} ({confidence:.2%} confidence)")
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Predict error: {e}", exc_info=True)
        return jsonify({"error": "Analysis failed. Please try again.", "detail": str(e)}), 500


@api_blueprint.route("/analyze", methods=["POST"])
def analyze():
    """
    Endpoint: POST /api/analyze
    Input: JSON with 'food_name' or 'ingredients' list and optional 'user_id'
    Output: JSON with nutrition, health score, recommendations
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        food_name = data.get("food_name", "").strip()
        ingredients = data.get("ingredients", [])
        user_id = data.get("user_id","anonymous")
        portion_size = data.get("portion_size", 100)  # grams

        if not food_name and not ingredients:
            return jsonify({"error": "Provide either 'food_name' or 'ingredients'"}), 400

        # Get user profile
        user_profile = _get_user_profile(user_id)

        # Get nutrition data
        nutrition_analyzer = get_nutrition_analyzer()

        if food_name:
            nutrition_data = nutrition_analyzer.get_nutrition(food_name, portion_size)
            display_name = food_name
        else:
            nutrition_data = nutrition_analyzer.analyze_ingredients(ingredients, portion_size)
            display_name = ", ".join(ingredients[:3]) + ("..." if len(ingredients) > 3 else "")

        # Calculate health score
        health_scorer = get_health_scorer()
        health_result = health_scorer.score(nutrition_data, user_profile)

        # Get personalized recommendations
        rec_engine = get_recommendation_engine()
        recommendations = rec_engine.get_recommendations(
            display_name, nutrition_data, health_result, user_profile
        )

        # Log to database
        _log_food_entry(user_id, display_name, nutrition_data, health_result, "text")

        response = {
            "status": "success",
            "input_type": "text",
            "food_name": display_name,
            "portion_size_g": portion_size,
            "nutrition": nutrition_data,
            "health_score": health_result,
            "recommendations": recommendations,
            "timestamp": datetime.utcnow().isoformat()
        }

        logger.info(f"Analyze: {display_name}")
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Analyze error: {e}", exc_info=True)
        return jsonify({"error": "Analysis failed. Please try again.", "detail": str(e)}), 500


@api_blueprint.route("/history", methods=["GET"])
def history():
    """
    Endpoint: GET /api/history?user_id=<id>&limit=<n>
    Returns user's food log history.
    """
    try:
        user_id = request.args.get("user_id", "anonymous")
        limit = min(int(request.args.get("limit", 20)), 100)

        logs = FoodLog.query.filter_by(user_id=user_id)\
            .order_by(FoodLog.timestamp.desc())\
            .limit(limit).all()

        history_data = [log.to_dict() for log in logs]

        # Calculate summary stats
        summary = _calculate_history_summary(history_data)

        return jsonify({
            "status": "success",
            "user_id": user_id,
            "count": len(history_data),
            "history": history_data,
            "summary": summary
        }), 200

    except Exception as e:
        logger.error(f"History error: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve history"}), 500


@api_blueprint.route("/profile", methods=["GET", "POST"])
def profile():
    """
    Endpoint: GET/POST /api/profile
    Manage user health profile for personalized recommendations.
    """
    try:
        user_id = request.args.get("user_id") or (request.get_json() or {}).get("user_id", "anonymous")

        if request.method == "GET":
            user = UserProfile.query.filter_by(user_id=user_id).first()
            if not user:
                return jsonify({"status": "not_found", "user_id": user_id}), 404
            return jsonify({"status": "success", "profile": user.to_dict()}), 200

        # POST - Create or update profile
        data = request.get_json() or {}
        user = UserProfile.query.filter_by(user_id=user_id).first()

        if not user:
            user = UserProfile(user_id=user_id)
            db.session.add(user)

        # Update fields
        allowed_fields = ["age", "weight_kg", "height_cm", "gender", "activity_level",
                         "health_conditions", "dietary_preferences", "allergies", "goal"]
        for field in allowed_fields:
            if field in data:
                setattr(user, field, json.dumps(data[field]) if isinstance(data[field], (list, dict)) else data[field])

        user.updated_at = datetime.utcnow()
        db.session.commit()
        print("PROFILE SAVED:", user_id)

        return jsonify({"status": "success", "message": "Profile updated", "profile": user.to_dict()}), 200

    except Exception as e:
        logger.error(f"Profile error: {e}", exc_info=True)
        return jsonify({"error": "Profile operation failed"}), 500


@api_blueprint.route("/nutrients/<food_name>", methods=["GET"])
def get_nutrients(food_name):
    """
    Endpoint: GET /api/nutrients/<food_name>
    Returns detailed nutrition information for a food item.
    """
    try:
        portion = int(request.args.get("portion", 100))
        nutrition_analyzer = get_nutrition_analyzer()
        nutrition_data = nutrition_analyzer.get_nutrition(food_name, portion)

        return jsonify({
            "status": "success",
            "food_name": food_name,
            "portion_g": portion,
            "nutrition": nutrition_data
        }), 200

    except Exception as e:
        logger.error(f"Nutrients error: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve nutrition data"}), 500


@api_blueprint.route("/search", methods=["GET"])
def search_foods():
    """
    Endpoint: GET /api/search?q=<query>
    Search for food items in the database.
    """
    try:
        query = request.args.get("q", "").strip()
        if len(query) < 2:
            return jsonify({"error": "Query must be at least 2 characters"}), 400

        nutrition_analyzer = get_nutrition_analyzer()
        results = nutrition_analyzer.search_foods(query)

        return jsonify({
            "status": "success",
            "query": query,
            "results": results
        }), 200

    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        return jsonify({"error": "Search failed"}), 500


@api_blueprint.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "AI Food Health Monitor",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }), 200


# ─── Helper Functions ──────────────────────────────────────────────────────────

def _get_user_profile(user_id):
    """Retrieve user profile from database."""
    if not user_id:
        return None
    try:
        user = UserProfile.query.filter_by(user_id=user_id).first()
        return user.to_dict() if user else None
    except Exception:
        return None


def _log_food_entry(user_id, food_name, nutrition, health_result, input_type):
    """Log a food entry to the database."""
    try:
        log = FoodLog(
            user_id=user_id or "anonymous",
            food_name=food_name,
            input_type=input_type,
            calories=nutrition.get("calories", 0),
            protein=nutrition.get("protein", 0),
            carbs=nutrition.get("carbohydrates", 0),
            fats=nutrition.get("fat", 0),
            health_score=health_result.get("score", 0),
            health_label=health_result.get("label", "unknown"),
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        logger.warning(f"Failed to log food entry: {e}")


def _calculate_history_summary(history_data):
    """Calculate summary statistics from food history."""
    if not history_data:
        return {}

    total_calories = sum(h.get("calories", 0) for h in history_data)
    avg_health_score = sum(h.get("health_score", 0) for h in history_data) / len(history_data)
    label_counts = {}
    for h in history_data:
        label = h.get("health_label", "unknown")
        label_counts[label] = label_counts.get(label, 0) + 1

    return {
        "total_entries": len(history_data),
        "total_calories": round(total_calories, 1),
        "avg_calories_per_meal": round(total_calories / len(history_data), 1),
        "avg_health_score": round(avg_health_score, 1),
        "label_distribution": label_counts
    }
