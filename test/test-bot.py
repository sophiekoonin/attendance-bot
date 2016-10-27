import json
import unittest
from unittest.mock import patch
from bot import AttendanceBot
import yaml
import dbutils

@patch("bot.SlackClient.api_call")
class TestBot(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        settings = yaml.load(open("../settings.yaml"))
        self.bot = AttendanceBot(settings)
        self.test_db = dbutils.connect_to_db()
        cur = self.test_db.cursor()
        cur.execute("CREATE TABLE if not exists Members(SlackID varchar(255), RealName varchar(255))")
        cur.execute("CREATE TABLE if not exists Posts(PostTimestamp varchar(255), PostDate varchar(255))")
        self.test_db.commit()

    def test_init_func(self, mock_api_call):
        self.assertEqual(self.bot.bot_name, "attendance-bot")
        self.assertEqual(self.bot.bot_emoji, ":memo:")

    def test_post_message(self, mock_api_call):
        expected_value = ['12345', 'abc123']
        mock_api_call.return_value = {"ts": "12345", "channel": "abc123"}

        result = self.bot.post_message("test_message")
        self.assertEqual(result, expected_value)

    def test_get_reactions(self, mock_api_call):
        expected_value = [{"name": "foo", "users": ["user1", "user2"]}]
        mock_api_call.return_value = {"message": {"reactions": expected_value}}
        result = self.bot.get_reactions("test_timestamp", "test_channel")
        self.assertEqual(result, expected_value)

    def test_get_real_name_not_present(self, mock_api_call):
        expected_value = "Bobby Tables"
        mock_api_call.return_value = {"ok": "true", "user": { "profile": {"real_name": "Bobby Tables"}}}

        result = self.bot.get_real_name("12345")
        self.assertEqual(result, expected_value)

    def test_get_real_name_is_present(self, mock_api_call):
        self.test_db.cursor().execute("INSERT INTO Members VALUES(%s, %s)", ("54321", "Robert Tables"))
        self.test_db.commit()
        expected_value = "Robert Tables"
        result = self.bot.get_real_name("54321")
        self.assertEqual(result, expected_value)

    @classmethod
    def tearDownClass(self):
        self.bot.db.close()
        cur = self.test_db.cursor()
        cur.execute("DROP TABLE Members, Posts")
        self.test_db.commit()
        self.test_db.close()