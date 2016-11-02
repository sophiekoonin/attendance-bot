import unittest
from unittest.mock import patch
import app
import os
class TestApp(unittest.TestCase):
    def setUp(self):
        self.app = app.app.test_client()
        self.token = os.environ.get('SLASH_TOKEN')
        self.team = os.environ.get('SLACK_TEAM_ID')

    @patch("app.AttendanceBot.create_absence_message")
    def test_attendance_report(self, mock_attendance_msg):
        mock_attendance_msg.return_value = "The following members have been absent:\nTobias Funke\nBob Loblaw"
        res = self.app.post('/attendance', data={
            'text': "report",
            'command': "attendance",
            'token': self.token,
            'team_id': self.team,
            'method': ['POST']
        })
        assert res.status_code == 200
        assert b"The following members have been absent" in res.data
        assert b"Tobias Funke" in res.data

    def test_attendance_noargs(self):
        res = self.app.post('/attendance', data={
            'text': "",
            'command': "attendance",
            'token': self.token,
            'team_id': self.team,
            'method': ['POST']
        })
        assert res.status_code == 200
        assert b"I am the attendance bot! :robot_face::memo:" in res.data

    def test_attendance_bad_args(self):
        res = self.app.post('/attendance', data={
            'text': "foo",
            'command': "attendance",
            'token': self.token,
            'team_id': self.team,
            'method': ['POST']
        })
        assert res.status_code == 200
        assert b"Sorry, I didn't understand that command." in res.data


    def test_attendance_help(self):
        res = self.app.post('/attendance', data={
            'text': "help",
            'command': "attendance",
            'token': self.token,
            'team_id': self.team,
            'method': ['POST']
        })
        assert res.status_code == 200
        assert b"I am the attendance bot! :robot_face::memo:" in res.data

    @patch("app.AttendanceBot.get_timestamp")
    def test_process_attendance_bad_date(self, mock_timestamp):
        mock_timestamp.return_value = None
        res = self.app.post('/attendance', data={
            'text': "here 31/10/16 Bob Loblaw ",
            'command': "attendance",
            'token': self.token,
            'team_id': self.team,
            'method': ['POST']
        })
        assert b"that date doesn\'t seem to match up" in res.data

    def test_bankholiday_call_no_args(self):
        res = self.app.post('/attendance', data={
            'text': "bankholiday",
            'command': "attendance",
            'token': self.token,
            'team_id': self.team,
            'method': ['POST']
        })
        assert b"Date needed!" in res.data

    @patch("app.AttendanceBot.pause_scheduled_jobs")
    def test_bankholiday_call(self, mock_pause):
        mock_pause.return_value = True
        res = self.app.post('/attendance', data={
            'text': "bankholiday 31/10/16",
            'command': "attendance",
            'token': self.token,
            'team_id': self.team,
            'method': ['POST']
        })
        assert b"I have been paused until the week after 31/10/16" in res.data

    def test_resume_job(self):
        res = self.app.post('/attendance', data={
            'text': "resumejobs",
            'command': "attendance",
            'token': self.token,
            'team_id': self.team,
            'method': ['POST']
        })
        assert b"jobs resumed" in res.data

    @patch("app.AttendanceBot.get_slack_id")
    @patch("app.AttendanceBot.is_admin")
    @patch("app.AttendanceBot.set_ignore")
    def test_set_ignore(self, mock_ignore, mock_admin, mock_slack_id):
        mock_admin.return_value = True
        mock_ignore.return_value = None
        mock_slack_id.return_value = "12345"
        res = self.app.post('/attendance', data= {
            'text': 'ignore Tobias Funke',
            'command': 'attendance',
            'token': self.token,
            'team_id': self.team,
            'method': ['POST']
        })
        assert b"Tobias Funke has been set to ignore = True" in res.data

    @patch("app.AttendanceBot.get_slack_id")
    @patch("app.AttendanceBot.is_admin")
    @patch("app.AttendanceBot.set_ignore")
    def test_set_ignore_stop(self, mock_ignore, mock_admin, mock_slack_id):
        mock_admin.return_value = True
        mock_ignore.return_value = None
        mock_slack_id.return_value = "12345"
        res = self.app.post('/attendance', data={
            'text': 'ignore stop Tobias Funke',
            'command': 'attendance',
            'token': self.token,
            'team_id': self.team,
            'method': ['POST']
        })
        assert b"Tobias Funke has been set to ignore = False" in res.data

    @patch("app.AttendanceBot.is_admin")
    def test_check_admin_true(self, mock_admin):
        mock_admin.return_value = True
        res = app.check_admin("12345", self.dummy_func)
        self.assertTrue(res)

    @patch("app.AttendanceBot.is_admin")
    def test_check_admin_false(self, mock_admin):
        mock_admin.return_value = False
        res = app.check_admin("12345", self.dummy_func)
        assert "Sorry, you don't have permission" in res

    def dummy_func(self, *args):
        return True