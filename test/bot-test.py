import json
import unittest
from unittest.mock import patch, MagicMock
import bot

class TestBot(unittest.TestCase):

    @patch("bot.SlackClient.api_call")
    def test_post_message(self, mock_api_call):
        expected_value = ['12345', 'abc123']
        mock_api_call.return_value = {"ts" : "12345", "channel": "abc123"}

        result = bot.post_message("test", "test")
        self.assertEqual(result, expected_value)