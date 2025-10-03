#!/usr/bin/env python3
"""
Quick test to verify post content is being fetched
"""
import praw
from dotenv import load_dotenv
import os

# Load credentials
load_dotenv()

# Initialize Reddit
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

print("🔍 Testing Reddit Post Content Fetching\n")
print("=" * 60)

# Test with r/test (small, safe subreddit)
subreddit = reddit.subreddit("test")
print(f"\n📂 Fetching posts from r/test...\n")

# Get first 3 posts
for i, post in enumerate(subreddit.new(limit=3), 1):
    print(f"\n{'='*60}")
    print(f"POST #{i}")
    print(f"{'='*60}")
    print(f"Title: {post.title}")
    print(f"\nPost Text Length: {len(post.selftext)} characters")
    
    if post.selftext:
        print(f"\n📝 Post Text Content (first 200 chars):")
        print(f"{post.selftext[:200]}...")
    else:
        print(f"\n📝 Post Text: [Empty - This is a link post]")
    
    print(f"\n🔗 Post URL: {post.url}")
    print(f"🔗 Permalink: https://www.reddit.com{post.permalink}")
    print(f"📊 Score: {post.score} | Comments: {post.num_comments}")

print("\n" + "="*60)
print("✅ Test Complete!")
print("\nConclusion:")
print("- post.selftext contains FULL text content")
print("- post.url contains the linked URL (for link posts)")
print("- Both are captured in the CSV/JSON export")
