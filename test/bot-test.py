import json
import unittest
from unittest.mock import patch
from bot import AttendanceBot

@patch("bot.SlackClient.api_call")
class TestBot(unittest.TestCase):

    @patch("bot.yaml.load")
    def mocked_bot_factory(self, mock_yaml_load):
        mock_yaml_load.return_value = {"bot-token": "abc123", "bot-name": "testbot", "bot-emoji": "test"}
        return AttendanceBot()

    def setUp(self):
        self.bot = self.mocked_bot_factory()

    def test_init_func(self, mock_api_call):
        self.assertEqual(self.bot.bot_name, "testbot")
        self.assertEqual(self.bot.bot_emoji, ":test:")

    def test_post_message(self, mock_api_call):
        expected_value = ['12345', 'abc123']
        mock_api_call.return_value = {"ts": "12345", "channel": "abc123"}

        result = self.bot.post_message("test_message", "test_channel")
        self.assertEqual(result, expected_value)

    def test_get_reactions(self, mock_api_call):
        expected_value = [{"name": "foo", "users": ["user1", "user2"]}]
        mock_api_call.return_value = {"message": {"reactions": expected_value}}

        result = self.bot.get_reactions("test_timestamp", "test_channel")
        self.assertEqual(result, expected_value)

