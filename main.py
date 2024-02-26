import os
import json
import time
import pandas as pd
import requests
from instaloader import Instaloader, RateController, LoginRequiredException, Profile, Post
import logging
from datetime import datetime
import re
import config  # config contains INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD


class InstagramManager:
    class MyInstaloader(Instaloader):
        def __init__(self, *args, **kwargs):
            custom_session = kwargs.pop('session', None)
            super().__init__(*args, **kwargs)
            if custom_session:
                self.context._session = custom_session

    def __init__(self):
        # Set up logging
        self.profile = None
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

        # Define proxies
        proxies = {
            "http": "http://mVout46tOdwHSDcN:O5Co3kSWlU7j7Yxn_country-de_streaming-1@geo.iproyal.com:12321",
            "https": "http://mVout46tOdwHSDcN:O5Co3kSWlU7j7Yxn_country-de_streaming-1@geo.iproyal.com:12321"
        }

        # Create a request session with proxies
        self.session = requests.Session()
        self.session.proxies.update(proxies)

        # Initialize MyInstaloader with the session
        self.L = self.MyInstaloader(rate_controller=RateController, session=self.session)

        # Login and initialize
        self.login_and_initialize(config.INSTAGRAM_USERNAME, config.INSTAGRAM_PASSWORD)

    def login_and_initialize(self, userId, password_):
        try:
            self.L.load_session_from_file(userId)
        except FileNotFoundError:
            try:
                self.L.login(userId, password_)
                self.L.save_session_to_file()
                logging.info("Logged in and saved session.")
            except LoginRequiredException:
                logging.error("Login failed. Please check credentials or try again later.")

    def extract_and_save_posts(self, posts_data: list, profile_id: str) -> None:
        df = pd.DataFrame(posts_data)
        excel_filename = f"{profile_id}_posts.xls"
        df.to_excel(excel_filename, index=False)
        logging.info(f"Data saved to {excel_filename}")

    def _get_last_post_date(self, profile_id):
        filename = f"{profile_id}_last_post.json"
        if os.path.exists(filename):
            try:
                with open(filename, "r") as file:
                    data = json.load(file)
                    last_post_date_str = data.get('last_post_date', None)
                    if last_post_date_str:
                        return datetime.fromisoformat(last_post_date_str)  # Convert back to datetime
            except json.JSONDecodeError:
                logging.error(f"Error reading JSON from {filename}. File may be corrupted or empty.")
                return None
        return None

    def _save_last_post_date(self, profile_id, date):
        # Ensure that 'date' is a datetime object before calling iso format
        if isinstance(date, datetime):
            formatted_date = date.isoformat()  # Convert datetime to ISO format string
        else:
            formatted_date = date  # 'date' is already a string

        with open(f"{profile_id}_last_post.json", "w") as file:
            json.dump({'last_post_date': formatted_date}, file)

    def count_internal_capitals(self, sentence):
        count = 0
        for i in range(1, len(sentence)):
            if sentence[i].isupper() and (i == 1 or sentence[i - 1] == ' '):
                count += 1
        return count

    def calculate_score(self, segment, french_combinations, common_french_words, common_german_words,
                        german_umlauts):
        score = 0
        segment_lower = segment.lower()

        for combo in french_combinations:
            score += segment_lower.count(combo)

        words = re.split(r'[\s,]+', segment_lower)
        for word in common_french_words:
            score += words.count(word) / 3

        for word in common_german_words:
            score -= words.count(word) / 3

        for umlaut in german_umlauts:
            score -= segment_lower.count(umlaut)

        sentences = re.split(r'(?<=[.!?])\s+', segment)
        for sentence in sentences:
            score -= self.count_internal_capitals(sentence)

        return score

    def predict_language_segment_simplified(self, text):
        french_combinations = ["é", "è", "ç", "ê", "à", "ô", "ù", "ë", "î", "œ", "eau", "air", "ez", "our"]
        common_french_words = ["le", "de", "un", "à", "être", "et", "en", "avoir", "que", "pour", "dans", "ce",
                               "il",
                               "qui",
                               "ne", "sur", "se", "que", "pas", "plus", "par", "au", "avec", "sa", "ses", "son",
                               "sont",
                               "entre", "comme", "mais"]
        common_german_words = ["der", "und", "sein", "in", "ein", "zu", "haben", "ich", "werden", "sie", "von",
                               "nicht",
                               "mit", "es", "sich", "auch", "auf", "für", "an", "das", "er", "so", "zum", "war",
                               "wird",
                               "aus", "bei", "ist", "eine", "nach", "die"]
        german_umlauts = ["ä", "ö", "ü"]

        threshold = 0.5

        if '//' in text:
            language = "Multi"
            segments = text.split('//')
            scores = []
            for segment in segments:
                score = self.calculate_score(segment, french_combinations, common_french_words, common_german_words,
                                             german_umlauts)
                scores.append(score)

            highest_score_index = scores.index(max(scores))
            lowest_score_index = scores.index(min(scores))

            return {
                'language': language,
                'french_segment': segments[highest_score_index].strip(),
                'french_score': scores[highest_score_index],
                'german_segment': segments[lowest_score_index].strip(),
                'german_score': scores[lowest_score_index]
            }
        else:
            score = self.calculate_score(text, french_combinations, common_french_words, common_german_words,
                                         german_umlauts)
            abs_score = abs(score)
            if abs_score > threshold:
                language = "FR" if score > 0 else "DE"
            else:
                language = "Unknown"  # or use '' for blank

            return {'language': language, 'german_segment': text.strip() if language == "DE" else '',
                    'french_segment': text.strip() if language == "FR" else ''}

    def _extract_post_data(self, post):
        media_urls = []

        if post.typename == 'GraphSidecar':
            for i, item in enumerate(post.get_sidecar_nodes(), start=1):
                media_urls.append(item.video_url if item.is_video else item.display_url)
        else:
            media_urls.append(post.video_url if post.is_video else post.url)

        caption = post.caption if post.caption else ''
        language_result = self.predict_language_segment_simplified(caption)
        language = language_result.get('language', '')
        caption_de = language_result.get('german_segment', '') if language in ['DE', 'Multi'] else ''
        caption_fr = language_result.get('french_segment', '') if language in ['FR', 'Multi'] else ''

        post_data = {
            'Post ID': post.shortcode,
            'Post Date': post.date,
            'Caption': post.caption,
            'Caption_DE': caption_de,
            'Caption_FR': caption_fr,
            'Language': language,
            'Hashtags': [tag.strip('#') for tag in post.caption_hashtags],
            'Likes': post.likes,
            'Post URL': f'https://www.instagram.com/p/{post.shortcode}/',
            'Media URLs': media_urls,
            'Type': 'Video' if post.is_video else 'Image'
        }

        time.sleep(2)
        return post_data

    def scrape_profile(self, profile_id):
        try:
            self.profile = Profile.from_username(self.L.context, profile_id)

            last_post_date = self._get_last_post_date(profile_id)
            posts_data = []

            for post in self.profile.get_posts():
                if last_post_date is None or post.date_utc > last_post_date:
                    post_data = self._extract_post_data(post)
                    posts_data.append(post_data)
                    print(f"Scraping Post ID: {post_data['Post ID']}, Date: {post_data['Post Date']}")
                    time.sleep(2)

            if posts_data:
                self._save_last_post_date(profile_id, posts_data[0]['Post Date'])
                self.extract_and_save_posts(posts_data, profile_id)
                try:
                    self.download_media(profile_id)
                except Exception as e:
                    logging.error(f"An error occurred while downloading media for {profile_id}: {e}")
            else:
                logging.info(f"No new posts found for {profile_id}")

        except Exception as e:
            logging.error(f"An error occurred while scraping {profile_id}: {e}")

    def download_media(self, profile_id):
        try:
            profile = Profile.from_username(self.L.context, profile_id)
            for post in profile.get_posts():
                self.L.download_post(post, profile_id)
        except Exception as e:
            logging.error("An error occurred:", e)

    def update_likes_in_excel(self, profile_id):
        excel_filename = f"{profile_id}_posts.xls"
        if os.path.exists(excel_filename):
            try:
                df = pd.read_excel(excel_filename)
                if 'Post ID' in df.columns and 'Likes' in df.columns:
                    for index, row in df.iterrows():
                        post_shortcode = row['Post ID']
                        post = Post.from_shortcode(self.L.context, post_shortcode)
                        if post:
                            df.at[index, 'Likes'] = post.likes
                            df.to_excel(excel_filename, index=False)
                            logging.info(
                                f"Likes for post {post_shortcode} updated to {post.likes} in {excel_filename}")
                        else:
                            logging.warning(f"Post {post_shortcode} not found. Skipping like update.")
                else:
                    logging.warning(
                        f"Missing columns 'Post ID' or 'Likes' in {excel_filename}. Unable to update Likes.")
            except Exception as e:
                logging.error(f"Error updating Likes in {excel_filename}: {e}")
        else:
            logging.warning(f"Excel file {excel_filename} not found. Skipping like update.")


if __name__ == "__main__":
    manager = InstagramManager()
    profiles = config.PROFILES  # List of Instagram profiles

    for profile_name in profiles:
        manager.scrape_profile(profile_name)
        manager.update_likes_in_excel(profile_name)
