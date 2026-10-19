"""Proves unitàries d'analitza_logs.py. S'executen amb:  python -m unittest -v"""

import unittest

from analitza_logs import analitza, analitza_linia, main

LINIA_OK = '192.168.1.10 - - [18/Oct/2026:10:15:32 +0200] "GET /index.html HTTP/1.1" 200 5120 "-" "Mozilla/5.0"'
LINIA_404 = '10.0.0.5 - - [18/Oct/2026:10:16:01 +0200] "GET /no-existeix HTTP/1.1" 404 - "-" "curl/8.5"'


class ProvaLinia(unittest.TestCase):
    def test_linia_valida(self):
        p = analitza_linia(LINIA_OK)
        self.assertEqual(p["ip"], "192.168.1.10")
        self.assertEqual(p["metode"], "GET")
        self.assertEqual(p["ruta"], "/index.html")
        self.assertEqual(p["estat"], 200)
        self.assertEqual(p["mida"], 5120)

    def test_mida_amb_guio_es_zero(self):
        self.assertEqual(analitza_linia(LINIA_404)["mida"], 0)

    def test_linia_invalida(self):
        self.assertIsNone(analitza_linia("açò no és una línia de registre"))


class ProvaResum(unittest.TestCase):
    def setUp(self):
        self.resum = analitza([LINIA_OK, LINIA_OK, LINIA_404, "brossa", ""])

    def test_comptadors(self):
        self.assertEqual(self.resum["total"], 3)
        self.assertEqual(self.resum["invalides"], 1)
        self.assertEqual(self.resum["errors"], 1)

    def test_percentatge_errors(self):
        self.assertEqual(self.resum["percentatge_errors"], 33.3)

    def test_ip_mes_activa(self):
        self.assertEqual(self.resum["ips"].most_common(1)[0], ("192.168.1.10", 2))

    def test_resum_buit(self):
        self.assertEqual(analitza([])["percentatge_errors"], 0.0)


class ProvaCodisEixida(unittest.TestCase):
    def test_fitxer_inexistent_torna_2(self):
        self.assertEqual(main(["no-hi-ha-cap-fitxer.log"]), 2)


if __name__ == "__main__":
    unittest.main()
