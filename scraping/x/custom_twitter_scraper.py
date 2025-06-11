"""
Custom Twitter Scraper for Bittensor Data Universe
Reads from database where background service stores real Twitter data
Similar to how enhanced_apidojo_scraper works with external services
"""

import asyncio
import logging
import json
import gzip
import sqlite3
import traceback
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
import bittensor as bt

from common.data import DataEntity, DataLabel, DataSource
from common.date_range import DateRange
from scraping.scraper import ScrapeConfig, Scraper, ValidationResult, HFValidationResult
from scraping.x.model import XContent
from scraping.x import utils


class CustomTwitterScraper(Scraper):
    """
    Custom Twitter scraper that reads from database where background service
    stores real Twitter data. Works like enhanced_apidojo_scraper but uses
    our own sophisticated Twitter scraping service.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db_path = "./SqliteMinerStorage.sqlite"
        
        # Verify database exists and has data
        self._verify_database()
    
    def _verify_database(self):
        """Verify the database exists and has recent data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if DataEntity table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='DataEntity'
            """)
            
            if not cursor.fetchone():
                self.logger.warning(f"No 'DataEntity' table found in {self.db_path}")
                return
            
            # Check for recent Twitter data (source = 2 for X/Twitter)
            cursor.execute("""
                SELECT COUNT(*) FROM DataEntity 
                WHERE source = 2 AND datetime > datetime('now', '-1 hour')
            """)
            
            recent_count = cursor.fetchone()[0]
            self.logger.info(f"✅ Database verified: {recent_count} Twitter DataEntities in last hour")
            
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Database verification failed: {e}")
    
    async def scrape(self, scrape_config: ScrapeConfig) -> List[DataEntity]:
        """
        Scrape Twitter data from our database where background service stores real tweets
        """
        self.logger.info(f"🔥 Starting custom Twitter scrape from database")
        self.logger.info(f"📊 Target: {scrape_config.entity_limit} tweets")
        self.logger.info(f"🏷️  Labels: {[label.value for label in scrape_config.labels]}")
        self.logger.info(f"📅 Date range: {scrape_config.date_range.start} to {scrape_config.date_range.end}")
        
        try:
            # Get DataEntity objects directly from database
            data_entities = await self._get_tweets_from_database(scrape_config)
            
            if not data_entities:
                self.logger.warning("No tweets found in database")
                return []
            
            self.logger.success(f"✅ Custom Twitter scrape completed: {len(data_entities)} DataEntity objects")
            return data_entities
            
        except Exception as e:
            self.logger.error(f"Error in custom Twitter scraping: {traceback.format_exc()}")
            return []
    
    async def _get_tweets_from_database(self, scrape_config: ScrapeConfig) -> List[DataEntity]:
        """Get DataEntity objects from database based on scrape configuration"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build query based on labels and date range
            query_parts = []
            params = []
            
            # Base query for Twitter data (source = 2)
            base_query = """
                SELECT uri, datetime, timeBucketId, source, label, content, contentSizeBytes
                FROM DataEntity 
                WHERE source = 2
            """
            
            # Add date range filter
            if scrape_config.date_range:
                query_parts.append("AND datetime >= ? AND datetime <= ?")
                params.extend([
                    scrape_config.date_range.start.isoformat(),
                    scrape_config.date_range.end.isoformat()
                ])
            
            # Add label filters
            if scrape_config.labels:
                label_conditions = []
                for label in scrape_config.labels:
                    label_conditions.append("label = ?")
                    params.append(label.value)
                
                if label_conditions:
                    query_parts.append(f"AND ({' OR '.join(label_conditions)})")
            
            # Add ordering and limit
            query_parts.append("ORDER BY datetime DESC")
            
            if scrape_config.entity_limit:
                query_parts.append("LIMIT ?")
                params.append(scrape_config.entity_limit)
            
            # Execute query
            full_query = base_query + " " + " ".join(query_parts)
            self.logger.debug(f"Executing query: {full_query}")
            self.logger.debug(f"With params: {params}")
            
            cursor.execute(full_query, params)
            rows = cursor.fetchall()
            
            # Convert to DataEntity objects
            data_entities = []
            for row in rows:
                try:
                    uri, dt_str, time_bucket_id, source, label_str, content_blob, content_size = row
                    
                    # Parse datetime
                    if isinstance(dt_str, str):
                        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                    else:
                        dt = dt_str
                    
                    # Create DataEntity
                    label = DataLabel(value=label_str) if label_str else None
                    
                    data_entity = DataEntity(
                        uri=uri,
                        datetime=dt,
                        source=DataSource(source),
                        label=label,
                        content=content_blob,
                        content_size_bytes=len(content_blob)
                    )
                    
                    data_entities.append(data_entity)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to parse DataEntity row: {e}")
                    continue
            
            conn.close()
            
            self.logger.info(f"📊 Found {len(data_entities)} DataEntity objects matching criteria")
            return data_entities
            
        except Exception as e:
            self.logger.error(f"Database query failed: {e}")
            return []
    
    def _parse_tweets_to_xcontent(self, tweets_data: List[Dict[str, Any]]) -> List[XContent]:
        """Parse tweet data from database into XContent objects"""
        x_contents = []
        
        for tweet_data in tweets_data:
            try:
                # Create XContent object
                x_content = XContent(
                    username=f"@{tweet_data.get('author_username', '')}" if tweet_data.get('author_username') else "",
                    text=utils.sanitize_scraped_tweet(tweet_data.get('text', '')),
                    url=tweet_data.get('url', ''),
                    timestamp=tweet_data.get('created_at', datetime.now(timezone.utc)),
                    tweet_hashtags=tweet_data.get('hashtags', [])
                )
                
                x_contents.append(x_content)
                
            except Exception as e:
                self.logger.warning(f"Failed to parse tweet to XContent: {e}")
                continue
        
        return x_contents
    
    async def validate(self, entities: List[DataEntity]) -> List[ValidationResult]:
        """Validate the correctness of a list of DataEntities by URI."""
        
        async def validate_entity(entity) -> ValidationResult:
            if not utils.is_valid_twitter_url(entity.uri):
                return ValidationResult(
                    is_valid=False,
                    reason="Invalid URI.",
                    content_size_bytes_validated=entity.content_size_bytes,
                )
            
            try:
                # Look up the tweet in our database
                tweet_data = await self._get_tweet_by_url(entity.uri)
                
                if not tweet_data:
                    return ValidationResult(
                        is_valid=False,
                        reason="Tweet not found in database.",
                        content_size_bytes_validated=entity.content_size_bytes,
                    )
                
                # Convert to XContent for validation
                x_content = XContent(
                    username=f"@{tweet_data.get('author_username', '')}" if tweet_data.get('author_username') else "",
                    text=utils.sanitize_scraped_tweet(tweet_data.get('text', '')),
                    url=tweet_data.get('url', ''),
                    timestamp=tweet_data.get('created_at', datetime.now(timezone.utc)),
                    tweet_hashtags=tweet_data.get('hashtags', [])
                )
                
                # Use existing validation logic
                is_retweet = tweet_data.get('is_retweet', False)
                return utils.validate_tweet_content(
                    actual_tweet=x_content,
                    entity=entity,
                    is_retweet=is_retweet
                )
                
            except Exception as e:
                bt.logging.error(f"Failed to validate entity {entity.uri}: {traceback.format_exc()}")
                return ValidationResult(
                    is_valid=False,
                    reason=f"Validation failed: {str(e)}",
                    content_size_bytes_validated=entity.content_size_bytes,
                )
        
        if not entities:
            return []
        
        results = await asyncio.gather(
            *[validate_entity(entity) for entity in entities]
        )
        
        return results
    
    async def validate_hf(self, entities) -> HFValidationResult:
        """Validate the correctness of HF entities by URL."""
        
        async def validate_hf_entity(entity) -> ValidationResult:
            if not utils.is_valid_twitter_url(entity.get('url')):
                return ValidationResult(
                    is_valid=False,
                    reason="Invalid URI.",
                    content_size_bytes_validated=0,
                )
            
            try:
                # Look up the tweet in our database
                tweet_data = await self._get_tweet_by_url(entity.get('url'))
                
                if not tweet_data:
                    return ValidationResult(
                        is_valid=False,
                        reason="Tweet not found in database.",
                        content_size_bytes_validated=0,
                    )
                
                # Convert to format expected by HF validation
                actual_tweet = {
                    "text": utils.sanitize_scraped_tweet(tweet_data.get('text', '')),
                    "url": tweet_data.get('url', ''),
                    "datetime": tweet_data.get('created_at', datetime.now(timezone.utc)),
                    "media": tweet_data.get('media_urls', []) if tweet_data.get('media_urls') else None
                }
                
                # Use existing HF validation logic
                return utils.validate_hf_retrieved_tweet(
                    actual_tweet=actual_tweet,
                    tweet_to_verify=entity
                )
                
            except Exception as e:
                bt.logging.error(f"Failed to validate HF entity {entity.get('url')}: {traceback.format_exc()}")
                return ValidationResult(
                    is_valid=False,
                    reason=f"HF validation failed: {str(e)}",
                    content_size_bytes_validated=0,
                )
        
        results = await asyncio.gather(
            *[validate_hf_entity(entity) for entity in entities]
        )
        
        is_valid, valid_percent = utils.hf_tweet_validation(validation_results=results)
        return HFValidationResult(
            is_valid=is_valid, 
            validation_percentage=valid_percent,
            reason=f"Validation Percentage = {valid_percent}"
        )
    
    async def _get_tweet_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Get a specific tweet from database by URL"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Normalize URL for comparison
            normalized_url = utils.normalize_url(url)
            
            cursor.execute("""
                SELECT 
                    id, url, text, author_username, author_display_name,
                    created_at, like_count, retweet_count, reply_count, quote_count,
                    hashtags, media_urls, is_retweet, is_reply, conversation_id
                FROM tweets 
                WHERE url = ? OR url = ?
            """, (url, normalized_url))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            # Convert to dictionary
            columns = [
                'id', 'url', 'text', 'author_username', 'author_display_name',
                'created_at', 'like_count', 'retweet_count', 'reply_count', 'quote_count',
                'hashtags', 'media_urls', 'is_retweet', 'is_reply', 'conversation_id'
            ]
            tweet_dict = dict(zip(columns, row))
            
            # Parse JSON fields
            try:
                if tweet_dict.get('hashtags'):
                    tweet_dict['hashtags'] = json.loads(tweet_dict['hashtags'])
                else:
                    tweet_dict['hashtags'] = []
            except:
                tweet_dict['hashtags'] = []
            
            try:
                if tweet_dict.get('media_urls'):
                    tweet_dict['media_urls'] = json.loads(tweet_dict['media_urls'])
                else:
                    tweet_dict['media_urls'] = []
            except:
                tweet_dict['media_urls'] = []
            
            # Parse datetime
            try:
                if tweet_dict.get('created_at'):
                    tweet_dict['created_at'] = datetime.fromisoformat(tweet_dict['created_at'])
            except:
                tweet_dict['created_at'] = datetime.now(timezone.utc)
            
            return tweet_dict
            
        except Exception as e:
            self.logger.error(f"Failed to get tweet by URL {url}: {e}")
            return None
    
    def get_scraper_stats(self) -> Dict[str, Any]:
        """Get scraper statistics"""
        stats = {
            "scraper_type": "custom_twitter",
            "database_path": self.db_path
        }
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total Twitter DataEntities (source = 2)
            cursor.execute("SELECT COUNT(*) FROM DataEntity WHERE source = 2")
            stats["total_tweets"] = cursor.fetchone()[0]
            
            # Recent tweets (last hour)
            cursor.execute("""
                SELECT COUNT(*) FROM DataEntity 
                WHERE source = 2 AND datetime > datetime('now', '-1 hour')
            """)
            stats["recent_tweets_1h"] = cursor.fetchone()[0]
            
            # Recent tweets (last 24 hours)
            cursor.execute("""
                SELECT COUNT(*) FROM DataEntity 
                WHERE source = 2 AND datetime > datetime('now', '-1 day')
            """)
            stats["recent_tweets_24h"] = cursor.fetchone()[0]
            
            # Most recent tweet
            cursor.execute("""
                SELECT datetime FROM DataEntity 
                WHERE source = 2 
                ORDER BY datetime DESC LIMIT 1
            """)
            result = cursor.fetchone()
            if result:
                stats["most_recent_tweet"] = result[0]
            
            # Labels distribution
            cursor.execute("""
                SELECT label, COUNT(*) FROM DataEntity 
                WHERE source = 2 AND label IS NOT NULL
                GROUP BY label 
                ORDER BY COUNT(*) DESC 
                LIMIT 10
            """)
            label_stats = cursor.fetchall()
            stats["top_labels"] = [{"label": label, "count": count} for label, count in label_stats]
            
            conn.close()
            
        except Exception as e:
            self.logger.warning(f"Failed to get database stats: {e}")
            stats.update({
                "total_tweets": 0,
                "recent_tweets_1h": 0,
                "recent_tweets_24h": 0,
                "most_recent_tweet": None,
                "top_labels": []
            })
        
        return stats


