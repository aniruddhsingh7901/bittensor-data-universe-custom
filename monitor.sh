#!/bin/bash
while true; do
    clear
    echo "🐘 Bittensor Mining Dashboard - $(date)"
    echo "=================================="
    
    # Services Status
    echo "📡 API Service: $(systemctl is-active twitter-api)"
    echo "🔄 Background Scraper: $(systemctl is-active twitter-scraper)"
    echo "💾 PostgreSQL: $(systemctl is-active postgresql)"
    
    # API Test
    API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ 2>/dev/null || echo "000")
    echo "🌐 API Response: $API_STATUS"
    
    # Database Stats
    echo -e "\n💾 Database Statistics:"
    DB_COUNT=$(PGPASSWORD=postgres psql -h localhost -U postgres -d bittensor_mining -t -c "SELECT COUNT(*) FROM DataEntity WHERE source = 2;" 2>/dev/null | tr -d ' ' || echo "0")
    echo "  Total tweets: $DB_COUNT"
    
    RECENT=$(PGPASSWORD=postgres psql -h localhost -U postgres -d bittensor_mining -t -c "SELECT COUNT(*) FROM DataEntity WHERE source = 2 AND datetime > NOW() - INTERVAL '1 hour';" 2>/dev/null | tr -d ' ' || echo "0")
    echo "  Tweets last hour: $RECENT"
    
    echo -e "\nPress Ctrl+C to exit..."
    sleep 30
done
