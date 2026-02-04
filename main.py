"""
Lacak Emas API

REST API untuk mendapatkan harga emas dari Galeri24.
Built with FastAPI + Swagger UI + Supabase.

Author: Generated with Claude AI
"""
import os
import logging
from datetime import datetime, date
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from models import (
    PriceResponse,
    VendorResponse,
    InfoResponse,
    HealthResponse,
    ErrorResponse,
    MetaInfo,
    PriceChangeResponse,
    PriceChange,
    PriceHistoryResponse,
    PriceHistoryItem,
    TrendResponse,
    TrendSummary,
    SyncResponse,
)
from scraper import (
    scrape_galeri24,
    filter_prices,
    get_available_vendors,
    clear_cache,
    set_cache_ttl,
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG", "false").lower() == "true" else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))

# Check if Supabase is configured
SUPABASE_ENABLED = bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info("Starting Lacak Emas API...")
    set_cache_ttl(CACHE_TTL)
    logger.info(f"Cache TTL set to {CACHE_TTL} seconds")
    
    if SUPABASE_ENABLED:
        logger.info("Supabase integration enabled")
    else:
        logger.warning("Supabase not configured - history/changes features disabled")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Lacak Emas API...")
    clear_cache()


# Initialize FastAPI app
app = FastAPI(
    title="Lacak Emas API",
    description="""
## API untuk mendapatkan harga emas terkini dari Galeri24

### Fitur:
- 📊 **Harga real-time** dari galeri24.co.id
- 🔍 **Filter** berdasarkan vendor (ANTAM, UBS, dll) dan berat
- ⚡ **Caching** untuk performa optimal
- 📈 **Tracking perubahan harga** (naik/turun/stabil)
- 📅 **History harga** hingga 90 hari
- 📖 **Swagger UI** untuk dokumentasi interaktif

### Vendor yang tersedia:
- `antam` - ANTAM
- `ubs` - UBS  
- `galeri24` - GALERI 24
- `dinar` - DINAR G24
- `baby` - BABY GALERI 24

### Contoh penggunaan:
```
GET /prices                    # Semua harga
GET /prices?vendor=antam       # Filter ANTAM saja
GET /prices?vendor=ubs&weight=1  # UBS 1 gram
GET /prices/changes            # Perubahan harga hari ini
GET /prices/history?days=7     # History 7 hari
```
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Prices", "description": "Endpoints untuk mendapatkan harga emas"},
        {"name": "History", "description": "History dan tracking perubahan harga"},
        {"name": "Info", "description": "Informasi API dan health check"},
    ]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# INFO ENDPOINTS
# ============================================================================

@app.get(
    "/info",
    response_model=InfoResponse,
    tags=["Info"],
    summary="Informasi API",
    description="Mendapatkan informasi tentang API dan endpoints yang tersedia"
)
async def get_info():
    """Get API information"""
    return InfoResponse(
        app_name="Lacak Emas API",
        version="2.0.0",
        status="running",
        description="REST API untuk mendapatkan harga emas dari Galeri24 dengan tracking perubahan harga",
        source="galeri24.co.id",
        endpoints={
            "GET /": "Interactive API documentation (Swagger)",
            "GET /info": "API information",
            "GET /health": "Health check",
            "GET /prices": "Get gold prices with optional filters",
            "GET /prices/changes": "Get price changes (up/down/stable)",
            "GET /prices/history": "Get price history",
            "GET /prices/trend": "Get trend summary",
            "POST /prices/sync": "Sync prices to database",
            "GET /vendors": "List available vendors",
            "POST /cache/clear": "Clear price cache",
        },
        github="https://github.com/masfaiz-code/track-emas-api"
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Info"],
    summary="Health Check",
    description="Cek status kesehatan API"
)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat()
    )


# ============================================================================
# VENDOR ENDPOINTS
# ============================================================================

@app.get(
    "/vendors",
    response_model=VendorResponse,
    tags=["Prices"],
    summary="List Vendor",
    description="Mendapatkan daftar vendor emas yang tersedia"
)
async def get_vendors():
    """Get list of available gold vendors"""
    vendors = get_available_vendors()
    return VendorResponse(
        success=True,
        vendors=vendors,
        total=len(vendors)
    )


# ============================================================================
# PRICE ENDPOINTS
# ============================================================================

@app.get(
    "/prices",
    response_model=PriceResponse,
    responses={
        200: {"description": "Berhasil mendapatkan harga"},
        500: {"model": ErrorResponse, "description": "Error saat scraping"},
    },
    tags=["Prices"],
    summary="Harga Emas",
    description="""
Mendapatkan harga emas dari Galeri24.

### Query Parameters:
- **vendor**: Filter berdasarkan vendor (antam, ubs, galeri24, dinar, baby)
- **weight**: Filter berdasarkan berat tepat (dalam gram)
- **min_weight**: Filter berat minimum
- **max_weight**: Filter berat maksimum
- **no_cache**: Set ke `true` untuk bypass cache

### Contoh:
```
/prices                       # Semua harga
/prices?vendor=antam          # Hanya ANTAM
/prices?vendor=ubs&weight=1   # UBS 1 gram
/prices?min_weight=1&max_weight=10  # Berat 1-10 gram
```
    """
)
async def get_prices(
    vendor: Optional[str] = Query(
        None,
        description="Filter by vendor slug (antam, ubs, galeri24, dinar, baby)",
        examples=["antam", "ubs", "galeri24"]
    ),
    weight: Optional[float] = Query(
        None,
        description="Filter by exact weight in grams",
        examples=[1, 0.5, 5, 10]
    ),
    min_weight: Optional[float] = Query(
        None,
        description="Filter by minimum weight in grams"
    ),
    max_weight: Optional[float] = Query(
        None,
        description="Filter by maximum weight in grams"
    ),
    no_cache: bool = Query(
        False,
        description="Set to true to bypass cache and fetch fresh data"
    )
):
    """Get gold prices with optional filtering"""
    try:
        # Scrape prices
        use_cache = not no_cache
        prices = await scrape_galeri24(use_cache=use_cache, cache_ttl=CACHE_TTL)
        
        # Apply filters
        filtered_prices = filter_prices(
            prices,
            vendor=vendor,
            weight=weight,
            min_weight=min_weight,
            max_weight=max_weight,
        )
        
        return PriceResponse(
            success=True,
            data=filtered_prices,
            meta=MetaInfo(
                source="galeri24.co.id",
                scraped_at=datetime.now().isoformat(),
                total=len(filtered_prices),
                cached=use_cache,
            )
        )
        
    except Exception as e:
        logger.error(f"Error fetching prices: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================================
# HISTORY & CHANGES ENDPOINTS (Requires Supabase)
# ============================================================================

@app.get(
    "/prices/changes",
    response_model=PriceChangeResponse,
    tags=["History"],
    summary="Perubahan Harga",
    description="""
Mendapatkan perubahan harga emas hari ini dibanding kemarin.

### Query Parameters:
- **vendor**: Filter berdasarkan vendor
- **trend**: Filter berdasarkan trend (up, down, stable)

### Response:
- `change_amount`: Selisih harga (positif = naik, negatif = turun)
- `change_percent`: Persentase perubahan
- `trend`: "up", "down", atau "stable"
    """
)
async def get_price_changes(
    vendor: Optional[str] = Query(None, description="Filter by vendor"),
    trend: Optional[str] = Query(None, description="Filter by trend: up, down, stable")
):
    """Get price changes from previous day"""
    if not SUPABASE_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY."
        )
    
    try:
        from database import get_price_changes, get_trend_summary
        
        changes = await get_price_changes(vendor=vendor, trend=trend)
        summary = await get_trend_summary(days=1)
        
        # Convert to PriceChange models
        change_list = [
            PriceChange(
                vendor=c["vendor"],
                weight=float(c["weight"]),
                previous_price=c.get("previous_price"),
                current_price=c.get("current_price"),
                change_amount=c.get("change_amount"),
                change_percent=float(c["change_percent"]) if c.get("change_percent") else None,
                trend=c.get("trend", "stable"),
                price_date=c["price_date"],
            )
            for c in changes
        ]
        
        return PriceChangeResponse(
            success=True,
            data=change_list,
            summary=summary,
            meta=MetaInfo(
                source="galeri24.co.id",
                scraped_at=datetime.now().isoformat(),
                total=len(change_list),
                cached=False,
            )
        )
        
    except ImportError:
        raise HTTPException(status_code=503, detail="Database module not available")
    except Exception as e:
        logger.error(f"Error getting price changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/prices/history",
    response_model=PriceHistoryResponse,
    tags=["History"],
    summary="History Harga",
    description="""
Mendapatkan history harga emas untuk beberapa hari terakhir.

### Query Parameters:
- **vendor**: Filter berdasarkan vendor
- **weight**: Filter berdasarkan berat
- **days**: Jumlah hari (default: 7, max: 90)
    """
)
async def get_history(
    vendor: Optional[str] = Query(None, description="Filter by vendor"),
    weight: Optional[float] = Query(None, description="Filter by weight in grams"),
    days: int = Query(7, ge=1, le=90, description="Number of days of history")
):
    """Get price history"""
    if not SUPABASE_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY."
        )
    
    try:
        from database import get_price_history
        
        history = await get_price_history(vendor=vendor, weight=weight, days=days)
        
        # Convert to models
        history_list = [
            PriceHistoryItem(
                vendor=h["vendor"],
                weight=float(h["weight"]),
                selling_price=h.get("selling_price"),
                buyback_price=h.get("buyback_price"),
                price_date=h["price_date"],
                source=h.get("source", "galeri24"),
            )
            for h in history
        ]
        
        return PriceHistoryResponse(
            success=True,
            data=history_list,
            meta=MetaInfo(
                source="galeri24.co.id",
                scraped_at=datetime.now().isoformat(),
                total=len(history_list),
                cached=False,
            )
        )
        
    except ImportError:
        raise HTTPException(status_code=503, detail="Database module not available")
    except Exception as e:
        logger.error(f"Error getting price history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/prices/trend",
    response_model=TrendResponse,
    tags=["History"],
    summary="Trend Summary",
    description="Mendapatkan ringkasan trend harga untuk periode tertentu"
)
async def get_trend(
    days: int = Query(7, ge=1, le=90, description="Period in days")
):
    """Get trend summary"""
    if not SUPABASE_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY."
        )
    
    try:
        from database import get_trend_summary
        
        summary = await get_trend_summary(days=days)
        
        return TrendResponse(
            success=True,
            summary=TrendSummary(
                up=summary.get("up", 0),
                down=summary.get("down", 0),
                stable=summary.get("stable", 0),
                total=summary.get("total", 0),
                period_days=days,
            ),
            meta=MetaInfo(
                source="galeri24.co.id",
                scraped_at=datetime.now().isoformat(),
                total=summary.get("total", 0),
                cached=False,
            )
        )
        
    except ImportError:
        raise HTTPException(status_code=503, detail="Database module not available")
    except Exception as e:
        logger.error(f"Error getting trend: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/prices/sync",
    response_model=SyncResponse,
    tags=["History"],
    summary="Sync ke Database",
    description="""
Scrape harga terbaru dan simpan ke database.
Otomatis menghitung perubahan harga dari hari sebelumnya.

**Note:** Endpoint ini bisa dipanggil oleh cron job untuk auto-update harian.
    """
)
async def sync_prices():
    """Sync current prices to database"""
    if not SUPABASE_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY."
        )
    
    try:
        from database import save_prices
        
        # Scrape fresh prices
        prices = await scrape_galeri24(use_cache=False)
        
        # Convert to dict format
        price_dicts = [
            {
                "vendor": p.vendor,
                "weight": p.weight,
                "selling_price": p.selling_price,
                "buyback_price": p.buyback_price,
            }
            for p in prices
        ]
        
        # Save to database
        result = await save_prices(price_dicts)
        
        return SyncResponse(
            success=True,
            saved=result.get("saved", 0),
            changes=result.get("changes", 0),
            message=f"Synced {result.get('saved', 0)} prices, recorded {result.get('changes', 0)} changes",
            timestamp=datetime.now().isoformat(),
        )
        
    except ImportError:
        raise HTTPException(status_code=503, detail="Database module not available")
    except Exception as e:
        logger.error(f"Error syncing prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CACHE ENDPOINTS
# ============================================================================

@app.post(
    "/cache/clear",
    tags=["Info"],
    summary="Clear Cache",
    description="Menghapus cache harga untuk mendapatkan data fresh"
)
async def clear_price_cache():
    """Clear the price cache"""
    clear_cache()
    return {
        "success": True,
        "message": "Cache cleared successfully",
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
    )
