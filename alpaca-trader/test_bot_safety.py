"""Paper-only allocation safeguards; all HTTP calls are mocked."""

import unittest
from unittest.mock import Mock, patch

import bot


class PaperAllocationSafetyTests(unittest.TestCase):
    def test_initial_order_has_stable_idempotency_identifier(self):
        with patch.object(bot.requests, "post", return_value=Mock(status_code=201, text="ok")) as post:
            bot.submit_order("SPY", 2)
        self.assertEqual(post.call_args.kwargs["json"]["client_order_id"], "lionel-initial-v1-SPY")

    def test_fresh_account_preflight_reads_only(self):
        with patch.object(bot.requests, "get", side_effect=[
            Mock(status_code=200, json=lambda: []),
            Mock(status_code=200, json=lambda: []),
        ]) as get, patch.object(bot.requests, "post") as post:
            bot.ensure_fresh_paper_account()
        self.assertEqual(get.call_count, 2)
        self.assertEqual(get.call_args.kwargs["params"], {"status": "all", "limit": 1})
        post.assert_not_called()

    def test_existing_order_blocks_before_any_submission(self):
        with patch.object(bot, "LIVE", True), patch.object(bot, "check_keys"), patch.object(
            bot.requests, "get", side_effect=[
                Mock(status_code=200, json=lambda: []),
                Mock(status_code=200, json=lambda: [{"id": "prior-order"}]),
            ]
        ), patch.object(bot, "get_price") as price, patch.object(bot, "submit_order") as submit:
            with self.assertRaisesRegex(RuntimeError, "bereits Positionen oder Orders"):
                bot.main()
        price.assert_not_called()
        submit.assert_not_called()

    def test_unverifiable_account_fails_closed(self):
        with patch.object(bot.requests, "get", return_value=Mock(status_code=503)):
            with self.assertRaisesRegex(RuntimeError, "konnte nicht geprueft"):
                bot.ensure_fresh_paper_account()


if __name__ == "__main__":
    unittest.main()
