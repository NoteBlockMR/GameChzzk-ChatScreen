import unittest
from channel import channel_id, chat_url


class ChannelTests(unittest.TestCase):
    def test_valid(self):
        key = "0123456789abcdef0123456789abcdef"
        for value in [key.upper(), f" https://chzzk.naver.com/{key} ",
                      f"https://chzzk.naver.com/live/{key}?from=share",
                      f"https://chzzk.naver.com/live/{key}/chat"]:
            self.assertEqual(channel_id(value), key)
        self.assertEqual(chat_url(key), f"https://chzzk.naver.com/live/{key}/chat?theme=dark")

    def test_reject(self):
        for value in ["", "invalid", "javascript:alert(1)", "https://chzzk.naver.com.evil.test/abc",
                      "https://chzzk.naver.com/video/123", "https://chzzk.naver.com:bad/abc",
                      "https://chzzk.naver.com@evil.test/abc"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                channel_id(value)


if __name__ == "__main__":
    unittest.main()
