# Reddit Scraper 🚀

A modern, interactive Reddit data scraper with AI-powered insights. Extract posts, comments, and analytics from any subreddit with a beautiful, responsive interface.

![Reddit Scraper](reddit-logo.png)

## 🌐 Live Demo

**Try it now**: [https://reddit-scraper-with-llm.streamlit.app/](https://reddit-scraper-with-llm.streamlit.app/)

## 🔍 Alternative & Inspiration
[**GummySearch**](https://gummysearch.com/)

## ✨ Features

- **🔍 Subreddit Scraping**: Extract posts from any subreddit with advanced filtering
- **🔗 Single Post Analysis**: Deep dive into specific posts and comment threads
- **🧠 AI-Powered Summarization**: GPT-4o integration for actionable business insights
- **📊 Interactive Analytics**: Real-time charts and visualizations using Plotly
- **🎯 Advanced Filtering**: Date ranges, scores, keywords, NSFW content, and more
- **🏷️ Smart Categorization**: AI-powered content classification (Pain Points, Solutions, etc.)
- **📥 Data Export**: Copy-to-clipboard JSON and CSV downloads
- **🌙 Modern UI**: Beautiful dark theme with responsive design
- **💰 Cost Control**: Built-in budget tracking for AI features (₹500/month limit)

## 🚀 Quick Start

### 1. Use the Live App
Visit [https://reddit-scraper-with-llm.streamlit.app/](https://reddit-scraper-with-llm.streamlit.app/) - no setup required!

### 2. Deploy Your Own
[![Deploy to Streamlit Cloud](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/)

1. Fork this repository
2. Get Reddit API credentials from [Reddit Apps](https://www.reddit.com/prefs/apps)
3. Deploy to [Streamlit Cloud](https://share.streamlit.io/)
4. Configure secrets with your Reddit API credentials

### 3. Run Locally
```bash
git clone https://github.com/jaigoyal01/reddit-scraper.git
cd reddit-scraper
pip install -r requirements.txt
streamlit run main.py
```

## 📋 Configuration

Add these secrets in Streamlit Cloud or `.streamlit/secrets.toml`:

```toml
REDDIT_CLIENT_ID = "your_client_id"
REDDIT_CLIENT_SECRET = "your_client_secret"
REDDIT_USER_AGENT = "RedditScraper/1.0 by /u/yourusername"

# Optional: For AI features
AZURE_OPENAI_API_KEY = "your_azure_key"
AZURE_OPENAI_ENDPOINT = "your_azure_endpoint"
AZURE_OPENAI_DEPLOYMENT_NAME = "gpt-4o"
```

## 🔧 Usage

### Subreddit Analysis
1. Enter subreddit name (without r/)
2. Set filters (date range, scores, keywords)
3. View analytics and export data

### Single Post Analysis  
1. Paste Reddit post URL
2. Analyze post and comment threads
3. Get AI-powered insights and summaries

## 🛠️ Tech Stack

- **Frontend**: Streamlit with custom CSS
- **Data Processing**: Pandas, Plotly
- **Reddit API**: PRAW
- **AI Integration**: Azure OpenAI (GPT-4o)
- **Deployment**: Streamlit Cloud

## 🐛 Troubleshooting

- **Invalid credentials**: Check Reddit API keys in secrets
- **No posts found**: Verify subreddit name and privacy settings  
- **Rate limiting**: Wait a few minutes between large requests
- **AI features not working**: Ensure Azure OpenAI credentials are configured

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions welcome! Please open an issue first for major changes.

---

**Happy Scraping! 🎉**

Made with ❤️ for the Reddit community