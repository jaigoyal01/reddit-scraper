"""
Azure OpenAI Service for Reddit Data Summarization
Provides cost-controlled LLM integration with GPT-4o
"""

import os
import json
import time
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Attempt to import streamlit, but allow this module to be imported in non-Streamlit contexts
try:
    import streamlit as st  # type: ignore
except ImportError:  # Fallback stub so tests/imports won't fail
    class _StreamlitStub:  # minimal attributes used in this file
        def warning(self, *args, **kwargs): pass
        def error(self, *args, **kwargs): pass
        def success(self, *args, **kwargs): pass
        def write(self, *args, **kwargs): pass
    st = _StreamlitStub()  # type: ignore
import pandas as pd
import tiktoken
from openai import AzureOpenAI


class CostTracker:
    """Track and manage AI usage costs"""
    
    def __init__(self, budget_limit: float = 100.0):
        self.usage_file = Path(".streamlit/usage_tracking.json")
        self.budget_limit = budget_limit
        self.cost_per_1k_tokens = 0.84  # GPT-4o blended rate in INR (approx)
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
        # Allow configurable output token ceilings via environment variables.
        # Upgrade defaults for higher quality output.
        self.single_post_max_output_tokens_env = int(os.getenv("SINGLE_POST_MAX_OUTPUT_TOKENS", "1600") or 1600)
        self.batch_max_output_tokens_env = int(os.getenv("BATCH_MAX_OUTPUT_TOKENS", "2400") or 2400)
        # Option to ignore budget constraints for quality-focused runs
        self.ignore_budget = os.getenv("IGNORE_BUDGET", "1") == "1"
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
        
        # GPT-4o: ₹0.42 per 1K input, ₹1.26 per 1K output
        input_cost = (input_tokens / 1000) * 0.42
        output_cost = (estimated_output_tokens / 1000) * 1.26
        
        return input_cost + output_cost
    
    def _call_llm(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> Tuple[str, dict]:
        """Make API call to Azure OpenAI"""
        if not self.is_available():
            return "", {"error": "Service not available"}
        
        try:
            start_time = time.time()
            
            deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") or st.secrets.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
            
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
            
            input_cost = (input_tokens / 1000) * 0.42
            output_cost = (output_tokens / 1000) * 1.26
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

    # -------------------------- Sanitization Helpers --------------------------
    @staticmethod
    def _sanitize_text(text: str) -> Tuple[str, bool]:
        """Lightly sanitize potentially sensitive content to reduce content filter triggers.
        Returns sanitized text and flag indicating if any change occurred.
        NOTE: This does NOT guarantee passing all filters; it only redacts obvious high‑risk tokens.
        Extend SENSITIVE_TERMS with project-specific patterns if needed.
        """
        if not text:
            return text, False
        # Generic placeholders (avoid listing explicit disallowed terms)
        SENSITIVE_TERMS = [
            r"(?i)\b(slur_[a-z0-9_]+)\b",  # placeholder pattern developers can replace
            r"(?i)\bhate\s+speech\b",
        ]
        redacted = text
        changed = False
        for pat in SENSITIVE_TERMS:
            new_redacted, n = re.subn(pat, "[REDACTED]", redacted)
            if n > 0:
                changed = True
                redacted = new_redacted
        # Collapse excessive repetition (previous pattern was too aggressive and matched normal text granularly)
        # New approach: only collapse when a word/phrase (>=4 chars) repeats 4+ times consecutively with optional spaces.
        # Example caught: "spam spam spam spam" or "ERRORERRORERRORERROR" but not normal prose.
        repetition_pattern = re.compile(r"(\b\w.{3,}?\b)(?:\s+\1){3,}", re.IGNORECASE)
        def _collapse(m):
            return f"[REPETITIVE_CONTENT:{m.group(1)[:20]}]"
        redacted_compact = repetition_pattern.sub(_collapse, redacted)
        if redacted_compact != redacted:
            changed = True
            redacted = redacted_compact
        # Hard truncate to a generous upper bound to reduce surface area
        MAX_LEN = 8000
        if len(redacted) > MAX_LEN:
            redacted = redacted[:MAX_LEN] + "\n[TRUNCATED]"
            changed = True
        return redacted, changed

    @staticmethod
    def _build_fallback_batch_prompt(posts_df: pd.DataFrame) -> str:
        """Build a minimal, metadata‑only prompt if original content triggered filters."""
        sample_rows = posts_df.head(30)[['Title', 'Category', 'Score', 'Total Comments']].to_dict(orient='records')
        return (
            "The original prompt content was redacted due to safety filtering. "
            "Using ONLY the structured metadata below (do not infer hidden content), produce high‑level, neutral, business insights as JSON with keys: "
            "executive_summary, market_trends, emerging_opportunities, strategic_recommendations, risk_factors.\n\n"
            f"POST_METADATA_JSON = {json.dumps(sample_rows, ensure_ascii=False)}"
        )

    @staticmethod
    def _build_fallback_single_prompt(post_data: pd.Series) -> str:
        meta = {
            "title": post_data.get('Title', ''),
            "category": post_data.get('Category', ''),
            "score": int(post_data.get('Score', 0)),
            "total_comments": int(post_data.get('Total Comments', 0))
        }
        return (
            "Original post body/comments were redacted for safety. Based ONLY on this metadata, "
            "produce JSON with keys: executive_summary, key_insights, sentiment, action_items (array). Be conservative.\n"
            f"POST_METADATA_JSON = {json.dumps(meta, ensure_ascii=False)}"
        )
    
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

        # Prepare post content (no manual truncation per user request)
        title = post_data.get('Title', '')
        raw_content = post_data.get('Post Text', '')
        content, content_sanitized = self._sanitize_text(raw_content)
        score = post_data.get('Score', 0)
        comment_count = post_data.get('Total Comments', 0)
        category = post_data.get('Category', 'General')

        # Top 40 comments by score, first 1500 chars each
        top_comments = comments_df.nlargest(40, 'Score') if not comments_df.empty else pd.DataFrame()
        comments_text_raw = "\n".join([
            f"[Score: {row['Score']}] {str(row['Comment Text'])[:1500]}" for _, row in top_comments.iterrows()
        ]) if not top_comments.empty else "No comments available"
        comments_text, comments_sanitized = self._sanitize_text(comments_text_raw)

        # User-specified prompt for three-section structured markdown output
        prompt = f"""You are analyzing a Reddit thread. Your task is to produce three clear sections in a structured way.\n\nSOURCE POST TITLE: {title}\nCATEGORY: {category}\nSCORE: {score} | TOTAL_COMMENTS: {comment_count}\n\nORIGINAL POST BODY (sanitized):\n{content}\n\nTOP COMMENTS (sanitized, score-tagged):\n{comments_text}\n\nFollow these exact output requirements:\n\n1. **Post Summary**  \n   - Provide a structured summary of the original post.  \n   - Start with a 1–2 sentence overview of the main idea.  \n   - Then add a bullet-point list that captures all key details, examples, and insights.  \n   - Use as many bullets as needed—be concise, but do not omit important information.  \n\n2. **Comments Summary**  \n   - Provide one consolidated narrative summary of the overall discussion in the comments.  \n   - Capture recurring themes, general sentiment, useful strategies, criticisms, and unique perspectives.  \n   - Do not list each comment separately—merge them into one comprehensive summary.  \n\n3. **Resources Mentioned**  \n   - List all books, tools, websites, or references mentioned in either the post or comments.  \n   - If none are mentioned, state “None.”  \n\nOutput formatting rules:\n- Use Markdown.\n- Keep tone neutral, clear, and information-dense.\n- Avoid filler phrases (e.g., "In conclusion", "Overall").\n- Do NOT hallucinate resources—only list those actually present in the provided content.\n- Preserve meaningful specificity (numbers, named entities, concrete examples) where present.\n"""

        # Dynamic output token sizing (more generous for quality)
        prompt_tokens = self.count_tokens(prompt)
        dynamic_output_cap = min(self.single_post_max_output_tokens_env, max(900, 700 + int(0.22 * prompt_tokens)))
        estimated_cost = self.estimate_cost(prompt, dynamic_output_cap)
        can_proceed, message = self.cost_tracker.check_budget(estimated_cost)
        if (not can_proceed) and (not self.ignore_budget):
            return {"error": message, "estimated_cost": estimated_cost, "note": "Budget enforcement active. Set IGNORE_BUDGET=1 to override."}

        response, metadata = self._call_llm(prompt, max_tokens=dynamic_output_cap, temperature=0.65)

        if metadata.get("error"):
            if 'content_filter' in metadata['error'] or 'ResponsibleAIPolicyViolation' in metadata['error']:
                fallback_prompt = self._build_fallback_single_prompt(post_data)
                fb_response, fb_meta = self._call_llm(fallback_prompt, max_tokens=min(600, dynamic_output_cap), temperature=0.3)
                if fb_meta.get('error'):
                    return {"error": fb_meta['error'], "note": "Content filter triggered and fallback failed."}
                return {
                    "formatted_markdown": fb_response,
                    "metadata": {
                        **fb_meta,
                        "fallback_mode": True,
                        "reason": "content_filter_triggered",
                        "prompt_preview": fallback_prompt,
                        "post_id": post_data.get('ID', ''),
                        "post_url": post_data.get('Permalink', ''),
                        "sanitized_post": content_sanitized,
                        "sanitized_comments": comments_sanitized
                    }
                }
            return {"error": metadata["error"]}

        return {
            "formatted_markdown": response,
            "metadata": {
                **metadata,
                "post_id": post_data.get('ID', ''),
                "post_url": post_data.get('Permalink', ''),
                "analyzed_at": datetime.now().isoformat(),
                "sanitized_post": content_sanitized,
                "sanitized_comments": comments_sanitized,
                "prompt_preview": prompt,
                "dynamic_output_token_limit": dynamic_output_cap,
                "prompt_tokens_estimate": prompt_tokens,
                "format": "markdown_sections_v1"
            }
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

        # Prepare summary data (sanitize titles/snippets)
        sampled_posts = sampled_posts.copy()
        sampled_posts['SafeTitle'], _ = zip(*[self._sanitize_text(t) for t in sampled_posts['Title'].fillna('').tolist()])
        sampled_posts['SafeSnippet'], _ = zip(*[self._sanitize_text((p or '')[:200]) for p in sampled_posts['Post Text'].fillna('').tolist()])
        category_counts = sampled_posts['Category'].value_counts().to_dict()
        avg_score = sampled_posts['Score'].mean()
        avg_comments = sampled_posts['Total Comments'].mean()
        
        # Get representative posts from each category
        category_samples = {}
        for category in sampled_posts['Category'].unique():
            cat_posts = sampled_posts[sampled_posts['Category'] == category]
            top_post = cat_posts.nlargest(1, 'Score').iloc[0]
            category_samples[category] = {
                "title": top_post['SafeTitle'],
                "score": int(top_post['Score']),
                "snippet": top_post['SafeSnippet']
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
        
        # Dynamic output token target for batch
        prompt_tokens = self.count_tokens(prompt)
        dynamic_output_cap = min(self.batch_max_output_tokens_env, max(1200, 800 + int(0.18 * prompt_tokens)))
        # Estimate and check cost with dynamic cap
        estimated_cost = self.estimate_cost(prompt, dynamic_output_cap)
        can_proceed, message = self.cost_tracker.check_budget(estimated_cost)
        if (not can_proceed) and (not self.ignore_budget):
            return {"error": message, "estimated_cost": estimated_cost, "note": "Budget enforcement active. Set IGNORE_BUDGET=1 to override."}
        
        # Make API call
        response, metadata = self._call_llm(prompt, max_tokens=dynamic_output_cap, temperature=0.7)

        if metadata.get("error"):
            if 'content_filter' in metadata['error'] or 'ResponsibleAIPolicyViolation' in metadata['error']:
                # Build fallback metadata‑only prompt
                fb_prompt = self._build_fallback_batch_prompt(sampled_posts)
                fb_response, fb_meta = self._call_llm(fb_prompt, max_tokens=min(800, dynamic_output_cap), temperature=0.3)
                if fb_meta.get('error'):
                    return {"error": fb_meta['error'], "note": "Content filter triggered and fallback failed."}
                try:
                    parsed = json.loads(fb_response)
                except json.JSONDecodeError:
                    parsed = {"raw_analysis": fb_response}
                parsed["metadata"] = {
                    "fallback_mode": True,
                    "reason": "content_filter_triggered",
                    **fb_meta
                }
                return parsed
            return {"error": metadata['error']}
        
        # Parse JSON response
        try:
            analysis = json.loads(response)
            analysis["metadata"] = {
                "posts_analyzed": len(sampled_posts),
                "total_posts": len(posts_df),
                "analyzed_at": datetime.now().isoformat(),
                **metadata
            }
            analysis["metadata"].update({
                "sanitized_batch": True if len(sampled_posts) else False,
                "dynamic_output_token_limit": dynamic_output_cap,
                "prompt_tokens_estimate": prompt_tokens
            })
            return analysis
        except json.JSONDecodeError:
            return {
                "raw_analysis": response,
                "metadata": {**metadata, "dynamic_output_token_limit": dynamic_output_cap, "prompt_tokens_estimate": prompt_tokens},
                "note": "Analysis returned in text format"
            }
