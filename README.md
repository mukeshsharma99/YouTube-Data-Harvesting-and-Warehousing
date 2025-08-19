# 📊 YouTube Data Harvesting and Warehousing using SQL & Streamlit

## 🚀 Introduction  
This project builds a complete data pipeline to **harvest data from YouTube**, **store it in a SQL data warehouse**, and **analyze it via an interactive Streamlit web app**. It provides a powerful way to extract meaningful insights from YouTube channels, videos, and comments — all in one seamless flow.
 
---
 
## 🧠 Project Overview   

### ✅ Streamlit Application  
An intuitive **web-based interface** built with Streamlit that allows users to:  
- Input YouTube channel IDs
- Harvest data  
- Migrate data to SQL
- Run queries
- Visualize insights interactively  

### ✅ YouTube API Integration      
Leverages the **YouTube Data API** to retrieve:
- Channel metadata
- Video details
- Comments and engagement metrics

### ✅ SQL Data Warehouse  
Migrates and stores structured YouTube data in **MySQL** to enable:
- Advanced data querying
- Analytics and reporting
- Scalable storage

---

## 🛠️ Technologies Used

| Technology | Purpose |
|------------|---------|
| **Python** | Core programming language |
| **Streamlit** | Web UI for interaction and visualization |
| **YouTube Data API** | Fetch YouTube channel/video/comment data |
| **MySQL** | Data warehouse for structured storage |
| **Pandas** | Data manipulation and transformation |

---

## 🧰 Setup Instructions

1. **Install Python**  
   Make sure Python is installed on your system.

2. **Install Dependencies**  
   Use pip to install required libraries:
   ```bash
   pip install streamlit pandas mysql-connector-python google-api-python-client
