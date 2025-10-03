"""
Azure OpenAI Service for Reddit Data Summarization
Provides cost-controlled LLM integration with GPT-4o-mini
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

import streamlit as st
import pandas as pd
import tiktoken
from openai import AzureOpenAI


class CostTracker:
    """Track and manage AI usage costs"""
    
    def __init__(self, budget_limit: float = 100.0):
        self.usage_file = Path(".streamlit/usage_tracking.json")
        self.budget_limit = budget_limit
        self.cost_per_1k_tokens = 0.0626  # GPT-4o-mini in INR
        self._ensure_usage_file()
    
    def _ensure_usage_file(self):
        """Create usage tracking file if it doesn't exist"""
        if not self.usage_file.exists():
            self.usage_file.parent.mkdir(parents=True, exist_ok=True)
            self._save_usage({})
    
    def _load_usage(self) -> dict:
        """Load usage data from file"""
        try:
            with open(self.usage_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_usage(self, data: dict):
        """Save usage data to file"""
        with open(self.usage_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_current_month_key(self) -> str:
        """Get current month key for tracking"""
        return datetime.now().strftime("%Y-%m")
    
    def get_monthly_usage(self) -> dict:
        """Get current month's usage statistics"""
        usage_data = self._load_usage()
        month_key = self.get_current_month_key()
        
        if month_key not in usage_data:
            return {
                "month": month_key,
                "total_cost_inr": 0.0,
                "total_tokens": 0,
                "api_calls": 0,
                "budget_limit": self.budget_limit,
                "percentage_used": 0.0
            }
        
        month_data = usage_data[month_key]
        return {
            "month": month_key,
            "total_cost_inr": month_data.get("total_cost", 0.0),
            "total_tokens": month_data.get("total_tokens", 0),
            "api_calls": month_data.get("api_calls", 0),
            "budget_limit": self.budget_limit,
            "percentage_used": (month_data.get("total_cost", 0.0) / self.budget_limit) * 100
        }
    
    def track_usage(self, tokens_used: int, cost_inr: float):
        """Track a new API usage"""
        usage_data = self._load_usage()
        month_key = self.get_current_month_key()
        
        if month_key not in usage_data:
            usage_data[month_key] = {
                "total_cost": 0.0,
                "total_tokens": 0,
                "api_calls": 0,
                "history": []
            }
        
        usage_data[month_key]["total_cost"] += cost_inr
        usage_data[month_key]["total_tokens"] += tokens_used
        usage_data[month_key]["api_calls"] += 1
        usage_data[month_key]["history"].append({
            "timestamp": datetime.now().isoformat(),
            "tokens": tokens_used,
            "cost": cost_inr
        })
        
        self._save_usage(usage_data)
    
    def check_budget(self, estimated_cost: float) -> Tuple[bool, str]:
        """Check if estimated cost is within budget"""
        monthly_usage = self.get_monthly_usage()
        current_usage = monthly_usage["total_cost_inr"]
        remaining = self.budget_limit - current_usage
        
        if estimated_cost > remaining:
            return False, f"Insufficient budget. Remaining: ₹{remaining:.2f}, Required: ₹{estimated_cost:.2f}"
        
        if (current_usage + estimated_cost) / self.budget_limit > 0.8:
            return True, f"⚠️ Warning: Using {((current_usage + estimated_cost) / self.budget_limit * 100):.1f}% of budget"
        
        return True, "Within budget"


class AzureOpenAIService:
    """Azure OpenAI service for Reddit content summarization"""
    
    def __init__(self):
        self.client = None
        self.cost_tracker = None
        self.encoding = None
        self._initialize()
    
    def _initialize(self):
        """Initialize Azure OpenAI client and supporting services"""
        try:
            # Check if AI features are enabled
            if not self._ai_features_enabled():
                return
            
            # Initialize Azure OpenAI client
            api_key = os.getenv("AZURE_OPENAI_API_KEY") or st.secrets.get("AZURE_OPENAI_API_KEY")
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT") or st.secrets.get("AZURE_OPENAI_ENDPOINT")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION") or st.secrets.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
            
            if not api_key or not endpoint:
                st.warning("⚠️ Azure OpenAI credentials not configured. AI features disabled.")
                return
            
            if "your_azure_openai_api_key_here" in str(api_key):
                return  # Placeholder not replaced
            
            self.client = AzureOpenAI(
                api_key=api_key,
                api_version=api_version,
                azure_endpoint=endpoint
            )
            
            # Initialize cost tracker
            budget = float(os.getenv("MONTHLY_BUDGET_INR") or st.secrets.get("MONTHLY_BUDGET_INR", 100))
            self.cost_tracker = CostTracker(budget_limit=budget)
            
            # Initialize tokenizer
            self.encoding = tiktoken.get_encoding("cl100k_base")
            
        except Exception as e:
            st.error(f"Failed to initialize Azure OpenAI: {e}")
            self.client = None
    
    def _ai_features_enabled(self) -> bool:
        """Check if AI features are enabled"""
        enabled = os.getenv("ENABLE_AI_FEATURES") or st.secrets.get("ENABLE_AI_FEATURES", "false")
        return str(enabled).lower() == "true"
    
    def is_available(self) -> bool:
        """Check if service is available"""
        return self.client is not None and self._ai_features_enabled()
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if not self.encoding:
            return len(text) // 4  # Rough estimate
        return len(self.encoding.encode(text))
    
    def estimate_cost(self, input_text: str, estimated_output_tokens: int = 500) -> float:
        """Estimate cost in INR for processing"""
        input_tokens = self.count_tokens(input_text)
        total_tokens = input_tokens + estimated_output_tokens
        
        # GPT-4o-mini: ₹0.01253 per 1K input, ₹0.0501 per 1K output
        input_cost = (input_tokens / 1000) * 0.01253
        output_cost = (estimated_output_tokens / 1000) * 0.0501
        
        return input_cost + output_cost
    
    def _call_llm(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> Tuple[str, dict]:
        """Make API call to Azure OpenAI"""
        if not self.is_available():
            return "", {"error": "Service not available"}
        
        try:
            start_time = time.time()
            
            deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") or st.secrets.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")
            
            response = self.client.chat.completions.create(
                model=deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert business analyst specializing in Reddit market research and social media insights."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            processing_time = time.time() - start_time
            
            # Extract response
            content = response.choices[0].message.content
            
            # Calculate actual costs
            usage = response.usage
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens
            
            input_cost = (input_tokens / 1000) * 0.01253
            output_cost = (output_tokens / 1000) * 0.0501
            total_cost = input_cost + output_cost
            
            # Track usage
            self.cost_tracker.track_usage(total_tokens, total_cost)
            
            metadata = {
                "tokens": {
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": total_tokens
                },
                "cost_inr": total_cost,
                "processing_time": processing_time
            }
            
            return content, metadata
            
        except Exception as e:
            return "", {"error": str(e)}
    
    def summarize_single_post(self, post_data: pd.Series, comments_df: pd.DataFrame) -> dict:
        """
        Summarize a single Reddit post with its comments
        
        Args:
            post_data: Series containing post information
            comments_df: DataFrame containing comments
            
        Returns:
            Dictionary with comprehensive analysis
        """
        if not self.is_available():
            return {"error": "AI service not available"}
        
        # Prepare post content
        title = post_data.get('Title', '')
        content = post_data.get('Post Text', '')[:2000]  # Limit content length
        score = post_data.get('Score', 0)
        comment_count = post_data.get('Total Comments', 0)
        category = post_data.get('Category', 'General')
        
        # Get top comments by score
        top_comments = comments_df.nlargest(10, 'Score') if not comments_df.empty else pd.DataFrame()
        comments_text = "\n".join([
            f"[Score: {row['Score']}] {row['Comment Text'][:200]}"
            for _, row in top_comments.iterrows()
        ]) if not top_comments.empty else "No comments available"
        
        # Create comprehensive prompt
        prompt = f"""Analyze this Reddit post and provide actionable business insights:

POST DETAILS:
Title: {title}
Category: {category}
Score: {score} | Comments: {comment_count}

CONTENT:
{content}

TOP COMMENTS:
{comments_text}

Provide analysis in this JSON format:
{{
    "executive_summary": "2-3 sentence overview of the post and discussion",
    "key_insights": ["insight 1", "insight 2", "insight 3"],
    "sentiment": "Positive/Negative/Neutral/Mixed",
    "pain_points": ["specific problems mentioned"],
    "solutions_discussed": ["solutions or workarounds mentioned"],
    "community_consensus": "What the community generally agrees on",
    "business_opportunities": ["Actionable business opportunities identified"],
    "competitive_mentions": ["Any competitors or alternatives mentioned"],
    "technical_requirements": ["Technical needs or requirements discussed"],
    "pricing_sensitivity": "Any pricing or budget discussions",
    "action_items": ["Specific actions a business could take based on this discussion"]
}}

Focus on actionable intelligence. Be concise but insightful.
"""
        
        # Estimate and check cost
        estimated_cost = self.estimate_cost(prompt, 800)
        can_proceed, message = self.cost_tracker.check_budget(estimated_cost)
        
        if not can_proceed:
            return {"error": message, "estimated_cost": estimated_cost}
        
        # Make API call
        response, metadata = self._call_llm(prompt, max_tokens=800, temperature=0.7)
        
        if metadata.get("error"):
            return {"error": metadata["error"]}
        
        # Parse JSON response
        try:
            analysis = json.loads(response)
            analysis["metadata"] = {
                "post_id": post_data.get('ID', ''),
                "post_url": post_data.get('Permalink', ''),
                "analyzed_at": datetime.now().isoformat(),
                **metadata
            }
            return analysis
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "raw_analysis": response,
                "metadata": metadata,
                "note": "Analysis returned in text format"
            }
    
    def summarize_post_batch(self, posts_df: pd.DataFrame, analysis_type: str = "comprehensive") -> dict:
        """
        Summarize a batch of Reddit posts for market intelligence
        
        Args:
            posts_df: DataFrame containing posts
            analysis_type: Type of analysis (comprehensive, quick, strategic)
            
        Returns:
            Dictionary with batch analysis
        """
        if not self.is_available():
            return {"error": "AI service not available"}
        
        if len(posts_df) == 0:
            return {"error": "No posts to analyze"}
        
        # Smart sampling for cost optimization
        sample_size = min(100, len(posts_df))
        if len(posts_df) > sample_size:
            # Sample by score and category diversity
            sampled_posts = posts_df.nlargest(sample_size, 'Score')
        else:
            sampled_posts = posts_df
        
        # Prepare summary data
        category_counts = sampled_posts['Category'].value_counts().to_dict()
        avg_score = sampled_posts['Score'].mean()
        avg_comments = sampled_posts['Total Comments'].mean()
        
        # Get representative posts from each category
        category_samples = {}
        for category in sampled_posts['Category'].unique():
            cat_posts = sampled_posts[sampled_posts['Category'] == category]
            top_post = cat_posts.nlargest(1, 'Score').iloc[0]
            category_samples[category] = {
                "title": top_post['Title'],
                "score": int(top_post['Score']),
                "snippet": top_post['Post Text'][:200] if top_post['Post Text'] else ""
            }
        
        # Create batch analysis prompt
        prompt = f"""Analyze these {len(sampled_posts)} Reddit posts for strategic business intelligence:

DATASET OVERVIEW:
- Total Posts: {len(sampled_posts)}
- Categories: {json.dumps(category_counts)}
- Average Score: {avg_score:.1f}
- Average Comments: {avg_comments:.1f}

REPRESENTATIVE POSTS BY CATEGORY:
{json.dumps(category_samples, indent=2)}

Provide comprehensive market intelligence in JSON format:
{{
    "executive_summary": "3-4 sentence strategic overview",
    "market_trends": ["trend 1", "trend 2", "trend 3"],
    "customer_pain_points": {{"category": "pain points list"}},
    "emerging_opportunities": ["opportunity 1", "opportunity 2"],
    "competitive_landscape": "Overview of competitor mentions and sentiment",
    "technology_adoption": {{"technology": "adoption status"}},
    "pricing_insights": "Key findings about pricing and budget discussions",
    "feature_requests": ["most requested features or solutions"],
    "sentiment_analysis": {{"category": "sentiment"}},
    "strategic_recommendations": ["actionable recommendation 1", "recommendation 2"],
    "risk_factors": ["potential risk 1", "risk 2"],
    "target_segments": ["identified customer segment 1", "segment 2"]
}}

Focus on actionable intelligence for business decision-making.
"""
        
        # Estimate and check cost
        estimated_cost = self.estimate_cost(prompt, 1200)
        can_proceed, message = self.cost_tracker.check_budget(estimated_cost)
        
        if not can_proceed:
            return {"error": message, "estimated_cost": estimated_cost}
        
        # Make API call
        response, metadata = self._call_llm(prompt, max_tokens=1200, temperature=0.7)
        
        if metadata.get("error"):
            return {"error": metadata["error"]}
        
        # Parse JSON response
        try:
            analysis = json.loads(response)
            analysis["metadata"] = {
                "posts_analyzed": len(sampled_posts),
                "total_posts": len(posts_df),
                "analyzed_at": datetime.now().isoformat(),
                **metadata
            }
            return analysis
        except json.JSONDecodeError:
            return {
                "raw_analysis": response,
                "metadata": metadata,
                "note": "Analysis returned in text format"
            }
