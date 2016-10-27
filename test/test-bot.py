import json
import unittest
from unittest.mock import patch
from bot import AttendanceBot
import yaml
import dbutils

class TestBot(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        settings = yaml.load(open("../settings.yaml"))
        self.bot = AttendanceBot(settings)
        self.test_db = dbutils.connect_to_db()
        cur = self.test_db.cursor()
        cur.execute("CREATE TABLE if not exists Members(SlackID varchar(255) not null primary key, RealName varchar(255) not null)")
        cur.execute("CREATE TABLE if not exists Posts(PostTimestamp varchar(255) not null primary key, RehearsalDate varchar(255) unique not null)")
        cur.execute("CREATE TABLE if not exists Attendance(SlackID varchar(255) references Members(SlackId), RehearsalDate varchar(255) references Posts(RehearsalDate), Present boolean)")
        dbutils.commit_or_rollback(self.test_db)

    def test_init_func(self):
        self.assertEqual(self.bot.bot_name, "attendance-bot")
        self.assertEqual(self.bot.bot_emoji, ":memo:")

    @patch("bot.SlackClient.api_call")
    def test_post_message_posts_message(self, mock_api_call):
        expected_value = ['12345', 'abc123']
        mock_api_call.return_value = {"ts": "12345", "channel": "abc123"}
        result = self.bot.post_message("test_message")
        self.assertEqual(result, expected_value)

    @patch("bot.SlackClient.api_call")
    def test_post_message_persists_timestamp(self, mock_api_call):
        mock_api_call.return_value = {"ts" : "543210", "channel": "abc123"}
        self.bot.post_message("test_message")
        cur = self.test_db.cursor()
        cur.execute("SELECT * FROM posts WHERE posttimestamp='543210'")
        result = cur.fetchone()
        self.assertIsNotNone(result)

    @patch("bot.SlackClient.api_call")
    def test_post_message_stores_post_date(self, mock_api_call):
        test_ts = "1477908000"
        expected_value = "31/10/16"
        mock_api_call.return_value = {"ts": "1477908000", "channel": "abc123"}
        self.bot.post_message("test_message")
        cur = self.test_db.cursor()
        cur.execute("select postdate from posts where posttimestamp=(%s)", (test_ts,))
        result = cur.fetchone()[0]
        self.assertEqual(result, expected_value)

    def test_get_latest_post_timestamp(self):
        cur = self.test_db.cursor()
        cur.execute("insert into posts values('1477908005', '31/10/16'), ('1477908006', '31/10/16'), ('1477908007', '31/10/16')")
        dbutils.commit_or_rollback(self.test_db)
        expected_value = "1477908007"
        result = self.bot.get_latest_post_timestamp()
        self.assertEqual(result, expected_value)

    @patch("bot.SlackClient.api_call")
    def test_get_reactions(self, mock_api_call):
        expected_value = [{"name": "foo", "users": ["user1", "user2"]}]
        mock_api_call.return_value = {"message": {"reactions": expected_value}}
        result = self.bot.get_reactions("test_timestamp", "test_channel")
        self.assertEqual(result, expected_value)

    @patch("bot.SlackClient.api_call")
    def test_get_real_name_not_present(self, mock_api_call):
        expected_value = "Bobby Tables"
        mock_api_call.return_value = {"ok": "true", "user": { "profile": {"real_name": "Bobby Tables"}}}

        result = self.bot.get_real_name("12345")
        self.assertEqual(result, expected_value)

    def test_get_real_name_is_present(self):
        self.test_db.cursor().execute("INSERT INTO Members VALUES(%s, %s)", ("54321", "Robert Tables"))
        dbutils.commit_or_rollback(self.test_db)
        expected_value = "Robert Tables"
        result = self.bot.get_real_name("54321")
        self.assertEqual(result, expected_value)

    def test_record_attendance(self):
        expected_value = True
        self.bot.record_attendance("12345", "31/10/16")
        cur = self.test_db.cursor()
        cur.execute("select Present from Attendance where SlackID='12345' and RehearsalDate='31/10/16'")
        result = cur.fetchone()
        self.assertEqual(result, expected_value)

    @classmethod
    def tearDownClass(self):
        self.bot.db.close()
        cur = self.test_db.cursor()
        cur.execute("DROP TABLE Members, Posts")
        dbutils.commit_or_rollback(self.test_db)
        self.test_db.close()