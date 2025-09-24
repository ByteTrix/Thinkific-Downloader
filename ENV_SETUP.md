# 🔧 Environment Setup Guide

This guide will walk you through setting up the required environment variables to download courses from Thinkific-based platforms.

## **Reference Video (Optional)**

For a general overview of using browser DevTools to extract authentication data, you can watch this reference video: **[How to Extract Authentication Data from Browser](https://youtu.be/owi-cOcpceI?t=60)**

**⚠️ Important Note:** The video above is just a **general reference** for understanding browser DevTools concepts. **Follow the specific steps below for this Thinkific Downloader project**, as the exact fields and process may differ from the video.

---

## Prerequisites

- A web browser (Chrome, Firefox, Edge, Safari)
- Access to the course you want to download
- Basic knowledge of browser Developer Tools

## 🎯 Quick Overview

You need to configure 3 main variables in your `.env` file:
- `COURSE_LINK` - The URL of the course
- `COOKIE_DATA` - Authentication cookies from your browser
- `CLIENT_DATE` - Timestamp for API requests

---

## 📝 Step-by-Step Setup

### **Step 1: Copy Environment Template**

First, create your environment file from the template:

```bash
# Copy the example file
cp .env.example .env
```

Or manually create a `.env` file and copy the contents from `.env.example`.

### **Step 2: Extract Authentication Data**

This is the most important step. You need to capture authentication cookies and timestamp.

**📺 Visual Reference:** While the [video guide](https://youtu.be/owi-cOcpceI?t=60) shows similar concepts, **follow these exact steps below** for Thinkific-based platforms.

#### **2.1 Open Developer Tools**

**For Chrome/Edge:**
- Press `F12` OR
- Right-click → "Inspect" OR  
- Menu → More Tools → Developer Tools

**For Firefox:**
- Press `F12` OR
- Right-click → "Inspect Element" OR
- Menu → Web Developer → Inspector

**For Safari:**
- Enable Developer menu first: Safari → Preferences → Advanced → "Show Develop menu"
- Then: Develop → Show Web Inspector

#### **2.2 Access Network Tab**

1. **Click on the "Network" tab** in Developer Tools
2. **Make sure "All" or "XHR" filter is selected**
3. **Clear any existing logs** (click the clear button 🗑️)

#### **2.3 Trigger Course Data Request**

1. **Refresh the course page** (F5 or Ctrl+R)
2. **OR navigate to any lesson** within the course
3. **Wait for the page to fully load**

#### **2.4 Find the API Request**

1. **In the Network tab, look for a request containing:**
   ```
   course_player/v2/courses/
   ```
   
2. **It might look like:**
   - `course_player/v2/courses/123456`
   - `course_player/v2/courses/your-course-id`
   
3. **Click on this request** to select it

#### **2.5 Extract Cookie Data**

1. **Click on the request** you found
2. **Look for the "Headers" section** (or click "Headers" tab)
3. **Find "Request Headers" section**
4. **Look for the "cookie:" line** (it will be long)
5. **Copy the entire cookie value** (everything after "cookie: ")

   ```env
   COOKIE_DATA=_session_id=abc123...; user_token=xyz789...; 
   ```

**⚠️ Important:** 
- Copy the ENTIRE cookie string
- It should be very long (several hundred characters)
- Include all parts separated by semicolons

#### **2.6 Extract Client Date**

1. **In the same request headers section**
2. **Look for "Response Headers"** 
3. **Find the "date:" field**
4. **Copy the date value**

   ```env
   CLIENT_DATE=25:08:202410:30:45 GMT
   ```

---


## ✅ Final Environment File

Your `.env` file should look like this:

```env
# Course Configuration
COURSE_LINK="https://your-platform.com/courses/your-course"

# Authentication (Required)
COOKIE_DATA="_session_id=abcd1234...; user_token=xyz789...; other_cookies=values..."
CLIENT_DATE="25:08:2024-10:30:45GMT"

# Download Settings (Optional)
OUTPUT_DIR=./downloads
CONCURRENT_DOWNLOADS=3
RETRY_ATTEMPTS=3
RESUME_PARTIAL=true
RATE_LIMIT_MB_S=10.0
DEBUG=false
```

---

## 🚨 Troubleshooting

**📺 Need visual help?** The [reference video](https://youtu.be/owi-cOcpceI?t=60) shows general DevTools concepts, but **follow our specific steps above** for this project.

### **Problem: Can't find course_player request**

**Solutions:**
1. Make sure you're logged into the course
2. Try navigating to different lessons
3. Refresh the page with Network tab open
4. Check if the URL pattern is slightly different (search for "course" in Network tab)

### **Problem: Cookies not working**

**Solutions:**
1. Make sure you copied the ENTIRE cookie string
2. Cookies expire - get fresh ones
3. Try logging out and back in, then repeat the process

### **Problem: Invalid date format**

**Solutions:**
1. Copy the exact date format from the response headers
2. It should look like: `Wed, 25 Sep 2024 10:30:45 GMT`
3. Don't modify the format

### **Problem: Download fails with authentication errors**

**Solutions:**
1. Refresh your cookies (they might have expired)
2. Make sure you have access to the course
3. Check that COURSE_LINK points to the correct course

---

## 🔒 Security Notes

- **Keep your .env file private** - it contains your authentication data
- **Don't commit .env to version control** (it's in .gitignore by default)
- **Cookies expire** - you may need to refresh them periodically
- **Only use on courses you have legitimate access to**

---

## 🎯 Quick Validation

Test your setup by running:

```bash
# Docker
docker-compose up

# Python
python thinkificdownloader.py
```

If authentication works, you should see course information being fetched. If not, double-check your cookie data.

---

## 📞 Need Help?

- 🐛 **Issues**: [Report Problems](https://github.com/ByteTrix/Thinkific-Downloader/issues)
- 💬 **Questions**: [Community Discussions](https://github.com/ByteTrix/Thinkific-Downloader/discussions)
- 📚 **Documentation**: [Main README](README.md)
- 🎯 **Selective Downloads**: [Download Specific Lessons Only](SELECTIVE_DOWNLOAD.md)

---

**⚡ Pro Tip:** Bookmark this guide! You'll need to refresh your cookies periodically as they expire.
