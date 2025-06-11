#!/usr/bin/env python3
"""
Background Twitter Scraper Service
Continuously scrapes Twitter data and stores it in database for Bittensor miners
"""

import asyncio
import logging
import os
import sys
import signal
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json

# Add your custom scraper to path - use current directory for cloned repo
scraper_path = os.path.join(os.getcwd(), 'X_scrapping')
if not os.path.exists(scraper_path):
    # Fallback to current directory if X_scrapping doesn't exist
    scraper_path = os.getcwd()

if scraper_path not in sys.path:
    sys.path.insert(0, scraper_path)

# Change to scraper directory to ensure all imports work
original_cwd = os.getcwd()
if os.path.exists(scraper_path) and scraper_path != os.getcwd():
    os.chdir(scraper_path)

try:
    from proxy_twitter_miner import ProxyTwitterMiner
    CUSTOM_SCRAPER_AVAILABLE = True
    print("✅ Successfully imported your sophisticated proxy_twitter_miner!")
    print(f"✅ ProxyTwitterMiner loaded from: {scraper_path}")
    
    # STAY in the scraper directory - don't change back!
    # os.chdir(original_cwd)  # Commented out to stay in X_scrapping directory
    
    # Create TweetData class to match your scraper's output
    class TweetData:
        def __init__(self, **kwargs):
            self.id = kwargs.get('id', '')
            self.url = kwargs.get('url', '')
            self.text = kwargs.get('text', '')
            self.author_username = kwargs.get('author_username', '')
            self.author_display_name = kwargs.get('author_display_name', '')
            self.created_at = kwargs.get('created_at', datetime.now())
            self.like_count = kwargs.get('like_count', 0)
            self.retweet_count = kwargs.get('retweet_count', 0)
            self.reply_count = kwargs.get('reply_count', 0)
            self.quote_count = kwargs.get('quote_count', 0)
            self.hashtags = kwargs.get('hashtags', [])
            self.media_urls = kwargs.get('media_urls', [])
            self.is_retweet = kwargs.get('is_retweet', False)
            self.is_reply = kwargs.get('is_reply', False)
            self.conversation_id = kwargs.get('conversation_id', '')
            
except ImportError as e:
    # Change back to original directory on error
    os.chdir(original_cwd)
    print(f"❌ Custom scraper not available: {e}")
    print("❌ FALLING BACK TO MOCK DATA - FIX IMPORT ISSUES!")
    CUSTOM_SCRAPER_AVAILABLE = False
    
    # Create mock classes for testing
    class ProxyTwitterMiner:
        def __init__(self):
            pass
        
        async def scrape_tweets(self, count):
            # Return mock tweets for testing
            mock_tweets = []
            for i in range(min(count, 10)):
                mock_tweets.append(TweetData(
                    id=f"mock_tweet_{i}",
                    url=f"https://twitter.com/mock/status/{i}",
                    text=f"Mock tweet {i} about #bitcoin and #crypto",
                    author_username=f"mock_user_{i}",
                    author_display_name=f"Mock User {i}",
                    created_at=datetime.now(),
                    like_count=i * 10,
                    retweet_count=i * 5,
                    hashtags=["bitcoin", "crypto"],
                    media_urls=[],
                    is_retweet=False,
                    is_reply=False
                ))
            return mock_tweets
        
        def get_stats(self):
            return {
                "working_proxies": 10,
                "working_accounts": 5,
                "successful_requests": 95,
                "total_requests": 100
            }
    
    class TweetData:
        def __init__(self, **kwargs):
            self.id = kwargs.get('id', '')
            self.url = kwargs.get('url', '')
            self.text = kwargs.get('text', '')
            self.author_username = kwargs.get('author_username', '')
            self.author_display_name = kwargs.get('author_display_name', '')
            self.created_at = kwargs.get('created_at', datetime.now())
            self.like_count = kwargs.get('like_count', 0)
            self.retweet_count = kwargs.get('retweet_count', 0)
            self.reply_count = kwargs.get('reply_count', 0)
            self.quote_count = kwargs.get('quote_count', 0)
            self.hashtags = kwargs.get('hashtags', [])
            self.media_urls = kwargs.get('media_urls', [])
            self.is_retweet = kwargs.get('is_retweet', False)
            self.is_reply = kwargs.get('is_reply', False)
            self.conversation_id = kwargs.get('conversation_id', '')
    
    class OptimizedDataStorage:
        def __init__(self, config):
            print("Using fallback storage (SQLite only)")
        
        def store_tweets_batch(self, tweets):
            return len(tweets)  # Mock successful storage
        
        def flush_pending_tweets(self):
            pass

