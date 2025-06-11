#!/usr/bin/env python3
"""
Custom Twitter API Service
FastAPI service that serves pre-scraped Twitter data to Bittensor miners
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import logging
import sqlite3
import gzip

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Add your custom scraper to path
sys.path.insert(0, '/home/anirudh/Downloads/twitter/X_scrapping')

try:
    from proxy_twitter_miner import ProxyTwitterMiner, TweetData
    from optimized_data_storage import OptimizedDataStorage
    CUSTOM_SCRAPER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Custom scraper not available: {e}")
    CUSTOM_SCRAPER_AVAILABLE = False

# FastAPI app
app = FastAPI(
    title="Custom Twitter API for Bittensor",
    description="API service that provides Twitter data to replace Apify",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class SearchRequest(BaseModel):
    action: str = "search"
    query: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    limit: int = 150
    include_retweets: bool = False

class ValidateRequest(BaseModel):
    action: str = "validate_urls"
    urls: List[str]
    include_metadata: bool = True

class TwitterAPIService:
    """Main service class that handles Twitter data requests"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db_path = "/home/anirudh/Downloads/twitter/X_scrapping/twitter_miner_data.sqlite"
        
        # Initialize custom scraper for real-time validation
        if CUSTOM_SCRAPER_AVAILABLE:
            self.scraper = ProxyTwitterMiner()
        else:
            self.scraper = None
            self.logger.warning("Custom scraper not available, using mock data")
    
    async def search_tweets(self, request: SearchRequest) -> Dict[str, Any]:
        """Search for tweets in pre-scraped database"""
        try:
            self.logger.info(f"Searching tweets: query='{request.query}', limit={request.limit}")
            
            # Query database for matching tweets
            tweets = await self._query_database(
                query=request.query,
                start_date=request.start_date,
                end_date=request.end_date,
                limit=request.limit
            )
            
            self.logger.info(f"Found {len(tweets)} tweets in database")
            
            # If no tweets found in database, try real-time scraping as fallback
            if not tweets and self.scraper:
                self.logger.info("No tweets in database, trying real-time scraping")
                tweets = await self._real_time_scrape(request.query, request.limit)
            
            return {
                "status": "success",
                "tweets": tweets,
                "count": len(tweets),
                "source": "database" if tweets else "real-time"
            }
            
        except Exception as e:
            self.logger.error(f"Search error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def validate_urls(self, request: ValidateRequest) -> Dict[str, Any]:
        """Validate specific tweet URLs"""
        try:
            self.logger.info(f"Validating {len(request.urls)} URLs")
            
            validated_tweets = []
            
            # First try to find tweets in database
            for url in request.urls:
                tweet = await self._find_tweet_by_url(url)
                if tweet:
                    validated_tweets.append(tweet)
            
            # If not found in database and scraper available, try real-time validation
            if len(validated_tweets) < len(request.urls) and self.scraper:
                missing_urls = [url for url in request.urls if not any(t.get("url") == url for t in validated_tweets)]
                if missing_urls:
                    self.logger.info(f"Real-time validating {len(missing_urls)} URLs")
                    real_time_tweets = await self._real_time_validate(missing_urls)
                    validated_tweets.extend(real_time_tweets)
            
            return {
                "status": "success",
                "tweets": validated_tweets,
                "count": len(validated_tweets),
                "requested": len(request.urls)
            }
            
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _query_database(self, query: str, start_date: str, end_date: str, limit: int) -> List[Dict]:
        """Query the SQLite database for matching tweets"""
        try:
            # Parse dates
            if start_date:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            else:
                start_dt = datetime.now() - timedelta(hours=24)
            
            if end_date:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            else:
                end_dt = datetime.now()
            
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Build SQL query
            sql_conditions = []
            params = []
            
            # Date range
            sql_conditions.append("datetime BETWEEN ? AND ?")
            params.extend([start_dt, end_dt])
            
            # Source filter (Twitter/X = 2)
            sql_conditions.append("source = ?")
            params.append(2)
            
            # Query filter
            if query and query.strip():
                # Handle hashtag queries
                if query.startswith('#'):
                    hashtag = query[1:].lower()
                    sql_conditions.append("label = ?")
                    params.append(hashtag)
                else:
                    # Text search in content
                    sql_conditions.append("content LIKE ?")
                    params.append(f"%{query}%")
            
            # Build final query
            sql = f"""
                SELECT uri, datetime, content, contentSizeBytes
                FROM DataEntity
                WHERE {' AND '.join(sql_conditions)}
                ORDER BY datetime DESC
                LIMIT ?
            """
            params.append(limit)
            
            # Execute query
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            # Convert to tweet format
            tweets = []
            for row in rows:
                try:
                    # Decompress and parse content
                    content_bytes = row['content']
                    if isinstance(content_bytes, bytes):
                        try:
                            # Try gzip decompression first
                            content_str = gzip.decompress(content_bytes).decode('utf-8')
                        except:
                            # Fallback to direct decode
                            content_str = content_bytes.decode('utf-8')
                    else:
                        content_str = str(content_bytes)
                    
                    # Parse JSON content
                    tweet_data = json.loads(content_str)
                    tweets.append(tweet_data)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to parse tweet content: {e}")
                    continue
            
            conn.close()
            return tweets
            
        except Exception as e:
            self.logger.error(f"Database query error: {e}")
            return []
    
    async def _find_tweet_by_url(self, url: str) -> Optional[Dict]:
        """Find a specific tweet by URL in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT content FROM DataEntity WHERE uri = ?", (url,))
            row = cursor.fetchone()
            
            if row:
                content_bytes = row['content']
                if isinstance(content_bytes, bytes):
                    try:
                        content_str = gzip.decompress(content_bytes).decode('utf-8')
                    except:
                        content_str = content_bytes.decode('utf-8')
                else:
                    content_str = str(content_bytes)
                
                tweet_data = json.loads(content_str)
                conn.close()
                return tweet_data
            
            conn.close()
            return None
            
        except Exception as e:
            self.logger.error(f"URL lookup error: {e}")
            return None
    
    async def _real_time_scrape(self, query: str, limit: int) -> List[Dict]:
        """Fallback real-time scraping when database is empty"""
        if not self.scraper:
            return []
        
        try:
            # Use your custom scraper for real-time data
            tweets = await self.scraper.scrape_tweets(limit)
            
            # Convert TweetData to dict format
            tweet_dicts = []
            for tweet in tweets:
                tweet_dict = {
                    "id": tweet.id,
                    "url": tweet.url,
                    "text": tweet.text,
                    "author_username": tweet.author_username,
                    "author_display_name": tweet.author_display_name,
                    "created_at": tweet.created_at.isoformat(),
                    "like_count": tweet.like_count,
                    "retweet_count": tweet.retweet_count,
                    "reply_count": tweet.reply_count,
                    "quote_count": tweet.quote_count,
                    "hashtags": tweet.hashtags,
                    "media_urls": tweet.media_urls,
                    "is_retweet": tweet.is_retweet,
                    "is_reply": tweet.is_reply,
                    "conversation_id": tweet.conversation_id
                }
                tweet_dicts.append(tweet_dict)
            
            return tweet_dicts
            
        except Exception as e:
            self.logger.error(f"Real-time scraping error: {e}")
            return []
    
    async def _real_time_validate(self, urls: List[str]) -> List[Dict]:
        """Real-time validation of specific URLs"""
        if not self.scraper:
            return []
        
        try:
            # This would use your scraper's validation functionality
            # For now, return empty list
            return []
            
        except Exception as e:
            self.logger.error(f"Real-time validation error: {e}")
            return []

# Global service instance
twitter_service = TwitterAPIService()

# Authentication
async def verify_token(authorization: str = Header(None)):
    """Simple token verification"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    token = authorization.replace("Bearer ", "")
    expected_token = os.getenv("CUSTOM_TWITTER_API_TOKEN", "your-api-token")
    
    if token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return token

# API endpoints
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "Custom Twitter API for Bittensor",
        "version": "1.0.0",
        "scraper_available": CUSTOM_SCRAPER_AVAILABLE
    }

@app.post("/api/search")
async def search_tweets(request: SearchRequest, token: str = Depends(verify_token)):
    """Search for tweets"""
    return await twitter_service.search_tweets(request)

@app.post("/api/validate")
async def validate_urls(request: ValidateRequest, token: str = Depends(verify_token)):
    """Validate tweet URLs"""
    return await twitter_service.validate_urls(request)

@app.get("/api/stats")
async def get_stats(token: str = Depends(verify_token)):
    """Get database statistics"""
    try:
        conn = sqlite3.connect(twitter_service.db_path)
        cursor = conn.cursor()
        
        # Get basic stats
        cursor.execute("SELECT COUNT(*) FROM DataEntity WHERE source = 2")
        total_tweets = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT label) FROM DataEntity WHERE source = 2 AND label IS NOT NULL")
        unique_labels = cursor.fetchone()[0]
        
        cursor.execute("SELECT MAX(datetime), MIN(datetime) FROM DataEntity WHERE source = 2")
        date_range = cursor.fetchone()
        
        conn.close()
        
        return {
            "total_tweets": total_tweets,
            "unique_labels": unique_labels,
            "date_range": {
                "latest": date_range[0],
                "earliest": date_range[1]
            },
            "database_path": twitter_service.db_path
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the API service
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
