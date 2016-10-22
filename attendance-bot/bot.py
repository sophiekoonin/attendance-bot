from slackclient import SlackClient
import yaml
import sqlite3


class AttendanceBot(object):

    def __init__(self):
        settings = yaml.load(open("../settings.yaml"))
        token = settings.get("bot-token")

        self.bot_name = settings.get("bot-name")
        self.bot_emoji = ":{emoji}:".format(emoji=settings.get("bot-emoji"))  # wrap emoji name in colons
        self.client = SlackClient(token)

    # post a message and return the timestamp of the message
    def post_message(self, message, channel):
        res = self.client.api_call(
            "chat.postMessage", channel=channel, text=message,
            username=self.bot_name, icon_emoji=self.bot_emoji
        )
        return [res.get("ts"), res.get("channel")]

    def get_reactions(self, ts, channel):
        res = self.client.api_call(
            "reactions.get", channel=channel, timestamp=ts
        )
        return res.get("message").get("reactions")

    def get_real_name(self, user_id):
        res = self.client.api_call(
            "users.info", user=user_id
        )
        return res.get("user").get("profile").get("real_name")
