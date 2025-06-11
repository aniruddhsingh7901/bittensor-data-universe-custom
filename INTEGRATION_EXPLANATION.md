# How Custom Twitter Scraper Integration Works

## Understanding the Data Flow

### Current Bittensor System
1. **Validator** requests data from **Miner**
2. **Miner** calls **Apify** (paid service) to scrape Twitter
3. **Miner** stores data locally in SQLite
4. **Miner** responds to Validator with data

### Your Custom Scraper Options

## Option 1: Direct Integration (Replace Apify)

### How it Works:
```python
# In your miner code (neurons/miner.py)
class Miner:
    def __init__(self):
        # Instead of using Apify
        # self.scraper = ApiDojoTwitterScraper()  # OLD
        
        # Use your custom scraper directly
        self.scraper = CustomTwitterScraper()     # NEW
    
    async def handle_request(self, synapse):
        # When validator requests data, scrape in real-time
        tweets = await self.scraper.scrape_tweets(query, limit)
        return tweets
```

### Pros:
- ✅ No additional infrastructure needed
- ✅ Real-time scraping on demand
- ✅ Direct replacement of Apify
- ✅ Maintains existing Bittensor flow

### Cons:
- ❌ Scraping happens during validator requests (slower response)
- ❌ Limited by request timeouts
- ❌ Proxy/account management per miner instance

## Option 2: Background Service + API (Recommended)

### Architecture Components:

#### 1. Background Scraper Service
```python
# Runs continuously, independent of miner
class BackgroundTwitterScraper:
    async def run_continuous(self):
        while True:
            # Scrape tweets continuously
            tweets = await self.scrape_batch()
            
            # Store in database
            await self.store_tweets(tweets)
            
            # Wait before next batch
            await asyncio.sleep(300)  # 5 minutes
```

#### 2. API Service
```python
# HTTP API that miners can call
class TwitterScraperAPI:
    async def get_tweets(self, query: str, limit: int):
        # Query pre-scraped data from database
        tweets = await self.db.query_tweets(query, limit)
        return tweets
    
    async def validate_urls(self, urls: List[str]):
        # Real-time validation for specific URLs
        results = await self.scraper.validate_tweets(urls)
        return results
```

#### 3. Modified Miner
```python
class Miner:
    def __init__(self):
        # Use API client instead of direct scraping
        self.twitter_api = CustomTwitterAPIClient()
    
    async def handle_request(self, synapse):
        # Fast response from pre-scraped data
        tweets = await self.twitter_api.get_tweets(query, limit)
        return tweets
```

### How Data Flows:

#### Background Process:
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Background      │───▶│ Twitter API     │───▶│ PostgreSQL DB   │
│ Scraper         │    │ (Your Proxies)  │    │ (Continuous     │
│ (Continuous)    │    │                 │    │  Storage)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

#### Miner Request:
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Validator       │───▶│ Miner           │───▶│ API Service     │
│ (Needs Data)    │    │ (Fast Response) │    │ (Query DB)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                      │
                              ▼                      ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │ SQLite Store    │    │ PostgreSQL DB   │
                       │ (Bittensor)     │    │ (Pre-scraped)   │
                       └─────────────────┘    └─────────────────┘
```

## Recommended Implementation

### Step 1: Background Scraper Service
```python
# scraper_service.py
class TwitterScraperService:
    def __init__(self):
        self.scraper = ProxyTwitterMiner()
        self.storage = OptimizedDataStorage()
        
    async def start_background_scraping(self):
        """Continuously scrape and store tweets"""
        while True:
            try:
                # Scrape tweets for target hashtags
                tweets = await self.scraper.scrape_tweets(1000)
                
                # Store in database
                await self.storage.store_tweets_batch(tweets)
                
                # Wait 5 minutes
                await asyncio.sleep(300)
                
            except Exception as e:
                logging.error(f"Background scraping error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

# Run as: python scraper_service.py
```

### Step 2: API Service
```python
# api_service.py
from fastapi import FastAPI
from typing import List, Dict

app = FastAPI()

class TwitterAPI:
    def __init__(self):
        self.storage = OptimizedDataStorage()
        self.scraper = ProxyTwitterMiner()  # For real-time validation
    
    async def search_tweets(self, query: str, start_date: str, end_date: str, limit: int):
        """Get pre-scraped tweets matching criteria"""
        return await self.storage.query_tweets(query, start_date, end_date, limit)
    
    async def validate_urls(self, urls: List[str]):
        """Real-time validation of specific URLs"""
        return await self.scraper.validate_tweet_urls(urls)

@app.post("/api/search")
async def search_tweets(request: dict):
    api = TwitterAPI()
    return await api.search_tweets(**request)

@app.post("/api/validate")
async def validate_urls(request: dict):
    api = TwitterAPI()
    return await api.validate_urls(request["urls"])

# Run as: uvicorn api_service:app --host 0.0.0.0 --port 8000
```

### Step 3: Integration Layer
```python
# scraping/custom_twitter_runner.py
class CustomTwitterRunner:
    """Replaces ActorRunner - calls your API instead of Apify"""
    
    def __init__(self):
        self.api_url = os.getenv("CUSTOM_TWITTER_API_URL", "http://localhost:8000")
        self.api_token = os.getenv("CUSTOM_TWITTER_API_TOKEN")
    
    async def run(self, config: RunConfig, run_input: dict) -> List[dict]:
        """Main entry point - maintains Apify compatibility"""
        
        if "searchTerms" in run_input:
            # Search request
            query_info = self._parse_search_query(run_input["searchTerms"][0])
            
            response = await self._call_api("/api/search", {
                "query": query_info["query"],
                "start_date": query_info["start_date"],
                "end_date": query_info["end_date"],
                "limit": run_input.get("maxTweets", 150)
            })
            
        elif "startUrls" in run_input:
            # URL validation request
            response = await self._call_api("/api/validate", {
                "urls": run_input["startUrls"]
            })
        
        # Convert your format to Apify format
        return self._convert_to_apify_format(response)
```

## Benefits of This Architecture

### 1. Performance
- **Fast Response**: Pre-scraped data = instant responses
- **No Timeouts**: Validators get quick responses
- **Scalable**: One scraper serves multiple miners

### 2. Reliability
- **Continuous Operation**: Scraper runs 24/7
- **Error Recovery**: Background process handles failures
- **Data Availability**: Always have fresh data ready

### 3. Cost Efficiency
- **No Apify Costs**: $0 instead of $100-500/month
- **Resource Sharing**: One scraper, multiple miners
- **Efficient Proxies**: Centralized proxy management

### 4. Compatibility
- **Drop-in Replacement**: Existing code unchanged
- **Same API**: Miners use same interface
- **Same Data Format**: Validators see identical data

## Deployment Strategy

### Single Server Setup:
```bash
# Terminal 1: Background scraper
python scraper_service.py

# Terminal 2: API service  
uvicorn api_service:app --host 0.0.0.0 --port 8000

# Terminal 3: Your miner
python -m neurons.miner --netuid 13
```

### Production Setup:
```bash
# Use systemd services for auto-restart
sudo systemctl start twitter-scraper
sudo systemctl start twitter-api
sudo systemctl start bittensor-miner
```

This architecture gives you the best of both worlds: the power of your custom scraper with the compatibility of the existing Bittensor system!
