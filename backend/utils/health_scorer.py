"""
Health Scorer
Computes a health score and identifies health risks for food items.
Considers both nutritional content and user profile.
"""

import logging
from typing import Optional

logger = logging.getLogger("utils.health_scorer")

# Daily recommended values (based on 2000 kcal diet, FDA guidelines)
DAILY_RECOMMENDATIONS = {
    "calories": 2000,
    "protein": 50,       # grams
    "fat": 65,           # grams
    "saturated_fat": 20, # grams
    "carbohydrates": 300, # grams
    "fiber": 28,         # grams
    "sugar": 50,         # grams (added)
    "sodium": 2300,      # mg
    "cholesterol": 300,  # mg
}

# Health risk thresholds per 100g serving
RISK_THRESHOLDS = {
    "high_sodium": 600,      # mg per 100g
    "high_sugar": 15,        # g per 100g
    "high_fat": 20,          # g per 100g
    "high_calories": 400,    # kcal per 100g
    "high_cholesterol": 100, # mg per 100g
    "low_fiber": 1.0,        # g per 100g (warning if below)
}


class HealthScorer:
    """Computes health score and risk assessment for food items."""

    def score(self, nutrition: dict, user_profile: Optional[dict] = None) -> dict:
        """
        Calculate comprehensive health score.

        Args:
            nutrition: Nutritional data dict (per serving)
            user_profile: Optional user profile for personalized scoring

        Returns:
            dict with score, label, risks, and breakdown
        """
        # Base score starts at 100
        score = 100.0
        penalties = []
        benefits = []
        risks = []

        # Extract values
        calories = nutrition.get("calories", 0)
        protein = nutrition.get("protein", 0)
        fat = nutrition.get("fat", 0)
        carbs = nutrition.get("carbohydrates", 0)
        fiber = nutrition.get("fiber", 0)
        sugar = nutrition.get("sugar", 0)
        sodium = nutrition.get("sodium", 0)
        cholesterol = nutrition.get("cholesterol", 0)
        gi = nutrition.get("glycemic_index", 50)
        portion_g = nutrition.get("portion_g", 100)
        scale = portion_g / 100.0

        # ─── Penalties ────────────────────────────────────────────────────────

        # High calorie density (per 100g, NOT scaled portion)
        cal_per_100g = calories / max(scale, 0.01)
        if cal_per_100g > 450:
            penalty = min((cal_per_100g - 450) / 8, 30)
            score -= penalty
            penalties.append(f"Very high calorie density ({cal_per_100g:.0f} kcal/100g)")
        elif cal_per_100g > 300:
            penalty = min((cal_per_100g - 300) / 15, 15)
            score -= penalty
            penalties.append(f"High calorie density ({cal_per_100g:.0f} kcal/100g)")

        # High sugar (per 100g)
        sugar_per_100g = sugar / max(scale, 0.01)
        if sugar_per_100g > 20:
            penalty = min((sugar_per_100g - 20) / 2, 30)
            score -= penalty
            penalties.append(f"Very high sugar content ({sugar_per_100g:.1f}g/100g)")
            risks.append({
                "risk": "Diabetes Risk",
                "level": "High",
                "reason": f"Sugar content ({sugar_per_100g:.1f}g/100g) is significantly above recommended limits",
                "icon": "🩸"
            })
        elif sugar_per_100g > 10:
            penalty = min((sugar_per_100g - 10) / 3, 18)
            score -= penalty
            penalties.append(f"High sugar content ({sugar_per_100g:.1f}g/100g)")
            risks.append({
                "risk": "Diabetes Risk",
                "level": "Moderate",
                "reason": "Sugar content is above recommended limits",
                "icon": "🩸"
            })

        # High sodium (per 100g)
        sodium_per_100g = sodium / max(scale, 0.01)
        if sodium_per_100g > 700:
            penalty = min((sodium_per_100g - 700) / 20, 35)
            score -= penalty
            penalties.append(f"Very high sodium ({sodium_per_100g:.0f}mg/100g)")
            risks.append({
                "risk": "Hypertension Risk",
                "level": "High",
                "reason": f"Sodium content ({sodium_per_100g:.0f}mg/100g) far exceeds heart-healthy limits",
                "icon": "❤️"
            })
        elif sodium_per_100g > 400:
            penalty = min((sodium_per_100g - 400) / 30, 20)
            score -= penalty
            penalties.append(f"High sodium content ({sodium_per_100g:.0f}mg/100g)")
            risks.append({
                "risk": "Hypertension Risk",
                "level": "Moderate",
                "reason": "Sodium content is above recommended heart-healthy limits",
                "icon": "❤️"
            })

        # High fat (per 100g)
        fat_per_100g = fat / max(scale, 0.01)
        if fat_per_100g > 20:
            penalty = min((fat_per_100g - 20) / 2, 20)
            score -= penalty
            penalties.append(f"High fat content ({fat_per_100g:.1f}g/100g)")
            risks.append({
                "risk": "High Cholesterol Risk",
                "level": "Moderate",
                "reason": "High fat content may contribute to elevated cholesterol",
                "icon": "💊"
            })

        # High cholesterol
        if cholesterol > 100:
            penalty = min((cholesterol - 100) / 8, 20)
            score -= penalty
            penalties.append(f"High dietary cholesterol ({cholesterol:.0f}mg)")
            risks.append({
                "risk": "Cardiovascular Risk",
                "level": "Moderate",
                "reason": "High cholesterol content may affect heart health",
                "icon": "🫀"
            })

        # High glycemic index
        if gi > 65:
            penalty = min((gi - 65) / 3, 15)
            score -= penalty
            penalties.append(f"High glycemic index ({gi})")
            if not any(r["risk"] == "Diabetes Risk" for r in risks):
                risks.append({
                    "risk": "Blood Sugar Spike",
                    "level": "Moderate",
                    "reason": f"High GI ({gi}) causes rapid blood sugar elevation",
                    "icon": "📈"
                })

        # ─── Benefits ─────────────────────────────────────────────────────────

        # High protein
        if protein > 20:
            boost = min((protein - 20) / 3, 10)
            score += boost
            benefits.append(f"Excellent protein source ({protein:.1f}g)")
        elif protein > 10:
            boost = min((protein - 10) / 5, 5)
            score += boost
            benefits.append(f"Good protein content ({protein:.1f}g)")

        # High fiber
        fiber_per_100g = fiber / max(scale, 0.01)
        if fiber_per_100g > 5:
            score += 8
            benefits.append(f"High fiber content ({fiber_per_100g:.1f}g/100g)")
        elif fiber_per_100g > 3:
            score += 5
            benefits.append(f"Good fiber content ({fiber_per_100g:.1f}g/100g)")
        elif fiber_per_100g < 1:
            score -= 3
            penalties.append("Low fiber content")

        # ─── User profile adjustments ──────────────────────────────────────
        if user_profile:
            score, risks = self._apply_profile_adjustments(score, risks, nutrition, user_profile)

        # Clamp score
        score = max(0, min(100, score))

        # Determine label
        if score >= 70:
            label = "Healthy"
            color = "#22c55e"
            emoji = "✅"
        elif score >= 45:
            label = "Moderate"
            color = "#f59e0b"
            emoji = "⚠️"
        else:
            label = "Unhealthy"
            color = "#ef4444"
            emoji = "❌"

        return {
            "score": round(score, 1),
            "label": label,
            "color": color,
            "emoji": emoji,
            "risks": risks,
            "benefits": benefits,
            "penalties": penalties,
            "daily_values": self._calculate_daily_values(nutrition),
            "nutrient_breakdown": {
                "calories_percent": round(calories / DAILY_RECOMMENDATIONS["calories"] * 100, 1),
                "protein_percent": round(protein / DAILY_RECOMMENDATIONS["protein"] * 100, 1),
                "fat_percent": round(fat / DAILY_RECOMMENDATIONS["fat"] * 100, 1),
                "carbs_percent": round(carbs / DAILY_RECOMMENDATIONS["carbohydrates"] * 100, 1),
                "fiber_percent": round(fiber / DAILY_RECOMMENDATIONS["fiber"] * 100, 1),
                "sodium_percent": round(sodium / DAILY_RECOMMENDATIONS["sodium"] * 100, 1),
            }
        }

    def _apply_profile_adjustments(self, score, risks, nutrition, user_profile):
        """Apply user-specific health adjustments."""
        conditions = user_profile.get("health_conditions", [])
        if isinstance(conditions, str):
            import json
            try:
                conditions = json.loads(conditions)
            except Exception:
                conditions = [conditions]

        sugar = nutrition.get("sugar", 0)
        sodium = nutrition.get("sodium", 0)
        fat = nutrition.get("fat", 0)
        cholesterol = nutrition.get("cholesterol", 0)

        if "diabetes" in str(conditions).lower():
            if sugar > 10:
                score -= 10
                risks.append({
                    "risk": "Diabetes Management",
                    "level": "High",
                    "reason": "High sugar content is particularly risky for diabetics",
                    "icon": "🩸",
                    "personalized": True
                })

        if "hypertension" in str(conditions).lower() or "high blood pressure" in str(conditions).lower():
            if sodium > 400:
                score -= 10
                risks.append({
                    "risk": "Blood Pressure",
                    "level": "High",
                    "reason": "Sodium intake should be strictly limited for hypertension",
                    "icon": "💉",
                    "personalized": True
                })

        if "heart disease" in str(conditions).lower() or "cholesterol" in str(conditions).lower():
            if fat > 15 or cholesterol > 100:
                score -= 8
                risks.append({
                    "risk": "Heart Health",
                    "level": "High",
                    "reason": "High fat/cholesterol is particularly harmful with existing heart conditions",
                    "icon": "🫀",
                    "personalized": True
                })

        # Age-based adjustments
        age = user_profile.get("age", 0)
        try:
            age = int(age)
        except (ValueError, TypeError):
            age = 0

        if age > 60 and sodium > 500:
            score -= 5
            risks.append({
                "risk": "Age-related Sodium Risk",
                "level": "Moderate",
                "reason": "Older adults are more sensitive to high sodium intake",
                "icon": "👴",
                "personalized": True
            })

        return score, risks

    def _calculate_daily_values(self, nutrition: dict) -> dict:
        """Calculate % of daily recommended values."""
        dv = {}
        for nutrient, daily in DAILY_RECOMMENDATIONS.items():
            value = nutrition.get(nutrient, 0)
            dv[nutrient] = round(value / daily * 100, 1)
        return dv
