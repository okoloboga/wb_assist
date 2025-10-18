"""
Pydantic schemas for notification API endpoints
"""
from typing import Optional
from pydantic import BaseModel, Field


class NotificationSettingsResponse(BaseModel):
    """Response schema for notification settings"""
    user_id: int
    notifications_enabled: bool
    new_orders_enabled: bool
    order_buyouts_enabled: bool
    order_cancellations_enabled: bool
    order_returns_enabled: bool
    negative_reviews_enabled: bool
    critical_stocks_enabled: bool
    grouping_enabled: bool
    max_group_size: int = Field(ge=1, le=50)
    group_timeout: int = Field(ge=1, le=300)

    class Config:
        from_attributes = True


class NotificationSettingsUpdate(BaseModel):
    """Schema for updating notification settings"""
    notifications_enabled: Optional[bool] = None
    new_orders_enabled: Optional[bool] = None
    order_buyouts_enabled: Optional[bool] = None
    order_cancellations_enabled: Optional[bool] = None
    order_returns_enabled: Optional[bool] = None
    negative_reviews_enabled: Optional[bool] = None
    critical_stocks_enabled: Optional[bool] = None
    grouping_enabled: Optional[bool] = None
    max_group_size: Optional[int] = Field(None, ge=1, le=50)
    group_timeout: Optional[int] = Field(None, ge=1, le=300)


class TestNotificationData(BaseModel):
    """Schema for test notification data"""
    notification_type: str = Field(..., pattern="^(new_order|order_buyout|order_cancellation|order_return|negative_review|critical_stocks)$")
    test_data: dict = Field(..., description="Test data for the notification")


class TestNotificationResponse(BaseModel):
    """Response schema for test notification"""
    success: bool
    message: str
    notification_sent: bool
    webhook_url: Optional[str] = None
    error: Optional[str] = None


class APIResponse(BaseModel):
    """Generic API response schema"""
    success: bool
    message: str
    data: Optional[dict] = None
    error: Optional[str] = None
