from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from typing import Callable, Dict, Any, Optional
import json
import os
from models import get_db, ScheduledPost
from utils.logger import get_logger
from config import get_settings

settings = get_settings()
logger = get_logger(__name__)

class PostScheduler:
    """Enhanced scheduler with persistence and cron support."""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone=settings.SCHEDULER_TIMEZONE)
        self.db = get_db()
        self._load_scheduled_jobs()
        logger.info("Scheduler initialized")
    
    def _load_scheduled_jobs(self):
        """Load scheduled jobs from database."""
        try:
            scheduled = self.db.query(ScheduledPost).filter(
                ScheduledPost.is_active == True
            ).all()
            
            for job in scheduled:
                # Only load if next_run is in the future
                if job.next_run and job.next_run > datetime.utcnow():
                    self.scheduler.add_job(
                        func=self._execute_scheduled_post,
                        trigger=IntervalTrigger(hours=job.interval_hours),
                        args=[job.id],
                        id=job.job_id,
                        replace_existing=True,
                        next_run_time=job.next_run
                    )
                    logger.info(f"Loaded scheduled job: {job.job_id}")
                    
        except Exception as e:
            logger.error(f"Failed to load scheduled jobs: {e}")
    
    def _execute_scheduled_post(self, job_id: int):
        """Execute a scheduled post generation."""
        try:
            job = self.db.query(ScheduledPost).filter(
                ScheduledPost.id == job_id,
                ScheduledPost.is_active == True
            ).first()
            
            if not job:
                logger.warning(f"Job {job_id} not found or inactive")
                return
            
            logger.info(f"Executing scheduled post: {job.topic}")
            
            # Update last run
            job.last_run = datetime.utcnow()
            job.next_run = datetime.utcnow() + timedelta(hours=job.interval_hours)
            self.db.commit()
            
            # Execute post generation (would call generator here)
            # This is a placeholder - actual generation would happen here
            
            logger.info(f"Scheduled post executed: {job.topic}")
            
        except Exception as e:
            logger.error(f"Failed to execute scheduled post {job_id}: {e}")
    
    def schedule_post(
        self,
        topic: str,
        interval_hours: int,
        parameters: Dict[str, Any],
        cron_expression: Optional[str] = None
    ) -> str:
        """Schedule a post with interval or cron expression."""
        job_id = f"post_{topic}_{int(datetime.now().timestamp())}"
        next_run = datetime.utcnow() + timedelta(hours=interval_hours)
        
        try:
            # Save to database
            scheduled = ScheduledPost(
                job_id=job_id,
                topic=topic,
                tone=parameters.get('tone', settings.default_tone),
                length=parameters.get('length', settings.default_length),
                audience=parameters.get('audience', settings.default_audience),
                interval_hours=interval_hours,
                next_run=next_run,
                metadata=parameters
            )
            self.db.add(scheduled)
            self.db.commit()
            
            # Add to scheduler
            if cron_expression:
                trigger = CronTrigger.from_crontab(cron_expression)
            else:
                trigger = IntervalTrigger(hours=interval_hours)
            
            self.scheduler.add_job(
                func=self._execute_scheduled_post,
                trigger=trigger,
                args=[scheduled.id],
                id=job_id,
                replace_existing=True,
                next_run_time=next_run
            )
            
            logger.info(f"Scheduled post: {job_id} - {topic}")
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to schedule post: {e}")
            self.db.rollback()
            raise
    
    def unschedule_post(self, job_id: str) -> bool:
        """Remove a scheduled post."""
        try:
            # Remove from scheduler
            self.scheduler.remove_job(job_id)
            
            # Update database
            scheduled = self.db.query(ScheduledPost).filter(
                ScheduledPost.job_id == job_id
            ).first()
            
            if scheduled:
                scheduled.is_active = False
                self.db.commit()
                logger.info(f"Unscheduled post: {job_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to unschedule post {job_id}: {e}")
            return False
    
    def get_scheduled_posts(self) -> list:
        """Get all scheduled posts."""
        try:
            scheduled = self.db.query(ScheduledPost).filter(
                ScheduledPost.is_active == True
            ).all()
            
            return [{
                'id': s.id,
                'job_id': s.job_id,
                'topic': s.topic,
                'tone': s.tone,
                'length': s.length,
                'interval_hours': s.interval_hours,
                'next_run': s.next_run.isoformat() if s.next_run else None,
                'last_run': s.last_run.isoformat() if s.last_run else None,
                'created_at': s.created_at.isoformat()
            } for s in scheduled]
            
        except Exception as e:
            logger.error(f"Failed to get scheduled posts: {e}")
            return []
    
    def start(self):
        """Start the scheduler."""
        self.scheduler.start()
        logger.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            'running': self.scheduler.running,
            'jobs': len(self.scheduler.get_jobs()),
            'scheduled_posts': len(self.get_scheduled_posts())
        }