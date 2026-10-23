# Meu Painel Financeiro

Aplicação local com Python 3.12+ e SQLite, com extração de PDF via pypdf.

## Executar

No diretório do projeto, instale a dependência uma vez (requer acesso ao registro de pacotes autorizado):

```sh
python -m pip install -r requirements.txt
```

Depois execute:

```sh
python3 app.py --db data/finance.db --port 8000
```

O servidor atende somente na interface local. Esta versão é para uso local individual, sem autenticação. O arquivo SQLite é criado somente se ausente; reiniciar não apaga dados. Faça backups do banco com a aplicação parada. Processos precisam ser iniciados novamente em novas tarefas na nuvem.

## Importação e classificação

Use a opção de importar JSON na tela. O formato está em `examples/sardenha.json`; instituição, conta e identificador desse exemplo são marcadores explícitos, não dados bancários reais. Nenhum exemplo é carregado automaticamente. Para dados reais, informe instituição, conta e identificador estável fornecido pelo banco. Valores são inteiros positivos em centavos; tipo é `debito` ou `credito`. A data usa `AAAA-MM-DD`. Campos bancários adicionais são preservados no JSON original no banco.

Após importar, selecione **Pendente de identificação** na coluna Classificação. O lançamento de referência passa a categoria **Não identificado**, mantém R$ 953,80 nas saídas realizadas e deixa de gerar recorrência ou projeção. O indicador de pendentes abre a lista filtrada. Em **Editar / histórico**, edite categoria, subcategoria, descrição personalizada, recorrência e observações ou consulte as alterações com horário UTC.

Cada seleção na interface cria uma classificação manual, inclusive a opção “Automática — não revisada”: o status de revisão e a origem da edição são campos distintos. Regras automáticas através de `Finance.classify(..., source='automatic')` respeitam a prioridade manual. Esta versão não presume categorias pelo nome de beneficiários.

Dados bancários e histórico têm proteção contra atualização e exclusão por triggers. Classificações ficam em tabela separada, com histórico antes/depois. A mesma identidade bancária é importada uma única vez; conflito nos dados gera erro e desfaz o lote inteiro. Transações com identificadores distintos são mantidas mesmo quando semelhantes, disponíveis para análise humana de duplicidade; não há exclusão por similaridade.

O total de pendentes soma os valores absolutos e inclui créditos e débitos; as saídas e categorias do dashboard consideram apenas débitos. A estimativa de despesas fixas soma os débitos explicitamente confirmados como recorrentes; não é um calendário de vencimentos e não deduplica meses históricos. Não marque múltiplos pagamentos históricos da mesma obrigação para estimar uma única parcela mensal.

## Testar

```sh
python3 -m unittest -v
```

Os testes usam bancos temporários e cobrem os seis requisitos, preservação dos originais, conflitos de importação e independência do aluguel. Nenhum dado real é necessário.

## Windows: iniciar localmente

Extraia todos os arquivos em uma pasta com permissao de escrita e abra `INICIAR_WINDOWS.bat` com duplo clique. O inicializador usa o Python instalado, inicia o painel e abre o navegador. Mantenha o terminal aberto durante o uso. Os dados ficam em `data/finance.db` nessa mesma pasta. A importação PDF requer pypdf: instale com `py -3 -m pip install -r requirements.txt` antes do uso. Após instalar, o processamento é local e não envia extratos a serviços externos. Requer Python 3.12+.

Se aparecer conexao recusada, confira se o terminal mostra a mensagem de inicializacao ou algum erro. Se aparecer uma pagina de bloqueio corporativo, solicite a TI autorizacao para o servidor local em `http://127.0.0.1:8000`; o inicializador nao altera politicas, proxy ou firewall.

## Extratos PDF

Na tela, selecione um PDF textual Bradesco Celular ou Banco do Brasil e confira a prévia antes de confirmar. Limite: 20 MB e 200 páginas. PDFs digitalizados e protegidos não são suportados. A prévia não grava lançamentos. Saldos e totais não viram transações; o total geral do Bradesco é conciliado quando disponível. Descrições em múltiplas linhas são reunidas. Nenhum beneficiário gera classificação confirmada automaticamente.

A identidade usa banco, conta, data, documento, descrição, tipo, valor e ocorrência. Reimportar o mesmo conteúdo mantém as classificações. PDFs sobrepostos que alterem descrições ou a quantidade de operações idênticas precisam de conferência humana; não é possível garantir identidade bancária universal a partir de PDF.

O JSON original de cada lançamento guarda documento, página e SHA-256 do PDF. O arquivo PDF completo não é armazenado pelo painel; guarde o original em local seguro. Arquivos enviados nesta conversa não fazem parte do repositório.

## Análise e conselheiro local

A seção Análise financeira oferece período, barras mensais de entradas/saídas, categorias, natureza dos débitos e dez maiores débitos. Clique nas barras ou no ranking para abrir as movimentações. Os cartões superiores continuam mostrando o conjunto completo; a seção Análise e a tabela usam o período selecionado.

Em Editar / histórico, confirme a classificação e defina a natureza: essencial, supérfluo, transferência ou investimento/resgate. Créditos confirmados como essenciais representam renda para as sugestões. Itens pendentes ou não revisados permanecem sem natureza analítica confirmada. Nenhum nome de estabelecimento determina sozinho que uma despesa é supérflua. A alteração de natureza fica no histórico. O SQLite recebe uma coluna adicional sem remover dados existentes.

As recomendações mostram valores observados e cenários: por exemplo, reduzir em 10% os débitos explicitamente marcados como supérfluos. O limiar de 30% da renda confirmada é apenas referência. Fluxo líquido não é saldo da conta; entradas não são automaticamente salário, e transferências podem aparecer nas duas contas. O assistente local responde sobre maiores débitos, fluxo e revisão; não usa modelo generativo nem mantém contexto conversacional entre perguntas. Não executa alterações bancárias.
