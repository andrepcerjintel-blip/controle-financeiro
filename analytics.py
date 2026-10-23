"""Local, explainable financial analysis. No external AI or data transmission."""
from collections import defaultdict

NATURES = ('nao_definido','essencial','superfluo','transferencia','investimento')

def analyze(rows, start='', end=''):
    rows = [r for r in rows if (not start or r['date'] >= start) and (not end or r['date'] <= end)]
    months = defaultdict(lambda: dict(incoming=0,outgoing=0,ids=[]))
    categories = defaultdict(lambda: dict(amount_cents=0,ids=[]))
    nature = {n:dict(amount_cents=0,ids=[]) for n in NATURES}
    incoming = outgoing = income = spending = 0
    for r in rows:
        amount = r['amount_cents']; debit = r['type']=='debito'
        month = months[r['date'][:7]]
        month['outgoing' if debit else 'incoming'] += amount; month['ids'].append(r['id'])
        if debit:
            outgoing += amount
            cat = 'Não identificados' if r['category']=='Não identificado' else r['category']
            categories[cat]['amount_cents'] += amount; categories[cat]['ids'].append(r['id'])
            n = r.get('nature','nao_definido') if r['status']=='confirmada' else 'nao_definido'
            nature[n]['amount_cents'] += amount; nature[n]['ids'].append(r['id'])
            if n not in ('transferencia','investimento'): spending += amount
        else:
            incoming += amount
            if r['status']=='confirmada' and r.get('nature') not in ('transferencia','investimento','nao_definido',None): income += amount
    top = sorted([r for r in rows if r['type']=='debito'],key=lambda r:r['amount_cents'],reverse=True)[:10]
    unknown = nature['nao_definido']['amount_cents']
    tips = []
    if not rows: tips.append('Importe lançamentos para iniciar a análise.')
    if unknown: tips.append(f'Há R$ {unknown/100:.2f} em saídas sem natureza confirmada. Revise antes de concluir onde cortar.')
    extra = nature['superfluo']['amount_cents']
    if extra:
        tips.append(f'Gastos que você marcou como supérfluos: R$ {extra/100:.2f}. Uma redução hipotética de 10% liberaria R$ {extra/1000:.2f} neste período.')
    if outgoing > incoming:
        tips.append(f'As saídas bancárias superam as entradas em R$ {(outgoing-incoming)/100:.2f}. Confira cobertura do período, transferências, resgates e empréstimos antes de interpretar como déficit de renda.')
    if income and extra > income * .30:
        tips.append('Supérfluos excedem 30% das entradas confirmadas como renda. Esse limiar é uma referência ajustável, não uma regra universal; avalie reduzir os maiores itens.')
    if top:
        tips.append(f'O maior débito é R$ {top[0]["amount_cents"]/100:.2f}, lançamento #{top[0]["id"]}. Confira sua finalidade antes de propor um corte.')
    tips.append('Entradas bancárias não equivalem necessariamente a renda; saídas podem incluir transferências e investimentos. Períodos incompletos e contas ausentes limitam conclusões.')
    return dict(incoming_cents=incoming,outgoing_cents=outgoing,net_cents=incoming-outgoing,
                confirmed_income_cents=income,spending_candidate_cents=spending,
                months=[dict(month=k,**v) for k,v in sorted(months.items())],categories=dict(categories),nature=nature,
                top=top,tips=tips,count=len(rows))


def answer(report, question):
    q=question.casefold()
    if not question.strip() or len(question)>2000: raise ValueError('Informe uma pergunta de até 2.000 caracteres')
    if any(w in q for w in ('maior','top','onde gasto')):
        return '\n'.join(f'#{r["id"]}: {r["custom_description"] or r["description"]} — R$ {r["amount_cents"]/100:.2f}' for r in report['top']) or 'Nenhum débito no período.'
    if any(w in q for w in ('entrada','saldo','saída','saida')):
        return f'Entradas bancárias: R$ {report["incoming_cents"]/100:.2f}. Saídas: R$ {report["outgoing_cents"]/100:.2f}. Fluxo líquido do período: R$ {report["net_cents"]/100:.2f} (não é saldo da conta).\n'+report['tips'][-1]
    return '\n'.join(report['tips'])+'\nVocê pode perguntar sobre maiores gastos, entradas e saídas ou onde economizar. Este assistente local usa regras, não uma IA generativa.'
