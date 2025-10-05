# 🚀 Reddit Scraper - Streamlit Cloud Deployment Instructions

## ✅ Repository Status: READY FOR DEPLOYMENT

The repository has been cleaned up and is production-ready:
- ✅ Redundant files removed
- ✅ Dependencies verified and optimized  
- ✅ Code tested locally
- ✅ Configuration files updated
- ✅ GPT-4o model integrated with cost controls

## 🚀 Deploy to Streamlit Cloud (FREE)

### Step 1: Get Reddit API Credentials
1. Visit [Reddit Apps](https://www.reddit.com/prefs/apps)
2. Click "Create App" → Select "script" type
3. Note your `Client ID` and `Client Secret`
4. Create a descriptive user agent: `"YourAppName/1.0 by /u/yourusername"`

### Step 2: Deploy to Streamlit Cloud
1. **Go to**: [https://share.streamlit.io/](https://share.streamlit.io/)
2. **Sign in** with your GitHub account
3. **Click "New app"**
4. **Select this repository** from your GitHub
5. **Set Main file**: `main.py`
6. **Set Python version**: `3.11` (recommended)

### Step 3: Configure Secrets (CRITICAL)
In your Streamlit app settings, add these secrets:

```toml
# Reddit API Configuration
REDDIT_CLIENT_ID = "your_actual_client_id_here"
REDDIT_CLIENT_SECRET = "your_actual_client_secret_here"  
REDDIT_USER_AGENT = "YourAppName/1.0 by /u/yourusername"

# Azure OpenAI Configuration (Optional - for AI features)
AZURE_OPENAI_API_KEY = "your_azure_openai_key"
AZURE_OPENAI_ENDPOINT = "your_azure_openai_endpoint"
AZURE_OPENAI_DEPLOYMENT_NAME = "gpt-4o"
AZURE_OPENAI_API_VERSION = "2025-01-01-preview"

# AI Budget Control
MONTHLY_BUDGET_INR = "500"
ENABLE_AI_FEATURES = "true"
```

### Step 4: Deploy!
Click **"Deploy!"** and wait 2-3 minutes for deployment to complete.

## 🧪 Local Development Testing

To test locally before deployment:

```bash
# Navigate to project
cd reddit-scraper

# Activate virtual environment  
.venv\Scripts\activate

# Run the app
streamlit run main.py
```

The app will be available at `http://localhost:8501`

## 🌟 Features Available After Deployment

### 🔍 Core Features
- **Subreddit Scraping**: Extract posts from any public subreddit
- **Single Post Analysis**: Analyze specific Reddit posts and comments
- **Advanced Filtering**: Date ranges, scores, keywords, NSFW filters
- **Data Export**: CSV and JSON downloads with copy-to-clipboard
- **Interactive Analytics**: Plotly charts and visualizations

### 🧠 AI Features (Optional)
- **Intelligent Summarization**: GPT-4o powered insights
- **Content Categorization**: Automatic classification of posts
- **Cost Control**: Built-in budget tracking (₹500/month limit)
- **Business Intelligence**: Extract actionable insights from Reddit data

## 💡 Usage Tips

### For Large Subreddits
- Use specific date ranges instead of "All"
- Apply filters to reduce data volume
- Monitor API rate limits (handled automatically)

### For Cost Control
- AI features are optional and can be disabled
- Set monthly budget limits in secrets
- Monitor usage in the app dashboard

## 🛠️ Troubleshooting

### Common Issues:
1. **Invalid credentials**: Check Reddit API keys in secrets
2. **No posts found**: Verify subreddit name and privacy settings
3. **App won't start**: Ensure all secrets are configured
4. **Rate limiting**: Wait a few minutes and retry

### Performance Issues:
- Clear browser cache
- Use smaller date ranges
- Apply content filters

## 📞 Support

- Check the troubleshooting section above
- Review the detailed `README.md`
- Ensure all dependencies match `requirements.txt`
- Test locally first using the instructions above

## 🎉 Success!

Your Reddit Scraper is now deployed and ready to use! 

**App URL**: `https://your-app-name.streamlit.app/`

### Key Benefits:
- ✅ **Free hosting** on Streamlit Cloud
- ✅ **Production-ready** with security best practices
- ✅ **Dual environment** - works both locally and in cloud
- ✅ **GPT-4o integration** for advanced AI insights
- ✅ **Cost controlled** with monthly budget limits
- ✅ **Modern UI** with responsive design

**Happy Reddit Scraping! 🚀**