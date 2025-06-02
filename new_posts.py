"""Send a notification message to Microsoft Teams

Usage:
  new_posts.py [--dry-run] [--verbose]
  new_posts.py (-h | --help)
  new_posts.py --version

Options:
  -h, --help                    Show this screen.
  --version                     Show version.
  -d, --dry-run                 Only a dry run, no MS Teams notifications are sent.
  --verbose                     Option to enable more verbose output.
"""

import logging
import os
import pyadaptivecard
import requests
import sys
import time
from pprint import pformat
from datetime import datetime, timedelta
from dotenv import load_dotenv, find_dotenv
from distutils.util import strtobool
from requests.auth import HTTPBasicAuth
from docopt import docopt


arguments = docopt(
    __doc__, version="Send a notification message to Microsoft Teams for new posts 1.0"
)

loglevel = logging.INFO
if arguments["--verbose"]:
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

# HTTP session
auth = HTTPBasicAuth(username, application_password)
session = requests.Session()
session.auth = auth


def wp_api_call(url, params):
    # Make the request to the WordPress REST API
    log.debug(f"{url=}, {params=}")
    try:
        response = session.get(url, params=params)
        response.raise_for_status()
        result = response.json()
        return result
    except requests.RequestException:
        log.exception(f"Failed to fetch from {url}")
        return None


def fetch_author(site_url, id):
    # Endpoint for fetching users by id
    endpoint = f'{site_url}/wp-json/wp/v2/users/{id}'

    return wp_api_call(endpoint, params={})


def fetch_latest_posts(site_url):
    # Endpoint for fetching the latest posts
    endpoint = f'{site_url}/wp-json/wp/v2/posts'

    yesterday = (datetime.now() - timedelta(days=1))
    params = {
        "status[]": ["publish", "future", "draft", "pending", "private"],
        "modified_after": yesterday.isoformat(),
    }

    return wp_api_call(endpoint, params)


def create_teams_notification(team_webhook_url, site_url, post):
    card = pyadaptivecard.AdaptiveCard(team_webhook_url)
    card.title(f"Blogpost erstellt/geändert: {post['title']['rendered']}")
    card.summary(f"Blogpost erstellt/geändert: {post['title']['rendered']}")
    card.color("3AB660")

    section = pyadaptivecard.CardSection()
    card.addSection(section)

    section.addFact("Autor", post['author'])
    section.addFact("Datum", datetime.fromisoformat(post['date']).strftime("%d.%m.%Y %H:%M"))
    section.addFact("Modified", datetime.fromisoformat(post['modified']).strftime("%d.%m.%Y %H:%M"))
    section.addFact("Link", f"[{post['link']}]({post['link']})")
    section.addFact("Status", post['status'].title())
    section.addLinkButton("Blog - Admin", f"{site_url}/wp-admin/edit.php")

    return card


try:
    posts = fetch_latest_posts(site_url)
    for post in posts:
        author = fetch_author(site_url, post["author"])["name"]

        log.info(f"Title: {post['title']['rendered']}")
        log.info(f"Author: {author}")
        log.info(f"Date: {post['date']}, Modified: {post['modified']}")
        log.debug(f"Link: {post['link']}")
        log.debug(f"Status: {post['status']}\n")
        log.debug(f"Dry Run: {arguments['--dry-run']}\n")

        post["author"] = author

        msg = create_teams_notification(team_webhook_url, site_url, post)
        if arguments["--verbose"]:
            log.debug(f"Message: {pformat(msg.to_json(), depth=8)}")

        if arguments["--dry-run"]:
            log.debug("Only a dry run, do not send message, continue...")
            continue

        log.debug("Sending message...")
        msg.send()
        time.sleep(5)
except Exception:
    log.exception("Error in new_posts.py")
    sys.exit(1)