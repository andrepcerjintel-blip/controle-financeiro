import unittest
from analytics import analyze, answer


def row(i, amount, kind='debito', nature='nao_definido', status='confirmada',date='2026-09-02'):
    return dict(id=i,amount_cents=amount,type=kind,nature=nature,status=status,date=date,category='Teste',description='Operação',custom_description='')

class AnalysisTests(unittest.TestCase):
    def test_totals_period_and_drilldown(self):
        d=analyze([row(1,100),row(2,300,'credito'),row(3,900,date='2026-08-01')],'2026-09-01','2026-09-30')
        self.assertEqual((d['incoming_cents'],d['outgoing_cents'],d['net_cents']),(300,100,200))
        self.assertEqual(d['categories']['Teste']['ids'],[1])
        self.assertEqual(d['months'][0]['ids'],[1,2])

    def test_unreviewed_is_not_judged_superfluous(self):
        d=analyze([row(1,500,nature='superfluo',status='pendente')])
        self.assertEqual(d['nature']['superfluo']['amount_cents'],0)
        self.assertEqual(d['nature']['nao_definido']['amount_cents'],500)

    def test_transfer_not_income_or_consumption(self):
        d=analyze([row(1,1000,'credito','transferencia'),row(2,1000,nature='transferencia')])
        self.assertEqual(d['confirmed_income_cents'],0)
        self.assertEqual(d['spending_candidate_cents'],0)
        self.assertEqual(d['outgoing_cents'],1000)

    def test_ranking_and_recommendation(self):
        d=analyze([row(1,500,nature='superfluo'),row(2,300)])
        self.assertEqual(d['top'][0]['id'],1)
        self.assertTrue(any('10%' in t for t in d['tips']))
        self.assertIn('#1',answer(d,'maiores gastos'))

    def test_empty(self):
        self.assertEqual(analyze([])['count'],0)
        self.assertIn('Nenhum débito',answer(analyze([]),'maiores'))

class PersistenceTests(unittest.TestCase):
    def test_nature_saved_and_audited(self):
        import tempfile
        import json
        from pathlib import Path
        from app import Finance
        with tempfile.TemporaryDirectory() as tmp:
            db=str(Path(tmp)/'db');f=Finance(db)
            f.import_records([dict(institution='Teste',account='1',external_id='1',date='2026-09-02',description='Original',amount_cents=100,type='debito')])
            tid=f.transactions()[0]['id']
            f.classify(tid,dict(status='confirmada',category='Lazer',nature='superfluo'))
            f.close();f=Finance(db)
            self.assertEqual(f.transactions()[0]['nature'],'superfluo')
            self.assertEqual(json.loads(f.history(tid)[0]['after_json'])['nature'],'superfluo')
            f.classify(tid,dict(status='pendente',category='Lazer',nature='superfluo'))
            self.assertEqual(f.transactions()[0]['nature'],'nao_definido')
            f.close()
