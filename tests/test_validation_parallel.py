import os
import unittest

from services.void_validation_runner import validation_parallel_workers


class ValidationParallelTest(unittest.TestCase):
    def test_default_scales_with_keys_and_per_key_cap(self) -> None:
        old_w = os.environ.pop("VALIDEMAIL_PARALLEL_WORKERS", None)
        old_f = os.environ.pop("VALIDEMAIL_PARALLEL_FACTOR", None)
        try:
            n = validation_parallel_workers(5, per_key=8, max_concurrent=40)
            self.assertEqual(n, 10)
        finally:
            if old_w is not None:
                os.environ["VALIDEMAIL_PARALLEL_WORKERS"] = old_w
            if old_f is not None:
                os.environ["VALIDEMAIL_PARALLEL_FACTOR"] = old_f

    def test_explicit_workers_capped_by_pool(self) -> None:
        old = os.environ.get("VALIDEMAIL_PARALLEL_WORKERS")
        os.environ["VALIDEMAIL_PARALLEL_WORKERS"] = "99"
        try:
            n = validation_parallel_workers(3, per_key=4, max_concurrent=12)
            self.assertEqual(n, 12)
        finally:
            if old is None:
                os.environ.pop("VALIDEMAIL_PARALLEL_WORKERS", None)
            else:
                os.environ["VALIDEMAIL_PARALLEL_WORKERS"] = old


if __name__ == "__main__":
    unittest.main()
