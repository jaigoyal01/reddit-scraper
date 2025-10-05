import os
import re
from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Tuple

import pandas as pd
import praw
import streamlit as st
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go

# Import LLM service
try:
    from llm_service import AzureOpenAIService
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    st.warning("⚠️ LLM service dependencies not installed. Run: pip install openai tiktoken")


# ────────────────────────────── env & reddit init ──────────────────────────────
if os.path.exists(".env"):  # load only in local/dev
    load_dotenv()

def init_reddit() -> praw.Reddit:
    """Create a PRAW `Reddit` instance from env / Streamlit secrets.
    Shows a helpful message and stops if credentials are missing.
    """
    client_id     = os.getenv("REDDIT_CLIENT_ID")     or st.secrets.get("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET") or st.secrets.get("REDDIT_CLIENT_SECRET")
    user_agent    = os.getenv("REDDIT_USER_AGENT")    or st.secrets.get("REDDIT_USER_AGENT")

    missing: list[str] = []
    if not client_id:
        missing.append("REDDIT_CLIENT_ID")
    if not client_secret:
        missing.append("REDDIT_CLIENT_SECRET")
    if not user_agent:
        missing.append("REDDIT_USER_AGENT")

    if missing:
        st.error(
            "Missing Reddit API credentials: " + ", ".join(missing) +
            "\n\nPlease add them in Settings → Secrets (or set environment variables)."
        )
        st.markdown(
            "Add these entries in your Streamlit secrets:")
        st.code(
            """REDDIT_CLIENT_ID = "your_actual_client_id"
REDDIT_CLIENT_SECRET = "your_actual_client_secret"
REDDIT_USER_AGENT = "RedditScraper/1.0 by /u/yourusername""",
            language="toml",
        )
        st.stop()

    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )


def init_llm_service():
    """Initialize LLM service for AI summarization"""
    if not LLM_AVAILABLE:
        return None
    try:
        service = AzureOpenAIService()
        return service if service.is_available() else None
    except Exception as e:
        st.error(f"Failed to initialize LLM service: {e}")
        return None


# ──────────────────────────── Intelligent Categorization ────────────────────────────
def get_category_keywords() -> Dict[str, List[str]]:
    """Define keywords and patterns for each category like GummySearch."""
    return {
        "Pain Points": [
            "problem", "issue", "struggling", "frustrated", "annoying", "broken", "doesn't work",
            "hate", "terrible", "awful", "worst", "failing", "difficult", "hard", "impossible",
            "bug", "error", "crash", "slow", "expensive", "overpriced", "waste", "scam",
            "disappointed", "regret", "mistake", "wrong", "bad", "horrible", "sucks",
            "fix", "solve", "help", "support", "trouble", "stuck", "confused", "lost"
        ],
        "Solution Requests": [
            "how to", "how do", "how can", "what's the best", "recommend", "suggestion",
            "advice", "help me", "looking for", "need", "want", "seeking", "search",
            "alternative", "replacement", "substitute", "instead of", "better than",
            "tutorial", "guide", "instructions", "step by step", "walkthrough",
            "best way", "most effective", "proven method", "tips", "tricks", "hacks"
        ],
        "Money Talk": [
            "price", "cost", "expensive", "cheap", "budget", "affordable", "money", "pay",
            "subscription", "monthly", "yearly", "fee", "charge", "billing", "invoice",
            "worth it", "value", "roi", "return on investment", "save money", "deal",
            "discount", "coupon", "promo", "sale", "free", "pricing", "quote", "estimate",
            "$", "usd", "euro", "pound", "currency", "salary", "income", "revenue", "profit"
        ],
        "Hot Discussions": [
            "trending", "viral", "popular", "everyone", "talking about", "buzz", "hype",
            "news", "announcement", "update", "release", "launch", "breaking", "controversy",
            "debate", "argument", "discussion", "thoughts", "opinions", "what do you think",
            "hot take", "unpopular opinion", "controversial", "drama", "gossip"
        ],
        "Seeking Alternatives": [
            "alternative", "replacement", "substitute", "instead of", "better than", "similar to",
            "like", "competitor", "switch from", "migrate", "move away", "leave", "quit",
            "fed up", "done with", "tired of", "sick of", "switching", "changing",
            "compare", "vs", "versus", "difference", "which is better", "pros and cons"
        ]
    }

def classify_post_content(title: str, text: str) -> Tuple[str, float]:
    """
    Classify a post into one of the GummySearch categories.
    Returns (category, confidence_score).
    """
    keywords = get_category_keywords()
    content = f"{title.lower()} {text.lower()}"
    
    # Remove common noise words for better classification
    noise_words = ["the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"]
    for word in noise_words:
        content = re.sub(rf'\b{word}\b', '', content)
    
    category_scores = {}
    
    for category, category_keywords in keywords.items():
        score = 0
        for keyword in category_keywords:
            # Use regex for better matching
            pattern = rf'\b{re.escape(keyword.lower())}\b'
            matches = len(re.findall(pattern, content))
            score += matches
            
            # Boost score for title matches (more important)
            title_matches = len(re.findall(pattern, title.lower()))
            score += title_matches * 2
        
        category_scores[category] = score
    
    # Get the category with highest score
    if max(category_scores.values()) == 0:
        return "General Discussion", 0.0
    
    best_category = max(category_scores, key=category_scores.get)
    max_score = category_scores[best_category]
    
    # Calculate confidence (normalize by content length and keyword count)
    total_words = len(content.split())
    confidence = min(max_score / max(total_words * 0.1, 1), 1.0)
    
    return best_category, confidence

def get_category_color(category: str) -> str:
    """Get color for category badges like GummySearch."""
    colors = {
        "Pain Points": "#FF4B4B",      # Red
        "Solution Requests": "#00D4FF", # Blue  
        "Money Talk": "#00FF88",       # Green
        "Hot Discussions": "#FF8C00",  # Orange
        "Seeking Alternatives": "#9966FF", # Purple
        "General Discussion": "#666666"  # Gray
    }
    return colors.get(category, "#666666")

def get_category_icon(category: str) -> str:
    """Get emoji icon for each category."""
    icons = {
        "Pain Points": "😣",
        "Solution Requests": "❓", 
        "Money Talk": "💰",
        "Hot Discussions": "🔥",
        "Seeking Alternatives": "🔄",
        "General Discussion": "💬"
    }
    return icons.get(category, "💬")


