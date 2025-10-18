# 📖 User Guide - Notification System

## 🎯 Overview

The Notification System provides comprehensive notification management for Wildberries sellers. Users can configure notification preferences, test the system, and receive real-time alerts about important events.

## 🚀 Getting Started

### **1. System Requirements**

- **Server:** FastAPI application running on port 8000
- **Database:** PostgreSQL with notification tables
- **Cache:** Redis for queue management and caching
- **Bot:** Telegram bot with webhook support

### **2. Initial Setup**

The system automatically creates default settings for new users:

```json
{
  "notifications_enabled": true,
  "new_orders_enabled": true,
  "order_buyouts_enabled": true,
  "order_cancellations_enabled": true,
  "order_returns_enabled": true,
  "negative_reviews_enabled": true,
  "critical_stocks_enabled": true,
  "grouping_enabled": false,
  "max_group_size": 5,
  "group_timeout": 300
}
```

## 🔧 Configuration

### **1. Notification Types**

The system supports 6 types of notifications:

#### **New Orders** 📦
- **Description:** Alerts when new orders are received
- **Settings:** `new_orders_enabled`
- **Example:** "Новый заказ #12345 на сумму 2,500₽"

#### **Order Buyouts** ✅
- **Description:** Alerts when orders are bought out
- **Settings:** `order_buyouts_enabled`
- **Example:** "Заказ #12345 выкуплен на сумму 2,500₽"

#### **Order Cancellations** ❌
- **Description:** Alerts when orders are cancelled
- **Settings:** `order_cancellations_enabled`
- **Example:** "Заказ #12345 отменен на сумму 2,500₽"

#### **Order Returns** 🔄
- **Description:** Alerts when orders are returned
- **Settings:** `order_returns_enabled`
- **Example:** "Заказ #12345 возвращен на сумму 2,500₽"

#### **Negative Reviews** ⭐
- **Description:** Alerts for low-rated reviews (1-3 stars)
- **Settings:** `negative_reviews_enabled`
- **Example:** "Негативный отзыв: 2/5 звезд на товар 'Test Product'"

#### **Critical Stocks** ⚠️
- **Description:** Alerts when stock levels are critically low
- **Settings:** `critical_stocks_enabled`
- **Example:** "Критический остаток: 'Test Product' - 5 шт. (порог: 10)"

### **2. Notification Grouping**

Users can enable notification grouping to reduce spam:

```json
{
  "grouping_enabled": true,
  "max_group_size": 5,
  "group_timeout": 300
}
```

**Benefits:**
- **Reduced spam:** Multiple notifications grouped into one message
- **Better readability:** Clear summary of all events
- **Configurable:** Adjust group size and timeout

**Example Grouped Notification:**
```
📦 Новые заказы (3):
• Заказ #12345 - 2,500₽
• Заказ #12346 - 1,800₽
• Заказ #12347 - 3,200₽
```

## 🧪 Testing

### **1. Test Notifications**

Users can test the notification system:

```bash
# Test new order notification
curl -X POST "http://localhost:8000/api/v1/notifications/test?telegram_id=123456789" \
  -H "Content-Type: application/json" \
  -d '{
    "notification_type": "new_order",
    "test_data": {
      "order_id": "test_order_123",
      "amount": 2500,
      "product_name": "Test Product",
      "status": "new"
    }
  }'
```

### **2. Test All Types**

Test all notification types to ensure the system works:

```bash
# Test order buyout
curl -X POST "http://localhost:8000/api/v1/notifications/test?telegram_id=123456789" \
  -H "Content-Type: application/json" \
  -d '{
    "notification_type": "order_buyout",
    "test_data": {
      "order_id": "test_order_123",
      "amount": 2500,
      "product_name": "Test Product",
      "status": "buyout"
    }
  }'

# Test negative review
curl -X POST "http://localhost:8000/api/v1/notifications/test?telegram_id=123456789" \
  -H "Content-Type: application/json" \
  -d '{
    "notification_type": "negative_review",
    "test_data": {
      "review_id": "test_review_123",
      "product_name": "Test Product",
      "rating": 2,
      "comment": "Bad product"
    }
  }'
```

## 📊 Monitoring

### **1. System Health**

Check system health:

```bash
curl -X GET "http://localhost:8000/health"
```

### **2. Queue Status**

Monitor notification queue:

