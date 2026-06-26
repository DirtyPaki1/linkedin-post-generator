from typing import List, Dict, Any
from agents.generator import PostGenerator
from agents.fact_checker import FactChecker
from utils.analytics import PerformanceAnalyzer
from utils.logger import get_logger
import time

logger = get_logger(__name__)

class AgentOrchestrator:
    """Orchestrates multiple agents for end-to-end post generation."""
    
    def __init__(self, model_type: str = None):
        self.model_type = model_type or "groq"
        self.generator = PostGenerator(model_type=self.model_type)
        self.fact_checker = FactChecker(model_type=self.model_type)
        self.analyzer = PerformanceAnalyzer()
        logger.info(f"Initialized AgentOrchestrator with {self.model_type}")
    
    def create_post_pipeline(
        self,
        topic: str,
        tone: str = "professional",
        length: str = "medium",
        audience: str = "professionals",
        num_posts: int = 3,
        enable_fact_check: bool = True,
        language: str = 'en',
        style: str = 'default'
    ) -> Dict[str, Any]:
        """
        Run the complete post generation pipeline.
        
        Returns:
            Dictionary with posts, fact checks, and analytics
        """
        start_time = time.time()
        logger.info(f"Starting pipeline for topic: {topic}")
        
        result = {
            'posts': [],
            'fact_checks': [],
            'analytics': [],
            'summary': {}
        }
        
        # Step 1: Generate posts
        try:
            posts = self.generator.generate_posts(
                topic=topic,
                tone=tone,
                length=length,
                audience=audience,
                num_posts=num_posts,
                language=language,
                style=style
            )
            result['posts'] = posts
            logger.info(f"Generated {len(posts)} posts")
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            result['summary']['error'] = str(e)
            return result
        
        # Step 2: Fact-check each post
        if enable_fact_check:
            for post in posts:
                try:
                    fact_check = self.fact_checker.check_post(post['content'])
                    post['fact_check'] = fact_check
                    result['fact_checks'].append(fact_check)
                except Exception as e:
                    logger.error(f"Fact-check failed for post: {e}")
                    post['fact_check'] = {'status': 'error', 'summary': str(e)}
        
        # Step 3: Analyze each post
        for post in posts:
            try:
                analysis = self.analyzer.analyze_post(post)
                post['analysis'] = analysis
                result['analytics'].append(analysis)
            except Exception as e:
                logger.error(f"Analysis failed: {e}")
        
        # Generate summary
        result['summary'] = {
            'total_posts': len(posts),
            'avg_engagement': self._calculate_average_engagement(result['analytics']),
            'fact_check_status': self._summarize_fact_checks(result['fact_checks']),
            'generation_time': time.time() - start_time
        }
        
        logger.info(f"Pipeline completed in {result['summary']['generation_time']:.2f}s")
        return result
    
    def _calculate_average_engagement(self, analytics: List[Dict]) -> float:
        """Calculate average engagement score from analytics."""
        if not analytics:
            return 0.0
        scores = [a.get('score', 0) for a in analytics]
        return sum(scores) / len(scores)
    
    def _summarize_fact_checks(self, fact_checks: List[Dict]) -> Dict:
        """Summarize fact-check results."""
        if not fact_checks:
            return {'status': 'no_checks'}
        
        statuses = [fc.get('status', 'unknown') for fc in fact_checks]
        summary = {
            'total': len(statuses),
            'verified': statuses.count('verified'),
            'unverified': statuses.count('unverified'),
            'inaccurate': statuses.count('inaccurate'),
            'no_claims': statuses.count('no_claims')
        }
        
        if summary['inaccurate'] > 0:
            summary['overall'] = 'requires_review'
        elif summary['unverified'] > 0:
            summary['overall'] = 'caution'
        elif summary['verified'] == summary['total']:
            summary['overall'] = 'verified'
        else:
            summary['overall'] = 'mixed'
        
        return summary