# ─────────────────────── helpers: fetch posts & single thread ──────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def get_subreddit_posts(
    _reddit: praw.Reddit,
    name: str,
    filter_type: str = "All",
    start: date | None = None,
    end:   date | None = None,
    max_posts: int = 100,
) -> pd.DataFrame:
    """
    Scrape posts that fall inside the requested window, up to max_posts limit.
    • "All", "Last Week", "Last Month", "Last Year" use rolling windows  
    • "Date Range" honours the explicit `start` → `end` span  
    • max_posts: Maximum number of posts to fetch (default: 100)
    Note: Reddit's API caps results at ~1 000 posts per listing; for huge
    subs you'll hit that limit unless you integrate Pushshift.
    """
    try:
        sub   = _reddit.subreddit(name)
        now   = datetime.now(timezone.utc)
        start_ts, end_ts = 0, now.timestamp()

        if filter_type == "Last Week":
            start_ts = (now - timedelta(days=7)).timestamp()
        elif filter_type == "Last Month":
            start_ts = (now - timedelta(days=30)).timestamp()
        elif filter_type == "Last Year":
            start_ts = (now - timedelta(days=365)).timestamp()
        elif filter_type == "Date Range" and start and end:
            start_ts = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc).timestamp()
            end_ts   = datetime.combine(end,   datetime.max.time(), tzinfo=timezone.utc).timestamp()

        rows: list[dict] = []
        posts_checked = 0
        for post in sub.new(limit=None):            # newest → oldest
            posts_checked += 1
            if post.created_utc > end_ts:
                continue
            if post.created_utc < start_ts:         # we're past window → stop
                break
            
            # Check if we've reached max_posts limit
            if len(rows) >= max_posts:
                break

            # Classify the post content
            category, confidence = classify_post_content(post.title, post.selftext or "")
            
            rows.append({
                "ID":                  post.id,
                "Title":               post.title,
                "Post Text":           post.selftext,
                "Subreddit":           post.subreddit.display_name,
                "Author":              str(post.author),
                "Created UTC":         datetime.fromtimestamp(post.created_utc, tz=timezone.utc),
                "Score":               post.score,
                "Up-vote Ratio":       post.upvote_ratio,
                "Total Comments":      post.num_comments,
                "Total Awards":        post.total_awards_received,
                "Flair":               post.link_flair_text,
                "Is Original Content": post.is_original_content,
                "Over 18":             post.over_18,
                "Spoiler":             post.spoiler,
                "Num Cross-posts":     post.num_crossposts,
                "Permalink":           f"https://www.reddit.com{post.permalink}",
                "Post URL":            post.url,
                "Category":            category,
                "Category Confidence": confidence,
            })
        return pd.DataFrame(rows)

    except Exception as exc:
        st.error(f"Error fetching subreddit posts: {exc}")
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def get_post_by_url(_reddit: praw.Reddit, url: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return a DataFrame for the submission + its **entire** comment tree."""
    try:
        s = _reddit.submission(url=url)
        
        # Classify the post content
        category, confidence = classify_post_content(s.title, s.selftext or "")
        
        post_df = pd.DataFrame([{
            "ID":            s.id,
            "Title":         s.title,
            "Post Text":     s.selftext,
            "Subreddit":     s.subreddit.display_name,
            "Author":        str(s.author),
            "Created UTC":   datetime.fromtimestamp(s.created_utc, tz=timezone.utc),
            "Score":         s.score,
            "Up-vote Ratio": s.upvote_ratio,
            "Total Comments": s.num_comments,
            "Total Awards":   s.total_awards_received,
            "Flair":          s.link_flair_text,
            "Is Original Content": s.is_original_content,
            "Over 18":            s.over_18,
            "Spoiler":            s.spoiler,
            "Num Cross-posts":    s.num_crossposts,
            "Permalink":          f"https://www.reddit.com{s.permalink}",
            "Post URL":           s.url,
            "Category":           category,
            "Category Confidence": confidence,
        }])

        s.comments.replace_more(limit=None)
        comments = [{
            "Comment ID":   c.id,
            "Parent ID":    c.parent_id,
            "Comment Text": c.body,
            "Author":       str(c.author),
            "Score":        c.score,
            "Created UTC":  datetime.fromtimestamp(c.created_utc, tz=timezone.utc),
            "Permalink":    f"https://www.reddit.com{c.permalink}",
            "Is Submitter": c.is_submitter,
        } for c in s.comments.list()]

        return post_df, pd.DataFrame(comments)

    except Exception as exc:
        st.error(f"Error fetching post: {exc}")
        return pd.DataFrame(), pd.DataFrame()


# ──────────────────────────────── Streamlit UI ────────────────────────────────
def apply_custom_css():
    """Apply custom CSS for modern dark theme and better styling."""
    st.markdown("""
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Main theme colors */
    :root {
        --primary-color: #FF4B4B;
        --secondary-color: #FF6B6B;
        --background-dark: #0E1117;
        --surface-dark: #1A1D23;
        --surface-light: #262730;
        --text-primary: #FAFAFA;
        --text-secondary: #A6A6A6;
        --accent-blue: #00D4FF;
        --accent-green: #00FF88;
        --border-color: #333644;
    }
    
    /* Main container styling */
    .stApp {
        background: linear-gradient(135deg, var(--background-dark) 0%, #1a1d29 100%);
        font-family: 'Inter', sans-serif;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, var(--surface-dark) 0%, var(--surface-light) 100%);
        border-right: 1px solid var(--border-color);
    }
    
    /* Headers and titles */
    .main-header {
        background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 700;
        display: inline-block;
        vertical-align: middle;
    }
    
    .section-header {
        color: var(--text-primary);
        font-size: 1.8rem;
        font-weight: 600;
        margin: 1.5rem 0 1rem 0;
        border-bottom: 2px solid var(--accent-blue);
        padding-bottom: 0.5rem;
    }
    
    /* Cards and containers */
    .filter-card {
        background: var(--surface-dark);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }
    
    .stats-card {
        background: linear-gradient(135deg, var(--surface-dark), var(--surface-light));
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
        border: 1px solid var(--border-color);
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(45deg, var(--primary-color), var(--secondary-color));
        border: none;
        border-radius: 8px;
        color: white;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 75, 75, 0.4);
    }
    
    /* Metrics */
    .metric-container {
        background: var(--surface-dark);
        border-radius: 8px;
        padding: 1rem;
        border-left: 4px solid var(--accent-blue);
    }
    
    /* Selectbox and inputs */
    .stSelectbox > div > div {
        background: var(--surface-light);
        border: 1px solid var(--border-color);
        border-radius: 6px;
    }
    
    .stTextInput > div > div > input {
        background: var(--surface-light);
        border: 1px solid var(--border-color);
        border-radius: 6px;
        color: var(--text-primary);
    }
    
    /* Success/Error messages */
    .stSuccess {
        background: linear-gradient(90deg, var(--accent-green), #00cc77);
        border-radius: 8px;
    }
    
    .stError {
        background: linear-gradient(90deg, #ff4757, #ff3742);
        border-radius: 8px;
    }
    
    /* DataFrame styling */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    
    /* Advanced filter section */
    .advanced-filters {
        background: var(--surface-dark);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1.5rem;
        margin-top: 1rem;
    }
    
    .filter-section {
        margin-bottom: 1rem;
        padding: 1rem;
        background: var(--surface-light);
        border-radius: 8px;
        border-left: 3px solid var(--accent-blue);
    }
    </style>
    """, unsafe_allow_html=True)

def create_category_analytics(df: pd.DataFrame):
    """Create category distribution analytics like GummySearch."""
    if df.empty or 'Category' not in df.columns:
        return
    
    st.markdown('<h3 class="section-header">🏷️ Content Categories</h3>', unsafe_allow_html=True)
    
    # Category distribution
    category_counts = df['Category'].value_counts()
    
    # Create category cards
    cols = st.columns(len(category_counts))
    for i, (category, count) in enumerate(category_counts.items()):
        with cols[i % len(cols)]:
            icon = get_category_icon(category)
            color = get_category_color(category)
            percentage = (count / len(df)) * 100
            
            st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, {color}20, {color}10);
                    border-left: 4px solid {color};
                    border-radius: 8px;
                    padding: 1rem;
                    margin: 0.5rem 0;
                    text-align: center;
                ">
                    <div style="font-size: 2rem; margin-bottom: 0.5rem;">{icon}</div>
                    <div style="font-weight: 600; color: {color};">{category}</div>
                    <div style="font-size: 1.5rem; font-weight: bold; margin: 0.5rem 0;">{count}</div>
                    <div style="font-size: 0.9rem; opacity: 0.8;">{percentage:.1f}%</div>
                </div>
            """, unsafe_allow_html=True)
    
    # Category distribution chart
    fig_categories = px.pie(
        values=category_counts.values,
        names=category_counts.index,
        title="Category Distribution",
        color=category_counts.index,
        color_discrete_map={
            cat: get_category_color(cat) for cat in category_counts.index
        }
    )
    fig_categories.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white'
    )
    st.plotly_chart(fig_categories, use_container_width=True)

