"""Маршрутизация HTML-шаблонов Aqua (Tori.fi / Posti.fi → HTMLfi)."""

from __future__ import annotations

import unittest

from services.aqua_keys import (
    aqua_service_for_html_dir,
    aqua_service_from_link,
    normalize_aqua_service,
    resolve_aqua_service,
)
from services.html_templates import (
    BACK_FILENAME,
    GO_FILENAME,
    html_subdir_for_service,
    html_template_path,
)


class GagHtmlRoutingTest(unittest.TestCase):
    def test_services_normalize(self) -> None:
        self.assertEqual(normalize_aqua_service("tori.fi"), "tori_fi")
        self.assertEqual(normalize_aqua_service("posti.fi"), "posti_fi")
        self.assertEqual(aqua_service_from_link("https://www.tori.fi/a/123"), "tori_fi")
        self.assertEqual(aqua_service_from_link("https://www.posti.fi/ilmoitus/1"), "posti_fi")

    def test_tori_maps_to_tori_fi_folder(self) -> None:
        self.assertEqual(aqua_service_for_html_dir("tori_fi"), "tori_fi")

    def test_posti_maps_to_posti_fi_folder(self) -> None:
        self.assertEqual(aqua_service_for_html_dir("posti_fi"), "posti_fi")

    def test_go_back_exist_for_tori(self) -> None:
        svc = "tori_fi"
        go = html_template_path(svc, GO_FILENAME)
        back = html_template_path(svc, BACK_FILENAME)
        self.assertIsNotNone(go, "GO missing for tori_fi")
        self.assertIsNotNone(back, "BACK missing for tori_fi")
        self.assertEqual(html_subdir_for_service(svc), "tori_fi")

    def test_go_back_exist_for_posti(self) -> None:
        svc = "posti_fi"
        go = html_template_path(svc, GO_FILENAME)
        back = html_template_path(svc, BACK_FILENAME)
        self.assertIsNotNone(go, "GO missing for posti_fi")
        self.assertIsNotNone(back, "BACK missing for posti_fi")
        self.assertEqual(html_subdir_for_service(svc), "posti_fi")

    def test_unknown_service_no_path(self) -> None:
        self.assertIsNone(html_template_path("", GO_FILENAME))
        self.assertIsNone(html_template_path("ebay_de", GO_FILENAME))

    def test_facebook_uses_profile_service(self) -> None:
        fb = "https://www.facebook.com/marketplace/item/123"
        self.assertIsNone(aqua_service_from_link(fb))
        self.assertEqual(
            resolve_aqua_service(offer_link=fb, user_setting="posti_fi"),
            "posti_fi",
        )
        self.assertEqual(
            resolve_aqua_service(offer_link=fb, user_setting="tori_fi"),
            "tori_fi",
        )

    def test_profile_overrides_marketplace_link(self) -> None:
        self.assertEqual(
            resolve_aqua_service(
                offer_link="https://www.tori.fi/a/1",
                user_setting="posti_fi",
            ),
            "posti_fi",
        )
        self.assertEqual(
            resolve_aqua_service(
                offer_link="https://www.posti.fi/ilmoitus/1",
                user_setting="tori_fi",
            ),
            "tori_fi",
        )


if __name__ == "__main__":
    unittest.main()
