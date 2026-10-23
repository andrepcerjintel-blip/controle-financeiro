'use strict';
const $ = id => document.getElementById(id);
const money = n => (n / 100).toLocaleString('pt-BR', {style:'currency', currency:'BRL'});
const dateLabel = value => value ? value.split('-').reverse().join('/') : '—';
const labels = {confirmada:'Confirmada', pendente:'Pendente de identificação', automatica:'Automática — não revisada'};
const natureLabels = {nao_definido:'Não definida / não revisada', essencial:'Essenciais', superfluo:'Supérfluos', transferencia:'Transferências', investimento:'Investimentos / resgates', renda:'Renda', divida:'Dívidas e custos financeiros'};
const colors = {nao_definido:'#b6c4c9', essencial:'#3d9684', superfluo:'#d89c76', transferencia:'#7496b1', investimento:'#93b498', renda:'#a7c58a', divida:'#b88c92'};
const pages = {
  overview:['Visão geral','Seu dinheiro, em perspectiva.','Entenda seus movimentos e transforme informação em decisões.'],
  plan:['Plano de ação','Pequenos passos. Mudanças reais.','Prioridades explicadas a partir dos seus números e objetivos.'],
  transactions:['Movimentações','Cada movimento conta.','Encontre, identifique e organize seus lançamentos.'],
  profile:['Perfil e metas','Um plano que cabe na sua vida.','Conte de onde você parte e aonde quer chegar.'],
  assistant:['Assistente IA','Vamos pensar no próximo passo?','Converse sobre seus números, suas metas e suas decisões.'],
  import:['Importar extratos','Tudo começa pelos seus dados.','Traga seus extratos e confira os lançamentos antes de salvar.']
};
const state = {records:[], report:null, profile:null, page:1, selected:null, detailIds:null, detailTitle:'', initialized:false, pdfRecords:[], chatHistory:[], chatting:false, period:{start:'',end:''}};
function node(tag, text, cls) { const el=document.createElement(tag); if(text!==undefined) el.textContent=text; if(cls) el.className=cls; return el; }
function notice(message, error=false) { $('notice').textContent=message; $('notice').hidden=false; $('notice').classList.toggle('error',error); }
async function api(path, data) {
  const response=await fetch(path, data===undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  let result;
  try { result=await response.json(); } catch { throw Error('Resposta inválida do servidor. Confira o terminal da aplicação.'); }
  if(!response.ok) throw Error(result.error || 'Não foi possível concluir a operação.');
  return result;
}
function navigate(page) {
  if(!pages[page]) page='overview';
  document.querySelectorAll('.page').forEach(el=>el.hidden=el.id!=='page-'+page);
  document.querySelectorAll('.nav-item').forEach(el=>{el.classList.toggle('active',el.dataset.page===page);el.setAttribute('aria-current',el.dataset.page===page?'page':'false');});
  [$('breadcrumb').textContent,$('pageTitle').textContent,$('pageSubtitle').textContent]=pages[page];
  history.replaceState(null,'','#'+page);
  if(page==='assistant') refreshAI();
}
document.querySelectorAll('[data-page]').forEach(b=>b.addEventListener('click',()=>navigate(b.dataset.page)));
window.addEventListener('hashchange',()=>navigate(location.hash.slice(1)));
function empty(container,title,description='') {const el=node('div',undefined,'empty-state');el.append(node('strong',title),node('span',description));container.append(el);}
function inPeriod(r) {return (!state.period.start||r.date>=state.period.start)&&(!state.period.end||r.date<=state.period.end);}
function showDetails(ids,title) {
  state.detailIds=ids;state.detailTitle=title;state.page=1;
  $('search').value='';$('statusFilter').value='';$('typeFilter').value='';renderTransactions();navigate('transactions');
}
function resetChat() {state.chatHistory=[];$('chatLog').replaceChildren();const el=node('div',undefined,'chat-welcome');el.append(node('span','✦','spark'),node('h3','Vamos cuidar do seu próximo passo?'),node('p','Pergunte sobre gastos, reserva, dívidas ou metas. O contexto usa o período aplicado.'));$('chatLog').append(el);}
function periodOptions() {
  const preset=$('periodPreset'),previous=preset.value;
  const months=[...new Set(state.records.map(r=>r.date.slice(0,7)))].sort().reverse();
  preset.replaceChildren();const all=node('option','Todos os lançamentos');all.value='all';preset.append(all);
  for(const month of months) {const option=node('option',new Date(month+'-02T12:00:00').toLocaleDateString('pt-BR',{month:'long',year:'numeric'}));option.value=month;preset.append(option);}
  const custom=node('option','Período personalizado');custom.value='custom';preset.append(custom);
  preset.value=previous||'all';
  if(!state.initialized) {preset.value=months[0]||'all';setPeriodInputs(preset.value);state.period={start:$('startDate').value,end:$('endDate').value};state.initialized=true;}
}
function setPeriodInputs(value) {
  if(value==='custom')return;
  if(value==='all'){$('startDate').value='';$('endDate').value='';return;}
  const [year,month]=value.split('-').map(Number);
  $('startDate').value=value+'-01';$('endDate').value=value+'-'+new Date(year,month,0).getDate();
}
$('periodPreset').onchange=()=>setPeriodInputs($('periodPreset').value);
for(const id of ['startDate','endDate']) $(id).onchange=()=>{$('periodPreset').value='custom';};
$('applyPeriod').onclick=async()=>{
  if(state.chatting){notice('Aguarde a resposta antes de mudar o período.',true);return;}
  const next={start:$('startDate').value,end:$('endDate').value};
  if(next.start&&next.end&&next.start>next.end){notice('A data inicial deve preceder a final.',true);return;}
  const previous=state.period;state.period=next;
  try {await loadReport();state.detailIds=null;state.page=1;resetChat();renderTransactions();}catch(e){state.period=previous;notice(e.message,true);}
};
async function load() {
  try {const [records,profile]=await Promise.all([api('/api/transactions'),api('/api/profile')]);state.records=records;state.profile=profile;periodOptions();fillProfile();await loadReport();renderTransactions();}
  catch(e){notice(e.message,true);}
}
async function loadReport() {
  state.report=await api('/api/analytics?'+new URLSearchParams(state.period));renderOverview();renderPlan();renderSuggestions();
}
function renderOverview() {
  const d=state.report,g=d.diagnosis;
  $('incoming').textContent=money(d.incoming_cents);$('outgoing').textContent=money(d.outgoing_cents);$('net').textContent=money(d.net_cents);
  $('pending').textContent=g.pending_count;$('pendingValue').textContent=money(g.pending_cents)+' · Abrir lançamentos →';
  $('clarityValue').textContent=g.known_percent===null?'—':g.known_percent+'%';
  document.querySelector('.clarity-ring').style.background=`conic-gradient(#a5dac0 ${(g.known_percent||0)*3.6}deg,#426b6c 0deg)`;
  $('heroTitle').textContent=g.actions[0]?.title||'Mais clareza para decidir com tranquilidade.';
  $('heroText').textContent=g.actions[0]?.detail||'Revise seu plano e mantenha suas metas próximas das decisões do dia a dia.';
  $('coverage').textContent=g.coverage.first?`${d.count} movimentos · Dados de ${dateLabel(g.coverage.first)} a ${dateLabel(g.coverage.last)}`:'Nenhum movimento no período';
  $('chatContext').textContent=`${d.count} movimentações no período aplicado. Saídas: ${money(d.outgoing_cents)}. Informação declarada no Perfil acompanha a conversa.`;
  const chart=$('monthlyChart');chart.replaceChildren();
  const months=d.months.slice(-12),max=Math.max(1,...months.flatMap(m=>[m.incoming,m.outgoing]));
  if(!months.length) empty(chart,'Seu primeiro gráfico começa aqui.','Importe um extrato para visualizar o fluxo.');
  for(const m of months) {
    const group=node('div',undefined,'month-group'),bars=node('div',undefined,'month-bars');
    for(const [key,label,cls,type] of [['incoming','Entradas','green-bg','credito'],['outgoing','Saídas','orange-bg','debito']]){
      const b=node('button',undefined,cls);b.style.height=Math.max(3,160*m[key]/max)+'px';b.title=`${m.month} · ${label}: ${money(m[key])}`;b.setAttribute('aria-label',b.title);
      b.onclick=()=>showDetails(state.records.filter(r=>inPeriod(r)&&r.date.startsWith(m.month)&&r.type===type).map(r=>r.id),label+' · '+m.month);bars.append(b);
    }
    group.append(bars,node('span',m.month.slice(5)+'/'+m.month.slice(2,4)));chart.append(group);
  }
  if(d.months.length>12)chart.append(node('small','Últimos 12 meses com movimentos.'));
  $('donutTotal').textContent=money(d.outgoing_cents);$('natureLegend').replaceChildren();
  let angle=0;const stops=[];
  for(const [key,item] of Object.entries(d.nature)){
    if(!item.amount_cents)continue;
    const next=angle+item.amount_cents/Math.max(d.outgoing_cents,1)*360;stops.push(`${colors[key]} ${angle}deg ${next}deg`);angle=next;
    const b=node('button',undefined,'nature-line'),name=node('span');const dot=node('i',undefined,'color-dot');dot.style.background=colors[key];name.append(dot,node('span',natureLabels[key]));b.append(name,node('strong',Math.round(item.amount_cents/d.outgoing_cents*100)+'%'));b.title=money(item.amount_cents);b.onclick=()=>showDetails(item.ids,natureLabels[key]);$('natureLegend').append(b);
  }
  $('natureDonut').style.background=stops.length?'conic-gradient('+stops.join(',')+')':'#edf1f1';
  if(!stops.length)$('natureLegend').append(node('p','Sem saídas neste período.','small'));
  $('natureDonut').setAttribute('aria-label','Saídas por natureza. Total '+money(d.outgoing_cents)+'. Use os botões da legenda para detalhes.');
  const cats=$('categories');cats.replaceChildren();const categories=Object.entries(d.categories).sort((a,b)=>b[1].amount_cents-a[1].amount_cents);
  if(!categories.length)empty(cats,'Categorias aparecerão aqui.');
  for(const [cat,v] of categories){const b=node('button',undefined,'category-bar'),caption=node('span',undefined,'bar-caption'),track=node('div',undefined,'bar-track'),fill=node('div',undefined,'bar-fill');caption.append(node('span',cat),node('strong',money(v.amount_cents)));fill.style.width=100*v.amount_cents/Math.max(1,d.outgoing_cents)+'%';track.append(fill);b.append(caption,track);b.onclick=()=>showDetails(v.ids,cat);cats.append(b);}
  $('topList').replaceChildren();if(!d.top.length)empty($('topList'),'Nenhum débito no período.');
  d.top.forEach((r,i)=>{const b=node('button',undefined,'rank-row'),desc=node('span',undefined,'rank-text');desc.append(node('strong',r.custom_description||r.description),node('small',dateLabel(r.date)+' · '+r.category));b.append(node('span',String(i+1).padStart(2,'0'),'rank-number'),desc,node('span',money(r.amount_cents),'rank-amount'));b.onclick=()=>showDetails([r.id],'Lançamento #'+r.id);$('topList').append(b);});
}
$('pendingCard').onclick=()=>showDetails(state.records.filter(r=>inPeriod(r)&&r.status==='pendente').map(r=>r.id),'Pendentes de identificação');
function renderPlan(){
  const g=state.report.diagnosis,priorities={alta:'REVISAR PRIMEIRO',oportunidade:'OPORTUNIDADE',planejamento:'PLANEJAMENTO',primeiro_passo:'PRIMEIRO PASSO'};
  $('actionList').replaceChildren();for(const a of g.actions){const card=node('article',undefined,'action-card');card.append(node('span',priorities[a.priority],'priority '+a.priority),node('h3',a.title),node('p',a.detail));if(a.ids.length){const b=node('button','Ver lançamentos →','quiet');b.onclick=()=>showDetails(a.ids,a.title);card.append(b);}else{const b=node('button','Abrir perfil →','quiet');b.onclick=()=>navigate(state.records.length?'profile':'import');card.append(b);}$('actionList').append(card);}
  $('budgetList').replaceChildren();for(const b of g.budgets){const item=node('div',undefined,'budget-item'),title=node('div',undefined,'bar-caption');title.append(node('strong',b.label),node('span',money(b.actual_cents)+' identificados'));item.append(title);if(b.limit_cents&&b.comparable){const track=node('div',undefined,'bar-track'),fill=node('div',undefined,'bar-fill');fill.style.width=Math.min(100,b.actual_cents/b.limit_cents*100)+'%';if(b.actual_cents>b.limit_cents)fill.style.background='#d18b62';track.append(fill);item.append(track,node('p',`Limite ${money(b.limit_cents)} · ${Math.round(b.actual_cents/b.limit_cents*100)}% usado`));}else item.append(node('p',b.limit_cents?'Escolha um único mês para comparar com o limite mensal.':'Defina o limite no Perfil.'));$('budgetList').append(item);}
  $('comparison').replaceChildren();if(g.comparison){const c=g.comparison;$('comparison').append(node('p',`${money(c.current_cents)} no período selecionado, frente a ${money(c.previous_cents)} em ${c.previous_month}.`),node('p',c.note,'small'));}else $('comparison').append(node('p','Selecione um único mês e importe o mês anterior para comparar os totais observados.','small'));
  $('goalSummary').replaceChildren(node('p',g.planning_margin_cents===null?'Informe a renda para avaliar o plano mensal.':`Margem do plano mensal declarado: ${money(g.planning_margin_cents)}. Não é dinheiro disponível em conta.`,'small'),node('p',g.reserve_coverage_months===null?'Informe os compromissos mensais para dimensionar a reserva.':`Reserva: ${g.reserve_coverage_months} mês(es) dos compromissos declarados. Meta: ${money(g.reserve_target_cents)}.`,'small'),node('p',g.goal_monthly_cents?`Aporte calculado para sua meta: ${money(g.goal_monthly_cents)}/mês, sem rendimentos.`:'Defina uma meta e um prazo para calcular o aporte.','small'));
}
function filteredRows(){
  const search=$('search').value.toLocaleLowerCase();return state.records.filter(r=>inPeriod(r)&&(!state.detailIds||state.detailIds.includes(r.id))&&(!$('statusFilter').value||r.status===$('statusFilter').value)&&(!$('typeFilter').value||r.type===$('typeFilter').value)&&[r.description,r.custom_description,r.category,r.institution].join(' ').toLocaleLowerCase().includes(search)).sort((a,b)=>$('sortFilter').value==='amount'?b.amount_cents-a.amount_cents:b.date.localeCompare(a.date)||b.id-a.id);
}
function renderTransactions(){
  const rows=filteredRows(),pages=Math.max(1,Math.ceil(rows.length/50));state.page=Math.min(state.page,pages);$('rows').replaceChildren();
  $('transactionCount').textContent=`${rows.length} lançamentos · ${money(rows.filter(r=>r.type==='debito').reduce((s,r)=>s+r.amount_cents,0))} em saídas nesta lista`;
  $('detailLabel').hidden=!state.detailIds;$('detailLabel').textContent=state.detailTitle+' · use Limpar filtros para voltar à lista';
  for(const r of rows.slice((state.page-1)*50,state.page*50)){
    const tr=node('tr'),dt=node('td',dateLabel(r.date));dt.append(node('small',r.institution));const desc=node('td');desc.append(node('span',r.custom_description||r.description,'description'));if(r.custom_description)desc.append(node('small',r.description));const cat=node('td',r.category);cat.append(node('small',natureLabels[r.nature]));const status=node('td'),select=node('select');select.setAttribute('aria-label','Classificação do lançamento '+r.id);
    for(const [key,label] of Object.entries(labels)){const o=node('option',label);o.value=key;select.append(o);}select.value=r.status;
    select.onchange=async()=>{select.disabled=true;try{await api('/api/classify/'+r.id,{...r,status:select.value,recurrence:!!r.recurrence});notice('Classificação salva somente neste lançamento.');await load();}catch(e){notice(e.message,true);select.value=r.status;}finally{select.disabled=false;}};
    status.append(select);const amount=node('td',(r.type==='debito'?'− ':'+ ')+money(r.amount_cents),'number '+(r.type==='debito'?'negative':'positive'));const action=node('td'),b=node('button','Editar','secondary');b.onclick=()=>edit(r);action.append(b);tr.append(dt,desc,cat,status,amount,action);$('rows').append(tr);
  }
  if(!rows.length){const tr=node('tr'),td=node('td','Nenhum lançamento corresponde aos filtros.','empty-state');td.colSpan=6;tr.append(td);$('rows').append(tr);}
  $('pageInfo').textContent=`Página ${state.page} de ${pages} · até 50 itens por página`;$('prevPage').disabled=state.page<=1;$('nextPage').disabled=state.page>=pages;
}
for(const id of ['search','statusFilter','typeFilter','sortFilter'])$(id).addEventListener(id==='search'?'input':'change',()=>{state.page=1;renderTransactions();});
$('prevPage').onclick=()=>{state.page--;renderTransactions();};$('nextPage').onclick=()=>{state.page++;renderTransactions();};
$('clearFilters').onclick=()=>{state.detailIds=null;state.page=1;$('search').value='';$('statusFilter').value='';$('typeFilter').value='';renderTransactions();};
function renderSuggestions(){
  const list=$('suggestions');list.replaceChildren();const suggestions=state.report.diagnosis.suggestions;
  if(!suggestions.length)empty(list,'Nenhuma sugestão para este período.','Você pode classificar qualquer lançamento manualmente.');
  for(const s of suggestions){const r=state.records.find(r=>r.id===s.id),el=node('div',undefined,'suggestion-row'),copy=node('div');copy.append(node('strong',s.category+' · '+money(r.amount_cents)),node('p',r.description),node('p',s.reason,'muted'));const b=node('button','Conferir','secondary');b.onclick=()=>edit(r);el.append(copy,b);list.append(el);}
}
const editFields=['status','nature','category','subcategory','custom_description','notes'];
async function edit(r){
  state.selected=r.id;const form=$('editForm');for(const key of editFields)form.elements[key].value=r[key];form.elements.recurrence.checked=!!r.recurrence;
  $('original').textContent=r.description;$('originalMeta').textContent=`${dateLabel(r.date)} · ${r.institution} · ${r.type==='debito'?'Débito':'Crédito'} ${money(r.amount_cents)}`;$('editError').textContent='';$('history').replaceChildren();
  const suggestion=state.report.diagnosis.suggestions.find(s=>s.id===r.id);$('editSuggestion').replaceChildren();$('editSuggestion').hidden=!suggestion;
  if(suggestion){const b=node('button','Preencher sugestão: '+suggestion.category,'secondary');b.type='button';b.onclick=()=>{form.elements.category.value=suggestion.category;form.elements.nature.value=suggestion.nature;form.elements.status.value='confirmada';syncPending();};$('editSuggestion').append(node('p',suggestion.reason,'small'),b);}
  syncPending();$('editor').showModal();
  try{const items=await api('/api/history/'+r.id);if(state.selected!==r.id)return;for(const item of items){const after=JSON.parse(item.after_json),before=item.before_json?JSON.parse(item.before_json):null;const el=node('div',undefined,'history-item');el.append(node('strong',new Date(item.changed_at).toLocaleString('pt-BR')));const changes=[];for(const key of ['status','category','nature','subcategory','custom_description','notes','recurrence'])if(!before||before[key]!==after[key])changes.push(`${key}: ${before?.[key]??'—'} → ${after[key]??'—'}`);el.append(node('p',changes.join(' · ')));$('history').append(el);}}catch(e){$('editError').textContent=e.message;}
}
function syncPending(){const f=$('editForm'),pending=f.elements.status.value==='pendente';f.elements.category.readOnly=pending;f.elements.nature.disabled=pending;f.elements.recurrence.disabled=pending;if(pending){f.elements.category.value='Não identificado';f.elements.nature.value='nao_definido';f.elements.recurrence.checked=false;}}
$('editForm').elements.status.onchange=syncPending;$('cancel').onclick=()=>$('editor').close();
$('editForm').onsubmit=async e=>{e.preventDefault();const f=e.target,data={};for(const key of editFields)data[key]=f.elements[key].value;data.recurrence=f.elements.recurrence.checked;const submit=f.querySelector('[type=submit]');submit.disabled=true;try{await api('/api/classify/'+state.selected,data);$('editor').close();notice('Lançamento atualizado. Histórico preservado.');await load();}catch(err){$('editError').textContent=err.message;}finally{submit.disabled=false;}};
function parseMoney(value){
  value=value.trim();if(!value)return 0;
  if(!/^(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d{1,2})?$/.test(value))throw Error('Use valores em reais no formato 1.234,56, sem símbolos.');
  const [whole,decimal='']=value.replaceAll('.','').split(',');const result=Number(whole)*100+Number(decimal.padEnd(2,'0'));if(!Number.isSafeInteger(result)||result>100000000000)throw Error('Valor fora do limite permitido.');return result;
}
function fillProfile(){const f=$('profileForm');for(const [key,value] of Object.entries(state.profile)){f.elements[key].value=key.endsWith('_cents')?(value?(value/100).toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2}):''):value;}}
$('profileForm').onsubmit=async e=>{e.preventDefault();const data={};try{for(const key of Object.keys(state.profile)){const value=e.target.elements[key].value;data[key]=key.endsWith('_cents')?parseMoney(value):key==='goal_name'?value:Number(value);}await api('/api/profile',data);state.profile=await api('/api/profile');await loadReport();resetChat();notice('Perfil salvo. Seu plano de ação foi atualizado.');navigate('plan');}catch(err){notice(err.message,true);}};
async function refreshAI(){
  const b=$('refreshAI');b.disabled=true;
  try{const d=await api('/api/ai/status'),previous=$('aiModel').value;$('aiStatus').textContent=d.message;$('aiStatus').classList.toggle('ready',d.available);$('aiModel').replaceChildren();
    if(!d.models.length){const o=node('option','Nenhum modelo local detectado');o.value='';$('aiModel').append(o);}for(const name of d.models){const o=node('option',name);o.value=name;$('aiModel').append(o);}if(d.models.includes(previous))$('aiModel').value=previous;
    $('chatMode').querySelector('[value=ollama]').disabled=!d.available;
    if(!d.available&&$('chatMode').value==='ollama'){$('chatMode').value='local_rules';updateMode();}
  }catch(e){$('aiStatus').textContent=e.message;}finally{b.disabled=false;}
}
function updateMode(){resetChat();$('chatModeLabel').textContent=$('chatMode').value==='ollama'?'IA local · '+$('aiModel').value:'Diagnóstico local por regras · sem modelo generativo';}
$('refreshAI').onclick=refreshAI;$('chatMode').onchange=updateMode;$('aiModel').onchange=updateMode;$('clearChat').onclick=()=>{if(!state.chatting)resetChat();};
function chatMessage(role,content,label){if($('chatLog').querySelector('.chat-welcome'))$('chatLog').replaceChildren();const el=node('div',undefined,'message '+role);el.append(node('span',label,'message-label'),document.createTextNode(content));$('chatLog').append(el);$('chatLog').scrollTop=$('chatLog').scrollHeight;return el;}
async function ask(question){
  if(state.chatting)return;state.chatting=true;$('sendChat').disabled=true;$('chatMode').disabled=true;$('aiModel').disabled=true;
  chatMessage('user',question,'VOCÊ');const waiting=chatMessage('assistant','Analisando seus dados… Um modelo local pode levar alguns minutos.','ASSISTENTE');
  try{const d=await api('/api/chat',{question,mode:$('chatMode').value,model:$('aiModel').value,messages:state.chatHistory.slice(-12),...state.period});waiting.remove();chatMessage('assistant',d.answer,d.mode==='ollama'?'IA LOCAL · '+d.model:'DIAGNÓSTICO POR REGRAS');state.chatHistory.push({role:'user',content:question},{role:'assistant',content:d.answer.slice(0,8000)});$('chatQuestion').value='';}catch(e){waiting.remove();chatMessage('assistant',e.message,'CONEXÃO NÃO CONCLUÍDA');}finally{state.chatting=false;$('sendChat').disabled=false;$('chatMode').disabled=false;$('aiModel').disabled=false;}
}
$('chatForm').onsubmit=e=>{e.preventDefault();const question=$('chatQuestion').value.trim();if(question)ask(question);};document.querySelectorAll('[data-prompt]').forEach(b=>b.onclick=()=>ask(b.dataset.prompt));
$('pdfFile').onchange=async e=>{
  const file=e.target.files[0];if(!file)return;state.pdfRecords=[];$('pdfPreview').hidden=true;e.target.disabled=true;
  try{if(file.size>20000000)throw Error('O arquivo excede 20 MB.');notice('Lendo o extrato. Aguarde a prévia…');const response=await fetch('/api/pdf/preview',{method:'POST',headers:{'Content-Type':'application/pdf'},body:file});const data=await response.json();if(!response.ok)throw Error(data.error);state.pdfRecords=data.records;$('pdfRows').replaceChildren();for(const r of data.records){const tr=node('tr');for(const value of [dateLabel(r.date),r.description,r.type==='debito'?'Débito':'Crédito',money(r.amount_cents)])tr.append(node('td',value));$('pdfRows').append(tr);}
    const outgoing=data.records.filter(r=>r.type==='debito').reduce((s,r)=>s+r.amount_cents,0),incoming=data.records.filter(r=>r.type==='credito').reduce((s,r)=>s+r.amount_cents,0);
    $('pdfSummary').textContent=`${data.bank} · ${data.records.length} lançamentos · Entradas ${money(incoming)} · Saídas ${money(outgoing)}`;$('pdfWarnings').replaceChildren(node('p',data.totals_verified?'Totais conferem com o PDF.':'Sem total geral disponível para conciliação automática.','small'),...data.warnings.map(w=>node('p',w,'small')));$('pdfPreview').hidden=false;notice('Prévia pronta. Confira e confirme para gravar.');
  }catch(err){notice(err.message,true);}finally{e.target.disabled=false;e.target.value='';}
};
$('cancelPdf').onclick=()=>{state.pdfRecords=[];$('pdfPreview').hidden=true;};
$('confirmPdf').onclick=async()=>{if(!state.pdfRecords.length)return;const button=$('confirmPdf');button.disabled=true;try{await api('/api/import',state.pdfRecords);state.pdfRecords=[];$('pdfPreview').hidden=true;if(!state.records.length)state.initialized=false;await load();notice('Extrato importado. Classificações manuais preservadas.');navigate('overview');}catch(e){notice(e.message,true);}finally{button.disabled=false;}};
$('importFile').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;await api('/api/import',JSON.parse(await file.text()));if(!state.records.length)state.initialized=false;await load();notice('Importação JSON concluída.');navigate('overview');}catch(err){notice(err.message,true);}finally{e.target.value='';}};
navigate(location.hash.slice(1)||'overview');load();
