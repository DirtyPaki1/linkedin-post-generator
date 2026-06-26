import pytest
from unittest.mock import Mock, patch
from agents.fact_checker import FactChecker

class TestFactChecker:
    
    def test_extract_claims(self):
        """Test claim extraction."""
        checker = FactChecker()
        text = "85% of marketers use AI. Revenue increased by 30%."
        claims = checker.extract_claims(text)
        assert len(claims) > 0
        assert "85%" in str(claims) or "30%" in str(claims)
    
    @patch('agents.fact_checker.GoogleSearch')
    def test_verify_claim(self, mock_search):
        """Test claim verification."""
        mock_search.return_value.get_dict.return_value = {
            'organic_results': [
                {'snippet': 'Verified fact: 85% of marketers use AI'}
            ]
        }
        
        checker = FactChecker()
        result = checker.verify_claim("85% of marketers use AI")
        
        assert 'status' in result
        assert 'confidence' in result