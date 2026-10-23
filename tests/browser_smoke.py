"""Optional UI validation: pip install playwright; use installed Chromium.
Run from repository root: python tests/browser_smoke.py
Only synthetic data and a temporary SQLite database are used.
"""
import json
import os
import sys
import tempfile
import threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import Finance,Handler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect


def run():
    with tempfile.TemporaryDirectory() as tmp:
        db=str(Path(tmp)/'ui.db');Finance(db).close()
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.db_path=db
        threading.Thread(target=server.serve_forever,daemon=True).start()
        errors=[]
        try:
            with sync_playwright() as p:
                executable=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium')
                browser=p.chromium.launch(executable_path=executable,headless=True,args=['--no-sandbox'])
                page=browser.new_page(viewport={'width':1440,'height':1100})
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}')
                expect(page.locator('#incoming')).to_have_text('R$ 0,00')
                expect(page.locator('#monthlyChart')).to_contain_text('primeiro gráfico')
                page.locator('.nav-item[data-page="import"]').click()
                fixture=[dict(institution='Banco Exemplo',account='TEST',external_id=str(i),date='2026-09-'+str(i%28+1).zfill(2),description='SUPERMERCADO EXEMPLO '+str(i),amount_cents=1000+i*100,type='debito') for i in range(65)]
                fixture+=[dict(institution='Banco Exemplo',account='TEST',external_id='salary',date='2026-09-01',description='CREDITO DE SALARIO EXEMPLO',amount_cents=800000,type='credito')]
                page.locator('#importFile').set_input_files({'name':'fixture.json','mimeType':'application/json','buffer':json.dumps(fixture).encode()})
                expect(page.locator('#incoming')).to_have_text('R$ 8.000,00')
                expect(page.locator('#coverage')).to_contain_text('66 movimentos')
                # Chart drill-down and pagination.
                page.locator('.month-bars button.orange-bg').click()
                expect(page.locator('#transactionCount')).to_contain_text('65 lançamentos')
                expect(page.locator('#rows tr')).to_have_count(50)
                page.locator('#nextPage').click();expect(page.locator('#rows tr')).to_have_count(15)
                # Edit one transaction; pending must persist and preserve value.
                page.locator('#rows button').first.click()
                page.locator('#editForm select[name=status]').select_option('pendente')
                expect(page.locator('#editForm input[name=category]')).to_have_value('Não identificado')
                page.locator('#editForm button[type=submit]').click()
                expect(page.locator('#editor')).not_to_be_visible()
                page.locator('.nav-item[data-page="overview"]').click()
                expect(page.locator('#pending')).to_have_text('1')
                page.locator('#pendingCard').click();expect(page.locator('#rows tr')).to_have_count(1)
                page.locator('#rows button').click()
                page.locator('#editForm select[name=status]').select_option('confirmada')
                page.locator('#editForm input[name=category]').fill('Lazer')
                page.locator('#editForm select[name=nature]').select_option('superfluo')
                page.locator('#editForm button[type=submit]').click()
                expect(page.locator('#editor')).not_to_be_visible()
                # Profile, monetary conversion and goal calculations.
                page.locator('.nav-item[data-page="profile"]').click()
                page.locator('[name=monthly_income_cents]').fill('8.000,00')
                page.locator('[name=essential_budget_cents]').fill('3.500,00')
                page.locator('[name=discretionary_budget_cents]').fill('1.000,00')
                page.locator('[name=reserve_cents]').fill('7.000,00')
                page.locator('[name=goal_target_cents]').fill('12.000,00')
                page.locator('#profileForm button[type=submit]').click()
                expect(page.locator('#page-plan')).to_be_visible()
                expect(page.locator('#goalSummary')).to_contain_text('2 mês(es)')
                page.reload();page.locator('.nav-item[data-page="profile"]').click()
                expect(page.locator('[name=monthly_income_cents]')).to_have_value('8.000,00')
                # Rules are explicitly labeled, and no model is needed.
                page.locator('.nav-item[data-page="assistant"]').click()
                page.locator('#chatQuestion').fill('Como organizar minha reserva?')
                page.locator('#sendChat').click()
                expect(page.locator('#chatLog')).to_contain_text('DIAGNÓSTICO POR REGRAS')
                expect(page.locator('#chatLog')).to_contain_text('reserva',timeout=15000)
                # All global totals respond to the same applied period.
                page.locator('#startDate').fill('2026-08-01');page.locator('#endDate').fill('2026-08-31')
                page.locator('#applyPeriod').click()
                expect(page.locator('#coverage')).to_have_text('Nenhum movimento no período')
                page.locator('.nav-item[data-page="overview"]').click();expect(page.locator('#incoming')).to_have_text('R$ 0,00')
                page.locator('#periodPreset').select_option('all');page.locator('#applyPeriod').click()
                expect(page.locator('#incoming')).to_have_text('R$ 8.000,00')
                page.screenshot(path='/tmp/finance-desktop.png',full_page=True)
                page.set_viewport_size({'width':390,'height':844})
                page.screenshot(path='/tmp/finance-mobile.png',full_page=True)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Horizontal overflow on mobile'
                assert not errors,errors
                browser.close()
                print('Browser OK: empty state, import, charts, pagination, classification, profile persistence, chat, period, mobile.')
        finally:
            server.shutdown();server.server_close()

if __name__=='__main__':run()
