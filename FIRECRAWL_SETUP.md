# 🔥 Firecrawl Setup Guide

## Overview
Firecrawl is used for cloud-compatible web scraping in the URL Job Loader feature. It replaces Selenium for Streamlit Cloud deployment, providing reliable scraping with JavaScript rendering.

## Getting Your API Key

1. **Sign up at Firecrawl**: https://firecrawl.dev/
2. **Get your API key** from the dashboard
3. **Add to your Streamlit secrets** (see below)

## Local Development Setup

Create or update `.streamlit/secrets.toml`:

```toml
[default]
FIRECRAWL_API_KEY = "your-api-key-here"
```

## Streamlit Cloud Setup

1. Go to your app's "Manage app" page
2. Click "Settings" → "Secrets"
3. Add:
```toml
FIRECRAWL_API_KEY = "your-api-key-here"
```

## Environment Variable (Alternative)

You can also set the environment variable:
```bash
export FIRECRAWL_API_KEY="your-api-key-here"
```

## How It Works

The scraper automatically detects the best method:

- **Cloud Deployment**: Uses Firecrawl API (reliable, fast)
- **Local Development**: Uses Firecrawl if configured, falls back to Selenium
- **Fallback**: If Firecrawl fails, tries Selenium (local only)

## Features

✅ **Cloud Compatible** - Works in Streamlit Cloud  
✅ **JavaScript Rendering** - Handles dynamic content  
✅ **AI Integration** - Automatic job info extraction  
✅ **Smart Fallback** - Multiple scraping methods  
✅ **Error Handling** - Graceful failure management  

## Testing

The scraper will show which method is being used:
- 🔥 "Using Firecrawl API for scraping" - Firecrawl active
- 🔧 "Using Selenium for scraping" - Local fallback
- ❌ "Firecrawl scraping failed" - Error with details

## Troubleshooting

**"Firecrawl scraper not available"**
- Check your API key is set correctly
- Ensure `firecrawl-py` package is installed

**"API error" messages**
- Check your API key is valid
- Verify you have API credits remaining
- Some sites may block automated scraping

## Cost Considerations

Firecrawl is a paid service. Monitor your usage:
- Each scrape consumes 1 credit
- Check your account dashboard for usage
- Consider rate limiting for heavy usage