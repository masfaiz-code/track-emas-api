"""
Supabase Database Integration (httpx-based)

Handles database operations for gold price tracking using httpx directly
to Supabase REST API (no supabase-py dependency needed).
"""
import os
import logging
from datetime import datetime, date, timedelta
from typing import Optional, Any
import httpx

logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


def get_headers() -> dict:
    """Get Supabase API headers"""
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def get_rest_url(table: str) -> str:
    """Get Supabase REST URL for a table"""
    return f"{SUPABASE_URL}/rest/v1/{table}"


async def save_prices(prices: list[dict], price_date: Optional[date] = None) -> dict:
    """
    Save gold prices to database.
    Also calculates and saves price changes.
    
    Args:
        prices: List of price dicts with vendor, weight, selling_price, buyback_price
        price_date: Date for the prices (defaults to today)
        
    Returns:
        Summary of saved/updated records
    """
    if not prices:
        return {"saved": 0, "updated": 0, "changes": 0}
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
    
    target_date = price_date or date.today()
    
    saved = 0
    changes_recorded = 0
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for price in prices:
            try:
                vendor = price.get("vendor")
                weight = float(price.get("weight", 0))
                selling_price = price.get("selling_price")
                buyback_price = price.get("buyback_price")
                
                if not vendor or weight <= 0:
                    continue
                
                # Prepare record
                record = {
                    "vendor": vendor,
                    "weight": weight,
                    "selling_price": selling_price,
                    "buyback_price": buyback_price,
                    "price_date": target_date.isoformat(),
                    "source": "galeri24",
                }
                
                # Upsert using POST with on_conflict
                url = get_rest_url("gold_prices")
                headers = get_headers()
                headers["Prefer"] = "resolution=merge-duplicates,return=representation"
                
                response = await client.post(url, json=record, headers=headers)
                
                if response.status_code in [200, 201]:
                    saved += 1
                    
                    # Calculate and save price change
                    change = await calculate_and_save_change(
                        client, vendor, weight, selling_price, target_date
                    )
                    if change:
                        changes_recorded += 1
                else:
                    logger.warning(f"Failed to save {vendor}: {response.status_code}")
                        
            except Exception as e:
                logger.warning(f"Error saving price for {price.get('vendor')}: {e}")
                continue
    
    logger.info(f"Saved {saved} prices, recorded {changes_recorded} changes")
    return {"saved": saved, "updated": 0, "changes": changes_recorded}


async def calculate_and_save_change(
    client: httpx.AsyncClient,
    vendor: str,
    weight: float,
    current_price: Optional[int],
    price_date: date
) -> Optional[dict]:
    """
    Calculate price change from previous day and save to price_changes table.
    """
    if current_price is None:
        return None
    
    previous_date = price_date - timedelta(days=1)
    
    try:
        # Get previous day's price
        url = get_rest_url("gold_prices")
        params = {
            "vendor": f"eq.{vendor}",
            "weight": f"eq.{weight}",
            "price_date": f"eq.{previous_date.isoformat()}",
            "select": "selling_price",
            "limit": "1",
        }
        
        response = await client.get(url, params=params, headers=get_headers())
        
        if response.status_code != 200 or not response.json():
            return None
        
        data = response.json()
        if not data:
            return None
        
        previous_price = data[0].get("selling_price")
        if previous_price is None:
            return None
        
        # Calculate change
        change_amount = current_price - previous_price
        change_percent = round((change_amount / previous_price) * 100, 2) if previous_price else 0
        
        if change_amount > 0:
            trend = "up"
        elif change_amount < 0:
            trend = "down"
        else:
            trend = "stable"
        
        # Save price change
        change_record = {
            "vendor": vendor,
            "weight": weight,
            "price_date": price_date.isoformat(),
            "previous_price": previous_price,
            "current_price": current_price,
            "change_amount": change_amount,
            "change_percent": change_percent,
            "trend": trend,
        }
        
        change_url = get_rest_url("price_changes")
        await client.post(change_url, json=change_record, headers=get_headers())
        
        return change_record
        
    except Exception as e:
        logger.warning(f"Error calculating change for {vendor} {weight}g: {e}")
        return None


async def get_price_history(
    vendor: Optional[str] = None,
    weight: Optional[float] = None,
    days: int = 7
) -> list[dict]:
    """
    Get price history for the last N days.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    
    start_date = (date.today() - timedelta(days=days)).isoformat()
    
    params: dict[str, Any] = {
        "price_date": f"gte.{start_date}",
        "select": "*",
        "order": "price_date.desc",
    }
    
    if vendor:
        params["vendor"] = f"ilike.*{vendor}*"
    
    if weight:
        params["weight"] = f"eq.{weight}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = get_rest_url("gold_prices")
        response = await client.get(url, params=params, headers=get_headers())
        
        if response.status_code == 200:
            return response.json()
        return []


async def get_price_changes(
    vendor: Optional[str] = None,
    price_date: Optional[date] = None,
    trend: Optional[str] = None
) -> list[dict]:
    """
    Get price changes, optionally filtered by vendor, date, or trend.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    
    target_date = price_date or date.today()
    
    params: dict[str, Any] = {
        "price_date": f"eq.{target_date.isoformat()}",
        "select": "*",
        "order": "change_percent.desc",
    }
    
    if vendor:
        params["vendor"] = f"ilike.*{vendor}*"
    
    if trend:
        params["trend"] = f"eq.{trend}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = get_rest_url("price_changes")
        response = await client.get(url, params=params, headers=get_headers())
        
        if response.status_code == 200:
            return response.json()
        return []


async def get_latest_prices(vendor: Optional[str] = None) -> list[dict]:
    """
    Get the most recent prices for all or specific vendor.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    
    today = date.today().isoformat()
    
    params: dict[str, Any] = {
        "price_date": f"eq.{today}",
        "select": "*",
        "order": "vendor,weight",
    }
    
    if vendor:
        params["vendor"] = f"ilike.*{vendor}*"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = get_rest_url("gold_prices")
        response = await client.get(url, params=params, headers=get_headers())
        
        if response.status_code == 200:
            return response.json()
        return []


async def get_trend_summary(days: int = 7) -> dict:
    """
    Get summary of price trends over the last N days.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {"up": 0, "down": 0, "stable": 0, "total": 0}
    
    start_date = (date.today() - timedelta(days=days)).isoformat()
    
    params = {
        "price_date": f"gte.{start_date}",
        "select": "trend",
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = get_rest_url("price_changes")
        response = await client.get(url, params=params, headers=get_headers())
        
        if response.status_code != 200:
            return {"up": 0, "down": 0, "stable": 0, "total": 0}
        
        data = response.json()
        
        trends = {"up": 0, "down": 0, "stable": 0}
        for record in data:
            trend = record.get("trend")
            if trend in trends:
                trends[trend] += 1
        
        trends["total"] = sum(trends.values())
        return trends
