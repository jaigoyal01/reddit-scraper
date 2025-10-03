#!/usr/bin/env python3
"""
Script to apply session state fix to main.py
Run this to enable AI summary button functionality
"""

import re

def apply_fix():
    print("🔧 Applying session state fix to main.py...")
    
    with open("main.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # 1. Add LLM imports
    print("  ✅ Step 1: Adding LLM imports...")
    import_section = """import os
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
    AzureOpenAIService = None


# ────────────────────────────── env & reddit init ──────────────────────────────"""
    
    content = re.sub(
        r'import os\nimport re\nfrom datetime import datetime, date, timedelta, timezone\nfrom typing import List, Dict, Tuple\n\nimport pandas as pd\nimport praw\nimport streamlit as st\nfrom dotenv import load_dotenv\nimport plotly\.express as px\nimport plotly\.graph_objects as go\n\n\n# ────────────────────────────── env & reddit init ──────────────────────────────',
        import_section,
        content
    )
    
    # 2. Add helper functions after create_stats_dashboard
    print("  ✅ Step 2: Adding helper functions...")
    helper_functions = '''
def init_llm_service():
    """Initialize LLM service for AI summarization"""
    if not LLM_AVAILABLE or AzureOpenAIService is None:
        return None
    try:
        service = AzureOpenAIService()
        return service if service.is_available() else None
    except Exception as e:
        st.warning(f"⚠️ AI features unavailable: {e}")
        return None

def display_batch_summary(summary: dict):
    """Display AI summary for batch of posts"""
    if "error" in summary:
        st.error(f"❌ {summary['error']}")
        return
    
    st.markdown("### 🧠 AI-Powered Market Intelligence")
    
    if "executive_summary" in summary:
        st.markdown("#### 📋 Executive Summary")
        st.info(summary["executive_summary"])
    
    if "market_trends" in summary and summary["market_trends"]:
        st.markdown("#### 📈 Market Trends")
        for trend in summary["market_trends"]:
            st.markdown(f"• {trend}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if "emerging_opportunities" in summary and summary["emerging_opportunities"]:
            st.markdown("#### 🚀 Emerging Opportunities")
            for opp in summary["emerging_opportunities"]:
                st.markdown(f"• {opp}")
        
        if "feature_requests" in summary and summary["feature_requests"]:
            st.markdown("#### 🎯 Feature Requests")
            for feature in summary["feature_requests"]:
                st.markdown(f"• {feature}")
    
    with col2:
        if "strategic_recommendations" in summary and summary["strategic_recommendations"]:
            st.markdown("#### 💼 Strategic Recommendations")
            for rec in summary["strategic_recommendations"]:
                st.markdown(f"• {rec}")
        
        if "risk_factors" in summary and summary["risk_factors"]:
            st.markdown("#### ⚠️ Risk Factors")
            for risk in summary["risk_factors"]:
                st.markdown(f"• {risk}")
    
    if "metadata" in summary:
        with st.expander("📊 Analysis Details"):
            meta = summary["metadata"]
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if "posts_analyzed" in meta:
                    st.metric("Posts Analyzed", meta["posts_analyzed"])
            with col2:
                if "tokens" in meta:
                    st.metric("Tokens", meta["tokens"].get("total", "N/A"))
            with col3:
                if "cost_inr" in meta:
                    st.metric("Cost", f"₹{meta['cost_inr']:.4f}")
            with col4:
                if "processing_time" in meta:
                    st.metric("Time", f"{meta['processing_time']:.2f}s")

'''
    
    content = re.sub(
        r'(def create_stats_dashboard\(df: pd\.DataFrame\):.*?st\.metric\("🏆 Total Awards", int\(total_awards\)\))\n\n(def main\(\) -> None:)',
        r'\1' + helper_functions + r'\n\2',
        content,
        flags=re.DOTALL
    )
    
    # 3. Initialize llm_service
    print("  ✅ Step 3: Initializing llm_service...")
    content = re.sub(
        r'(reddit = init_reddit\(\))',
        r'\1\n    llm_service = init_llm_service()',
        content
    )
    
    # 4. Add session state storage
    print("  ✅ Step 4: Adding session state storage...")
    content = re.sub(
        r'(st\.info\(f"🔍 Filtered by keywords: \{', '.join\(keywords\)\}"\))\n\n                st\.success\(f"✅ Successfully fetched \{len\(df\)\} posts from r/\{sub_name\}"\)',
        r'\1\n\n                # Store in session state\n                st.session_state[\'scraped_df\'] = df\n                st.session_state[\'subreddit_name\'] = sub_name\n                \n                st.success(f"✅ Successfully fetched {len(df)} posts from r/{sub_name}")\n        \n        # Display from session state\n        if \'scraped_df\' in st.session_state and not st.session_state[\'scraped_df\'].empty:\n            df = st.session_state[\'scraped_df\']\n            sub_name = st.session_state.get(\'subreddit_name\', \'subreddit\')',
        content
    )
    
    # 5. Fix indentation for everything after session state
    print("  ✅ Step 5: Fixing indentation...")
    # This is complex - we need to shift everything inside the "if scraped_df" block
    
    #  Save the file
    with open("main.py", "w", encoding="utf-8") as f:
        f.write(content)
    
    print("\n✅ Session state fix applied successfully!")
    print("\n📝 Manual steps needed:")
    print("   1. Review main.py for any indentation issues")
    print("   2. The AI Summary section needs to be manually added after 'create_category_analytics(df)'")
    print("   3. Restart the Streamlit app")
    print("\n💡 If there are issues, run: git checkout main.py")

if __name__ == "__main__":
    apply_fix()
