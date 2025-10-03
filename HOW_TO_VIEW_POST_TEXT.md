# 📝 How to View Post Text Content in the UI

## ✅ **FIXED: Post Text is Now Visible by Default!**

I've updated the app to show the **"Post Text"** column by default in the table view.

---

## 🎯 **Where to Find Post Content:**

### **Option 1: Default View (Now Includes Post Text!)**
After scraping, you'll now see these columns by default:
1. ✅ **Title** - Post title
2. ✅ **Post Text** - ⭐ **FULL text content of the post**
3. ✅ **Category** - AI classification
4. ✅ **Author** - Username
5. ✅ **Score** - Upvotes
6. ✅ **Total Comments** - Comment count
7. ✅ **Created UTC** - Date/time
8. ✅ **Permalink** - Reddit link

### **Option 2: Customize Columns**
Click the **"🔧 Customize Columns"** expander to:
- Add/remove any columns
- Reorder columns
- Show all 16+ available fields

### **Option 3: Download Full Data**
Click **"📥 Download Full CSV"** to get ALL columns including:
- Post Text (full content)
- Post URL (external links)
- Flair, Awards, NSFW flags, etc.

---

## 📊 **What Each Field Contains:**

### **Post Text** vs **Post URL**
- **Post Text** = The actual text content written in the post
- **Post URL** = External link (for link posts) OR Reddit permalink (for text posts)

### **Examples:**

#### Text Post:
```
Title: "My Homelab Setup"
Post Text: "After 6 months, here's my complete setup:
           - Server: Dell R720
           - Storage: 48TB ZFS pool
           - Services: Plex, Nextcloud, Home Assistant
           [Full detailed explanation...]"
Post URL: "https://www.reddit.com/r/homelab/comments/abc123/"
```

#### Link Post:
```
Title: "Cool Dashboard Project"
Post Text: "Check out this dashboard I made. 
           Built with React and Python."
Post URL: "https://github.com/user/dashboard-project"
```

---

## 🚀 **To See the Changes:**

1. **Restart the Streamlit app:**
   ```powershell
   # Press Ctrl+C in the terminal running the app
   # Then run again:
   D:/MyFolder/reddit-scraper/.venv/Scripts/python.exe -m streamlit run main.py
   ```

2. **Scrape a subreddit** (try r/test for quick results)

3. **Look at the table** - You'll now see "Post Text" column!

4. **Expand posts** - You can see the full text content right in the table

---

## 💡 **Pro Tips:**

### View Full Text of Long Posts:
1. Hover over the "Post Text" cell
2. Click to expand and see full content
3. Or download CSV and open in Excel/text editor

### Filter by Content:
1. Download the CSV
2. Use Excel/Python to filter by text content
3. Search for specific keywords in "Post Text" column

### Best Columns for Analysis:
- **Title + Post Text** - Full content
- **Category** - Content type classification
- **Score + Comments** - Engagement metrics
- **Permalink** - Link back to discussion

---

## 🎉 **Summary:**

✅ **Post Text IS being fetched** (always has been!)
✅ **Post Text NOW visible in UI by default** (just fixed!)
✅ **All data available in CSV exports** (complete dataset)

**Restart your app to see the changes!** 🚀
