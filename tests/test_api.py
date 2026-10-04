"""
Test Suite for NutriScan AI Backend
Tests API endpoints, nutrition analysis, and health scoring.

Run: pytest tests/ -v
"""

import json
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def app():
    """Create test Flask application."""
    from backend.app import create_app
    app = create_app('testing')
    yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


# ─── Health Check ─────────────────────────────────────────────────────────────
class TestHealthEndpoint:
    def test_health_check(self, client):
        res = client.get('/api/health')
        assert res.status_code == 200
        data = res.get_json()
        assert data['status'] == 'healthy'
        assert 'version' in data


# ─── Text Analysis ────────────────────────────────────────────────────────────
class TestAnalyzeEndpoint:
    def test_analyze_food_by_name(self, client):
        res = client.post('/api/analyze',
            data=json.dumps({'food_name': 'pizza', 'portion_size': 100}),
            content_type='application/json')
        assert res.status_code == 200
        data = res.get_json()
        assert data['status'] == 'success'
        assert 'nutrition' in data
        assert 'health_score' in data
        assert 'recommendations' in data

    def test_analyze_returns_nutrition_fields(self, client):
        res = client.post('/api/analyze',
            data=json.dumps({'food_name': 'chicken'}),
            content_type='application/json')
        n = res.get_json()['nutrition']
        for field in ['calories', 'protein', 'fat', 'carbohydrates']:
            assert field in n, f"Missing field: {field}"

    def test_analyze_ingredients(self, client):
        res = client.post('/api/analyze',
            data=json.dumps({'ingredients': ['chicken breast', 'rice', 'broccoli']}),
            content_type='application/json')
        assert res.status_code == 200
        data = res.get_json()
        assert data['status'] == 'success'

    def test_analyze_missing_input(self, client):
        res = client.post('/api/analyze',
            data=json.dumps({}),
            content_type='application/json')
        assert res.status_code == 400

    def test_analyze_portion_scaling(self, client):
        res100 = client.post('/api/analyze',
            data=json.dumps({'food_name': 'pizza', 'portion_size': 100}),
            content_type='application/json').get_json()
        res200 = client.post('/api/analyze',
            data=json.dumps({'food_name': 'pizza', 'portion_size': 200}),
            content_type='application/json').get_json()

        cal100 = res100['nutrition']['calories']
        cal200 = res200['nutrition']['calories']
        # 200g should have ~2x calories
        assert abs(cal200 - cal100 * 2) < 5, "Portion scaling incorrect"


# ─── Nutrition Analysis ───────────────────────────────────────────────────────
class TestNutritionAnalyzer:
    def test_known_food_lookup(self):
        from backend.utils.nutrition import NutritionAnalyzer
        na = NutritionAnalyzer()
        data = na.get_nutrition('pizza', 100)
        assert data['calories'] > 0
        assert data['protein'] >= 0
        assert data['fat'] >= 0

    def test_unknown_food_estimate(self):
        from backend.utils.nutrition import NutritionAnalyzer
        na = NutritionAnalyzer()
        data = na.get_nutrition('mystery food xyz', 100)
        assert data['calories'] > 0

    def test_ingredient_analysis(self):
        from backend.utils.nutrition import NutritionAnalyzer
        na = NutritionAnalyzer()
        data = na.analyze_ingredients(['chicken breast', 'rice'], 200)
        assert data['protein'] > 0
        assert data['carbohydrates'] > 0

    def test_search_foods(self):
        from backend.utils.nutrition import NutritionAnalyzer
        na = NutritionAnalyzer()
        results = na.search_foods('pizza')
        assert isinstance(results, list)
        assert len(results) > 0


