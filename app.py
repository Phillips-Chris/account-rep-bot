#!/usr/bin/env python
"""Bot to get owners of customers."""
import requests
import os
import base64
import logging
from slack import RTMClient
from slack.errors import SlackApiError
from dotenv import load_dotenv

load_dotenv()

LOG_FMT = "%(asctime)s %(levelname)-8s [%(name)s:%(funcName)s()] %(message)s"
logging.basicConfig(level=logging.DEBUG, format=LOG_FMT)
LOG = logging.getLogger("slackbot")

# Pull ZD API key and encode it in Base64
ZD_KEY = os.getenv("ZD_API")
ZD_KEY = base64.b64encode(ZD_KEY.encode("ascii")).decode("UTF8")

ZD_URL = "https://axonius.zendesk.com"
ZD_URL_ORG = f"{ZD_URL}/api/v2/organizations"


def process_whois(data, web_client):
    """Process a #whois command."""
    channel_id = data["channel"]
    thread_ts = data["ts"]
    search = data.get("text")
    search = search[7:]

    url = f"{ZD_URL_ORG}/autocomplete.json?name={search}"
    headers = {"Authorization": f"Basic {ZD_KEY}"}
    try:
        resp = requests.get(url=url, headers=headers)
    except Exception:
        LOG.exception(f"Error getting response from zendesk")

    json_response = resp.json()

    """
    Iterate through each result and return
    it as a Slack message with customer name, salea rep and CSM
    """
    for org in json_response["organizations"]:
        name = org["name"]
        salesrep = org["organization_fields"]["account_owner"]
        csm = org["organization_fields"]["assigned_csm"]
        text = [f"Customer: {name}", f"Sales Rep: {salesrep}", f"CSM: {csm}"]
        text = "\n".join(text)
        """
        text = "Customer:
          Sales Rep:
          CSM:
        "
        """
        try:
            web_client.chat_postMessage(
                channel=channel_id, text=text, thread_ts=thread_ts,
            )
        # You will get a SlackApiError if "ok" is False
        except SlackApiError as exc:
            assert exc.response["ok"] is False
            assert exc.response["error"]
            LOG.exception(f'Got an error: {exc.response["error"]}')


# Watch for messages from users with trigger
@RTMClient.run_on(event="message")
def get_info(**payload):
    """Process channel messages."""
    data = payload["data"]
    web_client = payload["web_client"]

    if "#whois" in data.get("text", []):
        try:
            process_whois(data=data, web_client=web_client)
        except Exception:
            LOG.exception(f"Exception in process_whois!!!")


RTM_CLIENT = RTMClient(token=os.getenv("SLACK_TOKEN"))
RTM_CLIENT.start()
