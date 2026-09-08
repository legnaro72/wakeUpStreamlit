import unittest

import wake_streamlit


class WakeStreamlitHelpersTest(unittest.TestCase):
    def test_unique_urls_preserves_order(self):
        urls = ["https://one.example/", "https://two.example/", "https://one.example/"]

        self.assertEqual(
            wake_streamlit.unique_urls(urls),
            ["https://one.example/", "https://two.example/"],
        )

    def test_wake_button_pattern_accepts_known_labels(self):
        labels = (
            "Yes, get this app back up!",
            "Get this app back up!",
            "Wake this app up",
            "Wake app up",
        )

        for label in labels:
            with self.subTest(label=label):
                self.assertIsNotNone(wake_streamlit.WAKE_BUTTON_PATTERN.search(label))

    def test_sleep_message_pattern_accepts_known_messages(self):
        messages = (
            "This app has gone to sleep",
            "This app is to sleep. Get this app back up!",
        )

        for message in messages:
            with self.subTest(message=message):
                self.assertIsNotNone(wake_streamlit.SLEEP_MESSAGE_PATTERN.search(message))


if __name__ == "__main__":
    unittest.main()
