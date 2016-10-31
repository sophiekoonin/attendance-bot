import unittest
from unittest.mock import patch
import app
import os
class TestApp(unittest.TestCase):
    def setUp(self):
        self.app = app.app.test_client()


    @patch("app.AttendanceBot.get_slack_id")
    def test_process_attendance_present(self, mock_slack_id):
        mock_slack_id.return_value = "12345"
        res = self.app.post('/here', data={
            'text': "Bob Loblaw, 31/10/16",
            'command': "here",
            'token': "lkcj497Oj2t4AQlRUH4Ivm1z",
            'team_id': "T2RT9TS8M",
            'method': ['POST']
        })
        assert res.status_code == 200
        assert b"Thanks! I have updated attendance for Bob Loblaw on 31/10/16. :thumbsup:" in res.data

    @patch("app.AttendanceBot.get_slack_id")
    def test_process_attendance_not_member(self, mock_slack_id):
        mock_slack_id.return_value = None
        res = self.app.post('/here', data={
            'text': "Bob Loblaw, 31/10/16",
            'command': "here",
            'token': "lkcj497Oj2t4AQlRUH4Ivm1z",
            'team_id': "T2RT9TS8M",
            'method': ['POST']
        })
        assert b"Sorry, I couldn't find anyone with that name. :confused:" in res.data

    def dummy_func(self, slack_id, date):
        pass