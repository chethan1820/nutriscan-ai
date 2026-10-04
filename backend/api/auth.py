"""
Authentication Blueprint (simplified for demo).
In production, use JWT or OAuth2.
"""

from flask import Blueprint, request, jsonify
import uuid

auth_blueprint = Blueprint("auth", __name__)


@auth_blueprint.route("/register", methods=["POST"])
def register():
    """Generate a unique user ID for session tracking."""
    user_id = str(uuid.uuid4())
    return jsonify({"status": "success", "user_id": user_id,
                    "message": "Save this user_id for future requests"}), 201


@auth_blueprint.route("/guest", methods=["GET"])
def guest_session():
    """Create a guest session."""
    return jsonify({"status": "success", "user_id": "anonymous",
                    "message": "Guest session active"}), 200
