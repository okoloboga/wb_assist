# 📚 API Documentation - Notification System

## 🎯 Overview

The Notification System provides a comprehensive API for managing user notification preferences and testing notification delivery. The system supports multiple notification types including new orders, order status changes, negative reviews, and critical stock alerts.

## 🔗 Base URL

```
http://localhost:8000/api/v1/notifications
```

## 🔐 Authentication

All API endpoints require authentication via `telegram_id` query parameter:

```
?telegram_id=123456789
```

## 📋 Endpoints

### **1. Get Notification Settings**

Retrieve current notification settings for a user.

**Endpoint:** `GET /settings`

**Parameters:**
- `telegram_id` (int, required): User's Telegram ID

**Response:**
```json
{
  "success": true,
  "data": {
    "notifications_enabled": true,
    "new_orders_enabled": true,
    "order_buyouts_enabled": true,
    "order_cancellations_enabled": false,
    "order_returns_enabled": false,
    "negative_reviews_enabled": true,
    "critical_stocks_enabled": true,
    "grouping_enabled": false,
    "max_group_size": 5,
    "group_timeout": 300
  },
  "message": "Settings retrieved successfully"
}
```

**Error Responses:**
```json
{
  "success": false,
  "data": null,
  "message": "User not found"
}
```

### **2. Update Notification Settings**

Update notification settings for a user.

**Endpoint:** `POST /settings`

**Parameters:**
- `telegram_id` (int, required): User's Telegram ID

**Request Body:**
```json
{
  "notifications_enabled": true,
  "new_orders_enabled": true,
  "order_buyouts_enabled": true,
  "order_cancellations_enabled": false,
  "order_returns_enabled": false,
  "negative_reviews_enabled": true,
  "critical_stocks_enabled": true,
  "grouping_enabled": false,
  "max_group_size": 5,
  "group_timeout": 300
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "notifications_enabled": true,
    "new_orders_enabled": true,
    "order_buyouts_enabled": true,
    "order_cancellations_enabled": false,
    "order_returns_enabled": false,
    "negative_reviews_enabled": true,
    "critical_stocks_enabled": true,
    "grouping_enabled": false,
    "max_group_size": 5,
    "group_timeout": 300
  },
  "message": "Settings updated successfully"
}
```

**Error Responses:**
```json
{
  "success": false,
  "data": null,
  "message": "Invalid settings data"
}
```

### **3. Send Test Notification**

Send a test notification to verify the system is working.

**Endpoint:** `POST /test`

**Parameters:**
- `telegram_id` (int, required): User's Telegram ID

**Request Body:**
```json
{
  "notification_type": "new_order",
  "test_data": {
    "order_id": "test_order_123",
    "amount": 2500,
    "product_name": "Test Product",
    "status": "new"
  }
}
```

**Supported Notification Types:**
- `new_order` - New order notification
- `order_buyout` - Order buyout notification
- `order_cancellation` - Order cancellation notification
- `order_return` - Order return notification
- `negative_review` - Negative review notification
- `critical_stocks` - Critical stocks notification

**Response:**
```json
{
  "success": true,
  "data": {
    "notification_sent": true,
    "notification_type": "new_order",
    "message": "Test notification sent successfully"
  },
  "message": "Test notification sent successfully"
}
```

**Error Responses:**
```json
{
  "success": false,
  "data": {
    "notification_sent": false,
    "notification_type": "new_order",
    "message": "User webhook URL not found"
  },
  "message": "Test notification failed"
}
```

## 📊 Data Models

### **NotificationSettings**

