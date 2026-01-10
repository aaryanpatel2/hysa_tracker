# 💰 High-Yield Savings Account (HYSA) Rate Tracker

A sophisticated, production-ready Python web scraper that monitors and analyzes high-yield savings account rates across major financial institutions in real-time. Built with a focus on reliability, scalability, and actionable insights.

## 🎯 Project Overview

This automated monitoring system tracks APY rates from 9+ major banks and aggregates data from 50+ financial institutions via industry-leading comparison sites (Bankrate, Investopedia). The system provides intelligent rate change detection, competitive analysis, and instant Slack notifications to optimize savings decisions.

## ✨ Key Features

### 🔍 **Multi-Strategy Web Scraping**
- **Hybrid Scraping Architecture**: Intelligently switches between static HTML parsing and Selenium-based dynamic rendering based on site requirements
- **Concurrent Processing**: ThreadPoolExecutor for parallel scraping operations, reducing total execution time by over 20%
- **Robust Error Handling**: Comprehensive fallback mechanisms and retry logic for maximum reliability
- **Custom Bank Scrapers**: Specialized scraping functions tailored to each bank's unique page structure

### 📊 **Comprehensive Data Collection**
- **Direct Bank Monitoring**: Real-time scraping from 9 major banks (Ally, SoFi, Capital One, Marcus, Barclays, Apple, Amex, Wealthfront, Betterment)
- **Aggregate Data Integration**: Scrapes comparison sites to track 50+ additional banks for market intelligence
- **Historical Tracking**: Maintains complete rate history with timestamp precision for trend analysis
- **Smart Data Categorization**: Separates main tracked banks from supplementary and market data

### 🤖 **Intelligent Analysis & Alerts**

#### **Automated Rate Change Detection**
- Tracks rate movements with directional indicators (↑↓)
- Calculates rate deltas against previous snapshots

#### **Advanced Market Intelligence**
- **Notable Mentions Algorithm**: 
  - 📈 Identifies banks with significant rate increases (>0.05%)
  - 🆕 Detects new entrants to top 10 market rates
  - 🎯 Highlights competitive threats (banks within 0.10% of best rate)
  
#### **Performance Metrics** (30-day rolling analysis)
- **Consistency Score**: Tracks how often each bank maintains #1 position
- **Stability Index**: Calculates mean rate to identify reliable high-performers
- **Rate Volatility**: Monitors standard deviation for risk assessment

### 🔔 **Smart Notification System**
- **Configurable Notification Modes**: 
  - `always` - Every execution (for testing/high-priority monitoring)
  - `smart` - Intelligent alerting on significant changes + weekly digest + monthly report
  - `weekly` - Sunday digest only
  - `monthly` - First of month summary
  - `never` - Silent data collection
- **Intelligent Alert Triggers** (smart mode):
  - 🔴 **Immediate**: Tracked bank drops ≥0.15%
  - 🔴 **Immediate**: NEW competitor crosses 0.20% above threshold OR existing competitor's gap widens by ≥0.10%
  - 🟡 **Weekly**: Sunday digest (even during quiet periods)
  - 🟢 **Monthly**: 1st of month comprehensive report with full 30-day analytics
- **Rich Slack Integration**: Formatted webhooks with markdown, ranked visualizations, and alert context
- **Alert Fatigue Prevention**: Eliminates daily "no change" notifications

## 🛠️ Technical Implementation

### **Technology Stack**
- **Python 3.x** - Core application logic
- **Selenium WebDriver** - Dynamic content rendering for JavaScript-heavy sites
- **BeautifulSoup4** - HTML parsing and data extraction
- **Requests** - HTTP client for static page scraping
- **Pandas** - Data manipulation and analysis
- **ThreadPoolExecutor** - Concurrent scraping operations

### **Architecture Highlights**

```
scraper.py
├── Core Scraping Engine
│   ├── Bank-specific scrapers (Ally, SoFi, Capital One, Marcus, etc.)
│   ├── Hybrid static/dynamic strategy per bank
│   └── Regex-based rate extraction with validation
├── Aggregate Data Pipeline
│   ├── Investopedia scraper (static HTML)
│   ├── Bankrate scraper (dynamic with pagination)
│   └── Bank alias matching system
├── Data Management
│   ├── history.json - Main tracked banks time series
│   ├── last_rates.json - Previous snapshot for delta calculation
│   └── market_rates_history.json - Full market data archive
├── Analytics Engine
│   ├── Rate change detection
│   ├── Ranking algorithms
│   ├── Notable mentions generator
│   └── 30-day trend analysis
└── Notification System
    └── Slack webhook with formatted reports
```

### **Code Quality Features**
- **Modular Design**: Separate functions for each bank with consistent interfaces
- **Configuration Management**: Environment variables via python-dotenv
- **Data Persistence**: JSON-based storage for historical analysis
- **Type Safety**: Explicit rate validation (0.1% - 10% range)
- **Scalability**: Easy addition of new banks via configuration dictionaries

## 📈 Sample Output

