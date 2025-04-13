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

# Predefined queries
def execute_query(question):
    query_mapping = {
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
    return fetch_data(query_mapping.get(question, "")) if question else pd.DataFrame()

# Fetch and cache channel data
def fetch_channel_data(channel_id):
    mydb = mysql.connector.connect(**db_config)
    cursor = mydb.cursor()
    cursor.execute("SELECT * FROM channels WHERE channel_id = %s", (channel_id,))
    if cursor.fetchone():
        st.warning("Channel data already exists in DB.")
        cursor.close()
        mydb.close()
        return

    try:
        response = youtube.channels().list(part="snippet,contentDetails,statistics", id=channel_id).execute()
        if "items" not in response or not response["items"]:
            st.error("No channel found.")
            return

        item = response["items"][0]
        data = {
            "channel_name": item["snippet"]["title"],
            "channel_id": channel_id,
            "channel_des": item["snippet"]["description"],
            "channel_playid": item["contentDetails"]["relatedPlaylists"]["uploads"],
            "channel_viewcount": item["statistics"]["viewCount"],
            "channel_subcount": item["statistics"]["subscriberCount"]
        }

        cursor.execute("""
            INSERT INTO channels (channel_name, channel_id, channel_des, channel_playid, channel_viewcount, channel_subcount)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, tuple(data.values()))
        mydb.commit()
        st.success("Channel data inserted successfully.")
        st.write(data)

    except HttpError as e:
        st.error(f"HTTP Error: {e}")
    finally:
        cursor.close()
        mydb.close()

# Get videos from channel’s uploads playlist
def playlist_videos_id(channel_id):
    video_ids = []
    try:
        response = youtube.channels().list(part="contentDetails", id=channel_id).execute()
        playlist_id = response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        next_page_token = None
        while True:
            playlist_response = youtube.playlistItems().list(
                part="snippet", playlistId=playlist_id, maxResults=10, pageToken=next_page_token).execute()

            video_ids += [item["snippet"]["resourceId"]["videoId"] for item in playlist_response["items"]]
            next_page_token = playlist_response.get("nextPageToken")
            if not next_page_token:
                break
    except HttpError as e:
        st.error(f"Error fetching playlist: {e}")
    return video_ids

# Fetch video data
def fetch_video_data(video_ids):
    video_info = []
    for vid in video_ids:
        try:
            response = youtube.videos().list(part="snippet,contentDetails,statistics", id=vid).execute()
            for i in response["items"]:
                data = {
                    "video_id": i["id"],
                    "video_title": i["snippet"]["title"],
                    "video_description": i["snippet"]["description"],
                    "channel_id": i['snippet']['channelId'],
                    "video_tags": str(i['snippet'].get("tags", [])),
                    "video_pubdate": i["snippet"]["publishedAt"],
                    "video_viewcount": i["statistics"]["viewCount"],
                    "video_likecount": i["statistics"].get('likeCount', 0),
                    "video_favoritecount": i["statistics"]["favoriteCount"],
                    "video_commentcount": i["statistics"].get("commentCount", 0),
                    "video_duration": iso8601_duration_to_seconds(i["contentDetails"]["duration"]),
                    "video_thumbnails": i["snippet"]["thumbnails"]['default']['url'],
                    "video_caption": i["contentDetails"]["caption"]
                }
                video_info.append(data)
        except:
            continue

    mydb = mysql.connector.connect(**db_config)
    cursor = mydb.cursor()
    for vid in video_info:
        cursor.execute("""
            INSERT IGNORE INTO videos (video_id, video_title, video_description, channel_id, video_tags, video_pubdate,
            video_viewcount, video_likecount, video_favoritecount, video_commentcount,
            video_duration, video_thumbnails, video_caption)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, tuple(vid.values()))
    mydb.commit()
    cursor.close()
    mydb.close()
    return pd.DataFrame(video_info)

# Fetch and insert comment data
def fetch_comment_data(channel_id):
    comments = []
    video_ids = playlist_videos_id(channel_id)
    for vid in video_ids:
        try:
            response = youtube.commentThreads().list(
                part="snippet", videoId=vid, maxResults=20).execute()
            for item in response["items"]:
                comment = {
                    "comment_id": item["snippet"]["topLevelComment"]["id"],
                    "comment_text": item["snippet"]["topLevelComment"]["snippet"]["textDisplay"],
                    "comment_authorname": item["snippet"]["topLevelComment"]["snippet"]["authorDisplayName"],
                    "published_date": item["snippet"]["topLevelComment"]["snippet"]["publishedAt"],
                    "video_id": item["snippet"]["topLevelComment"]["snippet"]["videoId"],
                    "channel_id": channel_id
                }
                comments.append(comment)
        except:
            continue

    mydb = mysql.connector.connect(**db_config)
    cursor = mydb.cursor()
    for c in comments:
        cursor.execute("""
            INSERT IGNORE INTO comments (comment_id, comment_text, comment_authorname, published_date, video_id, channel_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, tuple(c.values()))
    mydb.commit()
    cursor.close()
    mydb.close()
    return pd.DataFrame(comments)

# Streamlit App UI
def main():
    initialize_tables()

    st.title("📊 YouTube Data Harvesting & Warehousing")
    st.sidebar.header("Navigation")
    option = st.sidebar.radio("Choose", ["Enter Channel ID", "Channels", "Videos", "Comments", "Queries"])

    if option == "Enter Channel ID":
        st.subheader("🔍 Add New Channel")
        ch_id = st.text_input("Enter YouTube Channel ID")
        if st.button("Fetch Channel Info") and ch_id:
            fetch_channel_data(ch_id)
        if st.button("Fetch Videos") and ch_id:
            vids = playlist_videos_id(ch_id)
            df = fetch_video_data(vids)
            st.dataframe(df)
        if st.button("Fetch Comments") and ch_id:
            df = fetch_comment_data(ch_id)
            st.dataframe(df)

    elif option == "Channels":
        st.subheader("📺 All Channels")
        df = fetch_data("SELECT * FROM channels;")
        st.dataframe(df)

    elif option == "Videos":
        st.subheader("🎞 All Videos")
        df = fetch_data("SELECT * FROM videos;")
        st.dataframe(df)

    elif option == "Comments":
        st.subheader("💬 All Comments")
        df = fetch_data("SELECT * FROM comments;")
        st.dataframe(df)

    elif option == "Queries":
        st.subheader("🔍 Ask a Question")
        question = st.selectbox("Choose a query", list(execute_query.__annotations__.keys()) or [
            "All video titles with their channel names",
            "Channels with the most videos",
            "Top 10 most viewed videos",
            "Video comments count",
            "Most liked video",
            "Total likes per video",
            "Total views per channel",
            "Channels with videos from 2022",
            "Average video duration per channel",
            "Videos with most comments"
        ])
        if question:
            result = execute_query(question)
            st.dataframe(result)

if __name__ == "__main__":
    main()
