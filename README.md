# Lacak Emas API

REST API untuk mendapatkan harga emas terkini dari [Galeri24](https://galeri24.co.id/harga-emas). Built with FastAPI + Swagger UI.

## Features

- 📊 **Harga real-time** dari galeri24.co.id
- 🔍 **Filter** berdasarkan vendor (ANTAM, UBS, dll) dan berat
- ⚡ **Caching** untuk performa optimal (default 5 menit)
- 📖 **Swagger UI** untuk dokumentasi interaktif
- 🚀 **Production-ready** dengan error handling lengkap

## Vendor yang Tersedia

| Vendor | Slug | Keterangan |
|--------|------|------------|
| ANTAM | `antam` | Emas Antam |
| UBS | `ubs` | Emas UBS |
| GALERI 24 | `galeri24` | Emas Galeri 24 |
| DINAR G24 | `dinar` | Emas Dinar |
| BABY GALERI 24 | `baby` | Emas Baby Galeri |

## Environment Variables

Buat file `.env` di root project:

```env
# Cache Configuration (in seconds)
CACHE_TTL=300

# Server Configuration
HOST=0.0.0.0
PORT=8000

# Debug Mode
DEBUG=false
```

## Setup Lokal

```bash
# Clone repository
git clone https://github.com/yourusername/lacak-emas-api.git
cd lacak-emas-api

# Buat virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# atau
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Buat file .env
cp .env.example .env

# Jalankan server
python main.py
# atau
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Swagger Documentation

```
GET /
```

Buka browser di `http://localhost:8000` untuk melihat Swagger UI interaktif.

### Info

```
GET /info
```

### Health Check

```
GET /health
```

### List Vendors

```
GET /vendors
```

Response:
```json
{
  "success": true,
  "vendors": [
    {"name": "ANTAM", "slug": "antam"},
    {"name": "UBS", "slug": "ubs"},
    {"name": "GALERI 24", "slug": "galeri24"},
    {"name": "DINAR G24", "slug": "dinar"},
    {"name": "BABY GALERI 24", "slug": "baby"}
  ],
  "total": 5
}
```

### Get Prices

```
GET /prices
GET /prices?vendor=antam
GET /prices?vendor=ubs&weight=1
GET /prices?min_weight=1&max_weight=10
GET /prices?no_cache=true
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `vendor` | string | Filter by vendor slug |
| `weight` | float | Filter by exact weight (gram) |
| `min_weight` | float | Filter by minimum weight |
| `max_weight` | float | Filter by maximum weight |
| `no_cache` | bool | Bypass cache for fresh data |

Response:
```json
{
  "success": true,
  "data": [
    {
      "vendor": "ANTAM",
      "weight": 1.0,
      "unit": "gram",
      "selling_price": 1850000,
      "buyback_price": 1750000,
      "price": 1800000,
      "date": "2026-02-03"
    }
  ],
  "meta": {
    "source": "galeri24.co.id",
    "scraped_at": "2026-02-03T21:30:00.000000",
    "total": 1,
    "cached": true
  }
}
```

### Clear Cache

```
POST /cache/clear
```

## Testing dengan cURL

### Get All Prices

```bash
curl http://localhost:8000/prices
```

### Filter by Vendor

```bash
curl "http://localhost:8000/prices?vendor=antam"
```

### Filter by Vendor dan Weight

```bash
curl "http://localhost:8000/prices?vendor=ubs&weight=1"
```

### Fresh Data (No Cache)

```bash
curl "http://localhost:8000/prices?no_cache=true"
```

## Deploy ke Zeabur

1. Push code ke GitHub repository
2. Buka [https://zeabur.com](https://zeabur.com) dan login
3. Create new project
4. Deploy dari GitHub repository
5. Tambahkan environment variables:
   - `CACHE_TTL`
   - `PORT` (optional, Zeabur akan set otomatis)
6. Zeabur akan otomatis detect Python dan deploy

## Deploy ke Railway

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Init project
railway init

# Deploy
railway up
```

## Tech Stack

- **Runtime**: Python 3.11+
- **Web Framework**: FastAPI
- **Server**: Uvicorn (ASGI)
- **HTTP Client**: httpx
- **Validation**: Pydantic v2
- **Caching**: cachetools (in-memory)

## Project Structure

```
lacak-emas-api/
├── main.py           # FastAPI app + endpoints
├── scraper.py        # Galeri24 scraper logic
├── models.py         # Pydantic models
├── requirements.txt  # Dependencies
├── .env.example      # Environment template
├── .gitignore
└── README.md
```

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad request |
| 500 | Server error / Scraping failed |

## License

MIT

## Contributing

Pull requests are welcome! Untuk perubahan besar, silahkan buka issue terlebih dahulu.