| Field | Type | Description |
|-------|------|-------------|
| `notifications_enabled` | boolean | Master switch for all notifications |
| `new_orders_enabled` | boolean | Enable new order notifications |
| `order_buyouts_enabled` | boolean | Enable order buyout notifications |
| `order_cancellations_enabled` | boolean | Enable order cancellation notifications |
| `order_returns_enabled` | boolean | Enable order return notifications |
| `negative_reviews_enabled` | boolean | Enable negative review notifications |
| `critical_stocks_enabled` | boolean | Enable critical stock notifications |
| `grouping_enabled` | boolean | Enable notification grouping |
| `max_group_size` | integer | Maximum notifications per group |
| `group_timeout` | integer | Group timeout in seconds |

### **TestNotificationData**

| Field | Type | Description |
|-------|------|-------------|
| `notification_type` | string | Type of notification to test |
| `test_data` | object | Test data for the notification |

## 🔧 Error Handling

All API endpoints return consistent error responses:

```json
{
  "success": false,
  "data": null,
  "message": "Error description"
}
```

**Common Error Codes:**
- `400` - Bad Request (invalid data)
- `404` - Not Found (user not found)
- `500` - Internal Server Error

## 📝 Examples

### **Example 1: Get User Settings**

```bash
curl -X GET "http://localhost:8000/api/v1/notifications/settings?telegram_id=123456789"
```

### **Example 2: Update Settings**

```bash
curl -X POST "http://localhost:8000/api/v1/notifications/settings?telegram_id=123456789" \
  -H "Content-Type: application/json" \
  -d '{
    "notifications_enabled": true,
    "new_orders_enabled": true,
    "order_buyouts_enabled": true,
    "negative_reviews_enabled": false
  }'
```

### **Example 3: Send Test Notification**

```bash
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

## 🚀 Integration Guide

### **1. Bot Integration**

The bot should call these endpoints to manage user preferences:

```python
import requests

# Get user settings
response = requests.get(
    "http://localhost:8000/api/v1/notifications/settings",
    params={"telegram_id": user_id}
)

# Update user settings
response = requests.post(
    "http://localhost:8000/api/v1/notifications/settings",
    params={"telegram_id": user_id},
    json={
        "notifications_enabled": True,
        "new_orders_enabled": True,
        "negative_reviews_enabled": False
    }
)

# Send test notification
response = requests.post(
    "http://localhost:8000/api/v1/notifications/test",
    params={"telegram_id": user_id},
    json={
        "notification_type": "new_order",
        "test_data": {
            "order_id": "test_123",
            "amount": 1000,
            "product_name": "Test Product"
        }
    }
)
```

### **2. Webhook Integration**

The system sends notifications via webhooks to the bot:

```python
# Webhook payload example
{
  "type": "new_order",
  "user_id": 123456789,
  "data": {
    "order_id": "order_123",
    "amount": 2500,
    "product_name": "Test Product",
    "status": "new"
  },
  "timestamp": "2025-01-28T10:30:00Z"
}
```

## 🔍 Monitoring and Debugging

### **Logs**

The system logs all API requests and responses:

```
2025-01-28 10:30:00 INFO: GET /api/v1/notifications/settings?telegram_id=123456789
2025-01-28 10:30:00 INFO: Response: 200 OK
2025-01-28 10:30:01 INFO: POST /api/v1/notifications/test?telegram_id=123456789
2025-01-28 10:30:01 INFO: Response: 200 OK
```

### **Health Check**

Check system health:

```bash
curl -X GET "http://localhost:8000/health"
```

## 📈 Performance

### **Rate Limits**

- **Settings API:** 100 requests/minute per user
- **Test API:** 10 requests/minute per user

### **Response Times**

- **Settings API:** < 100ms
- **Test API:** < 500ms

## 🔒 Security

### **Authentication**

- All endpoints require `telegram_id` parameter
- No additional authentication required for internal use

### **Data Validation**

- All input data is validated using Pydantic schemas
- Invalid data returns 400 Bad Request

## 📞 Support

For technical support or questions about the API:

- **Documentation:** This file
- **Issues:** Create an issue in the repository
- **Contact:** Development team

---

*Last updated: 2025-01-28*  
*Version: 1.0*  
*Status: Production Ready* ✅