```python
from app.features.notifications.queue_manager import QueueManager

queue_manager = QueueManager(redis_client)
status = queue_manager.get_queue_status()

print(f"Queue length: {status['total_notifications']}")
print(f"High priority: {status['high_priority']}")
print(f"Medium priority: {status['medium_priority']}")
print(f"Low priority: {status['low_priority']}")
```

### **3. Performance Metrics**

Monitor system performance:

```python
from app.features.notifications.redis_integration import RedisIntegration

redis_integration = RedisIntegration(redis_client, cache_config)
metrics = redis_integration.get_system_metrics()

print(f"Cache hit rate: {metrics['cache_hit_rate']:.2%}")
print(f"Queue processing rate: {metrics['queue_processing_rate']:.2f}/min")
print(f"Error rate: {metrics['error_rate']:.2%}")
```

## 🔧 Troubleshooting

### **1. Common Issues**

#### **Notifications Not Received**
- **Check settings:** Ensure `notifications_enabled` is `true`
- **Check webhook:** Verify bot webhook URL is configured
- **Check logs:** Review system logs for errors

#### **Test Notifications Fail**
- **Check user:** Ensure user exists in database
- **Check webhook:** Verify bot webhook URL is set
- **Check settings:** Ensure notification type is enabled

#### **Performance Issues**
- **Check Redis:** Ensure Redis is running and accessible
- **Check database:** Ensure database connections are healthy
- **Check queue:** Monitor queue length and processing rate

### **2. Debug Mode**

Enable debug logging:

```python
import logging

# Set debug level
logging.basicConfig(level=logging.DEBUG)

# Enable notification service debug
from app.features.notifications.notification_service import NotificationService

service = NotificationService(db, redis)
service.debug_mode = True
```

### **3. Log Analysis**

Analyze system logs:

```bash
# View notification logs
tail -f /var/log/notifications.log

# Search for errors
grep "ERROR" /var/log/notifications.log

# Search for specific user
grep "user_id:123456789" /var/log/notifications.log
```

## 📈 Optimization

### **1. Performance Tuning**

#### **Redis Configuration**
```redis
# Increase memory limit
maxmemory 512mb
maxmemory-policy allkeys-lru

# Optimize persistence
save 900 1
save 300 10
save 60 10000
```

#### **Database Optimization**
```sql
-- Add indexes for better performance
CREATE INDEX idx_notification_settings_user_id ON notification_settings(user_id);
CREATE INDEX idx_order_status_history_user_id ON order_status_history(user_id);
CREATE INDEX idx_order_status_history_order_id ON order_status_history(order_id);
```

### **2. Scaling**

#### **Horizontal Scaling**
- **Multiple instances:** Run multiple server instances
- **Load balancer:** Distribute requests across instances
- **Redis cluster:** Use Redis cluster for high availability

#### **Vertical Scaling**
- **Increase memory:** Add more RAM for Redis and database
- **Increase CPU:** Add more CPU cores for processing
- **Increase storage:** Add more disk space for logs and data

## 🔒 Security

### **1. Access Control**

- **Authentication:** All API endpoints require `telegram_id`
- **Authorization:** Users can only access their own settings
- **Rate limiting:** Implement rate limits to prevent abuse

### **2. Data Protection**

- **Encryption:** Sensitive data encrypted at rest
- **Backup:** Regular backups of database and Redis
- **Monitoring:** Continuous monitoring for security issues

## 📞 Support

### **1. Getting Help**

- **Documentation:** This guide and API documentation
- **Logs:** Check system logs for error details
- **Monitoring:** Use monitoring tools to identify issues

### **2. Reporting Issues**

When reporting issues, include:

- **User ID:** Telegram ID of affected user
- **Error message:** Full error message from logs
- **Steps to reproduce:** Detailed steps to reproduce the issue
- **System information:** Server, database, and Redis versions

### **3. Feature Requests**

For new features:

- **Description:** Clear description of the feature
- **Use case:** Why the feature is needed
- **Priority:** High, medium, or low priority
- **Implementation:** Suggested implementation approach

## 📚 Additional Resources

### **1. API Reference**
- **Full API documentation:** `docs/S3/API_DOCUMENTATION.md`
- **Technical specification:** `docs/S3/S3_BACK.md`

### **2. Development**
- **Source code:** `server/app/features/notifications/`
- **Tests:** `server/tests/`
- **Configuration:** `server/app/core/config.py`

### **3. Deployment**
- **Docker:** `docker-compose.yml`
- **Environment:** `.env` file
- **Database:** Migration scripts

---

*Last updated: 2025-01-28*  
*Version: 1.0*  
*Status: Production Ready* ✅
