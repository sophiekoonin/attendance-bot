from slackclient import SlackClient
import os
from apscheduler.schedulers.background import BackgroundScheduler
import dbutils
from datetime import datetime
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
        self.settings = settings
        token = os.environ["BOT_TOKEN"]

        self.bot_name = settings.get("bot-name")
        self.bot_emoji = ":{emoji}:".format(emoji=settings.get("bot-emoji"))  # wrap emoji name in colons
        self.client = SlackClient(token)
        self.channel = settings.get("channel")
        self.emoji_present = settings.get("emoji-present")
        self.emoji_absent = settings.get("emoji-absent")

        self.sheet_id = settings.get("spreadsheet-id")

        self.db = dbutils.connect_to_db()

    def update_members(self):
        res = self.client.api_call("users.list")
        members = res["members"]
        cur = self.db.cursor()
        current_member_data = []
        ids_for_deletion = []
        for member in members:
            if member["deleted"] == False:
                slack_id = member["id"]
                real_name = member["real_name"]
                current_member_data.append({"id":slack_id, "realname":real_name})

            else:
               ids_for_deletion.append((member["id"],))
        cur.executemany("INSERT INTO members VALUES(%(id)s, %(realname)s) ON CONFLICT (slack_id) DO UPDATE SET real_name = %(realname)s WHERE members.slack_id = %(id)s", current_member_data)
        cur.executemany("DELETE FROM members WHERE slack_id = %s", ids_for_deletion)
        dbutils.commit_or_rollback(self.db)

    def update_attendance_table(self, date):
        query = "INSERT INTO attendance(slack_id, rehearsal_date) SELECT slack_id, %s FROM Members ON CONFLICT DO NOTHING"
        cur = self.db.cursor()
        cur.execute(query, (date,))
        dbutils.commit_or_rollback(self.db)


    # post a message and return the timestamp of the message
    def post_message(self, message):
        res = self.client.api_call(
            "chat.postMessage", channel=self.channel, text=message,
            username=self.bot_name, icon_emoji=self.bot_emoji
        )
        ts = res.get("ts")
        channel_id = res.get("channel")

        post_date = datetime.fromtimestamp(float(ts)).strftime("%d/%m/%y")
        self.db.cursor().execute("INSERT INTO posts VALUES(%s, %s, %s)", (ts, post_date, channel_id))
        dbutils.commit_or_rollback(self.db)
        return [ts, channel_id]

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

    def get_latest_post_data(self):
        cur = self.db.cursor()
        cur.execute("select post_timestamp, rehearsal_date, channel_id from posts order by post_timestamp desc limit 1")
        result = cur.fetchone()
        ts = result[0]
        date = result[1]
        channel_id = result[2]
        return {"ts": ts, "date": date, "channel_id": channel_id,}

    def get_reactions(self, ts, channel):
        res = self.client.api_call(
            "reactions.get", channel=channel, timestamp=ts
        )
        return res.get("message").get("reactions")

    def record_presence(self, id, date):
        self.record_attendance(id, date, True)

    def record_absence(self, id, date):
        self.record_attendance(id, date, False)

    def record_attendance(self, id, date, present):
        cur = self.db.cursor()
        cur.execute("UPDATE attendance SET present=(%s) WHERE slack_id=(%s) AND rehearsal_date=(%s)", (present, id, date))
        dbutils.commit_or_rollback(self.db)

    def process_attendance(self):
        self.update_members()
        post_data = self.get_latest_post_data()
        ts = post_data["ts"]
        channel_id = post_data["channel_id"]
        date = post_data["date"]
        self.update_attendance_table(date)
        reactions = self.get_reactions(ts, channel_id)
        for reaction in reactions:
            if reaction["name"] == "thumbsup":
                for user in reaction["users"]:
                    self.record_presence(user, date)
            elif reaction["name"] == "thumbsdown":
                for user in reaction["users"]:
                    self.record_absence(user, date)
            else:
                pass

if __name__ == "__main__":
    # schedule the rehearsal message post
    bot = AttendanceBot(yaml.parse(open('../settings.yaml')))
    schedule(
        bot.settings.get("rehearsal-day"),
        bot.settings.get("post-hour"),
        bot.settings.get("post-minute"),
        bot.post_message_with_reactions,
        [bot.settings.get("rehearsal-message")]
    )