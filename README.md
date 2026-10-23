# Meu Painel Financeiro

Aplicação local com Python 3.12+ e SQLite, sem dependências externas.

## Executar

No diretório do projeto:

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
