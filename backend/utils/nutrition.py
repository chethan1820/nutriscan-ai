"""
Nutrition Analyzer
Provides nutritional data lookup for food items.
Uses local database first, falls back to USDA FoodData API or estimated values.
"""

import os
import json
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger("utils.nutrition")

# ─── Comprehensive Nutrition Database ─────────────────────────────────────────
# Values per 100g unless noted. Source: USDA FoodData Central approximations.
NUTRITION_DB = {
    "apple pie": {"calories": 237, "protein": 2.0, "fat": 11.0, "carbohydrates": 34.0, "fiber": 1.4, "sugar": 14.3, "sodium": 208, "cholesterol": 0},
    "baby back ribs": {"calories": 297, "protein": 24.0, "fat": 22.0, "carbohydrates": 0.0, "fiber": 0, "sugar": 0, "sodium": 105, "cholesterol": 95},
    "baklava": {"calories": 428, "protein": 6.0, "fat": 22.0, "carbohydrates": 53.0, "fiber": 2.0, "sugar": 30.0, "sodium": 230, "cholesterol": 0},
    "beef": {"calories": 250, "protein": 26.0, "fat": 15.0, "carbohydrates": 0.0, "fiber": 0, "sugar": 0, "sodium": 72, "cholesterol": 80},
    "burger": {"calories": 295, "protein": 17.0, "fat": 14.0, "carbohydrates": 24.0, "fiber": 1.0, "sugar": 5.0, "sodium": 500, "cholesterol": 55},
    "hamburger": {"calories": 295, "protein": 17.0, "fat": 14.0, "carbohydrates": 24.0, "fiber": 1.0, "sugar": 5.0, "sodium": 500, "cholesterol": 55},
    "caesar salad": {"calories": 150, "protein": 9.0, "fat": 10.0, "carbohydrates": 8.0, "fiber": 1.5, "sugar": 2.0, "sodium": 400, "cholesterol": 30},
    "caprese salad": {"calories": 150, "protein": 8.0, "fat": 10.0, "carbohydrates": 5.0, "fiber": 1.0, "sugar": 4.0, "sodium": 150, "cholesterol": 25},
    "carrot cake": {"calories": 415, "protein": 4.5, "fat": 21.0, "carbohydrates": 54.0, "fiber": 1.5, "sugar": 38.0, "sodium": 320, "cholesterol": 55},
    "cheesecake": {"calories": 321, "protein": 5.5, "fat": 22.5, "carbohydrates": 25.5, "fiber": 0.2, "sugar": 22.0, "sodium": 234, "cholesterol": 90},
    "chicken": {"calories": 165, "protein": 31.0, "fat": 3.6, "carbohydrates": 0.0, "fiber": 0, "sugar": 0, "sodium": 74, "cholesterol": 85},
    "chicken curry": {"calories": 160, "protein": 14.0, "fat": 8.0, "carbohydrates": 10.0, "fiber": 2.0, "sugar": 3.0, "sodium": 350, "cholesterol": 50},
    "chicken wings": {"calories": 290, "protein": 27.0, "fat": 19.0, "carbohydrates": 1.0, "fiber": 0, "sugar": 0, "sodium": 150, "cholesterol": 100},
    "chocolate cake": {"calories": 371, "protein": 5.0, "fat": 15.0, "carbohydrates": 55.0, "fiber": 3.0, "sugar": 36.0, "sodium": 299, "cholesterol": 55},
    "clam chowder": {"calories": 170, "protein": 8.0, "fat": 9.0, "carbohydrates": 15.0, "fiber": 0.5, "sugar": 3.0, "sodium": 680, "cholesterol": 35},
    "donuts": {"calories": 452, "protein": 5.0, "fat": 25.0, "carbohydrates": 51.0, "fiber": 1.2, "sugar": 21.0, "sodium": 390, "cholesterol": 25},
    "edamame": {"calories": 121, "protein": 11.9, "fat": 5.2, "carbohydrates": 8.9, "fiber": 5.2, "sugar": 2.2, "sodium": 6, "cholesterol": 0},
    "eggs benedict": {"calories": 252, "protein": 14.0, "fat": 17.0, "carbohydrates": 12.0, "fiber": 0.5, "sugar": 1.5, "sodium": 600, "cholesterol": 280},
    "falafel": {"calories": 333, "protein": 13.3, "fat": 17.8, "carbohydrates": 31.8, "fiber": 4.9, "sugar": 0, "sodium": 585, "cholesterol": 0},
    "fish and chips": {"calories": 288, "protein": 14.0, "fat": 14.0, "carbohydrates": 26.0, "fiber": 1.5, "sugar": 0.5, "sodium": 450, "cholesterol": 45},
    "french fries": {"calories": 312, "protein": 3.4, "fat": 15.0, "carbohydrates": 41.0, "fiber": 3.8, "sugar": 0.3, "sodium": 210, "cholesterol": 0},
    "french toast": {"calories": 229, "protein": 8.0, "fat": 9.0, "carbohydrates": 30.0, "fiber": 1.0, "sugar": 10.0, "sodium": 290, "cholesterol": 150},
    "fried rice": {"calories": 163, "protein": 3.8, "fat": 4.0, "carbohydrates": 28.0, "fiber": 0.7, "sugar": 1.0, "sodium": 500, "cholesterol": 35},
    "frozen yogurt": {"calories": 127, "protein": 3.0, "fat": 4.0, "carbohydrates": 22.0, "fiber": 0, "sugar": 17.0, "sodium": 60, "cholesterol": 15},
    "greek salad": {"calories": 100, "protein": 3.5, "fat": 7.0, "carbohydrates": 8.0, "fiber": 2.0, "sugar": 5.0, "sodium": 400, "cholesterol": 10},
    "grilled salmon": {"calories": 206, "protein": 28.5, "fat": 9.7, "carbohydrates": 0.0, "fiber": 0, "sugar": 0, "sodium": 59, "cholesterol": 84},
    "guacamole": {"calories": 150, "protein": 2.0, "fat": 13.0, "carbohydrates": 8.0, "fiber": 5.0, "sugar": 1.0, "sodium": 300, "cholesterol": 0},
    "hot dog": {"calories": 290, "protein": 11.0, "fat": 26.0, "carbohydrates": 1.0, "fiber": 0, "sugar": 0, "sodium": 780, "cholesterol": 50},
    "hummus": {"calories": 177, "protein": 8.0, "fat": 10.0, "carbohydrates": 14.0, "fiber": 6.0, "sugar": 0.5, "sodium": 305, "cholesterol": 0},
    "ice cream": {"calories": 207, "protein": 3.5, "fat": 11.0, "carbohydrates": 24.0, "fiber": 0.7, "sugar": 21.0, "sodium": 80, "cholesterol": 44},
    "lasagna": {"calories": 166, "protein": 11.0, "fat": 7.0, "carbohydrates": 16.0, "fiber": 1.5, "sugar": 3.0, "sodium": 450, "cholesterol": 40},
    "macaroni and cheese": {"calories": 380, "protein": 13.0, "fat": 18.0, "carbohydrates": 44.0, "fiber": 1.0, "sugar": 5.0, "sodium": 560, "cholesterol": 45},
    "miso soup": {"calories": 40, "protein": 3.0, "fat": 1.0, "carbohydrates": 5.0, "fiber": 0.5, "sugar": 1.5, "sodium": 1100, "cholesterol": 0},
    "nachos": {"calories": 346, "protein": 9.0, "fat": 19.0, "carbohydrates": 36.0, "fiber": 3.0, "sugar": 1.0, "sodium": 440, "cholesterol": 25},
    "omelette": {"calories": 154, "protein": 10.6, "fat": 11.6, "carbohydrates": 1.1, "fiber": 0, "sugar": 0.7, "sodium": 342, "cholesterol": 328},
    "onion rings": {"calories": 411, "protein": 4.7, "fat": 26.0, "carbohydrates": 40.0, "fiber": 3.0, "sugar": 5.0, "sodium": 415, "cholesterol": 10},
    "pad thai": {"calories": 206, "protein": 11.0, "fat": 8.0, "carbohydrates": 24.0, "fiber": 1.5, "sugar": 7.0, "sodium": 620, "cholesterol": 80},
    "pancakes": {"calories": 227, "protein": 6.0, "fat": 9.0, "carbohydrates": 30.0, "fiber": 0.8, "sugar": 6.0, "sodium": 420, "cholesterol": 75},
    "pasta": {"calories": 131, "protein": 5.0, "fat": 1.1, "carbohydrates": 25.0, "fiber": 1.8, "sugar": 0.6, "sodium": 1, "cholesterol": 0},
    "pho": {"calories": 67, "protein": 5.0, "fat": 1.4, "carbohydrates": 7.0, "fiber": 0.5, "sugar": 1.0, "sodium": 670, "cholesterol": 20},
    "pizza": {"calories": 266, "protein": 11.0, "fat": 10.0, "carbohydrates": 33.0, "fiber": 2.3, "sugar": 3.6, "sodium": 598, "cholesterol": 17},
    "ramen": {"calories": 147, "protein": 9.0, "fat": 4.0, "carbohydrates": 20.0, "fiber": 1.0, "sugar": 2.0, "sodium": 1890, "cholesterol": 35},
    "risotto": {"calories": 166, "protein": 4.7, "fat": 4.6, "carbohydrates": 26.0, "fiber": 0.5, "sugar": 1.0, "sodium": 320, "cholesterol": 12},
    "salad": {"calories": 52, "protein": 3.0, "fat": 2.0, "carbohydrates": 6.0, "fiber": 2.5, "sugar": 3.0, "sodium": 180, "cholesterol": 5},
    "samosa": {"calories": 308, "protein": 5.7, "fat": 16.0, "carbohydrates": 37.0, "fiber": 3.0, "sugar": 2.0, "sodium": 350, "cholesterol": 0},
    "sashimi": {"calories": 127, "protein": 20.0, "fat": 4.5, "carbohydrates": 0.0, "fiber": 0, "sugar": 0, "sodium": 50, "cholesterol": 65},
    "seaweed salad": {"calories": 70, "protein": 1.3, "fat": 5.0, "carbohydrates": 5.0, "fiber": 1.5, "sugar": 2.0, "sodium": 430, "cholesterol": 0},
    "soup": {"calories": 72, "protein": 4.0, "fat": 2.5, "carbohydrates": 9.0, "fiber": 1.5, "sugar": 3.0, "sodium": 700, "cholesterol": 10},
    "spaghetti bolognese": {"calories": 190, "protein": 11.0, "fat": 7.0, "carbohydrates": 22.0, "fiber": 2.0, "sugar": 4.0, "sodium": 380, "cholesterol": 30},
    "spring rolls": {"calories": 190, "protein": 5.0, "fat": 10.0, "carbohydrates": 20.0, "fiber": 2.0, "sugar": 2.0, "sodium": 380, "cholesterol": 20},
    "steak": {"calories": 271, "protein": 26.0, "fat": 18.0, "carbohydrates": 0.0, "fiber": 0, "sugar": 0, "sodium": 59, "cholesterol": 78},
    "sushi": {"calories": 140, "protein": 5.5, "fat": 3.5, "carbohydrates": 21.0, "fiber": 0.6, "sugar": 2.5, "sodium": 300, "cholesterol": 15},
    "tacos": {"calories": 210, "protein": 11.0, "fat": 9.0, "carbohydrates": 21.0, "fiber": 2.0, "sugar": 2.0, "sodium": 390, "cholesterol": 30},
    "tiramisu": {"calories": 283, "protein": 5.5, "fat": 16.0, "carbohydrates": 30.0, "fiber": 0.4, "sugar": 22.0, "sodium": 90, "cholesterol": 115},
    "waffles": {"calories": 291, "protein": 7.9, "fat": 14.0, "carbohydrates": 34.0, "fiber": 1.3, "sugar": 8.0, "sodium": 490, "cholesterol": 85},
}

