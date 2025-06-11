#!/usr/bin/env python3
"""
Custom Twitter Runner - Replaces Apify ActorRunner
Integrates with your custom Twitter scraper via API
"""

import asyncio
import aiohttp
import json
import os
import re
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging

# Import base classes for compatibility
from scraping.apify import RunConfig, ActorRunError

class CustomTwitterRunner:
    """
    Drop-in replacement for ActorRunner that calls your custom Twitter API
    instead of Apify. Maintains full compatibility with existing Bittensor code.
    """
    
    def __init__(self):
        self.api_url = os.getenv("CUSTOM_TWITTER_API_URL", "http://localhost:8000")
        self.api_token = os.getenv("CUSTOM_TWITTER_API_TOKEN", "your-api-token")
        self.logger = logging.getLogger(__name__)
        
        if not self.api_token or self.api_token == "your-api-token":
            self.logger.warning("CUSTOM_TWITTER_API_TOKEN not set, using default")

    async def run(self, config: RunConfig, run_input: dict) -> List[dict]:
        """
        Main entry point - replaces ActorRunner.run()
        Converts Apify format to custom API format and back
        """
        try:
            self.logger.info(f"Custom Twitter Runner: Processing request with input: {run_input}")
            
            # Determine scraping type based on input
            if "searchTerms" in run_input:
                return await self._handle_search_scraping(config, run_input)
            elif "startUrls" in run_input:
                return await self._handle_url_validation(config, run_input)
            else:
                raise ActorRunError("Invalid run_input format: missing searchTerms or startUrls")
                
        except Exception as e:
            self.logger.error(f"Custom Twitter Runner failed: {e}")
            raise ActorRunError(f"Custom Twitter scraping failed: {str(e)}")

    async def _handle_search_scraping(self, config: RunConfig, run_input: dict) -> List[dict]:
        """Handle search-based scraping (replaces Apify search functionality)"""
        search_terms = run_input.get("searchTerms", [])
        max_tweets = run_input.get("maxTweets", config.max_data_entities)
        
        if not search_terms:
            self.logger.warning("No search terms provided")
            return []
        
        # Parse search query to extract components
        query_info = self._parse_search_query(search_terms[0])
        self.logger.info(f"Parsed query: {query_info}")
        
        # Convert to custom API format
        api_request = {
            "action": "search",
            "query": query_info["query"],
            "start_date": query_info["start_date"],
            "end_date": query_info["end_date"],
            "limit": max_tweets,
            "include_retweets": False
        }
        
        # Make API call to your custom scraper
        response_data = await self._call_custom_api("/api/search", api_request, config.timeout_secs)
        
        # Convert response to Apify format
        apify_tweets = self._convert_to_apify_format(response_data)
        self.logger.info(f"Returning {len(apify_tweets)} tweets in Apify format")
        
        return apify_tweets

    async def _handle_url_validation(self, config: RunConfig, run_input: dict) -> List[dict]:
        """Handle URL-based validation (replaces Apify URL fetching)"""
        start_urls = run_input.get("startUrls", [])
        max_items = run_input.get("maxItems", config.max_data_entities)
        
        if not start_urls:
            self.logger.warning("No URLs provided for validation")
            return []
        
        self.logger.info(f"Validating {len(start_urls)} URLs")
        
        # Convert to custom API format
        api_request = {
            "action": "validate_urls",
            "urls": start_urls[:max_items],
            "include_metadata": True
        }
        
        # Make API call
        response_data = await self._call_custom_api("/api/validate", api_request, config.timeout_secs)
        
        # Convert response to Apify format
        apify_tweets = self._convert_to_apify_format(response_data)
        self.logger.info(f"Validated {len(apify_tweets)} URLs")
        
        return apify_tweets

    def _parse_search_query(self, search_term: str) -> Dict[str, Any]:
        """Parse Apify search query format to extract components"""
        # Example: "since:2024-01-01_00:00:00_UTC until:2024-01-01_23:59:59_UTC #bitcoin"
        
        query_info = {
            "query": "",
            "start_date": None,
            "end_date": None
        }
        
        # Extract since date
        since_match = re.search(r'since:(\d{4}-\d{2}-\d{2}_\d{2}:\d{2}:\d{2}_UTC)', search_term)
        if since_match:
            date_str = since_match.group(1).replace('_UTC', '').replace('_', ' ')
            try:
                query_info["start_date"] = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S').isoformat()
            except ValueError:
                self.logger.warning(f"Failed to parse since date: {date_str}")
        
        # Extract until date
        until_match = re.search(r'until:(\d{4}-\d{2}-\d{2}_\d{2}:\d{2}:\d{2}_UTC)', search_term)
        if until_match:
            date_str = until_match.group(1).replace('_UTC', '').replace('_', ' ')
            try:
                query_info["end_date"] = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S').isoformat()
            except ValueError:
                self.logger.warning(f"Failed to parse until date: {date_str}")
        
        # Extract query terms (remove since/until parts)
        query = re.sub(r'since:\S+', '', search_term)
        query = re.sub(r'until:\S+', '', query)
        query_info["query"] = query.strip()
        
        # If no dates provided, use last 24 hours
        if not query_info["start_date"]:
            query_info["start_date"] = (datetime.now() - timedelta(hours=24)).isoformat()
        if not query_info["end_date"]:
            query_info["end_date"] = datetime.now().isoformat()
        
        return query_info

    async def _call_custom_api(self, endpoint: str, request_data: dict, timeout_secs: int) -> List[dict]:
        """Make API call to your custom Twitter scraper"""
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.api_url}{endpoint}"
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                timeout = aiohttp.ClientTimeout(total=timeout_secs)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(url, json=request_data, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            return data.get("tweets", data.get("data", []))
                        elif response.status == 429:
                            # Rate limited - wait and retry
                            wait_time = retry_delay * (attempt + 1)
                            self.logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            error_text = await response.text()
                            raise ActorRunError(f"API call failed with status {response.status}: {error_text}")
                            
            except asyncio.TimeoutError:
                if attempt == max_retries - 1:
                    raise ActorRunError(f"API call timed out after {timeout_secs} seconds")
                await asyncio.sleep(retry_delay)
                continue
            except Exception as e:
                if attempt == max_retries - 1:
                    raise ActorRunError(f"API call failed: {str(e)}")
                await asyncio.sleep(retry_delay)
                continue
        
        return []

    def _convert_to_apify_format(self, custom_data: List[dict]) -> List[dict]:
        """Convert your custom API response to Apify expected format"""
        apify_tweets = []
        
        for tweet_data in custom_data:
            try:
                # Convert your format to Apify format
                apify_tweet = self._convert_single_tweet(tweet_data)
                if apify_tweet:
                    apify_tweets.append(apify_tweet)
            except Exception as e:
                self.logger.warning(f"Failed to convert tweet: {e}")
                continue
        
        return apify_tweets

    def _convert_single_tweet(self, tweet_data: dict) -> Optional[dict]:
        """Convert a single tweet from your format to Apify format"""
        try:
            # Handle different input formats from your API
            if "text" in tweet_data and "author_username" in tweet_data:
                # Your TweetData format
                return self._convert_from_tweet_data(tweet_data)
            elif "content" in tweet_data:
                # Database format with JSON content
                return self._convert_from_db_format(tweet_data)
            else:
                # Try to handle as generic format
                return self._convert_generic_format(tweet_data)
                
        except Exception as e:
            self.logger.error(f"Error converting tweet: {e}")
            return None

    def _convert_from_tweet_data(self, tweet_data: dict) -> dict:
        """Convert from your TweetData format to Apify format"""
        # Parse created_at
        created_at = tweet_data.get("created_at")
        if isinstance(created_at, str):
            try:
                dt_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                created_at_str = dt_obj.strftime("%a %b %d %H:%M:%S %z %Y")
            except:
                created_at_str = created_at
        else:
            created_at_str = datetime.now().strftime("%a %b %d %H:%M:%S %z %Y")
        
        # Extract hashtags and symbols
        hashtags = []
        symbols = []
        
        for tag in tweet_data.get("hashtags", []):
            if tag.startswith("#"):
                hashtags.append({"text": tag[1:], "indices": [0, len(tag)]})
            elif tag.startswith("$"):
                symbols.append({"text": tag[1:], "indices": [0, len(tag)]})
        
        # Build Apify format
        apify_tweet = {
            "text": tweet_data.get("text", ""),
            "url": tweet_data.get("url", ""),
            "createdAt": created_at_str,
            "author": {
                "userName": tweet_data.get("author_username", "").replace("@", ""),
                "name": tweet_data.get("author_display_name", ""),
                "id": tweet_data.get("user_id", ""),
                "isVerified": tweet_data.get("user_verified", False),
                "followers": tweet_data.get("user_followers_count", 0),
                "following": tweet_data.get("user_following_count", 0)
            },
            "id": tweet_data.get("id", tweet_data.get("tweet_id", "")),
            "likeCount": tweet_data.get("like_count", 0),
            "retweetCount": tweet_data.get("retweet_count", 0),
            "replyCount": tweet_data.get("reply_count", 0),
            "quoteCount": tweet_data.get("quote_count", 0),
            "entities": {
                "hashtags": hashtags,
                "symbols": symbols
            },
            "media": self._convert_media_urls(tweet_data.get("media_urls", [])),
            "isRetweet": tweet_data.get("is_retweet", False),
            "isReply": tweet_data.get("is_reply", False),
            "isQuote": tweet_data.get("is_quote", False),
            "conversationId": tweet_data.get("conversation_id", ""),
            "inReplyToUserId": tweet_data.get("in_reply_to_user_id")
        }
        
        return apify_tweet

    def _convert_from_db_format(self, tweet_data: dict) -> dict:
        """Convert from database format with JSON content"""
        try:
            # Decode content if it's bytes or compressed
            content = tweet_data.get("content", "{}")
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            # Parse JSON content
            tweet_json = json.loads(content)
            return self._convert_from_tweet_data(tweet_json)
            
        except Exception as e:
            self.logger.error(f"Failed to parse DB format: {e}")
            return None

    def _convert_generic_format(self, tweet_data: dict) -> dict:
        """Handle generic/unknown formats"""
        return {
            "text": tweet_data.get("text", ""),
            "url": tweet_data.get("url", ""),
            "createdAt": datetime.now().strftime("%a %b %d %H:%M:%S %z %Y"),
            "author": {
                "userName": "unknown",
                "name": "Unknown User",
                "id": "",
                "isVerified": False,
                "followers": 0,
                "following": 0
            },
            "id": tweet_data.get("id", ""),
            "likeCount": 0,
            "retweetCount": 0,
            "replyCount": 0,
            "quoteCount": 0,
            "entities": {"hashtags": [], "symbols": []},
            "media": [],
            "isRetweet": False,
            "isReply": False,
            "isQuote": False,
            "conversationId": "",
            "inReplyToUserId": None
        }

    def _convert_media_urls(self, media_urls: List[str]) -> List[dict]:
        """Convert media URLs to Apify format"""
        media_items = []
        for url in media_urls:
            media_items.append({
                "media_url_https": url,
                "type": "photo"  # Default to photo, could be enhanced
            })
        return media_items
