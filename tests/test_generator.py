import pytest
from unittest.mock import Mock, patch
from agents.generator import PostGenerator

class TestPostGenerator:
    
    def test_initialization(self):
        """Test generator initialization."""
        generator = PostGenerator(model_type="groq")
        assert generator.model_type == "groq"
        assert generator.temperature == 0.7
    
    def test_parse_response(self):
        """Test response parsing."""
        generator = PostGenerator()
        response = """
        POST #1:
        This is a test post.
        HASHTAGS: #AI, #Tech
        """
        posts = generator._parse_response(response, 1)
        assert len(posts) == 1
        assert "test post" in posts[0]['content']
        assert "#AI" in posts[0]['hashtags']
    
    @patch('agents.generator.ChatGroq')
    def test_generate_posts(self, mock_groq):
        """Test post generation."""
        mock_instance = Mock()
        mock_instance.invoke.return_value.content = """
        POST #1:
        Test post content.
        HASHTAGS: #Test
        """
        mock_groq.return_value = mock_instance
        
        generator = PostGenerator(model_type="groq")
        posts = generator.generate_posts("test topic", num_posts=1)
        
        assert len(posts) == 1
        assert "Test post content" in posts[0]['content']