# ─── Health Scoring ───────────────────────────────────────────────────────────
class TestHealthScorer:
    def test_healthy_food_score(self):
        from backend.utils.health_scorer import HealthScorer
        scorer = HealthScorer()
        nutrition = {
            'calories': 80, 'protein': 15, 'fat': 2, 'carbohydrates': 5,
            'fiber': 4, 'sugar': 2, 'sodium': 150, 'cholesterol': 40, 'portion_g': 100
        }
        result = scorer.score(nutrition)
        assert result['score'] >= 70
        assert result['label'] == 'Healthy'

    def test_unhealthy_food_score(self):
        from backend.utils.health_scorer import HealthScorer
        scorer = HealthScorer()
        nutrition = {
            'calories': 550, 'protein': 5, 'fat': 35, 'carbohydrates': 60,
            'fiber': 0.5, 'sugar': 45, 'sodium': 1200, 'cholesterol': 80, 'portion_g': 100
        }
        result = scorer.score(nutrition)
        assert result['score'] < 45
        assert result['label'] == 'Unhealthy'

    def test_score_range(self):
        from backend.utils.health_scorer import HealthScorer
        scorer = HealthScorer()
        for nutrition in [
            {'calories': 200, 'protein': 10, 'fat': 8, 'carbohydrates': 25,
             'fiber': 2, 'sugar': 5, 'sodium': 300, 'cholesterol': 30, 'portion_g': 100},
        ]:
            result = scorer.score(nutrition)
            assert 0 <= result['score'] <= 100

    def test_risks_detected(self):
        from backend.utils.health_scorer import HealthScorer
        scorer = HealthScorer()
        nutrition = {
            'calories': 300, 'protein': 8, 'fat': 10, 'carbohydrates': 50,
            'fiber': 0.5, 'sugar': 40, 'sodium': 900, 'cholesterol': 30, 'portion_g': 100
        }
        result = scorer.score(nutrition)
        assert len(result['risks']) > 0

    def test_personalized_scoring_diabetes(self):
        from backend.utils.health_scorer import HealthScorer
        scorer = HealthScorer()
        nutrition = {
            'calories': 300, 'protein': 5, 'fat': 5, 'carbohydrates': 60,
            'fiber': 1, 'sugar': 35, 'sodium': 200, 'cholesterol': 10, 'portion_g': 100
        }
        result_no_profile = scorer.score(nutrition)
        result_with_profile = scorer.score(nutrition, {'health_conditions': ['diabetes']})
        # With diabetes profile, score should be lower
        assert result_with_profile['score'] <= result_no_profile['score']


# ─── Recommendations ──────────────────────────────────────────────────────────
class TestRecommendationEngine:
    def test_recommendations_structure(self):
        from backend.utils.recommendations import RecommendationEngine
        from backend.utils.health_scorer import HealthScorer

        engine = RecommendationEngine()
        scorer = HealthScorer()
        nutrition = {'calories': 300, 'protein': 10, 'fat': 15, 'carbohydrates': 30,
                     'fiber': 2, 'sugar': 10, 'sodium': 500, 'cholesterol': 40, 'portion_g': 100}
        health = scorer.score(nutrition)
        recs = engine.get_recommendations('pizza', nutrition, health)

        assert 'general_tips' in recs
        assert 'healthier_alternatives' in recs
        assert 'lifestyle_tips' in recs
        assert 'portion_advice' in recs

    def test_alternatives_for_unhealthy_food(self):
        from backend.utils.recommendations import RecommendationEngine
        engine = RecommendationEngine()
        alts = engine._get_alternatives('french fries', 'Unhealthy')
        assert len(alts) > 0
        assert alts[0] != 'Your current choice is already healthy! 🎉'


# ─── History Endpoint ─────────────────────────────────────────────────────────
class TestHistoryEndpoint:
    def test_history_returns_list(self, client):
        res = client.get('/api/history?user_id=test_user')
        assert res.status_code == 200
        data = res.get_json()
        assert 'history' in data
        assert isinstance(data['history'], list)


# ─── Nutrients Endpoint ───────────────────────────────────────────────────────
class TestNutrientsEndpoint:
    def test_get_nutrients(self, client):
        res = client.get('/api/nutrients/pizza')
        assert res.status_code == 200
        data = res.get_json()
        assert data['status'] == 'success'
        assert 'nutrition' in data

    def test_get_nutrients_with_portion(self, client):
        res = client.get('/api/nutrients/pizza?portion=200')
        data = res.get_json()
        assert data['nutrition']['portion_g'] == 200


# ─── Search Endpoint ──────────────────────────────────────────────────────────
class TestSearchEndpoint:
    def test_search_returns_results(self, client):
        res = client.get('/api/search?q=piz')
        assert res.status_code == 200
        data = res.get_json()
        assert 'results' in data

    def test_search_short_query_rejected(self, client):
        res = client.get('/api/search?q=p')
        assert res.status_code == 400