def create_stats_dashboard(df: pd.DataFrame):
    """Create a stats dashboard with key metrics."""
    if df.empty:
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 Total Posts", len(df))
    with col2:
        avg_score = df['Score'].mean() if 'Score' in df.columns else 0
        st.metric("⭐ Avg Score", f"{avg_score:.1f}")
    with col3:
        avg_comments = df['Total Comments'].mean() if 'Total Comments' in df.columns else 0
        st.metric("💬 Avg Comments", f"{avg_comments:.1f}")
    with col4:
        total_awards = df['Total Awards'].sum() if 'Total Awards' in df.columns else 0
        st.metric("🏆 Total Awards", int(total_awards))

def display_single_post_summary(summary: dict):
    """Display AI summary for a single post"""
    if "error" in summary:
        st.error(f"❌ {summary['error']}")
        return
    
    st.markdown("### 🧠 AI-Powered Post Analysis")

    # New preferred rendering: direct markdown sections produced by model
    if "formatted_markdown" in summary:
        view_mode = st.radio(
            "View Mode",
            ["Rendered", "Raw Markdown", "Raw JSON"],
            horizontal=True,
            key="single_summary_markdown_mode"
        )

        if view_mode == "Rendered":
            st.markdown(summary["formatted_markdown"], unsafe_allow_html=False)
        elif view_mode == "Raw Markdown":
            with st.expander("Markdown Output", expanded=True):
                st.code(summary["formatted_markdown"], language="markdown")
        else:  # Raw JSON
            with st.expander("Full JSON", expanded=True):
                st.json(summary)

        # Metadata display
        meta = summary.get("metadata", {})
        if meta:
            with st.expander("📊 Analysis Details"):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if meta.get("tokens"):
                        st.metric("Tokens", meta["tokens"].get("total", "N/A"))
                with col2:
                    if meta.get("cost_inr") is not None:
                        st.metric("Cost (INR)", f"₹{meta['cost_inr']:.4f}")
                with col3:
                    if meta.get("processing_time") is not None:
                        st.metric("Time", f"{meta['processing_time']:.2f}s")
                with col4:
                    if meta.get("dynamic_output_token_limit"):
                        st.metric("Out Tokens Cap", meta.get("dynamic_output_token_limit"))
                if meta.get("prompt_preview"):
                    with st.expander("🔍 Prompt Sent to LLM"):
                        st.code(meta["prompt_preview"], language="markdown")
                flags = []
                if meta.get("fallback_mode"): flags.append("fallback_mode")
                if meta.get("sanitized_post"): flags.append("sanitized_post")
                if meta.get("sanitized_comments"): flags.append("sanitized_comments")
                if flags:
                    st.caption("Flags: " + ", ".join(flags))
        return

    # Provide a display style toggle (defaults to narrative if advanced schema present)
    advanced_schema = 'problem' in summary and 'key_takeaway' in summary
    default_mode = 'Narrative' if advanced_schema else 'Structured'
    display_mode = st.radio(
        "Display Style",
        options=["Narrative", "Structured", "Raw JSON"],
        index=["Narrative", "Structured", "Raw JSON"].index(default_mode),
        horizontal=True,
        key="single_summary_display_mode"
    )

    # Advanced narrative rendering (ChatGPT-like) when new schema is present
    if advanced_schema and display_mode == 'Narrative':
        # Problem & Context
        if summary.get('problem'):
            st.markdown("#### 🧩 Core Problem")
            st.write(summary['problem'])
        if summary.get('context'):
            st.markdown("#### 📌 Context")
            st.write(summary['context'])

        cols_top = st.columns(2)
        with cols_top[0]:
            if summary.get('underlying_patterns'):
                st.markdown("#### 🧠 Underlying Patterns")
                for p in summary['underlying_patterns'][:8]:
                    st.markdown(f"• {p}")
            if summary.get('psychological_barriers'):
                st.markdown("#### 🚧 Psychological Barriers")
                for b in summary['psychological_barriers'][:8]:
                    st.markdown(f"• {b}")
        with cols_top[1]:
            if summary.get('risks_of_inaction'):
                st.markdown("#### ⚠️ Risks of Inaction")
                for r in summary['risks_of_inaction'][:8]:
                    st.markdown(f"• {r}")
            if summary.get('common_counterpoints'):
                st.markdown("#### ↔️ Common Counterpoints")
                for c in summary['common_counterpoints'][:10]:
                    st.markdown(f"• {c}")

        # Suggestions & Actions
        if summary.get('useful_suggestions'):
            st.markdown("#### 💡 Useful Suggestions")
            for s in summary['useful_suggestions'][:15]:
                st.markdown(f"• {s}")

        if summary.get('actionable_steps') and isinstance(summary['actionable_steps'], list):
            st.markdown("#### ✅ Actionable Steps")
            for step in summary['actionable_steps'][:10]:
                if isinstance(step, dict):
                    line = f"- **{step.get('step','')}**"
                    details = []
                    if step.get('rationale'): details.append(step['rationale'])
                    if step.get('effort'): details.append(f"Effort: {step['effort']}")
                    if step.get('impact'): details.append(f"Impact: {step['impact']}")
                    if details:
                        line += " — " + " | ".join(details)
                    st.markdown(line)
                else:
                    st.markdown(f"- {step}")

        # Resources
        if summary.get('resource_mentions'):
            st.markdown("#### 📚 Resource Mentions")
            for r in summary['resource_mentions'][:10]:
                if isinstance(r, dict):
                    st.markdown(f"• {r.get('type','resource').title()}: {r.get('title','')} — {r.get('mentioned_as','')}")
                else:
                    st.markdown(f"• {r}")

        # Quotes
        if summary.get('representative_quotes'):
            with st.expander("💬 Representative Quotes"):
                for q in summary['representative_quotes'][:12]:
                    st.markdown(f"> {q}")

        # Key Takeaway
        if summary.get('key_takeaway'):
            st.markdown("#### 🎯 Key Takeaway")
            st.success(summary['key_takeaway'])

        # Confidence
        if summary.get('confidence'):
            st.caption(f"Confidence: {summary['confidence']}")

        # Metadata + Debug
        if "metadata" in summary:
            with st.expander("📊 Analysis Details"):
                meta = summary["metadata"]
                col1, col2, col3 = st.columns(3)
                with col1:
                    if "tokens" in meta:
                        st.metric("Tokens Used", meta["tokens"].get("total", "N/A"))
                with col2:
                    if "cost_inr" in meta:
                        st.metric("Cost (INR)", f"₹{meta['cost_inr']:.4f}")
                with col3:
                    if "processing_time" in meta:
                        st.metric("Time", f"{meta['processing_time']:.2f}s")
                if meta.get("prompt_preview"):
                    with st.expander("🔍 Prompt Sent to LLM"):
                        st.code(meta["prompt_preview"])
        if display_mode == 'Raw JSON':
            with st.expander("🧪 Full Response JSON", expanded=True):
                st.json(summary)
        else:
            with st.expander("🧪 Full Response JSON"):
                st.json(summary)
        return

    # If model returned raw text instead of structured JSON (fallback or parse failure)
    if "executive_summary" not in summary and "raw_analysis" in summary:
        with st.expander("📝 Raw AI Output (Unstructured)", expanded=True):
            st.write(summary["raw_analysis"])
            if summary.get("note"):
                st.caption(summary["note"])
            if summary.get("metadata", {}).get("fallback_mode"):
                st.warning("Displayed result is from a fallback prompt due to content filtering.")
        # Show metadata if present
        if "metadata" in summary:
            with st.expander("📊 Analysis Details"):
                meta = summary["metadata"]
                if meta.get("prompt_preview"):
                    with st.expander("🔍 Prompt Sent to LLM", expanded=False):
                        st.code(meta["prompt_preview"], language="markdown")
                col1, col2, col3 = st.columns(3)
                with col1:
                    if "tokens" in meta:
                        st.metric("Tokens Used", meta["tokens"].get("total", "N/A"))
                with col2:
                    if "cost_inr" in meta:
                        st.metric("Cost (INR)", f"₹{meta['cost_inr']:.4f}")
                with col3:
                    if "processing_time" in meta:
                        st.metric("Processing Time", f"{meta['processing_time']:.2f}s")
                # Extra flags
                flags = []
                if meta.get("fallback_mode"): flags.append("fallback_mode")
                if meta.get("sanitized_post"): flags.append("sanitized_post")
                if meta.get("sanitized_comments"): flags.append("sanitized_comments")
                if flags:
                    st.caption("Flags: " + ", ".join(flags))
        # Optionally show full JSON for debugging
        with st.expander("🧪 Full Response JSON"):
            st.json(summary)
        return
    
    if display_mode == 'Narrative' and "executive_summary" in summary:
        st.markdown("#### 📋 Executive Summary")
        st.info(summary["executive_summary"])
    elif display_mode == 'Structured' and "executive_summary" in summary:
        st.markdown("#### 📋 Executive Summary")
        st.info(summary["executive_summary"])
    
    # Key Insights
    if "key_insights" in summary:
        st.markdown("#### 💡 Key Insights")
        for insight in summary["key_insights"]:
            st.markdown(f"• {insight}")
    
    # Create columns for detailed analysis
    col1, col2 = st.columns(2)
    
    with col1:
        # Pain Points
        if "pain_points" in summary and summary["pain_points"]:
            st.markdown("#### 😣 Pain Points")
            for pain in summary["pain_points"]:
                st.markdown(f"• {pain}")
        
        # Solutions
        if "solutions_discussed" in summary and summary["solutions_discussed"]:
            st.markdown("#### 💡 Solutions Discussed")
            for solution in summary["solutions_discussed"]:
                st.markdown(f"• {solution}")
        
        # Sentiment
        if "sentiment" in summary:
            st.markdown(f"#### 😊 Sentiment: **{summary['sentiment']}**")
    
    with col2:
        # Business Opportunities
        if "business_opportunities" in summary and summary["business_opportunities"]:
            st.markdown("#### 🎯 Business Opportunities")
            for opp in summary["business_opportunities"]:
                st.markdown(f"• {opp}")
        
        # Action Items
        if "action_items" in summary and summary["action_items"]:
            st.markdown("#### ✅ Action Items")
            for action in summary["action_items"]:
                st.markdown(f"• {action}")
    
    # Community Consensus
    if "community_consensus" in summary:
        st.markdown("#### 🗣️ Community Consensus")
        st.markdown(summary["community_consensus"])
    
    # Metadata
    if "metadata" in summary and display_mode != 'Raw JSON':
        with st.expander("📊 Analysis Details"):
            meta = summary["metadata"]
            if meta.get("prompt_preview"):
                with st.expander("🔍 Prompt Sent to LLM", expanded=False):
                    st.code(meta["prompt_preview"], language="markdown")
            col1, col2, col3 = st.columns(3)
            with col1:
                if "tokens" in meta:
                    st.metric("Tokens Used", meta["tokens"].get("total", "N/A"))
            with col2:
                if "cost_inr" in meta:
                    st.metric("Cost (INR)", f"₹{meta['cost_inr']:.4f}")
            with col3:
                if "processing_time" in meta:
                    st.metric("Processing Time", f"{meta['processing_time']:.2f}s")
            # Flags (fallback / sanitization)
            flags = []
            if meta.get("fallback_mode"): flags.append("fallback_mode")
            if meta.get("sanitized_post"): flags.append("sanitized_post")
            if meta.get("sanitized_comments"): flags.append("sanitized_comments")
            if flags:
                st.caption("Flags: " + ", ".join(flags))
    # Raw JSON view (if chosen explicitly)
    if display_mode == 'Raw JSON':
        with st.expander("🧪 Full Response JSON", expanded=True):
            st.json(summary)
    else:
        with st.expander("🧪 Full Response JSON"):
            st.json(summary)

