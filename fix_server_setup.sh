#!/bin/bash

echo "🔧 Fixing Server Setup for Bittensor Data Universe"
echo "================================================="

# Activate virtual environment if it exists
if [ -d "myenv" ]; then
    echo "🐍 Activating virtual environment..."
    source myenv/bin/activate
else
    echo "🐍 Creating virtual environment..."
    python3 -m venv myenv
    source myenv/bin/activate
fi

# Install missing Python packages
echo "📦 Installing missing Python packages..."
pip install uvicorn fastapi bittensor

# Install additional dependencies from requirements.txt
echo "📦 Installing requirements.txt..."
pip install -r requirements.txt

# Create logs directory
echo "📁 Creating logs directory..."
mkdir -p logs
chmod 755 logs

# Fix database paths in custom_twitter_scraper.py
echo "🔧 Fixing database paths in custom_twitter_scraper.py..."
if [ -f "scraping/x/custom_twitter_scraper.py" ]; then
    # Update database path to use current directory
    sed -i 's|/home/anirudh/Downloads/twitter/X_scrapping/twitter_miner_data.sqlite|./SqliteMinerStorage.sqlite|g' scraping/x/custom_twitter_scraper.py
    echo "✅ Updated database path in custom_twitter_scraper.py"
fi

# Fix database paths in background_scraper_service.py
echo "🔧 Fixing database paths in background_scraper_service.py..."
if [ -f "background_scraper_service.py" ]; then
    # Update database paths to use current directory
    sed -i 's|/home/anirudh/Downloads/twitter/X_scrapping/twitter_miner_data.sqlite|./SqliteMinerStorage.sqlite|g' background_scraper_service.py
    sed -i 's|/home/anirudh/Downloads/twitter/X_scrapping|.|g' background_scraper_service.py
    echo "✅ Updated database paths in background_scraper_service.py"
fi

# Check if .env needs configuration
if grep -q "YOUR_HUGGING_FACE_TOKEN_HERE" .env; then
    echo "⚠️  WARNING: Please update .env file with your real tokens:"
    echo "   - HUGGING_FACE_TOKEN"
    echo "   - Any other API keys you need"
    echo ""
fi

# Test custom scraper import
echo "🧪 Testing custom scraper import..."
python3 -c "
import sys
sys.path.append('.')
try:
    from scraping.x.custom_twitter_scraper import CustomTwitterScraper
    print('✅ CustomTwitterScraper imported successfully')
except Exception as e:
    print(f'❌ CustomTwitterScraper import failed: {e}')
"

echo ""
echo "✅ Setup complete!"
echo ""
echo "🔥 Next steps:"
echo "1. Update .env file with your real tokens (if needed)"
echo "2. Stop any running PM2 processes: pm2 delete all"
echo "3. Start services: pm2 start ecosystem.config.js"
echo "4. Check status: pm2 status"
echo "5. View logs: pm2 logs"
echo ""
echo "🎯 To test custom Twitter scraper:"
echo "   python3 -c \"import asyncio; import sys; sys.path.append('.'); from scraping.x.custom_twitter_scraper import test_custom_twitter_scraper; asyncio.run(test_custom_twitter_scraper())\""
