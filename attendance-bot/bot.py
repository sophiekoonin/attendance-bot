from slackclient import SlackClient
import yaml
import sqlite3

settings = yaml.load(open("settings.yaml"))

token = settings.get("bot-token")
bot_name = settings.get("bot-name")
bot_emoji = ":{emoji}:".format(emoji=settings.get("bot-emoji"))  # wrap emoji name in colons

client = SlackClient(token)

# post a message and return the timestamp of the message
def post_message(message, channel):
    res = client.api_call(
        "chat.postMessage", channel=channel, text=message,
        username=bot_name, icon_emoji=bot_emoji
    )
    return [res.get("ts"), res.get("channel")]

def get_reactions(ts, channel):
    res = client.api_call(
        "reactions.get", channel=channel, timestamp=ts
    )
    return res

