import unittest

from services.seller_name import (
    make_email_local,
    make_email_local_variants,
    seller_name_eligible,
    split_name_parts,
)


class SellerNameTest(unittest.TestCase):
    def test_single_name(self) -> None:
        self.assertEqual(make_email_local("Karina"), "karina")
        self.assertTrue(seller_name_eligible("Karina"))

    def test_hyphen(self) -> None:
        self.assertEqual(split_name_parts("hanne-elina"), ["hanne", "elina"])
        self.assertEqual(make_email_local("hanne-elina"), "hanne.elina")

    def test_space_two_words(self) -> None:
        self.assertEqual(make_email_local("seppo Olli"), "seppo.olli")

    def test_connector_ja(self) -> None:
        variants = make_email_local_variants("Leena ja Pauli")
        self.assertEqual(variants[0], "leena.ja.pauli")
        self.assertIn("leena.pauli", variants)

    def test_variants_dedupe(self) -> None:
        variants = make_email_local_variants("Anna Maria")
        self.assertEqual(variants[0], "anna.maria")
        self.assertLessEqual(len(variants), 3)


if __name__ == "__main__":
    unittest.main()
