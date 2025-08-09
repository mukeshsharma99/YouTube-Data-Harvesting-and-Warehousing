# Import necessary libraries
import streamlit as st
import mysql.connector 
import pandas as pd
import googleapiclient.discovery
from googleapiclient.errors import HttpError
import re  

# YouTube API setup
api_service_name = "youtube" 
api_version = "v3"
api_key = "YOUR_API_KEY"  # Replace with your actual API key

youtube = googleapiclient.discovery.build(api_service_name, api_version, developerKey=api_key) 

# MySQL database config
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "Rama@1234",
    "database": "youtube_data"
}

# App header styling
st.set_page_config(page_title="YouTube Data Warehouse", layout="wide")

# Initialize tables
def initialize_tables():
    mydb = mysql.connector.connect(**db_config)
    cursor = mydb.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS channels (
        channel_id VARCHAR(100) PRIMARY KEY,
        channel_name VARCHAR(255),
        channel_des TEXT,
        channel_playid VARCHAR(100),
        channel_viewcount BIGINT,
        channel_subcount BIGINT
    );""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS videos (
        video_id VARCHAR(100) PRIMARY KEY,
        video_title VARCHAR(255),
        video_description TEXT,
        channel_id VARCHAR(100),
        video_tags TEXT,
        video_pubdate DATETIME,
        video_viewcount BIGINT,
        video_likecount BIGINT,
        video_favoritecount BIGINT,
        video_commentcount BIGINT,
        video_duration INT,
        video_thumbnails TEXT,
        video_caption VARCHAR(10),
        FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
    );""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        comment_id VARCHAR(100) PRIMARY KEY,
        comment_text TEXT,
        comment_authorname VARCHAR(255),
        published_date DATETIME,
        video_id VARCHAR(100),
        channel_id VARCHAR(100),
        FOREIGN KEY (video_id) REFERENCES videos(video_id),
        FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
    );""")

    mydb.commit()
    cursor.close()
    mydb.close()

# Duration helper
def iso8601_duration_to_seconds(duration):
    match = re.match(r'^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$', duration)
    if not match:
        return None
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0
    return hours * 3600 + minutes * 60 + seconds

# Generic MySQL fetch
def fetch_data(query):
    mydb = mysql.connector.connect(**db_config)
    df = pd.read_sql(query, mydb)
    mydb.close()
    return df

# Predefined SQL Queries
query_options = {
    "All video titles with their channel names":
        """SELECT Video_title, channel_name FROM videos JOIN channels ON channels.channel_id = videos.channel_id;""",
    "Channels with the most videos":
        """SELECT channel_name, COUNT(video_id) AS video_count FROM videos 
           JOIN channels ON channels.channel_id = videos.channel_id 
           GROUP BY channel_name ORDER BY video_count DESC;""",
    "Top 10 most viewed videos":
        """SELECT video_title, channel_name FROM videos 
           JOIN channels ON channels.channel_id = videos.channel_id 
           ORDER BY video_viewcount DESC LIMIT 10;""",
    "Video comments count":
        """SELECT video_title, COUNT(*) AS comment_counts FROM videos 
           JOIN comments ON videos.video_id = comments.video_id 
           GROUP BY video_title;""",
    "Most liked video":
        """SELECT video_title, channel_name FROM videos 
           JOIN channels ON channels.channel_id = videos.channel_id 
           ORDER BY video_likecount DESC LIMIT 1;""",
    "Total likes per video":
        """SELECT Video_title, SUM(Video_likecount) AS total_likes FROM videos GROUP BY Video_title;""",
    "Total views per channel":
        """SELECT channel_name, SUM(video_viewcount) AS Total_views 
           FROM videos JOIN channels ON channels.channel_id = videos.channel_id 
           GROUP BY channel_name;""",
    "Channels with videos from 2022":
        """SELECT DISTINCT channel_name FROM channels 
           JOIN videos ON channels.channel_id = videos.channel_id 
           WHERE YEAR(Video_pubdate) = 2022;""",
    "Average video duration per channel":
        """SELECT channel_name, AVG(video_duration) AS avg_duration 
           FROM videos JOIN channels ON videos.channel_id = channels.channel_id 
           GROUP BY channel_name;""",
    "Videos with most comments":
        """SELECT video_title, channel_name FROM videos 
           JOIN channels ON videos.channel_id = channels.channel_id 
           ORDER BY Video_commentcount DESC LIMIT 1;"""
}

def execute_query(question):
    query = query_options.get(question)
    if query:
        return fetch_data(query)
    return pd.DataFrame()

# Streamlit App UI
def main():
    initialize_tables()

    st.markdown("# 📊 YouTube Data Harvesting & Warehousing")
    st.markdown("Easily extract, store, and analyze YouTube channel, video, and comment data.")

    st.sidebar.header("🔎 Navigation")
    option = st.sidebar.radio("Select Option", ["📥 Enter Channel ID", "📺 Channels", "🎞 Videos", "💬 Comments", "🧠 Smart Queries"])

    if option == "📥 Enter Channel ID":
        st.subheader("➕ Add a New YouTube Channel")
        ch_id = st.text_input("Enter YouTube Channel ID:")
        if st.button("Fetch Channel Info") and ch_id:
            fetch_channel_data(ch_id)
        if st.button("Fetch Videos") and ch_id:
            vids = playlist_videos_id(ch_id)
            df = fetch_video_data(vids)
            st.success("Fetched videos successfully.")
            st.dataframe(df)
        if st.button("Fetch Comments") and ch_id:
            df = fetch_comment_data(ch_id)
            st.success("Fetched comments successfully.")
            st.dataframe(df)

    elif option == "📺 Channels":
        st.subheader("📋 List of All Channels")
        df = fetch_data("SELECT * FROM channels;")
        st.dataframe(df)

    elif option == "🎞 Videos":
        st.subheader("🎥 List of All Videos")
        df = fetch_data("SELECT * FROM videos;")
        st.dataframe(df)

    elif option == "💬 Comments":
        st.subheader("💬 List of All Comments")
        df = fetch_data("SELECT * FROM comments;")
        st.dataframe(df)

    elif option == "🧠 Smart Queries":
        st.subheader("🧠 Run Predefined Queries")
        question = st.selectbox("Choose a query", list(query_options.keys()))
        if question:
            result = execute_query(question)
            st.dataframe(result)

if __name__ == "__main__":
    main()   
