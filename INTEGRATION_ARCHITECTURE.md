# Custom Twitter Scraper Integration Architecture

## Current Bittensor Data Universe Flow

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Validator     │───▶│    Miner     │───▶│  Apify Service  │
│ (Requests Data) │    │ (Scrapes)    │    │ ($100-500/month)│
└─────────────────┘    └──────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────┐
                       │ SQLite Store │
                       │ (Local Data) │
                       └──────────────┘
```

## Proposed Custom Scraper Integration

### Option 1: Direct Integration (Recommended)
```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Validator     │───▶│    Miner     │───▶│ Custom Scraper  │
│ (Requests Data) │    │ (Modified)   │    │ (Your Code)     │
└─────────────────┘    └──────────────┘    └─────────────────┘
                              │                      │
                              ▼                      ▼
                       ┌──────────────┐    ┌─────────────────┐
                       │ SQLite Store │    │ PostgreSQL DB   │
                       │ (Bittensor)  │    │ (Your Storage)  │
                       └──────────────┘    └─────────────────┘
```

### Option 2: API Service Architecture
```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Validator     │───▶│    Miner     │───▶│ Custom API      │
│ (Requests Data) │    │ (Uses API)   │    │ (HTTP Service)  │
└─────────────────┘    └──────────────┘    └─────────────────┘
                              │                      │
                              ▼                      ▼
                       ┌──────────────┐    ┌─────────────────┐
                       │ SQLite Store │    │ Background      │
                       │ (Bittensor)  │    │ Scraper Process │
                       └──────────────┘    └─────────────────┘
                                                    │
                                                    ▼
                                           ┌─────────────────┐
                                           │ PostgreSQL DB   │
                                           │ (Continuous)    │
                                           └─────────────────┘
