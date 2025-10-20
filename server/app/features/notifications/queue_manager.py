"""
Enhanced Queue Manager with priority support
"""
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class QueueManager:
    """
    Enhanced Queue Manager for notification processing with priority support
    """
    
    def __init__(self, redis_client):
        """
        Initialize Queue Manager
        
        Args:
            redis_client: Redis client instance
        """
        self.redis_client = redis_client
        self.queue_key = "notification_queue"
        self.priority_queues = {
            "CRITICAL": "notification_queue:critical",
            "HIGH": "notification_queue:high", 
            "MEDIUM": "notification_queue:medium",
            "LOW": "notification_queue:low"
        }
    
    def add_notification_to_queue(self, notification: Dict[str, Any]) -> None:
        """
        Add notification to appropriate priority queue
        
        Args:
            notification: Notification data dictionary
        """
        try:
            priority = notification.get("priority", "MEDIUM")
            queue_key = self.priority_queues.get(priority, self.priority_queues["MEDIUM"])
            
            # Ensure notification has required fields
            if "created_at" not in notification:
                notification["created_at"] = datetime.now(timezone.utc).isoformat()
            
            if "retry_count" not in notification:
                notification["retry_count"] = 0
                
            if "max_retries" not in notification:
                notification["max_retries"] = 3
            
            # Add to priority queue
            self.redis_client.lpush(queue_key, json.dumps(notification))
            
            logger.info(f"Added notification {notification.get('id', 'unknown')} to {priority} queue")
            
        except Exception as e:
            logger.error(f"Failed to add notification to queue: {e}")
            raise
    
    def get_next_notification(self) -> Optional[Dict[str, Any]]:
        """
        Get next notification from queues in priority order
        
        Returns:
            Next notification or None if no notifications available
        """
        try:
            # Check queues in priority order: CRITICAL -> HIGH -> MEDIUM -> LOW
            for priority in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                queue_key = self.priority_queues[priority]
                notification_data = self.redis_client.rpop(queue_key)
                
                if notification_data:
                    try:
                        notification = json.loads(notification_data)
                        logger.info(f"Retrieved notification {notification.get('id', 'unknown')} from {priority} queue")
                        return notification
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse notification JSON: {e}")
                        continue
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get next notification: {e}")
            return None
    
    def get_queue_status(self) -> Dict[str, int]:
        """
        Get current queue status with counts for each priority
        
        Returns:
            Dictionary with queue sizes
        """
        try:
            status = {}
            total = 0
            
            for priority, queue_key in self.priority_queues.items():
                count = self.redis_client.llen(queue_key)
                status[priority.lower()] = count
                total += count
            
            status["total"] = total
            return status
            
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            return {"critical": 0, "high": 0, "medium": 0, "low": 0, "total": 0}
    
    def clear_queue(self) -> None:
        """
        Clear all notification queues
        """
        try:
            for queue_key in self.priority_queues.values():
                self.redis_client.delete(queue_key)
            
            logger.info("Cleared all notification queues")
            
        except Exception as e:
            logger.error(f"Failed to clear queues: {e}")
            raise
    
    def get_notifications_by_priority(self, priority: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get notifications from specific priority queue
        
        Args:
            priority: Priority level (CRITICAL, HIGH, MEDIUM, LOW)
            limit: Maximum number of notifications to return
            
        Returns:
            List of notifications
        """
        try:
            queue_key = self.priority_queues.get(priority.upper())
            if not queue_key:
                logger.warning(f"Invalid priority: {priority}")
                return []
            
            notifications_data = self.redis_client.lrange(queue_key, 0, limit - 1)
            notifications = []
            
            for data in notifications_data:
                try:
                    notification = json.loads(data)
                    notifications.append(notification)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse notification JSON: {e}")
                    continue
            
            return notifications
            
        except Exception as e:
            logger.error(f"Failed to get notifications by priority: {e}")
            return []
    
    def requeue_notification(self, notification: Dict[str, Any]) -> bool:
        """
        Requeue a notification (for retry scenarios)
        
        Args:
            notification: Notification to requeue
            
        Returns:
            True if requeued successfully, False if max retries exceeded
        """
        try:
            retry_count = notification.get("retry_count", 0)
            max_retries = notification.get("max_retries", 3)
            
            if retry_count >= max_retries:
                logger.warning(f"Notification {notification.get('id', 'unknown')} exceeded max retries")
                return False
            
            # Increment retry count
            notification["retry_count"] = retry_count + 1
            
            # Add back to queue
            self.add_notification_to_queue(notification)
            
            logger.info(f"Requeued notification {notification.get('id', 'unknown')} (retry {retry_count + 1})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to requeue notification: {e}")
            return False
    
    def get_queue_metrics(self) -> Dict[str, Any]:
        """
        Get detailed queue metrics
        
        Returns:
            Dictionary with queue metrics
        """
        try:
            queue_sizes = self.get_queue_status()
            
            # Get processed counts
            processed_counts = {}
            total_processed = 0
            
            for priority in ["critical", "high", "medium", "low"]:
                count_key = f"processed_count:{priority}"
                count = self.redis_client.get(count_key)
                processed_count = int(count) if count else 0
                processed_counts[priority] = processed_count
                total_processed += processed_count
            
            processed_counts["total"] = total_processed
            
            return {
                "queue_sizes": queue_sizes,
                "processed_counts": processed_counts,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue metrics: {e}")
            return {
                "queue_sizes": {"critical": 0, "high": 0, "medium": 0, "low": 0, "total": 0},
                "processed_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0, "total": 0},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def increment_processed_count(self, priority: str) -> None:
        """
        Increment processed count for priority
        
        Args:
            priority: Priority level
        """
        try:
            count_key = f"processed_count:{priority.lower()}"
            self.redis_client.incr(count_key)
            
        except Exception as e:
            logger.error(f"Failed to increment processed count: {e}")
    
    def set_queue_expiry(self, priority: str, seconds: int) -> None:
        """
        Set expiry for priority queue
        
        Args:
            priority: Priority level
            seconds: Expiry time in seconds
        """
        try:
            queue_key = self.priority_queues.get(priority.upper())
            if queue_key:
                self.redis_client.expire(queue_key, seconds)
                
        except Exception as e:
            logger.error(f"Failed to set queue expiry: {e}")
    
    def get_notification_by_id(self, notification_id: str) -> Optional[Dict[str, Any]]:
        """
        Find notification by ID across all queues
        
        Args:
            notification_id: Notification ID to find
            
        Returns:
            Notification if found, None otherwise
        """
        try:
            for priority, queue_key in self.priority_queues.items():
                notifications = self.get_notifications_by_priority(priority, limit=1000)
                
                for notification in notifications:
                    if notification.get("id") == notification_id:
                        return notification
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find notification by ID: {e}")
            return None
    
    def remove_notification_by_id(self, notification_id: str) -> bool:
        """
        Remove notification by ID from all queues
        
        Args:
            notification_id: Notification ID to remove
            
        Returns:
            True if removed, False if not found
        """
        try:
            for priority, queue_key in self.priority_queues.items():
                notifications = self.get_notifications_by_priority(priority, limit=1000)
                
                for notification in notifications:
                    if notification.get("id") == notification_id:
                        # Remove from queue
                        result = self.redis_client.lrem(queue_key, 1, json.dumps(notification))
                        return result > 0
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to remove notification by ID: {e}")
            return False
