module.exports = {
  apps: [
    {
      name: 'twitter-api',
      script: 'python3',
      args: '-m uvicorn custom_twitter_api_service:app --host 0.0.0.0 --port 8000',
      cwd: process.cwd(),
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
        CUSTOM_TWITTER_API_URL: 'http://localhost:8000',
        CUSTOM_TWITTER_API_TOKEN: 'bittensor-custom-token-2024',
        POSTGRES_DB: 'bittensor_mining',
        POSTGRES_USER: 'postgres',
        POSTGRES_PASSWORD: 'postgres',
        POSTGRES_HOST: 'localhost',
        POSTGRES_PORT: '5432'
      },
      error_file: './logs/twitter-api-error.log',
      out_file: './logs/twitter-api-out.log',
      log_file: './logs/twitter-api-combined.log',
      time: true
    },
    {
      name: 'twitter-scraper',
      script: 'python3',
      args: 'background_scraper_service.py',
      cwd: process.cwd(),
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '2G',
      env: {
        NODE_ENV: 'production',
        CUSTOM_TWITTER_API_URL: 'http://localhost:8000',
        CUSTOM_TWITTER_API_TOKEN: 'bittensor-custom-token-2024',
        POSTGRES_DB: 'bittensor_mining',
        POSTGRES_USER: 'postgres',
        POSTGRES_PASSWORD: 'postgres',
        POSTGRES_HOST: 'localhost',
        POSTGRES_PORT: '5432',
        SCRAPER_BATCH_SIZE: '150',
        SCRAPER_BATCH_INTERVAL: '300',
        SCRAPER_TWEETS_PER_HOUR: '1800'
      },
      error_file: './logs/twitter-scraper-error.log',
      out_file: './logs/twitter-scraper-out.log',
      log_file: './logs/twitter-scraper-combined.log',
      time: true
    },
    {
      name: 'bittensor-miner-offline',
      script: 'python3',
      args: '-m neurons.miner --offline --logging.debug',
      cwd: process.cwd(),
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '4G',
      env: {
        NODE_ENV: 'production',
        CUSTOM_TWITTER_API_URL: 'http://localhost:8000',
        CUSTOM_TWITTER_API_TOKEN: 'bittensor-custom-token-2024'
      },
      error_file: './logs/bittensor-miner-offline-error.log',
      out_file: './logs/bittensor-miner-offline-out.log',
      log_file: './logs/bittensor-miner-offline-combined.log',
      time: true
    },
    {
      name: 'bittensor-miner-testnet',
      script: 'python3',
      args: '-m neurons.miner --netuid 13 --subtensor.network test --wallet.name default --wallet.hotkey default --logging.debug',
      cwd: process.cwd(),
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '4G',
      env: {
        NODE_ENV: 'production',
        CUSTOM_TWITTER_API_URL: 'http://localhost:8000',
        CUSTOM_TWITTER_API_TOKEN: 'bittensor-custom-token-2024'
      },
      error_file: './logs/bittensor-miner-testnet-error.log',
      out_file: './logs/bittensor-miner-testnet-out.log',
      log_file: './logs/bittensor-miner-testnet-combined.log',
      time: true
    }
  ]
};
