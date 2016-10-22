from slackclient import SlackClient
import yaml
from apscheduler.schedulers.background import BackgroundScheduler


class AttendanceBot(object):

    def __init__(self, settings):
        token = settings.get("bot-token")

        self.bot_name = settings.get("bot-name")
        self.bot_emoji = ":{emoji}:".format(emoji=settings.get("bot-emoji"))  # wrap emoji name in colons
        self.client = SlackClient(token)
        self.channel = settings.get("channel")
        #schedule the rehearsal message post
        self.schedule(
            settings.get("rehearsal-day"),
            settings.get("post-hour"),
            settings.get("post-minute"),
            self.post_message,
            [settings.get("rehearsal-message"),
            self.channel]
        )

    # post a message and return the timestamp of the message
    def post_message(self, message):
        res = self.client.api_call(
            "chat.postMessage", channel=self.channel, text=message,
            username=self.bot_name, icon_emoji=self.bot_emoji
        )
        return res.get("ts")

    # post a message, react to it, and return the timestamp of the message
    def post_message_with_reactions(self, message):
        ts = self.post_message(message)

        self.client.api_call(
            "reactions.add", channel=self.channel, timestamp=ts, name="thumbsup"
        )

        self.client.api_call(
            "reactions.add", channel=self.channel, timestamp=ts, name="thumbsdown"
        )
        return ts

    def get_reactions(self, ts):
        res = self.client.api_call(
            "reactions.get", channel=self.channel, timestamp=ts
        )
        return res.get("message").get("reactions")

    def get_real_name(self, user_id):
        res = self.client.api_call(
            "users.info", user=user_id
        )
        return res.get("user").get("profile").get("real_name")

    def schedule(self, day, hour, mins, func, args):
        sched = BackgroundScheduler()

        @sched.scheduled_job('cron', day_of_week=day, hour=hour, minute=mins)
        def scheduled_job():
            func(*args)

        sched.start()
        print("Post scheduled for {day} at {hour}:{mins}!".format(day=day, hour=hour, mins=mins))
