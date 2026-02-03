"""
Galeri24 Gold Price Scraper

Scrapes gold prices from https://galeri24.co.id/harga-emas
using the embedded __NUXT_DATA__ JSON.
"""
import json
import logging
import re
from datetime import datetime
from typing import Optional, Any
from cachetools import TTLCache
import httpx

from models import GoldPrice, VendorItem

logger = logging.getLogger(__name__)

# In-memory cache with TTL
_cache: TTLCache = TTLCache(maxsize=100, ttl=300)  # 5 minutes default

# Vendor slug mapping
VENDOR_SLUGS = {
    "antam": ["ANTAM"],
    "ubs": ["UBS"],
    "galeri24": ["GALERI 24", "GALERI24"],
    "dinar": ["DINAR G24", "DINAR"],
    "baby": ["BABY GALERI 24", "BABY GALERI24"],
    "batik": ["BATIK", "BATIK SERIES"],
}

# Reverse mapping for quick lookup
VENDOR_NAME_TO_SLUG = {}
for slug, names in VENDOR_SLUGS.items():
    for name in names:
        VENDOR_NAME_TO_SLUG[name.upper()] = slug


def get_vendor_slug(vendor_name: str) -> str:
    """Get slug from vendor name"""
    name_upper = vendor_name.upper().strip()
    return VENDOR_NAME_TO_SLUG.get(name_upper, name_upper.lower().replace(" ", ""))


def get_available_vendors() -> list[VendorItem]:
    """Return list of available vendors"""
    vendors = [
        VendorItem(name="ANTAM", slug="antam"),
        VendorItem(name="UBS", slug="ubs"),
        VendorItem(name="GALERI 24", slug="galeri24"),
        VendorItem(name="DINAR G24", slug="dinar"),
        VendorItem(name="BABY GALERI 24", slug="baby"),
    ]
    return vendors


