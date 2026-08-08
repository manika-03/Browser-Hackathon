import unittest
import logging

from mori_gateway.backend import MockBackend
from mori_gateway.models import Action, Result, chunks
from mori_gateway.telegram_app import RedactingFormatter


class GatewayTests(unittest.IsolatedAsyncioTestCase):
    async def test_learning_prompt(self) -> None:
        result = await MockBackend().respond({"event": {"type": "text", "text": "I want to be an ML engineer"}})
        self.assertIn("current level", result.text)
        self.assertEqual(len(result.actions), 2)

    def test_response_contract(self) -> None:
        result = Result.parse({"text": "Ready", "actions": [{"id": "go", "label": "Go"}]})
        self.assertEqual(result.actions[0], Action("go", "Go"))

    def test_https_is_required_for_urls(self) -> None:
        with self.assertRaises(ValueError):
            Action.parse({"id": "x", "label": "Open", "kind": "url", "url": "http://example.com"})

    def test_long_messages_split(self) -> None:
        self.assertGreater(len(chunks("word " * 100, 120)), 1)

    def test_token_is_redacted_from_formatted_logs(self) -> None:
        token = "123456:secret-token"
        formatter = RedactingFormatter(token)
        record = logging.LogRecord(
            "httpx",
            logging.INFO,
            __file__,
            1,
            "POST https://api.telegram.org/bot%s/getMe",
            (token,),
            None,
        )
        output = formatter.format(record)
        self.assertNotIn(token, output)
        self.assertIn("[REDACTED]", output)


if __name__ == "__main__":
    unittest.main()
