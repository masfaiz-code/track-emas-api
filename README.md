# Lacak Emas API

REST API untuk mendapatkan harga emas terkini dari [Galeri24](https://galeri24.co.id/harga-emas) dengan tracking perubahan harga harian.

Built with FastAPI + Swagger UI + Supabase.

## Features

- 📊 **Harga real-time** dari galeri24.co.id
- 🔍 **Filter** berdasarkan vendor (ANTAM, UBS, dll) dan berat
- ⚡ **Caching** untuk performa optimal (default 5 menit)
- 📈 **Tracking perubahan harga** (naik/turun/stabil)
- 📅 **History harga** hingga 90 hari
- 🗑️ **Auto-cleanup** data lama (retention 90 hari)
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

# Supabase Configuration (optional - for history & tracking)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key_here
```

## Setup Lokal

```bash
# Clone repository
git clone https://github.com/masfaiz-code/track-emas-api.git
cd track-emas-api

# Buat virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# atau
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Buat file .env
cp .env.example .env
# Edit .env dengan credentials Anda

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

### Info & Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/info` | API information |
| GET | `/health` | Health check |

### Prices

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/prices` | Get all gold prices |
| GET | `/prices?vendor=antam` | Filter by vendor |
| GET | `/prices?vendor=ubs&weight=1` | Filter by vendor and weight |
| GET | `/vendors` | List available vendors |

### History & Changes (Requires Supabase)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/prices/changes` | Price changes today (up/down/stable) |
| GET | `/prices/history?days=7` | Price history for last 7 days |
| GET | `/prices/trend?days=7` | Trend summary for period |
| POST | `/prices/sync` | Sync prices to database |

### Cache

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/cache/clear` | Clear price cache |

## Example Responses

### GET /prices?vendor=antam&weight=1

```json
{
  "success": true,
  "data": [
    {
      "vendor": "ANTAM",
      "weight": 1.0,
      "unit": "gram",
      "selling_price": 3129000,
      "buyback_price": 2722000,
      "price": null,
      "date": "2026-02-04"
    }
  ],
  "meta": {
    "source": "galeri24.co.id",
    "scraped_at": "2026-02-04T10:30:00.000000",
    "total": 1,
    "cached": true
  }
}
```

### GET /prices/changes?vendor=antam

```json
{
  "success": true,
  "data": [
    {
      "vendor": "ANTAM",
      "weight": 1.0,
      "previous_price": 3100000,
      "current_price": 3129000,
      "change_amount": 29000,
      "change_percent": 0.94,
      "trend": "up",
      "price_date": "2026-02-04"
    }
  ],
  "summary": {
    "up": 15,
    "down": 3,
    "stable": 2,
    "total": 20
  }
}
```

## Database Schema (Supabase)

### Table: gold_prices
- `id` (UUID) - Primary key
- `vendor` (TEXT) - Vendor name
- `weight` (DECIMAL) - Weight in grams
- `selling_price` (INTEGER) - Selling price in IDR
- `buyback_price` (INTEGER) - Buyback price in IDR
- `price_date` (DATE) - Price date
- `created_at` (TIMESTAMPTZ) - Record creation time

### Table: price_changes
- `id` (UUID) - Primary key
- `vendor` (TEXT) - Vendor name
- `weight` (DECIMAL) - Weight in grams
- `previous_price` (INTEGER) - Previous day's price
- `current_price` (INTEGER) - Current price
- `change_amount` (INTEGER) - Price difference
- `change_percent` (DECIMAL) - Percentage change
- `trend` (TEXT) - "up", "down", or "stable"
- `price_date` (DATE) - Date of change

### Auto-Cleanup (pg_cron)
Data older than 90 days is automatically deleted daily at 00:00 UTC (07:00 WIB).

## Deploy ke Zeabur

1. Push code ke GitHub repository
2. Buka [https://zeabur.com](https://zeabur.com) dan login
3. Create new project
4. Deploy dari GitHub repository
5. Tambahkan environment variables:
   - `CACHE_TTL`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
6. Zeabur akan otomatis detect Python dan deploy

## Tech Stack

- **Runtime**: Python 3.11+
- **Web Framework**: FastAPI
- **Server**: Uvicorn (ASGI)
- **HTTP Client**: httpx
- **Validation**: Pydantic v2
- **Caching**: cachetools (in-memory)
- **Database**: Supabase (PostgreSQL)

## Project Structure

```
track-emas-api/
├── main.py           # FastAPI app + endpoints
├── scraper.py        # Galeri24 scraper logic
├── database.py       # Supabase integration
├── models.py         # Pydantic models
├── requirements.txt  # Dependencies
├── Procfile          # For Zeabur/Heroku deployment
├── runtime.txt       # Python version
├── .env.example      # Environment template
├── .gitignore
└── README.md
```

## Cron Job for Auto-Sync

To automatically sync prices daily, you can set up an external cron job to call:

```bash
curl -X POST https://your-api-url/prices/sync
```

Recommended schedule: Daily at 09:00 WIB (after Galeri24 updates prices)

## License

MIT

## Contributing

Pull requests are welcome! Untuk perubahan besar, silahkan buka issue terlebih dahulu.