def display_batch_summary(summary: dict):
    """Display AI summary for batch of posts"""
    if "error" in summary:
        st.error(f"❌ {summary['error']}")
        return
    
    st.markdown("### 🧠 AI-Powered Market Intelligence")
    
    # New preferred rendering: direct markdown sections for batch analysis
    if "formatted_markdown" in summary:
        view_mode = st.radio(
            "View Mode",
            ["Rendered", "Raw Markdown", "Raw JSON"],
            horizontal=True,
            key="batch_summary_markdown_mode"
        )

        if view_mode == "Rendered":
            st.markdown(summary["formatted_markdown"], unsafe_allow_html=False)
        elif view_mode == "Raw Markdown":
            with st.expander("Markdown Output", expanded=True):
                st.code(summary["formatted_markdown"], language="markdown")
        else:  # Raw JSON
            with st.expander("Full JSON", expanded=True):
                st.json(summary)

        # Metadata display
        meta = summary.get("metadata", {})
        if meta:
            with st.expander("📊 Analysis Details"):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if meta.get("posts_analyzed"):
                        st.metric("Posts Analyzed", meta["posts_analyzed"])
                with col2:
                    if meta.get("tokens"):
                        st.metric("Tokens", meta["tokens"].get("total", "N/A"))
                with col3:
                    if meta.get("cost_inr") is not None:
                        st.metric("Cost (INR)", f"₹{meta['cost_inr']:.4f}")
                with col4:
                    if meta.get("processing_time") is not None:
                        st.metric("Time", f"{meta['processing_time']:.2f}s")
                if meta.get("prompt_preview"):
                    with st.expander("🔍 Prompt Sent to LLM"):
                        st.code(meta["prompt_preview"], language="markdown")
                flags = []
                if meta.get("fallback_mode"): flags.append("fallback_mode")
                if meta.get("sanitized_batch"): flags.append("sanitized_batch")
                if flags:
                    st.caption("Flags: " + ", ".join(flags))
        return
    
    # Legacy fallback: If model returned raw text instead of structured JSON
    if "executive_summary" not in summary and "raw_analysis" in summary:
        with st.expander("📝 Raw AI Output (Unstructured)", expanded=True):
            st.write(summary["raw_analysis"])
            st.caption("Model response couldn't be parsed as JSON. You can refine the prompt later to improve structure.")
        # Still show metadata if available
        if "metadata" in summary:
            with st.expander("📊 Analysis Details"):
                meta = summary["metadata"]
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if "posts_analyzed" in meta:
                        st.metric("Posts Analyzed", meta["posts_analyzed"])
                with col2:
                    if "tokens" in meta:
                        st.metric("Tokens Used", meta["tokens"].get("total", "N/A"))
                with col3:
                    if "cost_inr" in meta:
                        st.metric("Cost (INR)", f"₹{meta['cost_inr']:.4f}")
                with col4:
                    if "processing_time" in meta:
                        st.metric("Time", f"{meta['processing_time']:.2f}s")
        return

    # Executive Summary
    if "executive_summary" in summary:
        st.markdown("#### 📋 Executive Summary")
        st.info(summary["executive_summary"])
    
    # Market Trends
    if "market_trends" in summary and summary["market_trends"]:
        st.markdown("#### 📈 Market Trends")
        for trend in summary["market_trends"]:
            st.markdown(f"• {trend}")
    
    # Two column layout
    col1, col2 = st.columns(2)
    
    with col1:
        # Emerging Opportunities
        if "emerging_opportunities" in summary and summary["emerging_opportunities"]:
            st.markdown("#### 🚀 Emerging Opportunities")
            for opp in summary["emerging_opportunities"]:
                st.markdown(f"• {opp}")
        
        # Feature Requests
        if "feature_requests" in summary and summary["feature_requests"]:
            st.markdown("#### 🎯 Feature Requests")
            for feature in summary["feature_requests"]:
                st.markdown(f"• {feature}")
    
    with col2:
        # Strategic Recommendations
        if "strategic_recommendations" in summary and summary["strategic_recommendations"]:
            st.markdown("#### 💼 Strategic Recommendations")
            for rec in summary["strategic_recommendations"]:
                st.markdown(f"• {rec}")
        
        # Risk Factors
        if "risk_factors" in summary and summary["risk_factors"]:
            st.markdown("#### ⚠️ Risk Factors")
            for risk in summary["risk_factors"]:
                st.markdown(f"• {risk}")
    
    # Competitive Landscape
    if "competitive_landscape" in summary:
        st.markdown("#### 🔄 Competitive Landscape")
        st.markdown(summary["competitive_landscape"])
    
    # Customer Pain Points by Category
    if "customer_pain_points" in summary and isinstance(summary["customer_pain_points"], dict):
        with st.expander("😣 Pain Points by Category"):
            for category, points in summary["customer_pain_points"].items():
                st.markdown(f"**{category}:**")
                if isinstance(points, list):
                    for point in points:
                        st.markdown(f"  • {point}")
                else:
                    st.markdown(f"  {points}")
    
    # Metadata
    if "metadata" in summary:
        with st.expander("📊 Analysis Details"):
            meta = summary["metadata"]
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if "posts_analyzed" in meta:
                    st.metric("Posts Analyzed", meta["posts_analyzed"])
            with col2:
                if "tokens" in meta:
                    st.metric("Tokens Used", meta["tokens"].get("total", "N/A"))
            with col3:
                if "cost_inr" in meta:
                    st.metric("Cost (INR)", f"₹{meta['cost_inr']:.4f}")
            with col4:
                if "processing_time" in meta:
                    st.metric("Time", f"{meta['processing_time']:.2f}s")

