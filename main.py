"""
Lacak Emas API

REST API untuk mendapatkan harga emas dari Galeri24.
Built with FastAPI + Swagger UI.

Author: Generated with Claude AI
"""
import os
import logging
from datetime import datetime
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info("Starting Lacak Emas API...")
    set_cache_ttl(CACHE_TTL)
    logger.info(f"Cache TTL set to {CACHE_TTL} seconds")
    
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
```
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Prices", "description": "Endpoints untuk mendapatkan harga emas"},
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
        version="1.0.0",
        status="running",
        description="REST API untuk mendapatkan harga emas dari Galeri24",
        source="galeri24.co.id",
        endpoints={
            "GET /": "Interactive API documentation (Swagger)",
            "GET /info": "API information",
            "GET /health": "Health check",
            "GET /prices": "Get gold prices with optional filters",
            "GET /vendors": "List available vendors",
            "POST /cache/clear": "Clear price cache",
        },
        github="https://github.com/yourusername/lacak-emas-api"
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