# Test function similar to enhanced_apidojo_scraper
async def test_custom_twitter_scraper():
    """Test function for the custom Twitter scraper"""
    scraper = CustomTwitterScraper()
    
    print("\n===== TESTING CUSTOM TWITTER SCRAPER =====")
    
    # Get scraper stats
    stats = scraper.get_scraper_stats()
    print(f"Scraper stats: {json.dumps(stats, indent=2, default=str)}")
    
    # Test with hashtag
    print("\n===== TESTING WITH HASHTAG: #bitcoin =====")
    hashtag_config = ScrapeConfig(
        entity_limit=5,
        date_range=DateRange(
            start=datetime.now(timezone.utc) - timedelta(hours=24),
            end=datetime.now(timezone.utc)
        ),
        labels=[DataLabel(value="#bitcoin")]
    )
    
    hashtag_results = await scraper.scrape(hashtag_config)
    print(f"Results for hashtag '#bitcoin': {len(hashtag_results)} DataEntity objects")
    
    if hashtag_results:
        # Show first result
        first_result = hashtag_results[0]
        print(f"First result URI: {first_result.uri}")
        print(f"First result timestamp: {first_result.datetime}")
        print(f"First result source: {first_result.source}")
        
        # Decompress and show content
        try:
            content_json = gzip.decompress(first_result.content).decode('utf-8')
            content_data = json.loads(content_json)
            print(f"First result text: {content_data.get('text', '')[:100]}...")
        except Exception as e:
            print(f"Could not decompress content: {e}")
    
    # Test with keyword
    print("\n===== TESTING WITH KEYWORD: bitcoin =====")
    keyword_config = ScrapeConfig(
        entity_limit=5,
        date_range=DateRange(
            start=datetime.now(timezone.utc) - timedelta(hours=24),
            end=datetime.now(timezone.utc)
        ),
        labels=[DataLabel(value="bitcoin")]
    )
    
    keyword_results = await scraper.scrape(keyword_config)
    print(f"Results for keyword 'bitcoin': {len(keyword_results)} DataEntity objects")
    
    # Test with no labels (should return recent tweets)
    print("\n===== TESTING WITH NO LABELS (RECENT TWEETS) =====")
    recent_config = ScrapeConfig(
        entity_limit=10,
        date_range=DateRange(
            start=datetime.now(timezone.utc) - timedelta(hours=6),
            end=datetime.now(timezone.utc)
        ),
        labels=[]
    )
    
    recent_results = await scraper.scrape(recent_config)
    print(f"Recent tweets: {len(recent_results)} DataEntity objects")
    
    return {
        "stats": stats,
        "hashtag_results": hashtag_results,
        "keyword_results": keyword_results,
        "recent_results": recent_results
    }


if __name__ == "__main__":
    asyncio.run(test_custom_twitter_scraper())
