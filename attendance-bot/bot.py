from slackclient import SlackClient
import os
from apscheduler.schedulers.background import BackgroundScheduler
import apiclient
from oauth2client import service_account
import httplib2
import json
import yaml

def schedule(day, hour, mins, func, args):
    sched = BackgroundScheduler()

    @sched.scheduled_job('cron', day_of_week=day, hour=hour, minute=mins)
    def scheduled_job():
        func(*args)

    sched.start()
    print("Post scheduled for {day} at {hour}:{mins}!".format(day=day, hour=hour, mins=mins))


class AttendanceBot(object):

    def __init__(self, settings):
        token = os.environ.get("BOT_TOKEN")

        self.bot_name = settings.get("bot-name")
        self.bot_emoji = ":{emoji}:".format(emoji=settings.get("bot-emoji"))  # wrap emoji name in colons
        self.client = SlackClient(token)
        self.channel = settings.get("channel")
        self.emoji_present = settings.get("emoji-present")
        self.emoji_absent = settings.get("emoji-absent")

        self.sheet_id = settings.get("spreadsheet-id")


        # # schedule the rehearsal message post
        # schedule(
        #     settings.get("rehearsal-day"),
        #     settings.get("post-hour"),
        #     settings.get("post-minute"),
        #     self.post_message_with_reactions,
        #     [settings.get("rehearsal-message")]
        # )

    # post a message and return the timestamp of the message
    def post_message(self, message):
        res = self.client.api_call(
            "chat.postMessage", channel=self.channel, text=message,
            username=self.bot_name, icon_emoji=self.bot_emoji
        )
        return [res.get("ts"), res.get("channel")]

    # post a message, react to it, and return the timestamp of the message
    def post_message_with_reactions(self, message):
        post_data = self.post_message(message)
        ts = post_data[0]
        channel = post_data[1]

        print(self.client.api_call(
            "reactions.add", channel=channel, timestamp=ts, name=self.emoji_present
        ))

        self.client.api_call(
            "reactions.add", channel=channel, timestamp=ts, name=self.emoji_absent
        )
        return ts

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

    def get_google_credentials(self):
        scopes = "https://www.googleapis.com/auth/spreadsheets"
        config = json.load(os.environ.get('GOOGLE_CONFIG'))
        return service_account.ServiceAccountCredentials.from_json_keyfile_dict(config)
