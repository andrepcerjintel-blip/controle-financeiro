# Possibilidade de chat com IA generativa

É tecnicamente viável acrescentar um modelo por API ao backend Python. A conversa desta interface do ChatGPT não pode ser embutida ou reutilizada como autenticação do painel. Uma assinatura do ChatGPT não constitui credencial de API.

## Proposta de integração futura

1. Backend recebe a pergunta e calcula os mesmos agregados de analytics.py para o período selecionado. O modelo não calcula totais a partir do PDF.
2. Tela pede autorização explícita antes de transmitir dados a um provedor externo; informa quais dados serão enviados. Por padrão, apenas agregados por mês/categoria e identificadores locais, sem PDF, CPF, agência, conta ou nomes de beneficiários.
3. Credencial fica no ambiente do servidor, nunca no HTML, banco ou Git. A instalação corporativa precisa permitir a API escolhida.
4. Modelo recebe agregados como dados não confiáveis, inclusive descrições bancárias; instruções inseridas em documentos não devem alterar seu comportamento. Respostas devem citar período, valores e IDs e declarar limitações de cobertura.
5. A integração começa somente para leitura: nenhuma ferramenta para editar classificações, apagar lançamentos ou executar operações. Alterações continuam nos formulários existentes com histórico.
6. Definir provedor, custos/limites, retenção, timeouts e comportamento offline. Validar cálculos, referências, vazamento de dados e instruções maliciosas antes de ativar.

Nada disso foi ativado nesta versão. O chat atual é local por regras, identificado na interface. Para IA totalmente offline seria necessário escolher modelo e runtime compatíveis com o computador e com a política de instalação da empresa; isso exige avaliar memória e hardware disponíveis.
