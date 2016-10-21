import json
import unittest
from unittest.mock import patch
import bot

class TestBot(unittest.TestCase):

    @patch("bot.SlackClient.api_call")
    def test_post_message(self, mock_api_call):
        expected_value = ['12345', 'abc123']
        mock_api_call.return_value = {"ts" : "12345", "channel": "abc123"}

        result = bot.post_message("test_message", "test_channel")
        self.assertEqual(result, expected_value)

    @patch("bot.SlackClient.api_call")
    def test_get_reactions(self, mock_api_call):
        expected_value=[{"name" : "foo", "users" : ["user1", "user2"]}]
        mock_api_call.return_value = {"message": {"reactions": expected_value}}

        result = bot.get_reactions("test_timestamp", "test_channel")
        self.assertEqual(result, expected_value)