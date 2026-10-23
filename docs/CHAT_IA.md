# Assistente financeiro local

A versão 2 implementa uma integração real com o Ollama, executado no mesmo computador. Não usa chave de API, assinatura do ChatGPT ou provedor em nuvem. A conversa desta plataforma não é incorporada ao aplicativo.

## Ativar no Windows

1. Instale o Ollama usando o instalador oficial em https://ollama.com/download/windows, conforme as permissões do computador.
2. Para desativar recursos de nuvem do Ollama, configure a variável de ambiente de usuário `OLLAMA_NO_CLOUD` com valor `1` e reinicie o Ollama.
3. Abra um terminal e execute `ollama pull qwen2.5:3b`. Esse é um ponto de partida compacto, com limitações de raciocínio financeiro; modelos maiores podem responder melhor se houver memória e processamento suficientes. O download inicial exige internet, espaço em disco e acesso autorizado ao registro do Ollama. Não é necessário repetir a cada uso.
4. Mantenha o Ollama aberto. Execute o painel normalmente com `py -3 app.py --open-browser`.
5. Abra **Assistente IA**, clique em **Verificar conexão**, selecione o modelo instalado e escolha **IA local · Ollama**.

O painel só conecta a `http://127.0.0.1:11434`. Não há campo para informar servidores externos. O transporte ignora proxies e recusa redirecionamentos. A lista exclui modelos identificados como remotos/cloud; `/api/show` também é verificado antes de enviar o contexto. Não há download ou instalação automática de modelos pelo painel. Consulte https://docs.ollama.com para instruções e requisitos atualizados.

Se o Ollama não estiver aberto, não houver modelo ou a resposta exceder o tempo de espera, a interface informa o problema. Ela não apresenta silenciosamente respostas por regras como respostas de IA. O modo **Diagnóstico por regras** continua disponível de forma independente.

## O que entra no contexto

O servidor calcula os números primeiro e envia ao modelo: período, totais em centavos, distribuição por natureza, perfil declarado, prioridades, limites de gastos e até dez maiores débitos com ID, categoria, data e valor. Não inclui PDFs, agência, conta, observações ou descrições bancárias completas. Os textos declarados de categorias/metas e as mensagens do usuário são tratados como dados não confiáveis; instruções de extratos não devem governar o modelo.

O modelo recebe até 12 mensagens anteriores, limitado a 24 mil caracteres. A conversa fica apenas na memória da página e é reiniciada ao atualizar, mudar o período, salvar o perfil, mudar o modo/modelo ou clicar em **Nova conversa**. Nenhuma resposta de chat modifica classificações, pagamentos ou dados bancários.

## Limitações e validação

Recomendações dependem de renda declarada, qualidade das classificações e cobertura dos extratos. O modelo pode errar, inclusive em cálculos ou interpretação; valores devem ser conferidos no painel. Não há promessa de retorno, avaliação de crédito, perfil de investidor ou execução de operações. Contas/transferências ausentes e extratos incompletos impedem inferir saldo ou renda a partir do fluxo bancário.

O contrato HTTP do Ollama foi consultado no repositório oficial. Os testes do projeto verificam solicitação, histórico, indisponibilidade, bloqueio de modelos remotos e ausência de dados bancários identificadores no contexto, usando respostas simuladas. A qualidade e velocidade da geração real devem ser verificadas no computador com o modelo instalado; o ambiente de desenvolvimento não possui um modelo Ollama carregado.
