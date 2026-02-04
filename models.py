"""
Pydantic models for Lacak Emas API
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class GoldPrice(BaseModel):
    """Model for individual gold price item"""
    vendor: str = Field(..., description="Vendor/brand name (e.g., ANTAM, UBS)")
    weight: float = Field(..., description="Gold weight in grams")
    unit: str = Field(default="gram", description="Weight unit")
    selling_price: Optional[int] = Field(None, description="Selling price in IDR")
    buyback_price: Optional[int] = Field(None, description="Buyback price in IDR")
    price: Optional[int] = Field(None, description="Base price in IDR")
    date: str = Field(..., description="Price date (YYYY-MM-DD)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "vendor": "ANTAM",
                "weight": 1.0,
                "unit": "gram",
                "selling_price": 1850000,
                "buyback_price": 1750000,
                "price": 1800000,
                "date": "2026-02-03"
            }
        }


class MetaInfo(BaseModel):
    """Metadata for API responses"""
    source: str = Field(default="galeri24.co.id", description="Data source")
    scraped_at: str = Field(..., description="Scraping timestamp (ISO format)")
    total: int = Field(..., description="Total items returned")
    cached: bool = Field(default=False, description="Whether data is from cache")


class PriceResponse(BaseModel):
    """Response model for price endpoints"""
    success: bool = Field(default=True)
    data: list[GoldPrice] = Field(default_factory=list)
    meta: MetaInfo
    error: Optional[str] = Field(None, description="Error message if any")


class VendorItem(BaseModel):
    """Model for vendor item"""
    name: str = Field(..., description="Vendor display name")
    slug: str = Field(..., description="Vendor slug for query parameter")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "ANTAM",
                "slug": "antam"
            }
        }


class VendorResponse(BaseModel):
    """Response model for vendors endpoint"""
    success: bool = Field(default=True)
    vendors: list[VendorItem] = Field(default_factory=list)
    total: int = Field(..., description="Total vendors available")


class InfoResponse(BaseModel):
    """Response model for info endpoint"""
    app_name: str
    version: str
    status: str
    description: str
    source: str
    endpoints: dict[str, str]
    github: Optional[str] = None


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str = Field(default="healthy")
    timestamp: str


class ErrorResponse(BaseModel):
    """Response model for errors"""
    success: bool = Field(default=False)
    error: str
    detail: Optional[str] = None


# =============================================
# NEW MODELS FOR PRICE HISTORY & CHANGES
# =============================================

class PriceChange(BaseModel):
    """Model for price change tracking"""
    vendor: str = Field(..., description="Vendor name")
    weight: float = Field(..., description="Gold weight in grams")
    previous_price: Optional[int] = Field(None, description="Previous day's price")
    current_price: Optional[int] = Field(None, description="Current price")
    change_amount: Optional[int] = Field(None, description="Price change amount (can be negative)")
    change_percent: Optional[float] = Field(None, description="Price change percentage")
    trend: str = Field(..., description="Price trend: up, down, or stable")
    price_date: str = Field(..., description="Date of the price")
    
    class Config:
        json_schema_extra = {
            "example": {
                "vendor": "ANTAM",
                "weight": 1.0,
                "previous_price": 3100000,
                "current_price": 3129000,
                "change_amount": 29000,
                "change_percent": 0.94,
                "trend": "up",
                "price_date": "2026-02-04"
            }
        }


class PriceChangeResponse(BaseModel):
    """Response model for price changes endpoint"""
    success: bool = Field(default=True)
    data: list[PriceChange] = Field(default_factory=list)
    summary: Optional[dict] = Field(None, description="Summary of trends")
    meta: MetaInfo


class PriceHistoryItem(BaseModel):
    """Model for price history item"""
    vendor: str
    weight: float
    selling_price: Optional[int]
    buyback_price: Optional[int]
    price_date: str
    source: str = "galeri24"


class PriceHistoryResponse(BaseModel):
    """Response model for price history endpoint"""
    success: bool = Field(default=True)
    data: list[PriceHistoryItem] = Field(default_factory=list)
    meta: MetaInfo


class TrendSummary(BaseModel):
    """Model for trend summary"""
    up: int = Field(default=0, description="Number of prices that went up")
    down: int = Field(default=0, description="Number of prices that went down")
    stable: int = Field(default=0, description="Number of prices that stayed the same")
    total: int = Field(default=0, description="Total price changes tracked")
    period_days: int = Field(default=7, description="Period in days")


class TrendResponse(BaseModel):
    """Response model for trend summary endpoint"""
    success: bool = Field(default=True)
    summary: TrendSummary
    meta: MetaInfo


class SyncResponse(BaseModel):
    """Response model for sync/save operations"""
    success: bool = Field(default=True)
    saved: int = Field(default=0, description="Number of records saved")
    changes: int = Field(default=0, description="Number of price changes recorded")
    message: str
    timestamp: str
