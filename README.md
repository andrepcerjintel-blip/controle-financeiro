# Meu Painel Financeiro · versão 2

Painel local de finanças pessoais com Python 3.12+, SQLite, importação PDF e integração opcional com IA local via Ollama. Dados bancários e classificações são armazenados separadamente. A interface funciona sem bibliotecas, fontes ou serviços de gráficos externos.

## Iniciar no Windows

Extraia todos os arquivos, incluindo a pasta `assets`, em uma pasta onde você possa gravar. No terminal dessa pasta:

```bat
py -3 -m pip install -r requirements.txt
py -3 app.py --open-browser
```

Se seu Python for chamado `python`, substitua `py -3` por `python`. A instalação de `pypdf` é necessária apenas para importação PDF. Depois da instalação, o painel funciona localmente. O arquivo `INICIAR_WINDOWS.bat` é uma conveniência opcional; executar Python diretamente não depende dele. Mantenha o terminal aberto durante o uso.

O painel atende em `http://127.0.0.1:8000` e salva o banco em `data/finance.db`. Para usar outra porta ou banco, passe `--port` e `--db`. É um aplicativo local individual, sem autenticação multiusuário. Não é um serviço para publicar na internet.

## Atualizar preservando seus dados

1. Feche o painel e faça uma cópia da pasta `data` como backup.
2. Substitua os arquivos do projeto, inclusive `assets`, sem apagar ou substituir sua pasta `data`.
3. Execute a instalação das dependências e inicie novamente.

O SQLite é criado apenas se ausente. Mudanças de esquema são aditivas; perfil e metas ficam em uma tabela própria. Registros e histórico existentes são preservados. Não mantenha duas cópias da aplicação usando caminhos de banco diferentes sem saber qual contém seus dados.

## O que cada área faz

- **Visão geral:** entradas, saídas, fluxo líquido e pendências do mesmo período aplicado; barras mensais e distribuição das saídas; categorias e dez maiores débitos clicáveis.
- **Plano de ação:** prioridades explicadas, limites mensais, cenários de economia, reserva e aporte necessário para uma meta. Compara gastos a limites apenas em um único mês. Compara totais mensais observados, sem presumir extratos completos.
- **Movimentações:** busca, filtros, paginação e classificação individual. Sugestões por descrição são pistas para conferência; somente salvar no editor efetiva a alteração.
- **Perfil e metas:** renda líquida, limites, poupança, saldo/parcelas de dívidas, reserva e objetivo. Valores são declarados pelo usuário e separados das transações. Campos monetários em branco equivalem a informação não preenchida/zero para o planejamento, nunca a renda inferida.
- **Assistente IA:** diagnóstico por regras ou conversa com um modelo local real, com histórico em memória. Veja [configuração do Ollama](docs/CHAT_IA.md).
- **Importar extratos:** PDF com prévia e confirmação; formato JSON alternativo.

A natureza pode ser essencial, supérfluo, transferência, investimento/resgate, renda (crédito) ou dívida/custo financeiro. Ela só entra como confirmada na análise quando o status é Confirmada. Créditos essenciais de versões anteriores continuam tratados como renda por compatibilidade; novas edições devem usar Renda. Categorias e necessidade pessoal não são determinadas automaticamente por nomes de beneficiários.

O percentual de visibilidade indica a parcela das saídas cujo valor tem natureza confirmada. Não é score de crédito nem avaliação do perfil de investidor. Renda planejada não é saldo disponível. Essenciais, supérfluos, parcelas de dívidas e poupança devem ser planejados separadamente, sem sobreposição. A reserva usa essenciais + parcelas multiplicados pelos meses desejados. O aporte da meta não presume rendimentos nem inflação. Sugestões de redução de 10% são cenários, não previsões.

## Classificação manual e persistência

Selecionar **Pendente de identificação** define `status=pendente`, categoria **Não identificado**, natureza não definida e recorrência desativada. O valor continua nas saídas realizadas, disponível para análise, sem projeção automática. O indicador de pendentes considera créditos e débitos em valores absolutos; as saídas consideram apenas débitos.

O registro bancário original e o histórico são protegidos por triggers contra atualização e exclusão. Cada edição registra antes/depois com horário UTC, exibido no fuso do navegador. Categoria, subcategoria, descrição personalizada, natureza, recorrência e observações podem ser alteradas sem apagar o original. Ajustes manuais têm prioridade por lançamento e não se propagam para transações semelhantes.

A API legada `/api/dashboard` mantém uma soma simples de lançamentos explicitamente marcados como recorrentes; não é um calendário de parcelas nem uma previsão deduplicada. A nova interface baseia o planejamento nos valores declarados no Perfil e não apresenta essa soma como previsão futura.

## Importação

PDFs textuais Bradesco Celular e Banco do Brasil, até 20 MB e 200 páginas. Imagens digitalizadas e PDFs protegidos não são suportados. A prévia não grava dados. Saldos e totais não viram transações; o total geral do Bradesco é conciliado quando disponível. Aplicações e resgates permanecem movimentos bancários para revisão, sem serem presumidos consumo ou renda.

A identidade derivada do PDF usa banco, conta, data, documento, descrição, tipo, valor e ocorrência. Reimportar o mesmo conteúdo preserva as classificações. PDFs sobrepostos com descrições alteradas ou contagens diferentes de operações idênticas podem precisar de revisão de duplicidades. Não há exclusão automática por similaridade.

O JSON original preserva campos adicionais, documento, página e SHA-256 do PDF. O PDF completo não é armazenado pelo painel; guarde seu original. PDFs e dados reais enviados durante desenvolvimento não fazem parte do repositório.

O formato JSON está em `examples/sardenha.json`. Seus campos de instituição, conta e ID são marcadores explícitos de exemplo. Para uso real, informe dados bancários e identificadores estáveis. Valores são inteiros positivos em centavos e tipo `debito` ou `credito`; datas em `AAAA-MM-DD`. Conflito entre dados do mesmo ID rejeita o lote inteiro. Nenhum exemplo é importado automaticamente.

## Testes

```sh
python3 -m unittest -v
```

A suíte cobre classificação, reimportação, imutabilidade, migração, perfil, diagnóstico, contrato do Ollama e leitura de PDF com dados sintéticos.

Teste opcional de navegador, com Playwright instalado e Chromium disponível:

```sh
CHROMIUM_PATH=/usr/bin/chromium python3 tests/browser_smoke.py
```

Esse teste usa banco temporário e dados sintéticos; verifica importação, gráficos, filtros, edição, perfil, conversa por regras e layout móvel. Playwright não é uma dependência para executar o painel.
