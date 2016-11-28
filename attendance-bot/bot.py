from slackclient import SlackClient
import os
import dbutils
from datetime import datetime


class AttendanceBot(object):
    def __init__(self, settings):
        self.settings = settings
        token = os.environ.get("BOT_TOKEN")

        self.bot_name = os.environ.get("BOT_NAME")
        self.bot_emoji = ":{emoji}:".format(emoji=os.environ.get("BOT_EMOJI"))  # wrap emoji name in colons
        self.client = SlackClient(token)
        self.channel = os.environ.get("CHANNEL")
        self.emoji_present = os.environ.get("EMOJI_PRESENT")
        self.emoji_absent = os.environ.get("EMOJI_ABSENT")

        self.db = dbutils.connect_to_db()
        self.create_tables()

    def create_tables(self):
        cur = self.db.cursor()

        members_query = ("CREATE TABLE IF NOT EXISTS members"
                         "(slack_id varchar(255) PRIMARY KEY, "
                         "real_name varchar(255) NOT NULL,"
                         "ignore boolean)")
        posts_query = ("CREATE TABLE IF NOT EXISTS posts"
                       "(post_timestamp varchar(255) PRIMARY KEY, "
                       "rehearsal_date varchar(255) UNIQUE NOT NULL, "
                       "channel_id varchar(255) NOT NULL)")
        attendance_query = ("CREATE TABLE IF NOT EXISTS attendance"
                            "(slack_id varchar(255) REFERENCES members(slack_id) ON DELETE CASCADE, "
                            "post_timestamp varchar(255) REFERENCES posts(post_timestamp), "
                            "present boolean, "
                            "PRIMARY KEY (slack_id, post_timestamp))")

        cur.execute(members_query)
        cur.execute(posts_query)
        cur.execute(attendance_query)
        dbutils.commit_or_rollback(self.db)

    def update_members(self):
        res = self.client.api_call("users.list")
        members = res["members"]
        cur = self.db.cursor()
        current_member_data = []
        ids_for_deletion = []
        for member in members:
            if not member["deleted"]:
                slack_id = member["id"]
                real_name = member["real_name"]
                current_member_data.append({"id": slack_id, "realname": real_name})
            else:
                ids_for_deletion.append((member["id"],))

        insertion_query = ("INSERT INTO members VALUES(%(id)s, %(realname)s, FALSE) "
                           "ON CONFLICT (slack_id) DO UPDATE "
                           "SET real_name = %(realname)s "
                           "WHERE members.slack_id = %(id)s")
        cur.executemany(insertion_query, current_member_data)
        cur.executemany("DELETE FROM members WHERE slack_id = (%s)", ids_for_deletion)
        dbutils.commit_or_rollback(self.db)

    def update_attendance_table(self, timestamp):
        query = ("INSERT INTO attendance(slack_id, post_timestamp)"
                 "SELECT slack_id, (%s) FROM Members WHERE ignore = FALSE ON CONFLICT DO NOTHING")
        cur = self.db.cursor()
        cur.execute(query, (timestamp,))
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
        self.db.cursor().execute("INSERT INTO posts VALUES(%s, %s, %s) ON CONFLICT DO NOTHING", (ts, post_date, channel_id))
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
        query = "SELECT post_timestamp, channel_id FROM posts ORDER BY post_timestamp DESC LIMIT 1"
        result = dbutils.execute_fetchone(self.db, query)
        if result is None:
            return result
        ts = result[0]
        channel_id = result[1]
        return {"ts": ts, "channel_id": channel_id}

    def get_reactions(self, ts, channel):
        res = self.client.api_call(
            "reactions.get", channel=channel, timestamp=ts
        )
        return res.get("message").get("reactions")

    def get_slack_id(self, real_name):
        query = "SELECT slack_id FROM members WHERE real_name = (%s)"
        result = dbutils.execute_fetchone(self.db, query, (real_name,))
        if result is None:
            self.update_members()
            result = dbutils.execute_fetchone(self.db, query, (real_name,))
            if result is None:
                return result
        return result[0]

    def get_timestamp(self, date):
        query = "SELECT post_timestamp FROM posts WHERE rehearsal_date = (%s)"
        result = dbutils.execute_fetchone(self.db, query, (date,))
        if result is None:
            return result
        return result[0]

    def record_presence(self, slack_id, timestamp):
        self.record_attendance(slack_id, timestamp, True)

    def record_absence(self, slack_id, timestamp):
        self.record_attendance(slack_id, timestamp, False)

    def record_attendance(self, slack_id, timestamp, present):
        query = "UPDATE attendance SET present=(%s) WHERE slack_id=(%s) AND post_timestamp=(%s)"
        dbutils.execute_and_commit(self.db, query, [present, slack_id, timestamp])

    def process_attendance(self):
        self.update_members()
        post_data = self.get_latest_post_data()
        if post_data is None:
            return "Nothing to process!"  # Don't try to process attendance if there's nothing in posts db
        ts = post_data.get("ts")
        channel_id = post_data.get("channel_id")
        self.update_attendance_table(ts)
        reactions = self.get_reactions(ts, channel_id)
        present_count = 0
        absent_count = 0
        for reaction in reactions:
            if reaction.get("name") == self.emoji_present:
                for user in reaction.get("users"):
                    present_count += 1
                    self.record_presence(user, ts)
            elif reaction.get("name") == self.emoji_absent:
                for user in reaction.get("users"):
                    absent_count += 1
                    self.record_absence(user, ts)
            else:
                pass
        return "Attendance processed! There were {} present and {} absences.".format(present_count, absent_count)

    def get_absent_names(self):
        query = ("SELECT DISTINCT m.real_name "
                 "FROM (SELECT a.slack_id FROM attendance as a "
                 "WHERE a.post_timestamp IN "
                 "(SELECT p.post_timestamp FROM posts AS p "
                 "ORDER BY p.post_timestamp DESC LIMIT 4) "
                 "AND a.present IS NULL "
                 "GROUP BY slack_id "
                 "HAVING COUNT(slack_id) = 4) "
                 "AS Q NATURAL JOIN MEMBERS AS M")
        results = dbutils.execute_fetchall(self.db, query)
        names = []
        for result_tuple in results:
            names.append("\n")
            names.append(result_tuple[0])
        return names

    def set_ignore(self, slack_id, flag):
        query = "UPDATE members SET ignore = (%s) WHERE SLACK_ID = (%s)"
        dbutils.execute_and_commit(self.db, query, [flag, slack_id])

    def is_admin(self, slack_id):
        res = self.client.api_call('users.info', user=slack_id)
        return res.get("user").get("is_admin")

    def create_absence_message(self):
        absent_list = self.get_absent_names()
        if len(absent_list) == 0:
            return "Nobody has been absent 4 weeks in a row! :tada:"
        msg = ":robot_face: :memo: The following members have been absent for the last 4 rehearsals: "
        msg += ''.join(absent_list)
        return msg
