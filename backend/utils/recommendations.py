"""
Recommendation Engine
Provides personalized dietary recommendations based on food analysis and user profile.
"""

import logging
from typing import Optional

logger = logging.getLogger("utils.recommendations")


class RecommendationEngine:
    """Generates personalized food and health recommendations."""

    def get_recommendations(
        self,
        food_name: str,
        nutrition: dict,
        health_result: dict,
        user_profile: Optional[dict] = None
    ) -> dict:
        """
        Generate comprehensive recommendations.

        Returns:
            dict with tips, alternatives, and personalized advice
        """
        label = health_result.get("label", "Moderate")
        risks = health_result.get("risks", [])
        score = health_result.get("score", 50)

        tips = self._get_nutritional_tips(nutrition, label)
        alternatives = self._get_alternatives(food_name, label)
        portion_advice = self._get_portion_advice(nutrition, score)
        lifestyle_tips = self._get_lifestyle_tips(nutrition, risks)
        personalized = self._get_personalized_advice(nutrition, risks, user_profile)

        return {
            "general_tips": tips,
            "healthier_alternatives": alternatives,
            "portion_advice": portion_advice,
            "lifestyle_tips": lifestyle_tips,
            "personalized_advice": personalized,
            "meal_pairing": self._get_meal_pairings(food_name, nutrition, label)
        }

    def _get_nutritional_tips(self, nutrition: dict, label: str) -> list:
        """Generate tips based on nutritional content."""
        tips = []
        sugar = nutrition.get("sugar", 0)
        sodium = nutrition.get("sodium", 0)
        fat = nutrition.get("fat", 0)
        fiber = nutrition.get("fiber", 0)
        protein = nutrition.get("protein", 0)
        calories = nutrition.get("calories", 0)

        if sugar > 15:
            tips.append("🍭 Eat less sugar — try fruit-based desserts or reduce portion size")
        if sodium > 600:
            tips.append("🧂 High in sodium — limit to once a week and drink extra water")
        if fat > 20:
            tips.append("🧈 High in fat — balance with lean proteins and vegetables")
        if fiber < 2:
            tips.append("🥦 Low in fiber — pair with a fiber-rich side like salad or whole grains")
        if protein > 20:
            tips.append("💪 Excellent protein source — great for muscle building and satiety")
        if calories > 400:
            tips.append("🔥 High calorie density — consider smaller portions and increase physical activity")
        if label == "Healthy":
            tips.append("✅ This is a nutritious choice — keep up the healthy eating!")
        if fiber > 5:
            tips.append("🌾 Great source of dietary fiber — supports gut health and digestion")

        return tips[:5]  # Limit to 5 most relevant

    def _get_alternatives(self, food_name: str, label: str) -> list:
        """Suggest healthier alternatives."""
        if label == "Healthy":
            return ["Your current choice is already healthy! 🎉"]

        name = food_name.lower()
        alternatives_map = {
            "pizza": ["Cauliflower crust pizza with veggies", "Flatbread with hummus and veggies", "Zucchini pizza bites"],
            "burger": ["Turkey burger with avocado", "Portobello mushroom burger", "Salmon burger"],
            "french fries": ["Baked sweet potato fries", "Air-fried zucchini strips", "Baked carrot sticks"],
            "fried": ["Grilled version", "Baked alternative", "Air-fried version"],
            "cake": ["Greek yogurt parfait", "Fruit salad with honey", "Dark chocolate with almonds"],
            "ice cream": ["Frozen banana nice cream", "Greek yogurt with berries", "Coconut milk ice cream"],
            "pasta": ["Zucchini noodles (zoodles)", "Whole wheat pasta", "Lentil pasta"],
            "white rice": ["Brown rice", "Cauliflower rice", "Quinoa"],
            "chips": ["Kale chips", "Rice cakes", "Cucumber slices with hummus"],
            "soda": ["Sparkling water with lemon", "Herbal iced tea", "Infused water"],
            "donut": ["Oat bran muffin", "Whole grain toast with nut butter", "Banana with almond butter"],
        }

        for key, alts in alternatives_map.items():
            if key in name:
                return alts

        return [
            "Add a side of mixed vegetables",
            "Choose grilled instead of fried",
            "Opt for whole grain alternatives",
            "Reduce portion size by 25%"
        ]

    def _get_portion_advice(self, nutrition: dict, score: float) -> str:
        """Give specific portion size advice."""
        calories = nutrition.get("calories", 0)
        portion_g = nutrition.get("portion_g", 100)

        if score < 45:
            max_g = max(50, portion_g * 0.5)
            return f"Due to its nutritional profile, limit this to {max_g:.0f}g portions and enjoy occasionally (once a week or less)."
        elif score < 70:
            return f"Enjoy {portion_g}g as an occasional treat (2–3 times per week). Balance with nutrient-dense foods."
        else:
            return f"A {portion_g}g serving fits well into a balanced diet. You can enjoy this regularly."

    def _get_lifestyle_tips(self, nutrition: dict, risks: list) -> list:
        """Generate lifestyle tips based on health risks."""
        tips = []
        risk_names = [r.get("risk", "") for r in risks]

        if any("Diabetes" in r for r in risk_names):
            tips.append("🏃 Regular exercise helps regulate blood sugar levels")
            tips.append("💧 Stay hydrated — drink 8 glasses of water daily")
            tips.append("📅 Eat at consistent times to maintain stable blood sugar")

        if any("Hypertension" in r or "Blood Pressure" in r for r in risk_names):
            tips.append("🧘 Practice stress reduction techniques like meditation or yoga")
            tips.append("🚶 Aim for 30 minutes of moderate exercise most days")
            tips.append("🥗 Follow the DASH diet principles — lots of fruits and vegetables")

        if any("Cholesterol" in r or "Cardiovascular" in r for r in risk_names):
            tips.append("🐟 Increase omega-3 rich foods like fatty fish, flaxseeds, and walnuts")
            tips.append("🥑 Choose healthy fats (avocado, nuts, olive oil) over saturated fats")

        if not tips:
            tips = [
                "💧 Stay hydrated — aim for 8 glasses of water daily",
                "🥗 Balance your plate with half vegetables, quarter protein, quarter grains",
                "🚶 Aim for 150 minutes of moderate activity per week"
            ]

        return tips[:4]

    def _get_personalized_advice(self, nutrition, risks, user_profile):
        """Generate advice specific to user profile."""
        if not user_profile:
            return ["Create a profile for personalized health recommendations! 👤"]

        advice = []
        goal = user_profile.get("goal", "").lower()
        age = user_profile.get("age", 30)
        conditions = str(user_profile.get("health_conditions", "")).lower()

        try:
            age = int(age)
        except (ValueError, TypeError):
            age = 30

        # Goal-based advice
        if "weight loss" in goal or "lose weight" in goal:
            calories = nutrition.get("calories", 0)
            if calories > 300:
                advice.append(f"🎯 Weight Loss Goal: This {calories:.0f} kcal serving is significant — consider a smaller portion or save for a special occasion")
            advice.append("📊 Track your daily caloric intake to maintain a sustainable calorie deficit")

        elif "muscle" in goal or "gain" in goal:
            protein = nutrition.get("protein", 0)
            if protein > 20:
                advice.append("💪 Great protein content for muscle building goals!")
            else:
                advice.append("🥩 Your muscle building goal needs more protein — consider adding lean meats, eggs, or legumes")

        elif "endurance" in goal or "athletic" in goal:
            carbs = nutrition.get("carbohydrates", 0)
            if carbs > 30:
                advice.append("⚡ Good carb content for energy — great pre-workout or recovery meal")

        # Age-based advice
        if age > 50:
            calcium_foods = nutrition.get("calcium", "")
            advice.append(f"👴 At {age}, focus on calcium and vitamin D rich foods for bone health")

        if age < 25:
            advice.append(f"🌱 At {age}, building healthy eating habits now will benefit you lifelong")

        # Condition-based
        if "diabetes" in conditions:
            gi = nutrition.get("glycemic_index", 50)
            advice.append(f"🩸 Diabetes: GI of {gi} — {'low GI, suitable' if gi < 55 else 'moderate GI, consume with caution' if gi < 70 else 'high GI, avoid or pair with protein'}")

        return advice[:4] if advice else ["Looking good — this food aligns with your health profile! 🌟"]

    def _get_meal_pairings(self, food_name: str, nutrition: dict, label: str) -> list:
        """Suggest complementary foods for a balanced meal."""
        protein = nutrition.get("protein", 0)
        fiber = nutrition.get("fiber", 0)
        carbs = nutrition.get("carbohydrates", 0)

        pairings = []

        if protein < 10:
            pairings.append("Add grilled chicken, tofu, or legumes for protein")
        if fiber < 3:
            pairings.append("Pair with a side salad or roasted vegetables for fiber")
        if carbs < 20:
            pairings.append("Consider adding brown rice or sweet potato for sustained energy")
        if label in ["Unhealthy", "Moderate"]:
            pairings.append("Start with a vegetable soup to reduce overall calorie intake")
            pairings.append("Drink water or herbal tea instead of sugary beverages")

        return pairings[:3] if pairings else ["This is a well-balanced meal on its own! 🎉"]
