import pymongo
import os, time

from selenium import webdriver
from globals import titles, index_map, upgradation_vals, locations, video_data
from config import index
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options



class Config:
    def __init__(self):
        self.client = pymongo.MongoClient("mongodb://localhost:27017/")
        self.db = self.client["ScrapedData"]

    def get_connection(self):
        return self.db


class GetBookConfig :
    def __init__(self, title, index, upgradation_val, location):
        self.title = title
        self.index = index
        self.upgradation_val = upgradation_val
        self.location = location
    def add_book(self):
        titles.append(self.title)
        index_map.append(self.index)
        upgradation_vals.append(self.upgradation_val)
        locations.append(self.location)
        print(f"Book added, index of the book : {len(titles)-1}")


class GetVideoDataConfig :

    def fetch_video_data(self, playlist):
        # --- Configuration ---
        PLAYLIST_URL = playlist

        # --- Setup Chrome driver ---
        options = Options()
        options.add_argument("--headless")  # Run in background
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        driver = webdriver.Chrome(options=options)

        # --- Load Playlist ---
        driver.get(PLAYLIST_URL)
        time.sleep(3)

        # --- Scroll to Load all Videos ---
        last_height = driver.execute_script("return document.documentElement.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.documentElement.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # --- Extract video elements ---
        video_elements = driver.find_elements(By.CSS_SELECTOR, 'ytd-playlist-video-renderer')

        for video in video_elements:
            try:
                title_element = video.find_element(By.ID, 'video-title')
                title = title_element.get_attribute('title')
                url = title_element.get_attribute('href')
                video_data.append({
                    'title': title,
                    'url': url,
                    'video_id': url[32:43]
                })
            except Exception as e:
                print(f"Error parsing a video: {e}")

        driver.quit()

    def get_video_data(self):
        for playlist in index.playlists:
            self.fetch_video_data(playlist)


