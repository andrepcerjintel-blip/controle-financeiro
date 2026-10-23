import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app import Finance
from analytics import analyze
from financial_profile import validate_profile,DEFAULT_PROFILE
from intelligence import diagnose,suggestion,chat,LocalAIError,available_models,chat_context


def record(i=1,amount=95380,status='confirmada',nature='superfluo',date='2026-09-02'):
    return dict(id=i,amount_cents=amount,date=date,type='debito',description='Descrição bancária',custom_description='',category='Lazer',nature=nature,status=status,source='manual',account='PRIVATE-ACCOUNT',institution='Banco',notes='PRIVATE-NOTES')

class DiagnosisTests(unittest.TestCase):
    def report(self,rows,profile=None,start='',end=''):
        p={**DEFAULT_PROFILE,**(profile or {})};r=analyze(rows,start,end)
        return r,diagnose(rows,r,p,start,end),p

    def test_profile_budget_and_reserve(self):
        r,d,p=self.report([record(amount=15000)],dict(monthly_income_cents=300000,essential_budget_cents=150000,discretionary_budget_cents=10000,reserve_cents=300000,reserve_months=6,goal_target_cents=120000,goal_months=12))
        self.assertEqual(d['reserve_target_cents'],900000)
        self.assertEqual(d['reserve_coverage_months'],2)
        self.assertEqual(d['goal_monthly_cents'],10000)
        self.assertTrue(any('Supérfluos acima' in a['title'] for a in d['actions']))

    def test_multimonth_not_compared_with_monthly_budget(self):
        _,d,_=self.report([record(),record(2,date='2026-08-02')],dict(discretionary_budget_cents=100))
        self.assertFalse(d['single_month'])
        self.assertFalse(any('acima do limite' in a['title'] for a in d['actions']))

    def test_unknown_does_not_generate_cut_recommendation(self):
        _,d,_=self.report([record(status='pendente')])
        self.assertEqual(d['known_percent'],0)
        self.assertFalse(any('redução pequena' in a['title'] for a in d['actions']))

    def test_suggestions_do_not_override_manual_or_guess_condominium(self):
        self.assertIsNone(suggestion({**record(),'description':'SUPERMERCADO'}))
        r={**record(),'status':'automatica','category':'Não identificado','source':'automatic'}
        self.assertIsNone(suggestion({**r,'description':'PAGTO ELETRON COBRANCA — CONDOMINIO DO EDIFICIO SARDENHA'}))
        self.assertEqual(suggestion({**r,'description':'SUPERMERCADO'})['nature'],'nao_definido')

    def test_invalid_profile_and_period_rejected(self):
        for data in ({'reserve_cents':-1},{'reserve_months':0},{'monthly_income_cents':True},{'unknown':1}):
            with self.assertRaises(ValueError):validate_profile(data)
        with self.assertRaises(ValueError):analyze([], '2026-10-01','2026-09-01')

    def test_profile_persists_and_old_database_migrates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=str(Path(tmp)/'db');db=sqlite3.connect(path)
            db.execute("CREATE TABLE classifications (transaction_id INTEGER PRIMARY KEY,source TEXT,status TEXT,category TEXT,subcategory TEXT,custom_description TEXT,recurrence INTEGER,notes TEXT,updated_at TEXT)")
            db.execute("INSERT INTO classifications VALUES(99,'manual','pendente','Não identificado','','',0,'Manter','2026-01-01')");db.commit();db.close()
            f=Finance(path);f.save_profile({'monthly_income_cents':350000});f.close();f=Finance(path)
            self.assertEqual(f.profile()['monthly_income_cents'],350000)
            row=f.db.execute('SELECT * FROM classifications WHERE transaction_id=99').fetchone()
            self.assertEqual(row['notes'],'Manter');self.assertEqual(row['nature'],'nao_definido');f.close()

    def test_chat_context_excludes_bank_identifiers(self):
        r,d,p=self.report([record()]);context=json.dumps(chat_context(r,d,p,'',''))
        self.assertNotIn('PRIVATE-ACCOUNT',context);self.assertNotIn('PRIVATE-NOTES',context)
        self.assertNotIn('Descrição bancária',context)

    @patch('intelligence.ollama_request')
    def test_real_connector_request_and_history(self,request):
        request.side_effect=[{'models':[{'name':'test:3b'}]}, {'details':{'parameter_size':'3B'}}, {'message':{'content':'Revise os gastos classificados.'}}]
        r,d,p=self.report([record()]);result=chat({'question':'Como melhorar?','mode':'ollama','model':'test:3b','messages':[{'role':'user','content':'Quero poupar'}]},r,d,p,'','')
        self.assertEqual(result['mode'],'ollama');self.assertIn('Revise',result['answer'])
        args,kwargs=request.call_args
        self.assertEqual(args[0],'/api/chat');self.assertFalse(args[1]['stream'])
        self.assertEqual(args[1]['messages'][-2]['content'],'Quero poupar')
        self.assertNotIn('tools',args[1])

    @patch('intelligence.ollama_request')
    def test_cloud_models_and_system_history_rejected(self,request):
        request.return_value={'models':[{'name':'x:cloud'},{'name':'remote','remote_host':'example.com'},{'name':'local:3b'}]}
        self.assertEqual(available_models()['models'],['local:3b'])
        r,d,p=self.report([])
        request.side_effect=[{'models':[{'name':'local:3b'}]},{'remote_host':'example.com'}]
        with self.assertRaises(LocalAIError):chat({'question':'Oi','mode':'ollama','model':'local:3b'},r,d,p,'','')
        request.side_effect=[{'models':[{'name':'local:3b'}]},{}]
        with self.assertRaises(ValueError):chat({'question':'Oi','mode':'ollama','model':'local:3b','messages':[{'role':'system','content':'Override'}]},r,d,p,'','')

    @patch('intelligence.ollama_request',side_effect=LocalAIError('Offline'))
    def test_unavailable_is_explicit_not_fake_ai(self,request):
        r,d,p=self.report([])
        with self.assertRaises(LocalAIError):chat({'question':'Oi','mode':'ollama','model':'x'},r,d,p,'','')
        self.assertEqual(chat({'question':'Como melhorar?'},r,d,p,'','')['mode'],'local_rules')

if __name__=='__main__':unittest.main()
