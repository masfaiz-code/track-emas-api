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