class BackgroundTwitterScraperService:
    """
    Background service that continuously scrapes Twitter data
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.running = False
        
        # Initialize your custom scraper with correct db_path
        scraper_dir = '/home/anirudh/Downloads/twitter/X_scrapping'
        self.scraper = ProxyTwitterMiner(
            db_path=f"{scraper_dir}/enhanced_accounts.db"
        )
        
        # Initialize storage (PostgreSQL + SQLite)
        postgres_config = {
            "dbname": os.getenv("POSTGRES_DB", "bittensor_mining"),
            "user": os.getenv("POSTGRES_USER", "postgres"),
            "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", "5432"))
        }
        
        try:
            self.storage = OptimizedDataStorage(postgres_config)
            self.logger.info("Storage initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize storage: {e}")
            # Fallback to SQLite only
            self.storage = None
        
        # Configuration - Match your sophisticated scraper
        self.batch_size = int(os.getenv("SCRAPER_BATCH_SIZE", "150"))  # 150 tweets per batch (100+ in 5 min)
        self.batch_interval = int(os.getenv("SCRAPER_BATCH_INTERVAL", "300"))  # 5 minutes
        self.target_tweets_per_hour = int(os.getenv("SCRAPER_TWEETS_PER_HOUR", "1800"))  # Higher target
        self.max_concurrent = 5  # Parallel processing like your scraper
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # Statistics
        self.stats = {
            "total_scraped": 0,
            "total_stored": 0,
            "batches_completed": 0,
            "errors": 0,
            "start_time": datetime.now()
        }
        
        # Target hashtags for Bittensor subnet
        self.target_hashtags = [
            "#bitcoin", "#bitcoincharts", "#bitcoiner", "#bitcoinexchange",
            "#bitcoinmining", "#bitcoinnews", "#bitcoinprice", "#bitcointechnology",
            "#bitcointrading", "#bittensor", "#btc", "#cryptocurrency", "#crypto",
            "#defi", "#decentralizedfinance", "#tao", "#ai", "#artificialintelligence",
            "#blockchain", "#web3", "#ethereum", "#solana", "#cardano", "#polkadot"
        ]

    async def start_continuous_scraping(self):
        """Start the continuous scraping process"""
        self.running = True
        self.logger.info("🚀 Starting background Twitter scraper service")
        self.logger.info(f"📊 Configuration:")
        self.logger.info(f"   Batch size: {self.batch_size} tweets")
        self.logger.info(f"   Batch interval: {self.batch_interval} seconds")
        self.logger.info(f"   Target rate: {self.target_tweets_per_hour} tweets/hour")
        self.logger.info(f"   Target hashtags: {len(self.target_hashtags)} hashtags")
        self.logger.info(f"   Custom scraper available: {CUSTOM_SCRAPER_AVAILABLE}")
        
        batch_count = 0
        
        try:
            while self.running:
                batch_count += 1
                batch_start_time = datetime.now()
                
                self.logger.info(f"\n🔄 Starting batch {batch_count}")
                
                try:
                    # Scrape tweets using your sophisticated system
                    tweets = await self.scrape_batch()
                    
                    if tweets:
                        # Store tweets in database
                        stored_count = await self.store_batch(tweets)
                        
                        # Update statistics
                        self.stats["total_scraped"] += len(tweets)
                        self.stats["total_stored"] += stored_count
                        self.stats["batches_completed"] += 1
                        
                        batch_time = (datetime.now() - batch_start_time).total_seconds()
                        
                        self.logger.info(f"✅ Batch {batch_count} completed:")
                        self.logger.info(f"   📊 Scraped: {len(tweets)} tweets")
                        self.logger.info(f"   💾 Stored: {stored_count} tweets")
                        self.logger.info(f"   ⏱️  Time: {batch_time:.1f} seconds")
                        
                        # Show progress every 10 batches
                        if batch_count % 10 == 0:
                            await self.show_progress_stats()
                    
                    else:
                        self.logger.warning(f"❌ Batch {batch_count}: No tweets scraped")
                        self.stats["errors"] += 1
                
                except Exception as e:
                    self.logger.error(f"❌ Batch {batch_count} failed: {e}")
                    self.stats["errors"] += 1
                    
                    # Wait shorter time on error
                    await asyncio.sleep(60)
                    continue
                
                # Wait before next batch
                self.logger.info(f"⏳ Waiting {self.batch_interval} seconds before next batch...")
                await asyncio.sleep(self.batch_interval)
                
        except KeyboardInterrupt:
            self.logger.info("🛑 Received shutdown signal")
        except Exception as e:
            self.logger.error(f"💥 Critical error in scraping loop: {e}")
        finally:
            await self.shutdown()

    async def scrape_batch(self) -> List[TweetData]:
        """Scrape a batch of tweets using your custom scraper"""
        try:
            self.logger.info("📡 Starting tweet scraping...")
            
            if CUSTOM_SCRAPER_AVAILABLE:
                self.logger.info(f"🔥 Using your sophisticated ProxyTwitterMiner for {self.batch_size} tweets!")
                # Use your sophisticated scraper
                tweets = await self.scraper.scrape_tweets(self.batch_size)
            else:
                self.logger.warning("⚠️  Using fallback mock scraper (limited to 10 tweets)")
                # Fallback to mock scraper
                tweets = await self.scraper.scrape_tweets(self.batch_size)
            
            self.logger.info(f"📊 Scraper returned {len(tweets)} tweets")
            
            # Filter and validate tweets
            valid_tweets = []
            for tweet in tweets:
                if self.is_valid_tweet(tweet):
                    valid_tweets.append(tweet)
            
            self.logger.info(f"✅ {len(valid_tweets)} valid tweets after filtering")
            return valid_tweets
            
        except Exception as e:
            self.logger.error(f"Error in scrape_batch: {e}")
            return []

    def is_valid_tweet(self, tweet: TweetData) -> bool:
        """Validate tweet data"""
        try:
            # Basic validation
            if not tweet.text or not tweet.url or not tweet.id:
                return False
            
            # Check if tweet contains target hashtags
            if tweet.hashtags:
                for hashtag in tweet.hashtags:
                    if hashtag.lower() in [tag.lower() for tag in self.target_hashtags]:
                        return True
            
            # Check if text contains target keywords
            text_lower = tweet.text.lower()
            for hashtag in self.target_hashtags:
                if hashtag.lower().replace('#', '') in text_lower:
                    return True
            
            return False
            
        except Exception:
            return False

    async def store_batch(self, tweets: List[TweetData]) -> int:
        """Store tweets in database"""
        try:
            if not self.storage:
                # Fallback storage to SQLite
                return await self.store_batch_sqlite(tweets)
            
            # Use optimized storage
            stored_count = self.storage.store_tweets_batch(tweets)
            self.logger.info(f"💾 Stored {stored_count} tweets in database")
            return stored_count
            
        except Exception as e:
            self.logger.error(f"Error storing batch: {e}")
            # Try fallback storage
            return await self.store_batch_sqlite(tweets)

    async def store_batch_sqlite(self, tweets: List[TweetData]) -> int:
        """Fallback storage to SQLite"""
        try:
            import sqlite3
            import gzip
            
            db_path = "/home/anirudh/Downloads/twitter/X_scrapping/twitter_miner_data.sqlite"
            
            # Create table if not exists
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS DataEntity (
                    uri TEXT PRIMARY KEY,
                    datetime TIMESTAMP NOT NULL,
                    timeBucketId INTEGER NOT NULL,
                    source INTEGER NOT NULL,
                    label TEXT,
                    content BLOB NOT NULL,
                    contentSizeBytes INTEGER NOT NULL
                )
            """)
            
            stored_count = 0
            for tweet in tweets:
                try:
                    # Convert to JSON and compress
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
                    
                    content_json = json.dumps(tweet_dict, ensure_ascii=False)
                    content_bytes = gzip.compress(content_json.encode('utf-8'))
                    
                    # Calculate time bucket
                    time_bucket_id = int(tweet.created_at.timestamp() // 3600)
                    
                    # Get primary hashtag
                    label = None
                    if tweet.hashtags:
                        label = tweet.hashtags[0].lower().replace('#', '')
                    
                    cursor.execute("""
                        INSERT OR IGNORE INTO DataEntity 
                        (uri, datetime, timeBucketId, source, label, content, contentSizeBytes)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        tweet.url,
                        tweet.created_at,
                        time_bucket_id,
                        2,  # Twitter source
                        label,
                        content_bytes,
                        len(content_bytes)
                    ))
                    
                    if cursor.rowcount > 0:
                        stored_count += 1
                        
                except Exception as e:
                    self.logger.warning(f"Failed to store tweet {tweet.id}: {e}")
                    continue
            
            conn.commit()
            conn.close()
            
            return stored_count
            
        except Exception as e:
            self.logger.error(f"SQLite storage failed: {e}")
            return 0

    async def show_progress_stats(self):
        """Show progress statistics"""
        runtime = datetime.now() - self.stats["start_time"]
        runtime_hours = runtime.total_seconds() / 3600
        
        tweets_per_hour = self.stats["total_scraped"] / max(runtime_hours, 0.1)
        daily_projection = tweets_per_hour * 24
        
        self.logger.info(f"\n📊 Progress Statistics:")
        self.logger.info(f"   ⏱️  Runtime: {runtime_hours:.1f} hours")
        self.logger.info(f"   🔢 Total batches: {self.stats['batches_completed']}")
        self.logger.info(f"   🐦 Total scraped: {self.stats['total_scraped']:,}")
        self.logger.info(f"   💾 Total stored: {self.stats['total_stored']:,}")
        self.logger.info(f"   📈 Rate: {tweets_per_hour:.1f} tweets/hour")
        self.logger.info(f"   📅 Daily projection: {daily_projection:,.0f} tweets/day")
        self.logger.info(f"   ❌ Errors: {self.stats['errors']}")
        
        # Show scraper health
        scraper_stats = self.scraper.get_stats()
        self.logger.info(f"\n🏥 Scraper Health:")
        self.logger.info(f"   🔗 Working proxies: {scraper_stats.get('working_proxies', 0)}")
        self.logger.info(f"   👤 Working accounts: {scraper_stats.get('working_accounts', 0)}")
        self.logger.info(f"   ✅ Success rate: {(scraper_stats.get('successful_requests', 0) / max(1, scraper_stats.get('total_requests', 1)) * 100):.1f}%")

    async def shutdown(self):
        """Graceful shutdown"""
        self.running = False
        self.logger.info("🛑 Shutting down background scraper service")
        
        # Show final statistics
        runtime = datetime.now() - self.stats["start_time"]
        self.logger.info(f"\n📊 Final Statistics:")
        self.logger.info(f"   ⏱️  Total runtime: {runtime}")
        self.logger.info(f"   🔢 Total batches: {self.stats['batches_completed']}")
        self.logger.info(f"   🐦 Total scraped: {self.stats['total_scraped']:,}")
        self.logger.info(f"   💾 Total stored: {self.stats['total_stored']:,}")
        self.logger.info(f"   ❌ Total errors: {self.stats['errors']}")
        
        # Flush any pending data
        if self.storage:
            try:
                self.storage.flush_pending_tweets()
            except Exception as e:
                self.logger.error(f"Error flushing pending tweets: {e}")

def setup_signal_handlers(service):
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}")
        asyncio.create_task(service.shutdown())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

async def main():
    """Main function"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('background_scraper.log'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    if not CUSTOM_SCRAPER_AVAILABLE:
        logger.warning("Custom scraper not available. Using fallback mode.")
    else:
        logger.info("🔥 Your sophisticated ProxyTwitterMiner is ready!")
    
    # Create and start service
    service = BackgroundTwitterScraperService()
    
    # Setup signal handlers
    setup_signal_handlers(service)
    
    try:
        await service.start_continuous_scraping()
    except Exception as e:
        logger.error(f"Service failed: {e}")
    finally:
        await service.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
