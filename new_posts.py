import logging
import os
import pyadaptivecard
import requests
import sys
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv, find_dotenv
from requests.auth import HTTPBasicAuth


loglevel = logging.DEBUG
log = logging.getLogger(__name__)
log.setLevel(loglevel)

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=loglevel,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.captureWarnings(True)

# load .env file
load_dotenv(find_dotenv())

# Replace these with your WordPress site details
site_url = os.environ["WP_BASE_URL"]
username = os.environ["WP_USER"]
application_password = os.environ["WP_APPLICATION_PASSWORD"]
team_webhook_url = os.environ["MS_TEAMS_WEBHOOK_URL"]


def fetch_latest_posts(site_url, username, password):
    # Endpoint for fetching the latest posts
    endpoint = f'{site_url}/wp-json/wp/v2/posts'
    auth = HTTPBasicAuth(username, application_password)
    yesterday = (datetime.now() - timedelta(days=1))
    params = {
        "status[]": ["publish", "future", "draft", "pending", "private"],
        "modified_after": yesterday.isoformat()
    }

    # Make the request to the WordPress REST API
    try:
        response = requests.get(endpoint, params=params, auth=auth)
        response.raise_for_status()

        posts = response.json()
        return posts
    except requests.RequestException:
        log.exception(f"Failed to fetch posts from {site_url}")
        return []


def create_teams_notification(team_webhook_url, site_url, post):
    card = pyadaptivecard.AdaptiveCard(team_webhook_url)
    card.title(f"Blogpost erstellt/geändert: {post['title']['rendered']}")
    card.summary(f"Blogpost erstellt/geändert: {post['title']['rendered']}")
    card.color("3AB660")

    section = pyadaptivecard.CardSection()
    card.addSection(section)

    section.addFact("Datum", datetime.fromisoformat(post['date']).strftime("%d.%m.%Y %H:%M"))
    section.addFact("Modified", datetime.fromisoformat(post['modified']).strftime("%d.%m.%Y %H:%M"))
    section.addFact("Link", f"[{post['link']}]({post['link']})")
    section.addFact("Status", post['status'].title())
    section.addLinkButton("Blog - Admin", f"{site_url}/wp-admin/edit.php")

    return card


try:
    posts = fetch_latest_posts(site_url, username, application_password)
    for post in posts:
        log.debug(f"Title: {post['title']['rendered']}")
        log.debug(f"Date: {post['date']}, Modified: {post['modified']}")
        log.debug(f"Link: {post['link']}")
        log.debug(f"Status: {post['status']}\n")

        msg = create_teams_notification(team_webhook_url, site_url, post)
        msg.printme()
        msg.send()
        time.sleep(5)
except Exception:
    log.exception("Error in new_posts.py")
    sys.exit(1)