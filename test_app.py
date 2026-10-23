import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from app import Finance

RECORD = json.loads(Path('examples/sardenha.json').read_text())[0]

class FinanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name)/'test.db')
        self.f = Finance(self.path)
        self.f.import_records([RECORD])
        self.tid = self.f.transactions()[0]['id']
        self.f.classify(self.tid,dict(status='pendente',category='Condomínio',recurrence=True))

    def tearDown(self):
        self.f.close()
        self.temp.cleanup()

    def test_expense_remains_counted(self):
        d = self.f.dashboard()
        self.assertEqual(d['outgoing_cents'],95380)
        self.assertEqual(d['categories']['Não identificados'],95380)
        self.assertEqual((d['pending_count'],d['pending_cents']),(1,95380))

    def test_automatic_rule_cannot_override_manual(self):
        self.assertFalse(self.f.classify(self.tid,dict(status='confirmada',category='Condomínio',recurrence=True),source='automatic'))
        r = self.f.transactions()[0]
        self.assertEqual((r['status'],r['category'],r['recurrence']),('pendente','Não identificado',0))

    def test_excluded_from_future_projection(self):
        self.assertEqual(self.f.dashboard()['fixed_projection_cents'],0)

    def test_persists_after_restart(self):
        self.f.close()
        self.f = Finance(self.path)
        self.assertEqual(self.f.transactions()[0]['status'],'pendente')
        self.assertEqual(len(self.f.history(self.tid)),2)

    def test_reimport_preserves_manual(self):
        self.f.import_records([RECORD])
        self.assertEqual(len(self.f.transactions()),1)
        self.assertEqual(self.f.transactions()[0]['status'],'pendente')
        self.assertEqual(len(self.f.history(self.tid)),2)

    def test_can_reclassify(self):
        self.f.classify(self.tid,dict(status='confirmada',category='Serviços',subcategory='Avulso',custom_description='Identificado',notes='Revisado',recurrence=False))
        r = self.f.transactions()[0]
        self.assertEqual((r['status'],r['category'],r['description'],r['amount_cents']),('confirmada','Serviços',RECORD['description'],95380))
        self.assertEqual(len(self.f.history(self.tid)),3)

    def test_bank_data_and_history_are_immutable(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.f.db.execute('UPDATE bank_records SET amount_cents=1')
        with self.assertRaises(sqlite3.IntegrityError):
            self.f.db.execute('DELETE FROM bank_records')
        with self.assertRaises(sqlite3.IntegrityError):
            self.f.db.execute('DELETE FROM classification_history')

    def test_similar_transaction_is_not_changed(self):
        self.f.import_records([{**RECORD,'external_id':'outro'}])
        rows = self.f.transactions()
        self.assertEqual(len(rows),2)
        self.assertEqual(sum(r['status']=='pendente' for r in rows),1)
        self.assertEqual(self.f.dashboard()['outgoing_cents'],190760)

    def test_conflicting_reimport_rolls_back_batch(self):
        with self.assertRaises(ValueError):
            self.f.import_records([{**RECORD,'external_id':'novo'},{**RECORD,'amount_cents':1}])
        self.assertEqual(len(self.f.transactions()),1)

    def test_confirmed_rent_independent_of_pending(self):
        self.f.import_records([{**RECORD,'external_id':'aluguel','description':'Aluguel com condomínio','amount_cents':370000}])
        tid = next(r['id'] for r in self.f.transactions() if r['external_id']=='aluguel')
        self.f.classify(tid,dict(status='confirmada',category='Aluguel',recurrence=True))
        self.assertEqual(self.f.dashboard()['outgoing_cents'],465380)
        self.assertEqual(self.f.dashboard()['fixed_projection_cents'],370000)
        self.assertEqual(self.f.dashboard()['pending_cents'],95380)

if __name__ == '__main__': unittest.main()
