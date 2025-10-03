# 🔍 Keyword Filtering Feature Guide

## Overview

The Reddit Scraper now includes powerful keyword filtering capabilities to help you find exactly what you're looking for in posts and comments.

---

## ✨ Features

### 🎯 **Subreddit Post Filtering**

Search for specific keywords in post titles and/or content.

#### **Options:**

1. **Keywords Input**
   - Enter comma-separated keywords
   - Example: `docker, kubernetes, homelab`
   - Posts matching ANY or ALL keywords will be shown

2. **Case Sensitivity**
   - Toggle case-sensitive matching
   - Default: Case-insensitive (more results)

3. **Search Location**
   - **Title**: Search only in post titles
   - **Post Text**: Search only in post content
   - **Both**: Search in both title and content (default)

4. **Match Type**
   - **Any keyword (OR)**: Show posts with ANY of the keywords
   - **All keywords (AND)**: Show posts with ALL keywords

### 💬 **Comment Filtering**

Filter comments by keywords when scraping specific posts.

#### **Options:**

1. **Comment Keywords**
   - Comma-separated keywords
   - Only comments containing these keywords will be shown

2. **Case Sensitive**
   - Toggle for comment keyword matching

---

## 📋 Usage Examples

### Example 1: Find Docker-related Posts

```
Keywords: docker, container, containerization
Search In: Both
Match Type: Any keyword (OR)
Case Sensitive: No
```

**Result**: Posts mentioning "docker" OR "container" OR "containerization"

---

### Example 2: Find Specific Technical Questions

```
Keywords: error, fix, solution
Search In: Both
Match Type: All keywords (AND)
Case Sensitive: No
```

**Result**: Posts containing ALL three words: "error" AND "fix" AND "solution"

---

### Example 3: Case-Sensitive Brand Search

```
Keywords: Proxmox, TrueNAS, UnRAID
Search In: Title
Match Type: Any keyword (OR)
Case Sensitive: Yes
```

**Result**: Posts with exact brand names (proper capitalization) in titles

---

### Example 4: Filter Comments for Solutions

```
Comment Keywords: solution, worked, fixed, solved
Case Sensitive: No
```

**Result**: Only show comments that contain solution-related keywords

---

## 🎓 Best Practices

### ✅ **DO:**

1. **Start Broad, Then Narrow**
   - Begin with "Any keyword (OR)" to see what's available
   - Switch to "All keywords (AND)" to narrow results

2. **Use Synonyms**
   - Example: `problem, issue, error, broken`
   - Captures different ways people express the same thing

3. **Combine with Other Filters**
   - Use keyword filters WITH score/date filters for best results
   - Example: Keywords + Min Score 10 = Quality posts about your topic

4. **Use Case-Insensitive for Most Searches**
   - Catches more variations (Docker, docker, DOCKER)
   - Only use case-sensitive for specific brand names

### ❌ **DON'T:**

1. **Don't Use Too Many Keywords**
   - More keywords = fewer results with "AND" matching
   - Keep it focused (3-5 keywords max)

2. **Don't Forget Partial Matches**
   - Keywords match anywhere in text
   - Searching "test" will match "testing", "tested", "contest", etc.

3. **Don't Mix Languages Without Consideration**
   - English keywords won't match non-English posts
   - Consider this when searching international subreddits

---

## 🔧 Technical Details

### How It Works

1. **Text Extraction**
   - Extracts text from Title and/or Post Text
   - Converts to lowercase (if case-insensitive)

2. **Keyword Matching**
   - Checks if keywords appear anywhere in the text
   - Uses Python's `in` operator (substring matching)

3. **Filtering Logic**
   ```python
   # OR matching (Any keyword)
   matches = any(keyword in text for keyword in keywords)
   
   # AND matching (All keywords)
   matches = all(keyword in text for keyword in keywords)
   ```

4. **Performance**
   - Filtering happens AFTER fetching from Reddit API
   - Pandas DataFrame filtering is very fast
   - No impact on API rate limits

---

## 💡 Pro Tips

### Tip 1: Combine with Categories

```
Keywords: plex, media, streaming
Categories: Solution Requests, Pain Points
```
Find media server issues and questions specifically

### Tip 2: Use Negative Keywords (Workaround)

1. First scrape: `Keywords: homelab`
2. Download CSV
3. Second scrape: `Keywords: homelab, beginner`
4. Compare results to find "homelab" WITHOUT "beginner"

### Tip 3: Find Comparisons

```
Keywords: vs, versus, compared, better than
Search In: Title
```
Finds comparison posts

### Tip 4: Find Tutorials

```
Keywords: tutorial, guide, how to, step by step
Match Type: Any keyword (OR)
```
Finds educational content

### Tip 5: Research Specific Products

```
Keywords: Synology DS920+
Case Sensitive: Yes
Search In: Both
```
Finds specific model discussions

---

## 📊 Use Cases

### Market Research
```
Keywords: problem, frustration, wish, need
Category: Pain Points
```
Identify customer pain points

### Product Development
```
Keywords: feature request, should have, would be nice
Category: Solution Requests
```
Find feature ideas

### Competitive Analysis
```
Keywords: better than, alternative to, switching from
Category: Seeking Alternatives
```
Monitor competitor mentions

### Content Ideas
```
Keywords: how do I, best way, recommend
Min Comments: 5
```
Find popular questions to create content about

---

## 🚀 Future Enhancements

Planned features:
- [ ] Regular expression (regex) support
- [ ] Exclude keywords (negative filtering)
- [ ] Saved filter presets
- [ ] Highlight matched keywords in results
- [ ] Word stemming (match "run", "running", "ran")
- [ ] Fuzzy matching for typos

---

## 📞 Need Help?

- Check the in-app help tooltips (ℹ️ icons)
- Review the examples above
- Start with simple searches and build complexity
- Remember: filtering is cumulative with other filters

---

**Happy Filtering! 🎯**
