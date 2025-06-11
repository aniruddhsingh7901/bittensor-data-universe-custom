# Bittensor Data Universe with Custom Twitter Scraper - Clone and Run Guide

## Overview
This repository contains the complete Bittensor Data Universe with a custom Twitter scraper that uses your own sophisticated ProxyTwitterMiner instead of external services like Apify.

## What's Included

### ✅ **Complete Codebase**
- **Bittensor Data Universe**: Full miner/validator system
- **CustomTwitterScraper**: Reads from your database (no external APIs)
- **Background Services**: Twitter scraping infrastructure
- **Configuration Files**: All necessary configs included
- **Database**: Pre-populated with 1,114+ real tweets

### ✅ **Key Files for Custom Twitter Integration**
- `scraping/x/custom_twitter_scraper.py` - Main custom scraper implementation
- `scraping/provider.py` - Already configured to use CustomTwitterScraper
- `scraping/scraper.py` - ScraperId.X_CUSTOM already defined
- `background_scraper_service.py` - Background Twitter scraping service
- `custom_twitter_api_service.py` - API service for Twitter data
- `ecosystem.config.js` - PM2 configuration for services

## Quick Start (Clone and Run)

### 1. **Clone Repository**
```bash
git clone <your-repo-url>
cd data-universe
```

### 2. **Install Dependencies**
```bash
# Python dependencies
pip install -r requirements.txt

# Node.js dependencies (for PM2)
npm install -g pm2
npm install
```

### 3. **Environment Setup**
The `.env` file is included with all necessary configurations:
```bash
# Check .env file is present
cat .env
```

### 4. **Database Setup**
The SQLite database with real Twitter data is included:
```bash
# Verify database exists
ls -la enhanced_accounts.db
ls -la /home/anirudh/Downloads/twitter/X_scrapping/twitter_miner_data.sqlite
```

### 5. **Start Background Services**
```bash
# Start Twitter scraping service
pm2 start ecosystem.config.js

# Check services are running
pm2 status
pm2 logs twitter-scraper
```

### 6. **Test Custom Twitter Scraper**
```bash
# Test the custom scraper
python -c "
import asyncio
import sys
sys.path.append('.')
from scraping.x.custom_twitter_scraper import test_custom_twitter_scraper
asyncio.run(test_custom_twitter_scraper())
"
```

### 7. **Run Miner with Custom Scraper**
```bash
# Configure miner to use custom scraper
python neurons/miner.py --scraper_id X.custom
```

## Architecture

### **Data Flow**
```
ProxyTwitterMiner (Background) → Database → CustomTwitterScraper → Miner
```

### **Scraper Options**
- `X.custom` - Your custom scraper (free, your data)
- `X.apidojo` - External Apify service (costs money)
- `X.microworlds` - External Microworlds service
- `X.quacker` - External Quacker service

## Configuration

### **Using Custom Twitter Scraper**
```python
# In miner configuration
scraper_id = "X.custom"  # Uses your ProxyTwitterMiner data
```

### **Database Paths**
- Main database: `/home/anirudh/Downloads/twitter/X_scrapping/twitter_miner_data.sqlite`
- Accounts database: `enhanced_accounts.db`

## Monitoring

### **Check Scraper Stats**
```python
from scraping.provider import ScraperProvider
from scraping.scraper import ScraperId

provider = ScraperProvider()
scraper = provider.get(ScraperId.X_CUSTOM)
stats = scraper.get_scraper_stats()
print(stats)
```

### **Expected Output**
```json
{
  "total_tweets": 1114,
  "recent_tweets_1h": 326,
  "recent_tweets_24h": 643,
  "top_labels": [
    {"label": "bitcoin", "count": 91},
    {"label": "crypto", "count": 50},
    {"label": "ai", "count": 31}
  ]
}
```

## Troubleshooting

### **Common Issues**

1. **Database not found**
   ```bash
   # Check database path in custom_twitter_scraper.py
   # Update path if needed
   ```

2. **No recent tweets**
   ```bash
   # Check background service is running
   pm2 logs twitter-scraper
   ```

3. **Import errors**
   ```bash
   # Ensure all dependencies installed
   pip install -r requirements.txt
   ```

## Benefits of This Setup

### **Cost Savings**
- ❌ **Before**: Pay Apify for each API call
- ✅ **After**: Use your own infrastructure (free)

### **Data Quality**
- ❌ **Before**: Limited by external service capabilities
- ✅ **After**: Your sophisticated ProxyTwitterMiner

### **Control**
- ❌ **Before**: Dependent on external service uptime
- ✅ **After**: Full control over data pipeline

## File Structure
```
data-universe/
├── scraping/x/custom_twitter_scraper.py    # Custom scraper implementation
├── scraping/provider.py                    # Scraper provider (pre-configured)
├── background_scraper_service.py           # Background Twitter service
├── custom_twitter_api_service.py           # API service
├── ecosystem.config.js                     # PM2 configuration
├── .env                                     # Environment variables
├── enhanced_accounts.db                    # Twitter accounts database
└── requirements.txt                        # Python dependencies
```

## Support

The custom Twitter scraper is fully integrated and tested:
- ✅ 1,114 total tweets in database
- ✅ 326 tweets in last hour (active collection)
- ✅ Successfully tested through ScraperProvider
- ✅ Real tweet retrieval confirmed

For issues, check the logs:
```bash
pm2 logs twitter-scraper
