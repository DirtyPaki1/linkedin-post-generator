import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import plotly.express as px
import plotly.graph_objects as go
from textblob import TextBlob
import re
from models import get_db, PostAnalytics, Post
from sqlalchemy import func, desc
from utils.logger import get_logger

logger = get_logger(__name__)

class PerformanceAnalyzer:
    """Analyze post performance and provide recommendations."""
    
    @staticmethod
    def analyze_post(post: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive post analysis."""
        content = post.get('content', '')
        hashtags = post.get('hashtags', [])
        
        analysis = {
            'strengths': [],
            'improvements': [],
            'score': 0,
            'suggested_hashtags': [],
            'readability': {},
            'sentiment': {},
            'engagement_predictors': {}
        }
        
        # Sentiment analysis
        blob = TextBlob(content)
        analysis['sentiment'] = {
            'polarity': blob.sentiment.polarity,
            'subjectivity': blob.sentiment.subjectivity
        }
        
        # Readability
        words = content.split()
        sentences = content.split('.')
        avg_word_length = sum(len(w) for w in words) / len(words) if words else 0
        avg_sentence_length = len(words) / len(sentences) if sentences else 0
        
        analysis['readability'] = {
            'word_count': len(words),
            'sentence_count': len(sentences),
            'avg_word_length': avg_word_length,
            'avg_sentence_length': avg_sentence_length
        }
        
        # Engagement predictors
        engagement = {
            'has_question': '?' in content,
            'has_exclamation': '!' in content,
            'has_call_to_action': any(word in content.lower() for word in ['comment', 'share', 'tag', 'think', 'agree', 'join']),
            'has_personal_touch': any(word in content.lower() for word in ['i', 'we', 'our', 'my']),
            'has_data': bool(re.search(r'\d+%|\d+\.\d+|\$?\d+', content)),
            'has_storytelling': any(word in content.lower() for word in ['story', 'once', 'remember', 'experience']),
            'has_industry_insights': any(word in content.lower() for word in ['insight', 'learn', 'discover', 'key', 'important'])
        }
        analysis['engagement_predictors'] = engagement
        
        # Score calculation
        score = 0
        
        # Hook strength (first sentence)
        first_sentence = content.split('.')[0] if content else ''
        if '?' in first_sentence or '!' in first_sentence:
            analysis['strengths'].append('Strong hook with question/exclamation')
            score += 20
        elif len(first_sentence) < 20:
            analysis['improvements'].append('Add a stronger hook in first sentence')
            score += 5
        
        # Length check
        word_count = len(words)
        if 100 <= word_count <= 200:
            analysis['strengths'].append('Optimal length for LinkedIn')
            score += 20
        elif word_count < 50:
            analysis['improvements'].append('Post is too short - expand with insights')
            score += 5
        elif word_count > 300:
            analysis['improvements'].append('Post is too long - consider condensing')
            score += 10
        
        # Hashtags
        if 3 <= len(hashtags) <= 5:
            analysis['strengths'].append('Good number of hashtags')
            score += 15
        elif len(hashtags) > 5:
            analysis['improvements'].append('Too many hashtags - stick to 3-5')
            score += 5
        
        # Call to action
        if engagement['has_call_to_action']:
            analysis['strengths'].append('Includes call to action')
            score += 15
        else:
            analysis['improvements'].append('Add a call to action')
        
        # Personal touch
        if engagement['has_personal_touch']:
            analysis['strengths'].append('Personal tone - builds connection')
            score += 10
        else:
            analysis['improvements'].append('Add personal perspective')
        
        # Data/statistics
        if engagement['has_data']:
            analysis['strengths'].append('Includes data/statistics - adds credibility')
            score += 15
        
        # Storytelling
        if engagement['has_storytelling']:
            analysis['strengths'].append('Uses storytelling - engaging')
            score += 10
        
        # Sentiment bonus
        if blob.sentiment.polarity > 0.3:
            analysis['strengths'].append('Positive sentiment - good for engagement')
            score += 5
        
        # Generate suggested hashtags
        suggested = []
        words_lower = content.lower()
        popular_tags = {
            'AI': 'artificial intelligence',
            'Tech': 'technology',
            'Innovation': 'innovation',
            'Growth': 'growth',
            'Leadership': 'leadership',
            'Strategy': 'strategy',
            'Marketing': 'marketing',
            'Future': 'future',
            'Data': 'data',
            'Career': 'career'
        }
        
        for tag, keyword in popular_tags.items():
            if keyword in words_lower and tag.lower() not in [h.lower().strip('#') for h in hashtags]:
                suggested.append(f"#{tag}")
        
        analysis['suggested_hashtags'] = suggested[:3]
        
        # Cap score at 100
        analysis['score'] = min(score, 100)
        
        return analysis
    
    def get_best_practices(self) -> List[str]:
        """Return LinkedIn best practices."""
        return [
            "Start with a compelling hook or question",
            "Keep posts between 100-200 words",
            "Use 3-5 relevant hashtags",
            "Include a clear call to action",
            "Add personal experiences or insights",
            "Use data and statistics when possible",
            "Ask questions to encourage engagement",
            "Share valuable, actionable insights"
        ]

class AnalyticsTracker:
    """Track and analyze post performance."""
    
    def __init__(self):
        self.db = get_db()
    
    def track_post(self, post: Dict[str, Any], topic: str, tone: str, length: str) -> int:
        """Track a generated post with analytics."""
        try:
            # Create post record
            db_post = Post(
                topic=topic,
                content=post['content'],
                tone=tone,
                length=length,
                audience=post.get('audience', 'professionals'),
                language=post.get('language', 'en'),
                hashtags=post.get('hashtags', []),
                metadata=post.get('metadata', {})
            )
            self.db.add(db_post)
            self.db.flush()
            
            # Create analytics
            analysis = PerformanceAnalyzer.analyze_post(post)
            
            analytics = PostAnalytics(
                post_id=db_post.id,
                engagement_score=analysis['score'],
                word_count=analysis['readability']['word_count'],
                character_count=len(post['content']),
                readability_score=analysis['readability']['avg_sentence_length'],
                sentiment_score=analysis['sentiment']['polarity'],
                predicted_views=int(analysis['score'] * 10),
                predicted_likes=int(analysis['score'] * 3),
                predicted_comments=int(analysis['score'] * 1.5),
                metadata=analysis
            )
            self.db.add(analytics)
            self.db.commit()
            
            logger.info(f"Tracked post {db_post.id} with score {analysis['score']}")
            return db_post.id
            
        except Exception as e:
            logger.error(f"Failed to track post: {e}")
            self.db.rollback()
            return 0
    
    def get_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get analytics trends."""
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            results = self.db.query(
                Post.tone,
                func.avg(PostAnalytics.engagement_score).label('avg_engagement'),
                func.count(PostAnalytics.id).label('count')
            ).join(PostAnalytics).filter(
                Post.created_at >= cutoff
            ).group_by(Post.tone).all()
            
            if not results:
                return {'message': 'No data available'}
            
            df = pd.DataFrame([{
                'tone': r.tone,
                'avg_engagement': r.avg_engagement,
                'count': r.count
            } for r in results])
            
            return {
                'best_tone': df.loc[df['avg_engagement'].idxmax(), 'tone'],
                'most_used_tone': df.loc[df['count'].idxmax(), 'tone'],
                'average_engagement': df['avg_engagement'].mean(),
                'total_posts': df['count'].sum(),
                'trends': df.to_dict('records')
            }
            
        except Exception as e:
            logger.error(f"Failed to get trends: {e}")
            return {'error': str(e)}
    
    def get_engagement_chart(self, days: int = 30) -> Optional[go.Figure]:
        """Generate engagement trend chart."""
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            results = self.db.query(
                Post.created_at,
                Post.tone,
                PostAnalytics.engagement_score
            ).join(PostAnalytics).filter(
                Post.created_at >= cutoff
            ).order_by(Post.created_at).all()
            
            if not results:
                return None
            
            df = pd.DataFrame([{
                'date': r.created_at.date(),
                'tone': r.tone,
                'engagement_score': r.engagement_score
            } for r in results])
            
            fig = px.line(df, x='date', y='engagement_score', color='tone',
                          title='Engagement Score Trends',
                          labels={'engagement_score': 'Score', 'date': 'Date'})
            
            fig.update_layout(
                hovermode='x unified',
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=0.01
                )
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Failed to create chart: {e}")
            return None