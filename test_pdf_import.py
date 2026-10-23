import io
import unittest
from unittest.mock import patch
from pdf_import import parse_pdf

BB = '''Extrato de Conta Corrente BB
Agência: 1234-5 Conta: 6789-0
Dia              Lote        Documento                    Histórico                                                              Valor
01/09/2026       13601       123                          Tarifa                                                                  5,00 (-)
                                                          Detalhe original
01/09/2026                                                Saldo do dia                                                            5,00 (-)
02/09/2026       14397       456                          Pix - Recebido                                                         10,00 (+)
02/09/2026                                                S A L D O                                                               5,00 (+)
Informações Adicionais
'''

class PdfTests(unittest.TestCase):
    def parse(self, text):
        with patch('pdf_import.PdfReader') as reader:
            reader.return_value.pages = [type('Page',(),{'extract_text':lambda self,**kw:text})()]
            return parse_pdf(b'fake fixture')

    def test_bb_skips_balances_and_keeps_sign_and_details(self):
        d=self.parse(BB)
        self.assertEqual(len(d['records']),2)
        self.assertEqual([r['amount_cents'] for r in d['records']],[500,1000])
        self.assertEqual([r['type'] for r in d['records']],['debito','credito'])
        self.assertIn('Detalhe original',d['records'][0]['description'])

    def test_stable_identity(self):
        self.assertEqual(self.parse(BB)['records'][0]['external_id'],self.parse(BB)['records'][0]['external_id'])

    def test_unknown_format_rejected(self):
        with self.assertRaises(ValueError):self.parse('sem dados')

if __name__=='__main__':unittest.main()