### Smart Alert (Triggered by Significant Change)
```
🚨 ALERT TRIGGERED: 🔴 Marcus dropped 0.20% (threshold: 0.15%)

🔔 HYSA Rate Alert - 2026-01-08 22:38

📌 MY TRACKED BANKS (9/7 banks)
========================================
🥇 #1. Barclays: 3.85%
🥈 #2. Marcus: 3.45% (↓ -0.20%)
🥈 #2. Apple: 3.65%
📊 #4. Ally: 3.30%
📊 #4. Sofi: 3.30%
📊 #4. Capital One: 3.30%
📊 #4. Amex: 3.30%

💡 SUPPLEMENTARY BANKS (Monitoring)
========================================
• Wealthfront: 3.25%
• Betterment: 3.25%

🌐 OTHER TOP MARKET RATES (Top 15 of 47 banks)
========================================
#1. UFB Direct: 4.11%
#2. My Banking Direct: 4.10%
#3. Bread Savings: 4.05%
...

⭐ NOTABLE MENTIONS
📈 UFB Direct: 4.11% (↑ +0.15%)
🎯 Bask Bank: 3.90% (Within 0.10% of your best!)

📊 ANALYSIS REPORT (Last 30 Days)
========================================
🏆 Consistency (#1 Spot): Barclays (85% of time)
💎 Stability (Highest Avg): Barclays (3.83%)
```

### Console Output (Notification Decision)
```
==================================================
Notification Mode: smart
Should Send: True
Reason: 🔴 Marcus dropped 0.20% (threshold: 0.15%)
==================================================

✅ Slack notification sent! Status: 200
```

## ⚡ CI/CD & Automation

### **GitHub Actions Integration**
Fully automated daily execution with production-grade CI/CD pipeline:

- **Scheduled Runs**: Cron-based automation (daily at 1 PM UTC)
- **Data Persistence**: Automated git commits push updated JSON data back to repository

```yaml
# Runs daily + manual trigger capability
on:
  schedule:
    - cron: '0 13 * * *'
  workflow_dispatch:
```

## 🚀 Technical Achievements

1. **Performance Optimization**: Concurrent scraping reduces execution time from 60s+ to ~50s
2. **Reliability**: Multi-strategy approach achieves 95%+ successful scrape rate
3. **Data Quality**: Smart alias matching and validation prevents duplicate/invalid entries
4. **Scalability**: Dynamic "See More" button clicking loads 50+ banks from Bankrate pagination
5. **User Experience**: Rich, actionable notifications with emoji-based visual hierarchy
6. **Cloud Automation**: GitHub Actions CI/CD pipeline for scheduled execution
7. **UX Design**: Smart notification logic prevents alert fatigue while ensuring critical updates are delivered

## 📊 Data Structure

### History Entry Format
```json
{
  "date": "2026-01-08 22:38",
  "rates": {
    "Ally": 3.30,
    "Sofi": 3.30,
    "Marcus": 3.65,
    "Barclays": 3.85
  }
}
```

## 🔧 Configuration

The system uses a flexible configuration approach:
- **Environment Variables**: 
  - `SLACK_WEBHOOK_URL` - Your Slack webhook for notifications
  - `NOTIFICATION_MODE` - Notification strategy (default: `smart`)
- **Bank Definitions**: Easy-to-modify dictionaries for URLs and categories
- **Scraping Strategy**: Configurable lists for Selenium vs. static scraping
- **Tracking Preferences**: Separate main/supplementary bank lists
- **Alert Thresholds**: Customizable trigger values for smart notifications

## 💡 Problem-Solving Highlights

1. **JavaScript-Rendered Content**: Implemented selective Selenium usage only where necessary, falling back to faster static scraping
2. **Rate Extraction Variability**: Created robust regex patterns that handle "4.35%", "4.35% APY", and various formats
3. **Bank Name Normalization**: Built comprehensive alias system to match banks across different data sources
4. **Pagination Handling**: Automated "See More" button clicking with safety limits and scroll-to-element logic
5. **Data Integrity**: Validation ranges and deduplication logic ensure clean datasets
6. **Alert Fatigue**: Designed smart notification logic that eliminates noise while ensuring critical alerts are never missed

## 📦 Installation & Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cat > .env << EOF
SLACK_WEBHOOK_URL=your_webhook_url
NOTIFICATION_MODE=smart  # Options: always, smart, weekly, monthly, never
EOF

# Run tracker
python scraper.py
```

### Notification Modes Explained

| Mode | Behavior | Best For |
|------|----------|----------|
| `always` | Send notification every run | Testing, critical monitoring |
| `smart` | Immediate alerts + weekly digest + monthly report | **Recommended** - Complete coverage |
| `weekly` | Sunday digest only | Low-touch monitoring |
| `monthly` | 1st of month summary only | Long-term trend tracking |
| `never` | Silent data collection | Building historical dataset |

## 🎓 Skills Demonstrated

- **Web Scraping**: Multi-strategy approach with BeautifulSoup and Selenium
- **Concurrent Programming**: Thread pool management for parallel operations
- **Data Engineering**: ETL pipeline with validation and persistence
- **API Integration**: Slack webhooks for real-time notifications
- **Algorithm Design**: Ranking, change detection, and trend analysis
- **Error Handling**: Comprehensive exception handling and fallback strategies
- **Code Organization**: Clean, modular architecture with clear separation of concerns
- **Production Mindset**: Robust logging, validation, and monitoring
- **DevOps/CI/CD**: GitHub Actions automation with scheduled workflows
- **Cloud Infrastructure**: Serverless execution on GitHub-hosted runners

## 🚀 Future Enhancements
- [ ] Web dashboard with historical charts (Flask/Dash)
- [ ] Machine learning for rate prediction
- [ ] Containerization (Docker) for easy deployment

---

**Author**: Aaryan Patel  
**Project Type**: Personal Finance Automation Tool  
**Status**: Production-Ready  
**Last Updated**: January 2026
