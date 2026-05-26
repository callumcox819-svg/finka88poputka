"""Маршрутизация HTML-шаблонов по сервису Aqua (Tori.fi / HTMLfi)."""

from __future__ import annotations

import unittest

from services.aqua_keys import aqua_service_for_html_dir as gag_service_for_html_dir
from services.html_templates import (
    BACK_FILENAME,
    GO_FILENAME,
    html_subdir_for_service,
    html_template_path,
)


class GagHtmlRoutingTest(unittest.TestCase):
    def test_tori_maps_to_tori_fi_folder(self) -> None:
        self.assertEqual(gag_service_for_html_dir("tori_fi"), "tori_fi")
        self.assertEqual(gag_service_for_html_dir("tori.fi"), "tori_fi")

    def test_go_back_exist_for_tori(self) -> None:
        svc = "tori_fi"
        go = html_template_path(svc, GO_FILENAME)
        back = html_template_path(svc, BACK_FILENAME)
        self.assertIsNotNone(go, "GO missing for tori_fi")
        self.assertIsNotNone(back, "BACK missing for tori_fi")
        sub = html_subdir_for_service(svc)
        self.assertEqual(sub, "tori_fi")
        self.assertIn("tori_fi", str(go))
        self.assertIn("tori_fi", str(back))

    def test_unknown_service_no_path(self) -> None:
        self.assertIsNone(html_template_path("", GO_FILENAME))
        self.assertIsNone(html_template_path("ebay_de", GO_FILENAME))


if __name__ == "__main__":
    unittest.main()
