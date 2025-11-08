"""Redis Queue (RQ) configuration and utilities."""
import redis
from rq import Queue, Connection, Worker
from rq.job import Job
from rq import get_current_job
from typing import Optional, Dict, Any
from infra.config import settings


class RedisQueue:
    """Redis Queue client wrapper."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize Redis connection and RQ queue.
        
        Args:
            redis_url: Redis connection URL (defaults to settings.redis_url)
        """
        self.redis_url = redis_url or settings.redis_url
        
        try:
            # Parse Redis URL
            self.redis_conn = redis.from_url(self.redis_url)
            # Test connection
            self.redis_conn.ping()
            
            # Create RQ queue
            self.queue = Queue(connection=self.redis_conn, name='default')
            self._connected = True
        except Exception as e:
            print(f"⚠️  Redis connection failed: {e}")
            print("   Falling back to in-memory job storage")
            self._connected = False
            self.redis_conn = None
            self.queue = None
    
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected
    
    def enqueue(self, func, *args, **kwargs) -> Optional[Job]:
        """
        Enqueue a job.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Job instance or None if Redis is not connected
        """
        if not self._connected:
            return None
        
        try:
            job = self.queue.enqueue(func, *args, **kwargs, job_timeout='1h')
            return job
        except Exception as e:
            print(f"⚠️  Failed to enqueue job: {e}")
            return None
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get a job by ID.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job instance or None
        """
        if not self._connected:
            return None
        
        try:
            return Job.fetch(job_id, connection=self.redis_conn)
        except Exception:
            return None
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get job status information.
        
        Args:
            job_id: Job ID
            
        Returns:
            Dictionary with job status information
        """
        if not self._connected:
            return {
                "status": "unknown",
                "error": "Redis not connected"
            }
        
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            
            # Map RQ job status to our status format
            status_map = {
                'queued': 'queued',
                'started': 'processing',
                'finished': 'completed',
                'failed': 'failed',
                'deferred': 'queued',
                'scheduled': 'queued',
                'canceled': 'cancelled'
            }
            
            result = {
                "status": status_map.get(job.get_status(), 'unknown'),
                "jobId": job.id,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "ended_at": job.ended_at.isoformat() if job.ended_at else None,
            }
            
            # Add result if completed
            if job.is_finished:
                result["result"] = job.result
            
            # Add error if failed
            if job.is_failed:
                result["error"] = str(job.exc_info) if job.exc_info else "Unknown error"
            
            # Try to get custom metadata (progress, message, etc.)
            if hasattr(job, 'meta') and job.meta:
                result.update(job.meta)
            
            return result
            
        except Exception as e:
            return {
                "status": "not_found",
                "error": str(e)
            }
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job.
        
        Args:
            job_id: Job ID to cancel
            
        Returns:
            True if job was cancelled, False otherwise
        """
        if not self._connected:
            return False
        
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            
            # Check if job is still queued or processing
            if job.get_status() in ['queued', 'started', 'deferred', 'scheduled']:
                # Set cancel flag in metadata for running jobs
                if job.get_status() == 'started':
                    meta = job.meta or {}
                    meta['_cancelled'] = True
                    meta['status'] = 'cancelled'
                    meta['message'] = '任务已被用户取消'
                    job.meta = meta
                    job.save()
                
                # Cancel the job
                job.cancel()
                return True
            
            return False
            
        except Exception as e:
            print(f"⚠️  Failed to cancel job {job_id}: {e}")
            return False


# Global queue instance
_queue_instance: Optional[RedisQueue] = None


def get_queue() -> RedisQueue:
    """Get global queue instance."""
    global _queue_instance
    if _queue_instance is None:
        _queue_instance = RedisQueue()
    return _queue_instance


def update_job_progress(progress: int, message: str, **kwargs):
    """
    Update job progress and message in Redis.
    
    This function should be called from within a RQ worker task.
    
    Args:
        progress: Progress percentage (0-100)
        message: Status message
        **kwargs: Additional metadata to store
    """
    job = get_current_job()
    if job:
        meta = job.meta or {}
        meta.update({
            "progress": progress,
            "message": message,
            **kwargs
        })
        job.meta = meta
        job.save()

