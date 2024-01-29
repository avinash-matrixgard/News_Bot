import requests
import boto3
import json
from bs4 import BeautifulSoup
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import logging
from datetime import datetime


# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# function to get secrets from secrets manager
def get_secret():
    secret_name = "<secret_name>"
    region_name = "<region?"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=region_name)

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret = get_secret_value_response['SecretString']
        return json.loads(secret)['slack_token']
    except Exception as e:
        logging.error(f"Error retrieving secret: {e}")
        return None

# Use this function to retrieve the Slack token
slack_token = get_secret()
# Your Slack token and channel ID
channel_id = 'daily_news'

# Function to scrape Cyber Security Headlines
def scrape_cybersecurity_news():
    url = "https://cisoseries.com/category/podcast/cyber-security-headlines/"
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find news items
        news_items = soup.find_all('div', class_='td-module-container')
        today = datetime.now().date()

        if not news_items:
            logging.warning("No news items found on the page.")
            return []

        news_data = []
        for item in news_items:
            date_element = item.find('time', class_='entry-date')
            if date_element:
                news_date = datetime.strptime(date_element['datetime'], '%Y-%m-%dT%H:%M:%S%z').date()
                if news_date == today:
                    headline_element = item.find('h3', class_='entry-title td-module-title')
                    if headline_element and headline_element.a:
                        headline = headline_element.get_text(strip=True)
                        link = headline_element.a['href']
                        news_data.append({'headline': headline, 'link': link})

        logging.info(f"Found {len(news_data)} news items for today.")
        return news_data
    except Exception as e:
        logging.error(f"Error occurred while scraping: {e}")
        return []

# Function to post news to Slack
def post_to_slack(news_data, token, channel):
    client = WebClient(token=token)
    logging.info("Starting to post today's news to Slack.")

    for news in news_data:
        message = f"*{news['headline']}*\nRead more: {news['link']}"
        try:
            client.chat_postMessage(channel=channel, text=message)
            logging.info(f"Posted news: {news['headline']}")
        except SlackApiError as e:
            logging.error(f"Error posting to Slack: {e}")

# Main function
def main(event, context):
    logging.info("Script started.")
    news_data = scrape_cybersecurity_news()
    if news_data:
        post_to_slack(news_data, slack_token, channel_id)
    else:
        logging.warning("No news for today to post to Slack.")

if __name__ == "__main__":
    main()
