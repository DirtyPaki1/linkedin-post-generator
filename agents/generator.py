import os
import re
from typing import List, Dict, Any
from groq import Groq
from config import get_settings

settings = get_settings()

class PostGenerator:
    def __init__(self, temperature: float = None):
        self.temperature = temperature or settings.temperature
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = "llama-3.3-70b-versatile"
    
    def generate_posts(self, topic: str, tone: str = None, 
                       length: str = None, audience: str = None,
                       num_posts: int = None) -> List[Dict[str, Any]]:
        
        tone = tone or settings.default_tone
        num_posts = num_posts or settings.default_num_posts
        
        prompt = f"""You are an expert LinkedIn content creator who writes data-driven, evidence-based posts.

Topic: {topic}
Tone: {tone}

Generate {num_posts} unique, engaging LinkedIn posts that INCLUDE SPECIFIC FACTS, STATISTICS, OR DATA POINTS.

Each post must:
1. Start with a powerful hook
2. Include at least 2-3 specific facts, statistics, or data points (with numbers, percentages, or specific dates)
3. Share valuable insights based on these facts
4. End with a question
5. Include 3-5 relevant hashtags

Examples of fact-rich statements:
- "85% of companies increased productivity after implementing AI"
- "According to a 2024 study, remote workers are 47% more productive"
- "The AI market is projected to reach $1.8 trillion by 2030"
- "Companies using AI report a 30% reduction in operational costs"

Format each post exactly like this:

---POST 1---
[Your content here with specific facts/statistics]
Hashtags: #tag1 #tag2 #tag3

---POST 2---
[Your content here with specific facts/statistics]
Hashtags: #tag1 #tag2 #tag3

Make each post distinct, valuable, and backed by data.
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=2000
        )
        
        content = response.choices[0].message.content
        return self._parse_posts(content, num_posts)
    
    def _parse_posts(self, content: str, expected_count: int) -> List[Dict[str, Any]]:
        posts = []
        
        blocks = re.split(r'---POST \d+---', content)
        
        for block in blocks:
            if not block.strip():
                continue
            
            hashtag_match = re.search(r'Hashtags?:\s*(.+?)(?:\n|$)', block, re.IGNORECASE)
            hashtags = []
            if hashtag_match:
                hashtags_str = hashtag_match.group(1)
                hashtags = [tag.strip() for tag in re.findall(r'#\w+', hashtags_str)]
            
            text = block
            if hashtag_match:
                text = block[:block.lower().find('hashtags:')]
            
            text = text.strip()
            
            if text and len(text) > 20:
                posts.append({
                    'content': text,
                    'hashtags': hashtags
                })
        
        if not posts:
            for line in content.split('\n\n'):
                if len(line.strip()) > 50:
                    hashtags = re.findall(r'#\w+', line)
                    text = re.sub(r'#\w+', '', line).strip()
                    if text:
                        posts.append({
                            'content': text,
                            'hashtags': hashtags[:5]
                        })
        
        return posts[:expected_count]
