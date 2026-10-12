import unittest
from core.time_checker import validate_time


class TimeTests(unittest.TestCase):
    def test_sample(self):
        r = validate_time('7:55', '16:45', [('11:50', '12:35')])
        self.assertEqual((r.result, r.effective_minutes), ('pass', 485))

    def test_threshold(self):
        for end, status, minutes in [('16:15', 'pass', 450), ('16:14', 'fail', 449)]:
            r = validate_time('8:00', end, [('12:00', '12:45')])
            self.assertEqual((r.result, r.effective_minutes), (status, minutes))

    def test_missing_never_defaults(self):
        self.assertEqual(validate_time('8:00', '17:00', []).result, 'needs_review')
        self.assertEqual(validate_time('8:00', '17:00', [('', '')]).result, 'needs_review')

    def test_invalid_and_overnight(self):
        for a, b, breaks in [('25:00', '17:00', []), ('8:60', '17:00', []),
                             ('20:00','5:00',[('0:00','0:45')]),
                             ('8:00','17:00',[('7:00','7:45')]),
                             ('8:00','17:00',[('12:45','12:00')]),
                             ('8:00','17:00',[('12:00','13:00'),('12:30','13:30')])]:
            with self.subTest(a=a, b=b, breaks=breaks):
                self.assertEqual(validate_time(a, b, breaks).result, 'needs_review')

    def test_multiple_breaks_and_confirmed_none(self):
        self.assertEqual(validate_time('8:00','17:00',[('15:00','15:15'),('12:00','12:45')]).effective_minutes, 480)
        self.assertEqual(validate_time('8:00','17:00',[], no_break_confirmed=True).effective_minutes, 540)
