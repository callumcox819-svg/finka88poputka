import unittest
from unittest.mock import AsyncMock, patch

from services.validemail_pool import ValidemailKeyPool, find_deliverable_email


class ValidemailPoolTest(unittest.TestCase):
    async def _run(self, coro):
        import asyncio

        return await coro

    def test_skips_dead_key_and_uses_next(self) -> None:
        pool = ValidemailKeyPool(
            ["key1", "key2"],
            url="https://validemail.co/api/v1/validate",
            timeout_sec=8,
            concurrency_per_key=2,
        )

        async def fake_validate(email, *, api_key, url, timeout_sec):
            if api_key == "key1":
                return False, "payment_required", {}
            return True, "deliverable", {}

        with patch(
            "services.validemail_pool.validate_email_api",
            new=AsyncMock(side_effect=fake_validate),
        ):
            import asyncio

            ok, reason, _ = asyncio.run(pool.validate("test@gmail.com"))
            self.assertTrue(ok)
            self.assertEqual(reason, "deliverable")
            self.assertEqual(pool.live_key_count, 1)

    def test_all_keys_dead_is_fatal(self) -> None:
        pool = ValidemailKeyPool(
            ["key1"],
            url="https://validemail.co/api/v1/validate",
            timeout_sec=8,
            concurrency_per_key=2,
        )
        pool.mark_dead(0, "payment_required")
        self.assertEqual(pool.live_key_count, 0)


if __name__ == "__main__":
    unittest.main()