# Ingredient nutrition per 100g
INGREDIENT_DB = {
    "chicken breast": {"calories": 165, "protein": 31.0, "fat": 3.6, "carbohydrates": 0.0, "fiber": 0, "sugar": 0, "sodium": 74, "cholesterol": 85},
    "rice": {"calories": 130, "protein": 2.7, "fat": 0.3, "carbohydrates": 28.2, "fiber": 0.4, "sugar": 0.1, "sodium": 1, "cholesterol": 0},
    "broccoli": {"calories": 34, "protein": 2.8, "fat": 0.4, "carbohydrates": 7.0, "fiber": 2.6, "sugar": 1.7, "sodium": 33, "cholesterol": 0},
    "spinach": {"calories": 23, "protein": 2.9, "fat": 0.4, "carbohydrates": 3.6, "fiber": 2.2, "sugar": 0.4, "sodium": 79, "cholesterol": 0},
    "egg": {"calories": 155, "protein": 12.6, "fat": 10.6, "carbohydrates": 1.1, "fiber": 0, "sugar": 1.1, "sodium": 124, "cholesterol": 373},
    "milk": {"calories": 61, "protein": 3.2, "fat": 3.3, "carbohydrates": 4.8, "fiber": 0, "sugar": 5.1, "sodium": 44, "cholesterol": 10},
    "cheese": {"calories": 402, "protein": 25.0, "fat": 33.0, "carbohydrates": 1.3, "fiber": 0, "sugar": 0.5, "sodium": 654, "cholesterol": 105},
    "butter": {"calories": 717, "protein": 0.9, "fat": 81.0, "carbohydrates": 0.1, "fiber": 0, "sugar": 0.1, "sodium": 643, "cholesterol": 215},
    "olive oil": {"calories": 884, "protein": 0, "fat": 100.0, "carbohydrates": 0.0, "fiber": 0, "sugar": 0, "sodium": 2, "cholesterol": 0},
    "flour": {"calories": 364, "protein": 10.0, "fat": 1.0, "carbohydrates": 76.0, "fiber": 2.7, "sugar": 0.3, "sodium": 2, "cholesterol": 0},
    "sugar": {"calories": 387, "protein": 0, "fat": 0, "carbohydrates": 100.0, "fiber": 0, "sugar": 100.0, "sodium": 1, "cholesterol": 0},
    "tomato": {"calories": 18, "protein": 0.9, "fat": 0.2, "carbohydrates": 3.9, "fiber": 1.2, "sugar": 2.6, "sodium": 5, "cholesterol": 0},
    "onion": {"calories": 40, "protein": 1.1, "fat": 0.1, "carbohydrates": 9.3, "fiber": 1.7, "sugar": 4.2, "sodium": 4, "cholesterol": 0},
    "garlic": {"calories": 149, "protein": 6.4, "fat": 0.5, "carbohydrates": 33.0, "fiber": 2.1, "sugar": 1.0, "sodium": 17, "cholesterol": 0},
    "potato": {"calories": 77, "protein": 2.0, "fat": 0.1, "carbohydrates": 17.0, "fiber": 2.2, "sugar": 0.8, "sodium": 6, "cholesterol": 0},
    "pasta": {"calories": 131, "protein": 5.0, "fat": 1.1, "carbohydrates": 25.0, "fiber": 1.8, "sugar": 0.6, "sodium": 1, "cholesterol": 0},
    "bread": {"calories": 265, "protein": 9.0, "fat": 3.2, "carbohydrates": 49.0, "fiber": 2.7, "sugar": 5.0, "sodium": 491, "cholesterol": 0},
    "salmon": {"calories": 208, "protein": 20.0, "fat": 13.0, "carbohydrates": 0.0, "fiber": 0, "sugar": 0, "sodium": 59, "cholesterol": 63},
    "tuna": {"calories": 132, "protein": 28.0, "fat": 1.0, "carbohydrates": 0.0, "fiber": 0, "sugar": 0, "sodium": 40, "cholesterol": 49},
    "banana": {"calories": 89, "protein": 1.1, "fat": 0.3, "carbohydrates": 23.0, "fiber": 2.6, "sugar": 12.2, "sodium": 1, "cholesterol": 0},
    "apple": {"calories": 52, "protein": 0.3, "fat": 0.2, "carbohydrates": 14.0, "fiber": 2.4, "sugar": 10.3, "sodium": 1, "cholesterol": 0},
    "oats": {"calories": 389, "protein": 17.0, "fat": 7.0, "carbohydrates": 66.0, "fiber": 11.0, "sugar": 1.0, "sodium": 2, "cholesterol": 0},
    "yogurt": {"calories": 59, "protein": 10.0, "fat": 0.4, "carbohydrates": 3.6, "fiber": 0, "sugar": 3.2, "sodium": 36, "cholesterol": 5},
    "avocado": {"calories": 160, "protein": 2.0, "fat": 14.7, "carbohydrates": 8.5, "fiber": 6.7, "sugar": 0.7, "sodium": 7, "cholesterol": 0},
    "quinoa": {"calories": 120, "protein": 4.4, "fat": 1.9, "carbohydrates": 21.3, "fiber": 2.8, "sugar": 0.9, "sodium": 7, "cholesterol": 0},
    "lentils": {"calories": 116, "protein": 9.0, "fat": 0.4, "carbohydrates": 20.0, "fiber": 7.9, "sugar": 1.8, "sodium": 2, "cholesterol": 0},
}


