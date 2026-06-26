import os
import json
from typing import List, Dict, Any, Optional
from langchain.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from dotenv import load_dotenv
import time
from config import get_settings
from utils.cache import cached, redis_cache
from utils.logger import get_logger, log_performance

load_dotenv()
settings = get_settings()
logger = get_logger(__name__)

class PostGenerator:
    """Enhanced agent for generating LinkedIn posts with caching."""
    
    def __init__(self, model_type: str = None, temperature: float = None):
        """
        Initialize the generator with specified LLM.
        
        Args:
            model_type: 'groq', 'google', 'openai'
            temperature: Creativity temperature (0.0-1.0)
        """
        self.model_type = model_type or settings.default_model
        self.temperature = temperature or settings.temperature
        self.max_tokens = settings.max_tokens
        self.llm = self._initialize_llm()
        self.prompt_template = self._create_prompt_template()
        self.prompt_templates = self._create_multi_style_templates()
        logger.info(f"Initialized PostGenerator with {self.model_type}")
    
    def _initialize_llm(self):
        """Initialize the LLM based on model type with streaming support."""
        try:
            if self.model_type == "groq":
                return ChatGroq(
                    model="llama3-70b-8192",
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    api_key=settings.groq_api_key,
                    streaming=True,
                    callbacks=[StreamingStdOutCallbackHandler()]
                )
            elif self.model_type == "google":
                return ChatGoogleGenerativeAI(
                    model="gemini-pro",
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    google_api_key=settings.google_api_key
                )
            elif self.model_type == "openai":
                return ChatOpenAI(
                    model="gpt-4-turbo-preview",
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    api_key=settings.openai_api_key,
                    streaming=True,
                    callbacks=[StreamingStdOutCallbackHandler()]
                )
            else:
                raise ValueError(f"Unsupported model type: {self.model_type}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            raise
    
    def _create_prompt_template(self):
        """Create the primary prompt template."""
        template = """
        You are an expert LinkedIn content creator with years of experience writing engaging professional posts.
        
        Topic: {topic}
        Tone: {tone}
        Length: {length}
        Target Audience: {audience}
        
        Generate {num_posts} unique LinkedIn posts about the topic above.
        
        Requirements:
        1. Start with a compelling hook in the first 2-3 lines
        2. Include insights, personal experience, or data
        3. End with a question to encourage engagement
        4. Include 3-5 relevant hashtags
        5. Match the {tone} tone throughout
        6. Keep to {length} length
        7. Use {language} language
        
        Format each post exactly as:
        POST #:
        [content]
        HASHTAGS: [comma-separated hashtags]
        
        Make each post distinct and valuable to the {audience} audience.
        
        Posts:
        """
        
        return ChatPromptTemplate.from_template(template)
    
    def _create_multi_style_templates(self):
        """Create prompt templates for different writing styles."""
        return {
            'storytelling': """
                Tell a compelling story about {topic}. Start with a personal anecdote,
                build up to the main insight, and end with a reflection. Make it relatable
                and emotional. Include a call to action.
            """,
            'data_driven': """
                Write a data-driven post about {topic}. Start with a surprising statistic,
                explain its implications, and provide actionable insights. Back up claims
                with data points.
            """,
            'thought_leadership': """
                Write a thought leadership piece on {topic}. Challenge conventional wisdom,
                present a unique perspective, and invite discussion. Show expertise and
                vision.
            """
        }
    
    @cached(ttl=3600)
    def generate_posts(
        self,
        topic: str,
        tone: str = None,
        length: str = None,
        audience: str = None,
        num_posts: int = None,
        language: str = 'en',
        style: str = 'default'
    ) -> List[Dict[str, Any]]:
        """
        Generate LinkedIn posts with caching.
        
        Returns:
            List of dictionaries with 'content', 'hashtags', and metadata
        """
        start_time = time.time()
        
        # Use default values from settings
        tone = tone or settings.default_tone
        length = length or settings.default_length
        audience = audience or settings.default_audience
        num_posts = num_posts or settings.default_num_posts
        
        logger.info(f"Generating {num_posts} posts for topic: {topic}")
        
        # Check cache first (Redis)
        cache_key = f"posts:{topic}:{tone}:{length}:{audience}:{num_posts}:{language}:{style}"
        cached_result = redis_cache.get(cache_key)
        if cached_result:
            logger.info(f"Cache hit for {topic}")
            log_performance("generate_posts_cache_hit", time.time() - start_time, {'topic': topic})
            return cached_result
        
        try:
            # Select template based on style
            if style in self.prompt_templates:
                template = self.prompt_templates[style]
                prompt = ChatPromptTemplate.from_template(template)
            else:
                prompt = self.prompt_template
            
            # Format the prompt
            messages = prompt.format_messages(
                topic=topic,
                tone=tone,
                length=length,
                audience=audience,
                num_posts=num_posts,
                language=language
            )
            
            # Get response from LLM
            response = self.llm.invoke(messages)
            
            # Parse the response
            posts = self._parse_response(response.content, num_posts)
            
            # Add metadata
            for post in posts:
                post['metadata'] = {
                    'topic': topic,
                    'tone': tone,
                    'length': length,
                    'audience': audience,
                    'language': language,
                    'style': style,
                    'model': self.model_type,
                    'temperature': self.temperature,
                    'generated_at': time.time()
                }
            
            # Cache the result
            redis_cache.set(cache_key, posts)
            
            duration = time.time() - start_time
            log_performance("generate_posts", duration, {'topic': topic, 'num_posts': num_posts})
            
            logger.info(f"Successfully generated {len(posts)} posts")
            return posts
            
        except Exception as e:
            logger.error(f"Failed to generate posts: {e}")
            raise
    
    def _parse_response(self, response: str, expected_count: int) -> List[Dict[str, Any]]:
        """Parse the LLM response into structured post objects."""
        posts = []
        
        # Split by POST # pattern
        post_blocks = response.split("POST #")
        
        for block in post_blocks[1:]:  # Skip the first empty split
            if not block.strip():
                continue
            
            # Extract number if present
            lines = block.strip().split('\n')
            content_lines = []
            hashtags = []
            
            in_content = True
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if line.lower().startswith("hashtags:"):
                    hashtags_str = line.replace("hashtags:", "").strip()
                    hashtags = [tag.strip() for tag in hashtags_str.split(",")]
                    in_content = False
                elif in_content and not line.isdigit():
                    content_lines.append(line)
            
            content = " ".join(content_lines).strip()
            
            if content:
                posts.append({
                    "content": content,
                    "hashtags": hashtags
                })
        
        # If we didn't parse enough posts, try fallback
        if len(posts) < expected_count:
            posts = self._fallback_parse(response, expected_count)
        
        # Ensure we have the right number
        while len(posts) < expected_count:
            posts.append({
                "content": f"Generated post about {response[:50]}...",
                "hashtags": ["#AI", "#Tech", "#Innovation"]
            })
        
        return posts[:expected_count]
    
    def _fallback_parse(self, response: str, expected_count: int) -> List[Dict[str, Any]]:
        """Fallback parsing method."""
        posts = []
        lines = response.split("\n")
        current_post = []
        current_hashtags = []
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_post:
                    posts.append({
                        "content": " ".join(current_post),
                        "hashtags": current_hashtags
                    })
                    current_post = []
                    current_hashtags = []
                continue
            
            if line.lower().startswith("hashtags:"):
                hashtags_str = line.replace("hashtags:", "").strip()
                current_hashtags = [tag.strip() for tag in hashtags_str.split(",")]
            else:
                current_post.append(line)
        
        if current_post:
            posts.append({
                "content": " ".join(current_post),
                "hashtags": current_hashtags
            })
        
        return posts