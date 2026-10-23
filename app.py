import argparse
import json
import sqlite3
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


class Finance:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS bank_records (
          id INTEGER PRIMARY KEY, institution TEXT NOT NULL, account TEXT NOT NULL,
          external_id TEXT NOT NULL, date TEXT NOT NULL, description TEXT NOT NULL,
          amount_cents INTEGER NOT NULL CHECK(amount_cents>0),
          type TEXT NOT NULL CHECK(type IN ('debito','credito')), raw_json TEXT NOT NULL,
          UNIQUE(institution,account,external_id));
        CREATE TRIGGER IF NOT EXISTS immutable_bank_update BEFORE UPDATE ON bank_records
          BEGIN SELECT RAISE(ABORT,'Registro bancário imutável'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_bank_delete BEFORE DELETE ON bank_records
          BEGIN SELECT RAISE(ABORT,'Registro bancário imutável'); END;
        CREATE TABLE IF NOT EXISTS classifications (
          transaction_id INTEGER PRIMARY KEY REFERENCES bank_records(id),
          source TEXT NOT NULL CHECK(source IN ('manual','automatic')),
          status TEXT NOT NULL CHECK(status IN ('pendente','confirmada','automatica')),
          category TEXT NOT NULL, subcategory TEXT NOT NULL DEFAULT '',
          custom_description TEXT NOT NULL DEFAULT '', recurrence INTEGER NOT NULL DEFAULT 0,
          notes TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS classification_history (
          id INTEGER PRIMARY KEY, transaction_id INTEGER NOT NULL REFERENCES bank_records(id),
          changed_at TEXT NOT NULL, before_json TEXT, after_json TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS immutable_history_update BEFORE UPDATE ON classification_history
          BEGIN SELECT RAISE(ABORT,'Histórico imutável'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_history_delete BEFORE DELETE ON classification_history
          BEGIN SELECT RAISE(ABORT,'Histórico imutável'); END;
        ''')

    def close(self):
        self.db.close()

    def import_records(self, records):
        # Validate the complete batch before writing. Stable bank IDs are mandatory.
        from datetime import date
        for r in records:
            for k in ('institution', 'account', 'external_id', 'description'):
                if not isinstance(r.get(k), str) or not r[k].strip():
                    raise ValueError(f'Campo obrigatório: {k}')
            date.fromisoformat(r['date'])
            if type(r.get('amount_cents')) is not int or r['amount_cents'] <= 0:
                raise ValueError('amount_cents deve ser inteiro positivo')
            if r.get('type') not in ('debito', 'credito'):
                raise ValueError('Tipo inválido')
        with self.db:
            for r in records:
                existing = self.db.execute('SELECT * FROM bank_records WHERE institution=? AND account=? AND external_id=?',
                                          (r['institution'], r['account'], r['external_id'])).fetchone()
                if existing:
                    if any(existing[k] != r[k] for k in ('date','description','amount_cents','type')):
                        raise ValueError('Identificador bancário já existe com dados diferentes')
                    continue
                cur = self.db.execute('INSERT INTO bank_records(institution,account,external_id,date,description,amount_cents,type,raw_json) VALUES(?,?,?,?,?,?,?,?)',
                    tuple(r[k] for k in ('institution','account','external_id','date','description','amount_cents','type')) + (json.dumps(r, ensure_ascii=False),))
                self._classify(cur.lastrowid, {'status':'automatica','category':'Não identificado'}, 'automatic')

    def _classify(self, tid, data, source):
        before = self.db.execute('SELECT * FROM classifications WHERE transaction_id=?', (tid,)).fetchone()
        if source == 'automatic' and before and before['source'] == 'manual':
            return False
        if not self.db.execute('SELECT 1 FROM bank_records WHERE id=?', (tid,)).fetchone():
            raise ValueError('Lançamento inexistente')
        status = data.get('status')
        if status not in ('pendente','confirmada','automatica'):
            raise ValueError('Classificação inválida')
        values = {k: data.get(k, '') for k in ('category','subcategory','custom_description','notes')}
        if any(not isinstance(v, str) or len(v) > 10000 for v in values.values()):
            raise ValueError('Texto inválido')
        if type(data.get('recurrence', False)) is not bool:
            raise ValueError('Recorrência inválida')
        recurrence = int(data.get('recurrence', False))
        if status == 'pendente':
            values['category'] = 'Não identificado'
            recurrence = 0
        if not values['category'].strip():
            raise ValueError('Categoria obrigatória')
        stamp = self.db.execute("SELECT strftime('%Y-%m-%dT%H:%M:%fZ','now')").fetchone()[0]
        self.db.execute('''INSERT INTO classifications VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(transaction_id) DO UPDATE SET source=excluded.source,status=excluded.status,
            category=excluded.category,subcategory=excluded.subcategory,custom_description=excluded.custom_description,
            recurrence=excluded.recurrence,notes=excluded.notes,updated_at=excluded.updated_at''',
            (tid,source,status,values['category'],values['subcategory'],values['custom_description'],recurrence,values['notes'],stamp))
        after = dict(self.db.execute('SELECT * FROM classifications WHERE transaction_id=?',(tid,)).fetchone())
        self.db.execute('INSERT INTO classification_history(transaction_id,changed_at,before_json,after_json) VALUES(?,?,?,?)',
                        (tid,stamp,json.dumps(dict(before),ensure_ascii=False) if before else None,json.dumps(after,ensure_ascii=False)))
        return True

    def classify(self, tid, data, source='manual'):
        with self.db:
            return self._classify(tid, data, source)

    def transactions(self):
        return [dict(r) for r in self.db.execute('''SELECT b.id,b.institution,b.account,b.external_id,b.date,b.description,
            b.amount_cents,b.type,c.source,c.status,c.category,c.subcategory,c.custom_description,c.recurrence,c.notes,c.updated_at
            FROM bank_records b JOIN classifications c ON c.transaction_id=b.id ORDER BY b.date DESC,b.id DESC''')]

    def dashboard(self):
        rows = self.transactions()
        pending = [r for r in rows if r['status']=='pendente']
        categories = {}
        for r in rows:
            if r['type']=='debito':
                cat = 'Não identificados' if r['category']=='Não identificado' else r['category']
                categories[cat] = categories.get(cat,0) + r['amount_cents']
        return dict(outgoing_cents=sum(r['amount_cents'] for r in rows if r['type']=='debito'),
                    pending_count=len(pending),pending_cents=sum(r['amount_cents'] for r in pending),
                    fixed_projection_cents=sum(r['amount_cents'] for r in rows if r['type']=='debito' and r['status']=='confirmada' and r['recurrence']),
                    categories=categories)

    def history(self, tid):
        return [dict(r) for r in self.db.execute('SELECT * FROM classification_history WHERE transaction_id=? ORDER BY id DESC',(tid,))]


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, data):
        body = json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/':
            body = Path(__file__).with_name('index.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(body)
            return
        f = Finance(self.server.db_path)
        try:
            if path == '/api/transactions': self.send_json(200,f.transactions())
            elif path == '/api/dashboard': self.send_json(200,f.dashboard())
            elif path.startswith('/api/history/'):
                self.send_json(200,f.history(int(path.rsplit('/',1)[1])))
            else: self.send_json(404,{'error':'Não encontrado'})
        except ValueError as e: self.send_json(400,{'error':str(e)})
        finally: f.close()

    def do_POST(self):
        # JSON-only, same-origin requests; do not expose this local server publicly.
        if self.headers.get('Content-Type','').split(';')[0] != 'application/json':
            self.send_json(415,{'error':'Use application/json'})
            return
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + self.headers.get('Host',''):
            self.send_json(403,{'error':'Origem inválida'})
            return
        f = Finance(self.server.db_path)
        try:
            size = int(self.headers.get('Content-Length',0))
            if not 0 < size <= 5_000_000: raise ValueError('Tamanho inválido')
            data = json.loads(self.rfile.read(size))
            path = urlparse(self.path).path
            if path == '/api/import':
                if not isinstance(data,list): raise ValueError('Envie uma lista de lançamentos')
                f.import_records(data)
            elif path.startswith('/api/classify/'):
                f.classify(int(path.rsplit('/',1)[1]),data)
            else:
                self.send_json(404,{'error':'Não encontrado'})
                return
            self.send_json(200,{'ok':True})
        except (ValueError, KeyError, TypeError, sqlite3.IntegrityError) as e:
            self.send_json(400,{'error':str(e)})
        finally: f.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db',default='data/finance.db')
    parser.add_argument('--port',type=int,default=8000)
    args = parser.parse_args()
    Path(args.db).parent.mkdir(parents=True,exist_ok=True)
    Finance(args.db).close()
    server = ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    server.db_path = args.db
    print(f'Meu Painel Financeiro iniciado na porta {args.port}',flush=True)
    server.serve_forever()


if __name__ == '__main__': main()
