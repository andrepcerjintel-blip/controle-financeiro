"""Parsers for text-based Bradesco Celular and BB current-account statements."""
import hashlib
import io
import re
from collections import Counter
from datetime import datetime
from pypdf import PdfReader

MONEY = re.compile(r'\d[\d.]*,\d{2}')
DATE = re.compile(r'^\s*(\d{2}/\d{2}/\d{4})')


def cents(s):
    return int(s.replace('.', '').replace(',', ''))


def parse_pdf(content):
    reader = PdfReader(io.BytesIO(content))
    if len(reader.pages) > 200:
        raise ValueError('Limite de 200 páginas excedido')
    pages = [p.extract_text(extraction_mode='layout') or '' for p in reader.pages]
    text = '\n'.join(pages)
    bank = 'Bradesco' if 'Bradesco' in text else 'Banco do Brasil' if 'Extrato de Conta Corrente' in text and 'BB' in text else None
    if not bank:
        raise ValueError('PDF não reconhecido. Use extrato textual Bradesco Celular ou Banco do Brasil; imagens precisam de OCR.')
    account = re.search(r'Agência:\s*([\d-]+)\s*\|?\s*Conta:\s*([\d.-]+)', text)
    if not account:
        raise ValueError('Agência e conta não reconhecidas')
    account = '/'.join(account.groups())
    records, warnings = [], []
    current = None
    date = None
    pdf_hash = hashlib.sha256(content).hexdigest()
    totals = None
    for page_no, page in enumerate(pages, 1):
        lines = page.splitlines()
        if bank == 'Bradesco':
            header = next((l for l in lines if 'Crédito (R$)' in l and 'Débito (R$)' in l), None)
            if not header:
                raise ValueError(f'Cabeçalho não reconhecido na página {page_no}')
            doc_pos = header.index('Docto.')
            # Values are right-aligned beneath their column labels.
            credit_end = header.index('Crédito') + len('Crédito (R$)') + 2
            debit_end = header.index('Débito') + len('Débito (R$)') + 2
            active = False
            for line in lines:
                if line == header:
                    active = True
                    continue
                if not active or not line.strip(): continue
                if line.strip().startswith('Total'):
                    amounts = MONEY.findall(line)
                    if len(amounts) >= 2: totals = [cents(a) for a in amounts[:2]]
                    current = None
                    continue
                match = DATE.match(line)
                if match: date = datetime.strptime(match[1], '%d/%m/%Y').date().isoformat()
                amounts = [m for m in MONEY.finditer(line) if m.start() > doc_pos + 10]
                if amounts:
                    doc = re.search(r'\b\d+\b',line[doc_pos-4:header.index('Crédito')-4])
                    candidates = [m for m in amounts if m.end() <= debit_end]
                    if not candidates or not doc or not date:
                        if 'SALDO' not in line.upper(): warnings.append(f'Página {page_no}: linha monetária não reconhecida')
                        current = None
                        continue
                    m = candidates[0]
                    kind = 'credito' if m.end() <= credit_end else 'debito'
                    description = line[match.end() if match else 0:doc_pos-4].strip()
                    if not description: raise ValueError(f'Descrição ausente na página {page_no}')
                    current = dict(institution=bank,account=account,date=date,description=description,
                                   amount_cents=cents(m[0]),type=kind,document=doc[0],pdf_page=page_no)
                    records.append(current)
                elif current:
                    extra = line.strip()
                    if extra: current['description'] += ' — ' + extra
        else:
            active = False
            leading_description = ''
            for line in lines:
                if 'Histórico' in line and 'Valor' in line:
                    active = True
                    desc_pos = line.index('Histórico')
                    continue
                if not active or not line.strip(): continue
                if 'Informações Adicionais' in line:
                    active = False
                    continue
                match = DATE.match(line)
                if match:
                    date = datetime.strptime(match[1], '%d/%m/%Y').date().isoformat()
                    amount = re.search(r'(\d[\d.]*,\d{2})\s*\(([+-])\)\s*$',line)
                    if not amount:
                        warnings.append(f'Página {page_no}: lançamento sem valor reconhecido')
                        current = None
                        continue
                    desc = line[desc_pos:amount.start()].strip()
                    if desc in ('Saldo Anterior','Saldo do dia','S A L D O'):
                        current = None
                        continue
                    if leading_description:
                        desc = leading_description + ' — ' + desc
                        leading_description = ''
                    prefix = line[match.end():desc_pos].split()
                    document = prefix[-1] if prefix else ''
                    current = dict(institution=bank,account=account,date=date,description=desc,
                                   amount_cents=cents(amount[1]),type='credito' if amount[2]=='+' else 'debito',
                                   document=document,pdf_page=page_no)
                    records.append(current)
                elif current:
                    current['description'] += ' — ' + line.strip()
                else:
                    leading_description = line.strip()
    if not records: raise ValueError('Nenhum lançamento reconhecido')
    if any(r['amount_cents'] <= 0 for r in records):
        raise ValueError('Lançamento com valor zero; confira o PDF')
    if totals:
        actual = [sum(r['amount_cents'] for r in records if r['type']==kind) for kind in ('credito','debito')]
        if actual != totals:
            raise ValueError('Totais extraídos divergem do total do extrato; importação bloqueada para revisão')
    counts = Counter()
    for r in records:
        key = '|'.join(str(r[k]) for k in ('institution','account','date','document','description','amount_cents','type'))
        digest = hashlib.sha256(key.encode()).hexdigest()
        counts[digest] += 1
        r['external_id'] = 'pdf-v1-' + digest + '-' + str(counts[digest])
        r['source_pdf_sha256'] = pdf_hash
    warnings.append('Confira a prévia. IDs são derivados do conteúdo: PDFs com descrições ou formatos diferentes podem gerar duplicidades; nenhuma exclusão por similaridade é feita.')
    if bank == 'Banco do Brasil':
        warnings.append('Aplicações e resgates BB Rende Fácil são movimentações bancárias e foram mantidos, sem presumir consumo ou renda.')
    return dict(bank=bank,records=records,warnings=warnings,totals_verified=totals is not None)
