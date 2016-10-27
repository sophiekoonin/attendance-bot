from slackclient import SlackClient
import os
from apscheduler.schedulers.background import BackgroundScheduler
import dbutils
from datetime import datetime


def schedule(day, hour, mins, func, args):
    sched = BackgroundScheduler()

    @sched.scheduled_job('cron', day_of_week=day, hour=hour, minute=mins)
    def scheduled_job():
        func(*args)

    sched.start()
    print("Post scheduled for {day} at {hour}:{mins}!".format(day=day, hour=hour, mins=mins))


class AttendanceBot(object):
    def __init__(self, settings):
        token = os.environ["BOT_TOKEN"]

        self.bot_name = settings.get("bot-name")
        self.bot_emoji = ":{emoji}:".format(emoji=settings.get("bot-emoji"))  # wrap emoji name in colons
        self.client = SlackClient(token)
        self.channel = settings.get("channel")
        self.emoji_present = settings.get("emoji-present")
        self.emoji_absent = settings.get("emoji-absent")

        self.sheet_id = settings.get("spreadsheet-id")

        self.db = dbutils.connect_to_db()


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
        ts = res.get("ts")
        channelID = res.get("channel")

        post_date = datetime.fromtimestamp(float(ts)).strftime("%d/%m/%y")
        self.db.cursor().execute("INSERT INTO posts VALUES(%s, %s)", (ts, post_date))
        dbutils.commit_or_rollback(self.db)
        return [ts, channelID]

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

    def get_latest_post_timestamp(self):
        cur = self.db.cursor()
        cur.execute("select posttimestamp from posts order by posttimestamp desc limit 1")
        ts = cur.fetchone()[0]
        return ts

    def get_reactions(self, ts, channel):
        res = self.client.api_call(
            "reactions.get", channel=channel, timestamp=ts
        )
        return res.get("message").get("reactions")

    def get_real_name(self, user_id):
        cur = self.db.cursor()
        cur.execute("SELECT RealName FROM Members WHERE SlackID=(%s)", (user_id,))
        result = cur.fetchone()
        name = ""
        if (result == None):  # if the name isn't in the db, find it through an api call and store it for next time
            result = self.client.api_call(
                "users.info", user=user_id
            )
            name = result.get("user").get("profile").get("real_name")
            cur.execute("INSERT INTO members VALUES (%s, %s)", (user_id, name))
            dbutils.commit_or_rollback(self.db)

        else:
            name = result[0]
        return name

    def record_attendance(self, id, date):
        cur = self.db.cursor()
        cur.execute("UPDATE attendance SET present=TRUE WHERE slackid=(%s) AND rehearsaldate=(%s)",(id, date))
        dbutils.commit_or_rollback(self.db)