class NutritionAnalyzer:
    """Analyzes nutritional content of foods and ingredients."""

    def __init__(self, db_path: str = None):
        self.nutrition_db = NUTRITION_DB.copy()
        self.ingredient_db = INGREDIENT_DB.copy()

        # Load external database if provided
        if db_path and os.path.exists(db_path):
            try:
                with open(db_path) as f:
                    external = json.load(f)
                self.nutrition_db.update(external)
                logger.info(f"Loaded {len(external)} external nutrition records")
            except Exception as e:
                logger.warning(f"Could not load external DB: {e}")

    def get_nutrition(self, food_name: str, portion_g: float = 100) -> dict:
        """
        Get nutrition data for a food item.

        Args:
            food_name: Name of the food
            portion_g: Portion size in grams (default 100g)

        Returns:
            dict with nutritional values
        """
        # Normalize name
        key = food_name.lower().strip()

        # Direct match
        data = self.nutrition_db.get(key)

        # Fuzzy match
        if not data:
            for db_key, db_val in self.nutrition_db.items():
                if key in db_key or db_key in key:
                    data = db_val
                    break

        # Still not found - estimate
        if not data:
            data = self._estimate_nutrition(food_name)

        # Scale to portion size
        scale = portion_g / 100.0
        scaled = {k: round(v * scale, 2) for k, v in data.items()}

        return {
            **scaled,
            "portion_g": portion_g,
            "vitamins": self._get_vitamins(food_name),
            "minerals": self._get_minerals(food_name),
            "glycemic_index": self._estimate_gi(food_name, data)
        }

    def analyze_ingredients(self, ingredients: list, total_portion_g: float = 100) -> dict:
        """
        Analyze nutritional content of a list of ingredients.
        Assumes equal weight distribution unless specified otherwise.
        """
        per_ingredient_g = total_portion_g / max(len(ingredients), 1)

        totals = {
            "calories": 0, "protein": 0, "fat": 0, "carbohydrates": 0,
            "fiber": 0, "sugar": 0, "sodium": 0, "cholesterol": 0
        }

        for item in ingredients:
            key = item.lower().strip()
            data = self.ingredient_db.get(key)

            if not data:
                # Try partial match
                for k, v in self.ingredient_db.items():
                    if key in k or k in key:
                        data = v
                        break

            if not data:
                data = self._estimate_nutrition(item)

            scale = per_ingredient_g / 100.0
            for nutrient in totals:
                totals[nutrient] += data.get(nutrient, 0) * scale

        totals = {k: round(v, 2) for k, v in totals.items()}
        totals["portion_g"] = total_portion_g
        totals["vitamins"] = {}
        totals["minerals"] = {}
        totals["glycemic_index"] = self._estimate_gi("mixed", totals)

        return totals

    def search_foods(self, query: str, limit: int = 10) -> list:
        """Search for foods matching a query string."""
        query = query.lower()
        results = []

        for name in list(self.nutrition_db.keys()) + list(self.ingredient_db.keys()):
            if query in name:
                results.append({
                    "name": name.title(),
                    "key": name
                })
                if len(results) >= limit:
                    break

        return results

    def _estimate_nutrition(self, food_name: str) -> dict:
        """Estimate nutrition when food is not in database."""
        logger.info(f"Estimating nutrition for unknown food: {food_name}")
        name = food_name.lower()

        # Keyword-based estimation
        if any(w in name for w in ["salad", "vegetable", "veggie", "green"]):
            return {"calories": 60, "protein": 3.0, "fat": 3.0, "carbohydrates": 7.0, "fiber": 2.5, "sugar": 3.0, "sodium": 200, "cholesterol": 5}
        elif any(w in name for w in ["cake", "pie", "pastry", "cookie", "dessert", "sweet"]):
            return {"calories": 380, "protein": 5.0, "fat": 18.0, "carbohydrates": 50.0, "fiber": 1.0, "sugar": 30.0, "sodium": 300, "cholesterol": 60}
        elif any(w in name for w in ["steak", "beef", "meat", "pork", "lamb"]):
            return {"calories": 260, "protein": 25.0, "fat": 17.0, "carbohydrates": 0.0, "fiber": 0, "sugar": 0, "sodium": 70, "cholesterol": 80}
        elif any(w in name for w in ["chicken", "turkey", "poultry"]):
            return {"calories": 175, "protein": 25.0, "fat": 8.0, "carbohydrates": 0.0, "fiber": 0, "sugar": 0, "sodium": 80, "cholesterol": 80}
        elif any(w in name for w in ["fish", "seafood", "shrimp", "crab", "lobster"]):
            return {"calories": 150, "protein": 22.0, "fat": 6.0, "carbohydrates": 0.0, "fiber": 0, "sugar": 0, "sodium": 80, "cholesterol": 60}
        elif any(w in name for w in ["pasta", "noodle", "rice", "grain"]):
            return {"calories": 150, "protein": 5.0, "fat": 2.0, "carbohydrates": 30.0, "fiber": 1.5, "sugar": 1.0, "sodium": 100, "cholesterol": 0}
        elif any(w in name for w in ["soup", "stew", "broth"]):
            return {"calories": 80, "protein": 5.0, "fat": 3.0, "carbohydrates": 9.0, "fiber": 1.5, "sugar": 2.0, "sodium": 700, "cholesterol": 15}
        elif any(w in name for w in ["fried", "chips", "fries"]):
            return {"calories": 350, "protein": 4.0, "fat": 18.0, "carbohydrates": 42.0, "fiber": 3.0, "sugar": 0.5, "sodium": 350, "cholesterol": 0}
        else:
            return {"calories": 200, "protein": 8.0, "fat": 8.0, "carbohydrates": 25.0, "fiber": 2.0, "sugar": 5.0, "sodium": 300, "cholesterol": 30}

    def _get_vitamins(self, food_name: str) -> dict:
        """Estimated key vitamins."""
        name = food_name.lower()
        if any(w in name for w in ["salad", "spinach", "broccoli", "vegetable"]):
            return {"vitamin_a": "25% DV", "vitamin_c": "40% DV", "vitamin_k": "80% DV", "folate": "20% DV"}
        elif any(w in name for w in ["salmon", "tuna", "fish"]):
            return {"vitamin_d": "50% DV", "vitamin_b12": "80% DV", "vitamin_b6": "30% DV"}
        elif any(w in name for w in ["orange", "citrus", "mango"]):
            return {"vitamin_c": "80% DV", "vitamin_a": "15% DV", "folate": "10% DV"}
        else:
            return {"vitamin_c": "5% DV", "vitamin_b6": "8% DV", "folate": "5% DV"}

    def _get_minerals(self, food_name: str) -> dict:
        """Estimated key minerals."""
        name = food_name.lower()
        if any(w in name for w in ["spinach", "kale", "leafy"]):
            return {"iron": "15% DV", "calcium": "10% DV", "magnesium": "20% DV", "potassium": "15% DV"}
        elif any(w in name for w in ["milk", "cheese", "dairy", "yogurt"]):
            return {"calcium": "30% DV", "phosphorus": "25% DV", "potassium": "10% DV"}
        elif any(w in name for w in ["meat", "beef", "chicken", "steak"]):
            return {"iron": "15% DV", "zinc": "35% DV", "phosphorus": "20% DV", "selenium": "40% DV"}
        else:
            return {"potassium": "8% DV", "phosphorus": "10% DV", "magnesium": "5% DV"}

    def _estimate_gi(self, food_name: str, nutrition: dict) -> int:
        """Estimate glycemic index."""
        sugar = nutrition.get("sugar", 0)
        carbs = nutrition.get("carbohydrates", 0)
        fiber = nutrition.get("fiber", 0)
        name = food_name.lower()

        if any(w in name for w in ["candy", "soda", "sugar"]):
            return 80
        elif any(w in name for w in ["white bread", "donut", "french fries"]):
            return 75
        elif any(w in name for w in ["pasta", "rice", "pizza"]):
            return 55
        elif any(w in name for w in ["apple", "orange", "berry", "fruit"]):
            return 40
        elif any(w in name for w in ["lentil", "bean", "legume"]):
            return 30
        elif any(w in name for w in ["salad", "vegetable", "broccoli"]):
            return 20

        # Estimate from macros
        if carbs > 0 and fiber > 0:
            fiber_ratio = fiber / carbs
            if fiber_ratio > 0.3:
                return 35
            elif fiber_ratio > 0.1:
                return 55
        if sugar / max(carbs, 1) > 0.5:
            return 70

        return 50  # Default medium GI
