"""
CareerPilot AI — Code Service
Handles code review and SQL coaching operations.
"""

from backend.services.ai_service import AIService
from backend.models.project import CodeReviewModel, SQLQueryModel


class CodeService:
    """Business logic for code review operations."""

    @staticmethod
    def review_code(user_id: int, code: str, language: str = "python") -> dict:
        """Run AI code review and save results."""
        review = AIService.review_code(code, language)
        
        # Save to database
        try:
            CodeReviewModel.create(
                user_id=user_id,
                language=language,
                code_input=code,
                review_data=review
            )
        except Exception as e:
            print(f"[WARN] Failed to save code review: {str(e)}")
        
        return review

    @staticmethod
    def get_history(user_id: int) -> list[dict]:
        """Get code review history for a user."""
        from backend.utils.helpers import safe_json_loads
        reviews = CodeReviewModel.get_by_user(user_id)
        for r in reviews:
            r['review_data'] = safe_json_loads(r.get('review_data', '{}'), {})
        return reviews


class SQLCoachService:
    """Business logic for SQL coaching operations."""

    @staticmethod
    def analyze_query(user_id: int, query: str) -> dict:
        """Analyze a SQL query and save results."""
        analysis = AIService.analyze_sql(query)
        
        # Save to database
        try:
            SQLQueryModel.create(
                user_id=user_id,
                query_input=query,
                analysis_data=analysis
            )
        except Exception as e:
            print(f"[WARN] Failed to save SQL analysis: {str(e)}")
        
        return analysis

    @staticmethod
    def get_history(user_id: int) -> list[dict]:
        """Get SQL analysis history for a user."""
        from backend.utils.helpers import safe_json_loads
        queries = SQLQueryModel.get_by_user(user_id)
        for q in queries:
            q['analysis_data'] = safe_json_loads(q.get('analysis_data', '{}'), {})
        return queries