def main() -> None:
    st.set_page_config(
        page_title="Reddit Data Scraper",
        page_icon="reddit-logo.png",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    apply_custom_css()
    
    # Main header with custom logo inline
    st.markdown(
        '''
        <div style="display: flex; align-items: center; justify-content: center; margin-bottom: 2rem;">
            <img src="data:image/png;base64,{}" width="50" style="margin-right: 15px;">
            <h1 class="main-header" style="margin: 0;">Reddit Data Scraper</h1>
        </div>
        '''.format(
            __import__('base64').b64encode(open('reddit-logo.png', 'rb').read()).decode()
        ),
        unsafe_allow_html=True
    )
    
    reddit = init_reddit()
    llm_service = init_llm_service()

    # Enhanced sidebar with better organization
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
        
        # Mode selection with better styling
        mode = st.radio(
            "**Scraping Mode**",
            ("Subreddit Posts", "Specific Post by URL"),
            help="Choose what type of data you want to scrape"
        )
        
        st.markdown("---")
        
        # LLM Usage Statistics
        if llm_service and llm_service.is_available():
            st.markdown("### 🧠 AI Usage Stats")
            try:
                usage_stats = llm_service.cost_tracker.get_monthly_usage()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("This Month", f"₹{usage_stats['total_cost_inr']:.2f}")
                with col2:
                    st.metric("Budget", f"₹{usage_stats['budget_limit']:.0f}")
                
                # Progress bar
                usage_percent = usage_stats['percentage_used']
                st.progress(min(usage_percent / 100, 1.0))
                
                if usage_percent > 80:
                    st.warning(f"⚠️ {usage_percent:.0f}% of budget used")
                elif usage_percent > 50:
                    st.info(f"ℹ️ {usage_percent:.0f}% of budget used")
                
                st.caption(f"API Calls: {usage_stats['api_calls']}")
            except Exception as e:
                st.error(f"Error loading usage stats: {e}")
            
            st.markdown("---")
        
        # Advanced options
        with st.expander("🔧 Advanced Options"):
            show_charts = st.checkbox("Show Analytics Charts", value=True)
            auto_refresh = st.checkbox("Auto-refresh Data", value=False)
            if auto_refresh:
                refresh_interval = st.slider("Refresh Interval (minutes)", 1, 60, 5)

    # ── Subreddit mode ─────────────────────────────────────────────────────────
    if mode == "Subreddit Posts":
        st.markdown('<h2 class="section-header">🔍 Subreddit Posts Scraper</h2>', unsafe_allow_html=True)

        # Main input section with better layout
        col1, col2 = st.columns([2, 1])
        with col1:
            sub_name = st.text_input(
                "**Subreddit Name**",
                value="",
                placeholder="e.g., selfhosted, programming, technology",
                help="Enter the name of the subreddit without 'r/'"
            )
        with col2:
            max_posts = st.number_input(
                "**Max Posts**",
                min_value=10,
                max_value=1000,
                value=100,
                step=10,
                help="Maximum number of posts to fetch"
            )

        # Enhanced filter section
        st.markdown("**📅 Date & Time Filters**")
        
        col1, col2 = st.columns(2)
        with col1:
            filter_opt = st.selectbox(
                "Time Period",
                ("All", "Last Week", "Last Month", "Last Year", "Date Range"),
                help="Select the time period for post filtering"
            )
        with col2:
            sort_option = st.selectbox(
                "Sort By",
                ("New", "Hot", "Top", "Rising"),
                help="Choose how posts should be sorted"
            )

        start_d = end_d = None
        if filter_opt == "Date Range":
            col1, col2 = st.columns(2)
            with col1:
                start_d = st.date_input("Start date", value=date.today() - timedelta(days=7))
            with col2:
                end_d = st.date_input("End date", value=date.today())
            if start_d > end_d:
                st.warning("⚠️ Start date must be before end date.")

        # Content filters
        with st.expander("🎯 Content Filters"):
            col1, col2, col3 = st.columns(3)
            with col1:
                min_score = st.number_input("Min Score", value=0, help="Minimum post score")
                include_nsfw = st.checkbox("Include NSFW", value=False)
            with col2:
                min_comments = st.number_input("Min Comments", value=0, help="Minimum comment count")
                include_spoilers = st.checkbox("Include Spoilers", value=True)
            with col3:
                min_awards = st.number_input("Min Awards", value=0, help="Minimum award count")
                oc_only = st.checkbox("Original Content Only", value=False)
        
        # Keyword filters
        with st.expander("🔍 Keyword Search Filters"):
            st.markdown("**Search for specific keywords in posts:**")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                search_keywords = st.text_input(
                    "Keywords (comma-separated)",
                    placeholder="e.g., docker, kubernetes, homelab",
                    help="Enter keywords separated by commas. Posts matching ANY keyword will be included."
                )
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)  # Spacing
                case_sensitive = st.checkbox("Case Sensitive", value=False, help="Enable case-sensitive matching")
            
            col1, col2 = st.columns(2)
            with col1:
                search_in = st.multiselect(
                    "Search In",
                    ["Title", "Post Text", "Both"],
                    default=["Both"],
                    help="Choose where to search for keywords"
                )
            with col2:
                match_type = st.radio(
                    "Match Type",
                    ["Any keyword (OR)", "All keywords (AND)"],
                    help="Match any keyword or require all keywords"
                )
        
        # Category filters (like GummySearch)
        with st.expander("🏷️ Category Filters (GummySearch Style)"):
            st.markdown("**Filter by Content Categories:**")
            categories = ["All Categories", "Pain Points", "Solution Requests", "Money Talk", "Hot Discussions", "Seeking Alternatives", "General Discussion"]
            
            col1, col2 = st.columns(2)
            with col1:
                selected_categories = st.multiselect(
                    "Select Categories",
                    categories[1:],  # Exclude "All Categories" from multiselect
                    default=[],
                    help="Choose which types of content to include"
                )
            with col2:
                min_confidence = st.slider(
                    "Category Confidence",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.1,
                    step=0.1,
                    help="Minimum confidence for category classification"
                )

        # Action button with better styling
        if st.button("🚀 Start Scraping", use_container_width=True):
            with st.spinner("🔍 Collecting posts from r/{} ...".format(sub_name)):
                df = get_subreddit_posts(
                    reddit, sub_name,
                    filter_type=filter_opt,
                    start=start_d, end=end_d,
                    max_posts=max_posts,
                )

            if not df.empty:
                original_count = len(df)
                # Apply content filters
                if min_score > 0:
                    df = df[df['Score'] >= min_score]
                if min_comments > 0:
                    df = df[df['Total Comments'] >= min_comments]
                if min_awards > 0:
                    df = df[df['Total Awards'] >= min_awards]
                if not include_nsfw:
                    df = df[~df['Over 18']]
                if not include_spoilers:
                    df = df[~df['Spoiler']]
                if oc_only:
                    df = df[df['Is Original Content']]
                # Category filters
                if selected_categories:
                    df = df[df['Category'].isin(selected_categories)]
                if min_confidence > 0:
                    df = df[df['Category Confidence'] >= min_confidence]
                # Keyword filters
                if search_keywords and search_keywords.strip():
                    keywords = [k.strip() for k in search_keywords.split(',') if k.strip()]
                    if keywords:
                        def matches_keywords(row):
                            search_text = ""
                            if "Both" in search_in or not search_in:
                                search_text = f"{row['Title']} {row['Post Text']}"
                            elif "Title" in search_in:
                                search_text = row['Title']
                            elif "Post Text" in search_in:
                                search_text = row['Post Text']
                            if not case_sensitive:
                                search_text = search_text.lower()
                                kws = [k.lower() for k in keywords]
                            else:
                                kws = keywords
                            if match_type == "All keywords (AND)":
                                return all(k in search_text for k in kws)
                            return any(k in search_text for k in kws)
                        df = df[df.apply(matches_keywords, axis=1)]
                        st.info(f"🔍 Filtered by keywords: {', '.join(keywords)}")
                # Persist to session
                st.session_state['posts_df'] = df
                st.session_state['posts_original_count'] = original_count
                st.session_state.pop('batch_summary', None)  # reset previous summary
                st.success("✅ Posts scraped. Scroll down to view analytics and generate AI summary.")

        # Retrieve persisted DF if available (for reruns after button clicks)
        df = st.session_state.get('posts_df')
        if df is not None and not df.empty:
            original_count = st.session_state.get('posts_original_count', len(df))
            if len(df) < original_count:
                st.success(f"✅ Successfully fetched {original_count} posts from r/{sub_name} → {len(df)} posts after filters")
            else:
                st.success(f"✅ Successfully fetched {len(df)} posts from r/{sub_name}")

            # Stats & analytics
            create_stats_dashboard(df)
            create_category_analytics(df)

            # AI Summary Section
            if llm_service and llm_service.is_available() and len(df) > 0:
                st.markdown('<h3 class="section-header">🧠 AI-Powered Market Intelligence</h3>', unsafe_allow_html=True)
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    summary_type = st.selectbox(
                        "Analysis Type:",
                        ["Comprehensive Market Intel", "Quick Overview", "Strategic Deep-Dive"],
                        help="Choose the depth of AI analysis",
                        key="summary_type_select"
                    )
                with col2:
                    st.info(f"💡 Will analyze top {min(len(df), 100)} posts")
                with col3:
                    generate_summary = st.button("🧠 Generate AI Summary", use_container_width=True, type="primary", key="generate_summary_btn")

                # Display existing summary if present
                if 'batch_summary' in st.session_state and st.session_state['batch_summary']:
                    display_batch_summary(st.session_state['batch_summary'])

                if generate_summary:
                    with st.spinner("🤖 Analyzing posts with GPT-4o... This may take 15-30 seconds."): 
                        try:
                            estimated_cost = 0.75 if len(df) <= 50 else 1.50
                            can_proceed, message = llm_service.cost_tracker.check_budget(estimated_cost)
                            if not can_proceed:
                                st.error(f"❌ {message}")
                                st.info("💡 Tip: Wait for next month or increase your MONTHLY_BUDGET_INR in secrets.toml")
                            else:
                                if "Warning" in message:
                                    st.warning(message)
                                batch_summary = llm_service.summarize_post_batch(df, summary_type)
                                st.session_state['batch_summary'] = batch_summary
                                display_batch_summary(batch_summary)
                        except Exception as e:
                            st.error(f"❌ Error generating summary: {e}")
                            st.info("💡 Check your Azure OpenAI credentials in secrets.toml")

            # Charts section
            if show_charts and len(df) > 0:
                st.markdown('<h3 class="section-header">📊 Analytics</h3>', unsafe_allow_html=True)
                chart_col1, chart_col2 = st.columns(2)
                with chart_col1:
                    fig_score = px.histogram(
                        df, x='Score', nbins=20,
                        title="Score Distribution",
                        color_discrete_sequence=['#FF4B4B']
                    )
                    fig_score.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='white')
                    st.plotly_chart(fig_score, use_container_width=True)
                with chart_col2:
                    df['Date'] = pd.to_datetime(df['Created UTC']).dt.date
                    posts_per_day = df.groupby('Date').size().reset_index(name='Posts')
                    fig_time = px.line(posts_per_day, x='Date', y='Posts', title="Posts Over Time", color_discrete_sequence=['#00D4FF'])
                    fig_time.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='white')
                    st.plotly_chart(fig_time, use_container_width=True)

            # Data table & downloads
            st.markdown('<h3 class="section-header">📋 Post Data</h3>', unsafe_allow_html=True)
            st.info("💡 **Tip:** 'Post Text' column contains the full text content of each post. Use the column selector below to customize your view.")
            with st.expander("🔧 Customize Columns", expanded=False):
                all_columns = df.columns.tolist()
                default_columns = ['Title', 'Post Text', 'Category', 'Author', 'Score', 'Total Comments', 'Created UTC', 'Permalink']
                selected_columns = st.multiselect(
                    "Select columns to display:",
                    all_columns,
                    default=[col for col in default_columns if col in all_columns],
                    key="columns_multiselect"
                )
            display_df = df[selected_columns] if selected_columns else df
            if 'Category' in display_df.columns:
                styled_df = display_df.copy()
                def style_category(val):
                    color = get_category_color(val)
                    return f"background-color: {color}20; color: {color}; font-weight: bold;"
                styled_df = styled_df.style.applymap(style_category, subset=['Category'])
                st.dataframe(styled_df, use_container_width=True, height=400)
            else:
                st.dataframe(display_df, use_container_width=True, height=400)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.download_button(
                    "📥 Download Full CSV",
                    df.to_csv(index=False).encode(),
                    f"{sub_name}_posts_full.csv",
                    "text/csv",
                    use_container_width=True
                )
            with col2:
                if selected_columns:
                    st.download_button(
                        "📥 Download Selected CSV",
                        display_df.to_csv(index=False).encode(),
                        f"{sub_name}_posts_selected.csv",
                        "text/csv",
                        use_container_width=True
                    )
            with col3:
                st.download_button(
                    "📥 Download JSON",
                    df.to_json(orient='records', date_format='iso').encode(),
                    f"{sub_name}_posts.json",
                    "application/json",
                    use_container_width=True
                )
        else:
            # No posts persisted in session
            st.info("ℹ️ Use 'Start Scraping' to fetch posts.")

    # ── Single-thread mode ─────────────────────────────────────────────────────
    else:
        st.markdown('<h2 class="section-header">🔗 Post URL Scraper</h2>', unsafe_allow_html=True)

        # URL input with validation
        url = st.text_input(
            "**Reddit Post URL**",
            placeholder="https://www.reddit.com/r/subreddit/comments/post_id/title/",
            help="Enter the full URL of the Reddit post you want to scrape"
        )
        
        # Comment analysis options
        with st.expander("🔧 Comment Analysis Options"):
            col1, col2 = st.columns(2)
            with col1:
                include_deleted = st.checkbox("Include Deleted Comments", value=False)
                sort_comments = st.selectbox("Sort Comments By", ["Score", "Date", "Author"])
            with col2:
                min_comment_score = st.number_input("Min Comment Score", value=-1000)
                max_comments = st.number_input("Max Comments", value=1000, min_value=1)
        
        # Keyword filter for comments
        with st.expander("🔍 Comment Keyword Filter"):
            comment_keywords = st.text_input(
                "Filter comments by keywords (comma-separated)",
                placeholder="e.g., solution, tutorial, help",
                help="Only show comments containing these keywords"
            )
            comment_case_sensitive = st.checkbox("Case Sensitive (Comments)", value=False)

        # Persisted single post data (if previously scraped)
        persisted_post_df = st.session_state.get('single_post_df')
        persisted_cmt_df = st.session_state.get('single_comments_df')
        persisted_summary = st.session_state.get('single_post_summary')

        if st.button("🚀 Scrape Post & Comments", use_container_width=True):
            if url:
                with st.spinner("📥 Fetching submission & comments..."):
                    post_df, cmt_df = get_post_by_url(reddit, url)
                if not post_df.empty:
                    st.session_state['single_post_df'] = post_df
                    st.session_state['single_comments_df'] = cmt_df
                    st.session_state.pop('single_post_summary', None)
                    persisted_post_df, persisted_cmt_df = post_df, cmt_df
                else:
                    st.error("❌ Failed to fetch post data. Please check the URL and try again.")
            else:
                st.warning("⚠️ Please enter a valid Reddit post URL.")

        # Use persisted data if available
        if persisted_post_df is not None and not persisted_post_df.empty:
            post_df = persisted_post_df
            cmt_df = persisted_cmt_df if persisted_cmt_df is not None else pd.DataFrame()

            if not post_df.empty:
                    # Post details section
                    st.markdown('<h3 class="section-header">📄 Post Details</h3>', unsafe_allow_html=True)
                    
                    # Display key metrics for the post
                    if len(post_df) > 0:
                        post = post_df.iloc[0]
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("👍 Score", int(post['Score']))
                        with col2:
                            st.metric("💬 Comments", int(post['Total Comments']))
                        with col3:
                            st.metric("🏆 Awards", int(post['Total Awards']))
                        with col4:
                            ratio = post['Up-vote Ratio']
                            st.metric("📈 Upvote Ratio", f"{ratio:.1%}")
                    
                    # Post data table
                    st.dataframe(post_df, use_container_width=True)
                    
                    # AI Summary Section for Single Post
                    if llm_service and llm_service.is_available() and not cmt_df.empty:
                        st.markdown("---")
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown("### 🧠 AI-Powered Post Analysis")
                            st.info("💡 Get comprehensive insights from the post and its comments using GPT-4o")
                        with col2:
                            generate_post_summary = st.button("🧠 Analyze Post", use_container_width=True, type="primary")
                        
                        # Display existing summary if present
                        if persisted_summary:
                            display_single_post_summary(persisted_summary)

                        if generate_post_summary:
                            with st.spinner("🤖 Analyzing post and comments... This may take 5-10 seconds."):
                                try:
                                    post_series = post_df.iloc[0]
                                    post_summary = llm_service.summarize_single_post(post_series, cmt_df)
                                    st.session_state['single_post_summary'] = post_summary
                                    display_single_post_summary(post_summary)
                                except Exception as e:
                                    st.error(f"❌ Error generating summary: {e}")
                                    st.info("💡 Check your Azure OpenAI credentials in secrets.toml")

                    # Comments section
                    if not cmt_df.empty:
                        # Filter comments
                        filtered_cmt_df = cmt_df.copy()
                        
                        if min_comment_score > -1000:
                            filtered_cmt_df = filtered_cmt_df[filtered_cmt_df['Score'] >= min_comment_score]
                        
                        if not include_deleted:
                            filtered_cmt_df = filtered_cmt_df[
                                ~filtered_cmt_df['Comment Text'].isin(['[deleted]', '[removed]'])
                            ]
                        
                        # Sort comments
                        if sort_comments == "Score":
                            filtered_cmt_df = filtered_cmt_df.sort_values('Score', ascending=False)
                        elif sort_comments == "Date":
                            filtered_cmt_df = filtered_cmt_df.sort_values('Created UTC', ascending=False)
                        elif sort_comments == "Author":
                            filtered_cmt_df = filtered_cmt_df.sort_values('Author')
                        
                        # Limit comments
                        if len(filtered_cmt_df) > max_comments:
                            filtered_cmt_df = filtered_cmt_df.head(max_comments)
                        
                        # Apply keyword filter to comments
                        if comment_keywords and comment_keywords.strip():
                            keywords = [k.strip() for k in comment_keywords.split(',') if k.strip()]
                            if keywords:
                                def comment_matches_keywords(text):
                                    search_text = str(text)
                                    if not comment_case_sensitive:
                                        search_text = search_text.lower()
                                        keywords_to_match = [k.lower() for k in keywords]
                                    else:
                                        keywords_to_match = keywords
                                    return any(keyword in search_text for keyword in keywords_to_match)
                                
                                original_count = len(filtered_cmt_df)
                                filtered_cmt_df = filtered_cmt_df[filtered_cmt_df['Comment Text'].apply(comment_matches_keywords)]
                                st.info(f"🔍 Filtered comments by keywords: {', '.join(keywords)} ({len(filtered_cmt_df)} of {original_count} comments match)")
                        
                        st.markdown(f'<h3 class="section-header">💬 Comments ({len(filtered_cmt_df)} of {len(cmt_df)})</h3>', unsafe_allow_html=True)
                        
                        # Comment analytics
                        if show_charts and len(filtered_cmt_df) > 0:
                            chart_col1, chart_col2 = st.columns(2)
                            
                            with chart_col1:
                                # Comment score distribution
                                fig_comments = px.histogram(
                                    filtered_cmt_df, x='Score', nbins=20,
                                    title="Comment Score Distribution",
                                    color_discrete_sequence=['#00D4FF']
                                )
                                fig_comments.update_layout(
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    font_color='white'
                                )
                                st.plotly_chart(fig_comments, use_container_width=True)
                            
                            with chart_col2:
                                # Comments over time
                                filtered_cmt_df['Date'] = pd.to_datetime(filtered_cmt_df['Created UTC']).dt.date
                                comments_per_day = filtered_cmt_df.groupby('Date').size().reset_index(name='Comments')
                                fig_cmt_time = px.line(
                                    comments_per_day, x='Date', y='Comments',
                                    title="Comments Over Time",
                                    color_discrete_sequence=['#00FF88']
                                )
                                fig_cmt_time.update_layout(
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    font_color='white'
                                )
                                st.plotly_chart(fig_cmt_time, use_container_width=True)
                        
                        # Comments data table
                        st.dataframe(filtered_cmt_df, use_container_width=True, height=400)
                    else:
                        st.info("No comments found for this post.")

                    # Enhanced download section
                    st.markdown('<h3 class="section-header">📥 Download Options</h3>', unsafe_allow_html=True)
                    col1, col2, col3, col4, col5 = st.columns(5)
                    
                    with col1:
                        st.download_button(
                            "📄 Post CSV",
                            post_df.to_csv(index=False).encode(),
                            "post_details.csv",
                            "text/csv",
                            use_container_width=True
                        )
                    with col2:
                        if not cmt_df.empty:
                            st.download_button(
                                "💬 Comments CSV",
                                filtered_cmt_df.to_csv(index=False).encode(),
                                "comments.csv",
                                "text/csv",
                                use_container_width=True
                            )
                    with col3:
                        if st.button("📄 Copy Post JSON", use_container_width=True):
                            st.code(post_df.to_json(orient='records', date_format='iso', indent=2), language='json')
                            st.success("✅ Post JSON displayed above - you can copy it from the code block")
                    with col4:
                        if not cmt_df.empty:
                            if st.button("💬 Copy Comments JSON", use_container_width=True):
                                st.code(filtered_cmt_df.to_json(orient='records', date_format='iso', indent=2), language='json')
                                st.success("✅ Comments JSON displayed above - you can copy it from the code block")
                    with col5:
                        if st.button("🔗 Copy Combined JSON", use_container_width=True):
                            # Extract specific fields from post
                            post_data = {
                                "ID": post_df.iloc[0]["ID"] if "ID" in post_df.columns else "",
                                "Title": post_df.iloc[0]["Title"] if "Title" in post_df.columns else "",
                                "Post Text": post_df.iloc[0]["Post Text"] if "Post Text" in post_df.columns else "",
                                "Subreddit": post_df.iloc[0]["Subreddit"] if "Subreddit" in post_df.columns else "",
                                "Author": post_df.iloc[0]["Author"] if "Author" in post_df.columns else "",
                                "Permalink": post_df.iloc[0]["Permalink"] if "Permalink" in post_df.columns else ""
                            }
                            
                            # Extract specific fields from comments
                            comments_data = []
                            if not cmt_df.empty:
                                for _, comment in filtered_cmt_df.iterrows():
                                    comment_data = {
                                        "Comment Text": comment["Comment Text"] if "Comment Text" in comment else "",
                                        "Author": comment["Author"] if "Author" in comment else "",
                                        "Score": comment["Score"] if "Score" in comment else 0
                                    }
                                    comments_data.append(comment_data)
                            
                            # Combine into single structure
                            combined_data = {
                                "post": post_data,
                                "comments": comments_data
                            }
                            
                            import json
                            st.code(json.dumps(combined_data, indent=2), language='json')
                            st.success("✅ Combined JSON displayed above - you can copy it from the code block")
        elif url:
            st.info("🔎 Click 'Scrape Post & Comments' to fetch the post.")

if __name__ == "__main__":
    main()