def parse_price(value: str | int | None) -> Optional[int]:
    """Parse price string to integer"""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        # Remove non-numeric characters except digits
        cleaned = re.sub(r'[^\d]', '', str(value))
        return int(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


def parse_weight(value: str | float | None) -> Optional[float]:
    """Parse weight/denomination to float"""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def resolve_nuxt_value(raw_data: list, index: int, visited: set = None) -> Any:
    """
    Resolve a value from Nuxt serialized data by following references.
    
    Nuxt 3 uses a special payload format where values can be references
    to other indices in the array.
    """
    if visited is None:
        visited = set()
    
    # Prevent infinite loops
    if index in visited:
        return None
    visited.add(index)
    
    if index < 0 or index >= len(raw_data):
        return None
    
    value = raw_data[index]
    
    # If it's a primitive, return as is
    if isinstance(value, (str, bool, float)) or value is None:
        return value
    
    # If it's an int, it might be an actual int or a reference
    # We'll return it as-is since we can't know for sure
    if isinstance(value, int):
        return value
    
    return value


def parse_nuxt_payload(html_content: str) -> list[dict]:
    """
    Parse Nuxt 3 payload format.
    
    The __NUXT_DATA__ contains a flat array where:
    - Primitives (strings, numbers, booleans, null) are stored directly
    - Objects store their values as references to other indices
    - Arrays store their elements as references to other indices
    
    We need to find the goldPrice array and reconstruct the objects.
    """
    pattern = r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>'
    match = re.search(pattern, html_content, re.DOTALL)
    
    if not match:
        logger.error("Could not find __NUXT_DATA__ in page")
        return []
    
    try:
        raw_data = json.loads(match.group(1))
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse __NUXT_DATA__ JSON: {e}")
        return []
    
    logger.info(f"Raw data has {len(raw_data)} elements")
    
    # Build a lookup of all string values for quick access
    string_lookup = {}
    date_indices = []
    vendor_indices = []
    
    for i, item in enumerate(raw_data):
        if isinstance(item, str):
            string_lookup[i] = item
            # Check for date pattern
            if re.match(r'^\d{4}-\d{2}-\d{2}$', item):
                date_indices.append(i)
            # Check for vendor names
            if any(v in item.upper() for v in ['ANTAM', 'UBS', 'GALERI', 'DINAR', 'BABY']):
                vendor_indices.append((i, item))
    
    logger.info(f"Found {len(vendor_indices)} vendor strings, {len(date_indices)} date strings")
    
    # Find the gold price objects by looking for dict patterns
    # Nuxt serializes objects with their keys and values as references
    gold_prices = []
    
    # Look for objects that have the gold price schema
    gold_price_fields = {'id', 'price', 'sellingPrice', 'buybackPrice', 
                         'denomination', 'vendorName', 'date', 'status'}
    
    for i, item in enumerate(raw_data):
        if not isinstance(item, dict):
            continue
        
        keys = set(item.keys())
        matching_keys = keys & gold_price_fields
        
        # If this object has at least 4 gold price fields, try to resolve it
        if len(matching_keys) >= 4:
            resolved = {}
            for key, ref in item.items():
                if isinstance(ref, int) and 0 <= ref < len(raw_data):
                    resolved[key] = raw_data[ref]
                else:
                    resolved[key] = ref
            
            # Validate that vendorName is a proper string
            vendor_name = resolved.get('vendorName')
            if isinstance(vendor_name, str) and len(vendor_name) > 1:
                gold_prices.append(resolved)
    
    if gold_prices:
        logger.info(f"Found {len(gold_prices)} gold price objects via dict parsing")
        return gold_prices
    
    # Alternative: Build gold prices from vendor strings
    logger.info("Trying alternative parsing via vendor string positions")
    return parse_by_pattern_matching(raw_data, vendor_indices, date_indices)


def parse_by_pattern_matching(raw_data: list, vendor_indices: list, date_indices: list) -> list[dict]:
    """
    Parse gold prices by finding patterns in the raw data.
    
    Look for sequences that match the gold price object pattern.
    """
    gold_prices = []
    used_vendors = set()
    
    # Get the most recent date
    current_date = datetime.now().strftime('%Y-%m-%d')
    for idx in date_indices:
        date_val = raw_data[idx]
        if isinstance(date_val, str):
            current_date = date_val
            break
    
    # For each vendor string, look for associated price data
    for vendor_idx, vendor_name in vendor_indices:
        if vendor_idx in used_vendors:
            continue
        
        # Look for denomination patterns near this vendor
        # Denominations are usually small numbers like 0.001, 0.5, 1, 5, 10, etc
        search_start = max(0, vendor_idx - 30)
        search_end = min(len(raw_data), vendor_idx + 30)
        
        found_prices = []
        
        for i in range(search_start, search_end):
            item = raw_data[i]
            
            # Look for price-like strings (numeric with possible formatting)
            if isinstance(item, str):
                # Check if it's a price (larger number)
                price_match = re.match(r'^[\d,\.]+$', item.replace(' ', ''))
                if price_match:
                    try:
                        # Remove formatting
                        clean = item.replace(',', '').replace('.', '')
                        val = int(clean)
                        if 10000 <= val <= 100000000:  # Reasonable price range in IDR
                            found_prices.append((i, val, 'price'))
                    except ValueError:
                        pass
                
                # Check if it's a denomination
                denom_match = re.match(r'^(0?\.\d+|\d+\.?\d*)$', item)
                if denom_match:
                    try:
                        val = float(item)
                        if 0.001 <= val <= 1000:  # Reasonable weight range
                            found_prices.append((i, val, 'weight'))
                    except ValueError:
                        pass
        
        # If we found both prices and weights, create entries
        weights = [(i, v) for i, v, t in found_prices if t == 'weight']
        prices = [(i, v) for i, v, t in found_prices if t == 'price']
        
        for weight_idx, weight in weights:
            # Find the closest price to this weight
            closest_price = None
            min_distance = float('inf')
            
            for price_idx, price in prices:
                distance = abs(price_idx - weight_idx)
                if distance < min_distance:
                    min_distance = distance
                    closest_price = price
            
            if closest_price and min_distance < 15:
                gold_prices.append({
                    'vendorName': vendor_name,
                    'denomination': str(weight),
                    'sellingPrice': str(closest_price),
                    'buybackPrice': None,
                    'price': str(closest_price),
                    'date': current_date,
                })
        
        used_vendors.add(vendor_idx)
    
    return gold_prices


def filter_prices(
    prices: list[GoldPrice],
    vendor: Optional[str] = None,
    weight: Optional[float] = None,
    min_weight: Optional[float] = None,
    max_weight: Optional[float] = None,
) -> list[GoldPrice]:
    """Filter prices by vendor and weight"""
    filtered = prices
    
    if vendor:
        vendor_lower = vendor.lower().strip()
        # Get the vendor names that match this slug
        vendor_names = VENDOR_SLUGS.get(vendor_lower, [vendor])
        filtered = [
            p for p in filtered 
            if any(vn.upper() in p.vendor.upper() for vn in vendor_names)
        ]
    
    if weight is not None:
        # Allow small tolerance for float comparison
        filtered = [p for p in filtered if abs(p.weight - weight) < 0.001]
    
    if min_weight is not None:
        filtered = [p for p in filtered if p.weight >= min_weight]
    
    if max_weight is not None:
        filtered = [p for p in filtered if p.weight <= max_weight]
    
    return filtered


async def scrape_galeri24(use_cache: bool = True, cache_ttl: int = 300) -> list[GoldPrice]:
    """
    Scrape gold prices from Galeri24.
    
    Args:
        use_cache: Whether to use cached data if available
        cache_ttl: Cache TTL in seconds (default 5 minutes)
        
    Returns:
        List of GoldPrice objects
    """
    cache_key = "galeri24_prices"
    
    # Check cache first
    if use_cache and cache_key in _cache:
        logger.info("Returning cached data")
        return _cache[cache_key]
    
    url = "https://galeri24.co.id/harga-emas"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            logger.info(f"Fetching {url}")
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            html_content = response.text
            logger.info(f"Received {len(html_content)} bytes")
            
    except httpx.TimeoutException:
        logger.error("Request timeout while fetching Galeri24")
        raise Exception("Request timeout - Galeri24 tidak merespon")
    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching Galeri24: {e}")
        raise Exception(f"HTTP error: {e}")
    
    # Parse the __NUXT_DATA__
    raw_prices = parse_nuxt_payload(html_content)
    
    logger.info(f"Found {len(raw_prices)} raw price entries")
    
    # Convert to GoldPrice models
    gold_prices = []
    for item in raw_prices:
        try:
            vendor_name = item.get('vendorName')
            if not vendor_name or not isinstance(vendor_name, str):
                continue
            
            # Skip if vendor name is too short or doesn't look like a vendor
            if len(vendor_name) < 2:
                continue
                
            denomination = item.get('denomination')
            weight = parse_weight(denomination)
            if weight is None or weight <= 0:
                continue
            
            selling_price = parse_price(item.get('sellingPrice'))
            buyback_price = parse_price(item.get('buybackPrice'))
            base_price = parse_price(item.get('price'))
            
            # Need at least one valid price
            if not any([selling_price, buyback_price, base_price]):
                continue
            
            date_str = item.get('date')
            if not isinstance(date_str, str) or not date_str:
                date_str = datetime.now().strftime('%Y-%m-%d')
            
            price = GoldPrice(
                vendor=vendor_name,
                weight=weight,
                unit="gram",
                selling_price=selling_price,
                buyback_price=buyback_price,
                price=base_price,
                date=date_str,
            )
            gold_prices.append(price)
            
        except Exception as e:
            logger.warning(f"Failed to parse price item: {e}")
            continue
    
    logger.info(f"Parsed {len(gold_prices)} valid gold prices")
    
    # Remove duplicates (same vendor + weight)
    seen = set()
    unique_prices = []
    for p in gold_prices:
        key = (p.vendor, p.weight)
        if key not in seen:
            seen.add(key)
            unique_prices.append(p)
    
    gold_prices = unique_prices
    
    # Sort by vendor name and weight
    gold_prices.sort(key=lambda x: (x.vendor, x.weight))
    
    # Update cache
    if use_cache:
        _cache[cache_key] = gold_prices
    
    return gold_prices


def clear_cache():
    """Clear the price cache"""
    _cache.clear()
    logger.info("Cache cleared")


def set_cache_ttl(ttl: int):
    """Set cache TTL (creates new cache)"""
    global _cache
    _cache = TTLCache(maxsize=100, ttl=ttl)
    logger.info(f"Cache TTL set to {ttl} seconds")
