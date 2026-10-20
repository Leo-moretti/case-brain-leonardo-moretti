# Registro de uso de IA

Uma entrada por sessão, da mais antiga para a mais recente. Formato e regras em `AGENTS.md`.


### 2026-10-19T19:49-03:00 · Claude Code (Claude Opus 5.5)

- **Pedido:** comandos do candidato, em ordem:
  1. Perguntou se a IA tinha o contexto da conversa anterior, fechada sem registro. A IA verificou a memória, as transcrições, o `AI_LOG.md` e o git: não havia nada salvo, então o trabalho recomeçou do zero.
  2. Pediu o escopo e as restrições do trabalho:
     - **Prazo:** último commit até as 22h.
     - **Repositório:** GitHub pessoal e público, usado como treino.
     - **Restrição de nomes:** proibido citar o empregador ou clientes em qualquer arquivo.
     - **EDA:** detalhada, separando perguntas técnicas, as perguntas do enunciado e perguntas de negócio.
     - **Stack:** SQLite como fonte; camadas bronze, silver e gold, com "dbt simples ou SQL e Python direto"; testes; Docker para reprodutibilidade; chat com IA via Gemini ou modelo local, conforme o README.
  3. Pediu para melhorar este registro, dando ênfase aos comandos e às validações dele. Avisou que começaria a revisar o trabalho em seguida.

- **O que a IA fez ou sugeriu:**
  1. **Integridade dos dados:** conferiu o SHA-256 e a contagem de linhas dos 9 CSVs contra o `MANIFESTO_v1.csv`. Tudo bateu.
  2. **EDA:** fez 4 rodadas de perfilamento e cruzamento de chaves com DuckDB, em scripts temporários fora do repositório. Registrou tudo em `docs/EDA.md`, marcando cada item como [C] confirmado, [H] hipótese ou [?] pergunta. Principais achados:
     - `orders.user_id` vem 100% vazio; o usuário só existe em `carts`.
     - A categoria Cashback mistura Pix com compra de pontos, que não é resgate.
     - A categoria Varejo inclui transferências para parceiros.
     - Algumas compras dividem o pagamento entre 2 contas, gerando 2 linhas de resgate.
     - Lote de 1.520 resgates de aéreas em 12/01/2026.
     - Há expiração de saldo migrado com validade registrada em 2028.
     - Nenhum ponto do programa novo expirou.
     - O CRM não tem grupo de controle.
     - O relatório do operador soma pontos de todos os status, o que explica o "R$ 0,016".
     - A adoção do Pix é de ~18% com ou sem a campanha.
  3. **Decisão de ferramenta:** recomendou SQL puro orquestrado por Python, em vez de dbt. Motivo: o adaptador SQLite do dbt é frágil. Implementou assim.
  4. **Pipeline:** `pipeline/build.py` com 7 modelos silver e 8 gold, cada um com o grão declarado. Criou o catálogo semântico `catalog/gold.yml`, que o build carrega no SQLite para o agente consultar. Escreveu também `pipeline/eda.py`, que reproduz os números citados.
  5. **Testes:** 54 testes cobrindo manifesto, chaves, integridade, conciliações ledger × pedidos, valores da apresentação e o validador de SQL do agente.
  6. **Dashboard e agente:** Streamlit com 6 abas. O agente transforma texto em SQL, restrito à gold, em conexão somente leitura. O provedor é Gemini ou Ollama, escolhido por variável de ambiente.
  7. **Entrega:** Dockerfile e compose; apresentação (`docs/apresentacao.md`), recomendação de uma página (`docs/recomendacao.md`) e seção de solução no README.
  8. **Git:** antes de cada commit, rodou `git grep` em busca de nomes proibidos. Confirmou que o git local usa o e-mail pessoal. Fez 2 commits com push na branch `entrega`, usando a credencial do `gh`.

- **O que o candidato conferiu, corrigiu ou rejeitou:**
  - **Definido pelo candidato:** a restrição de nomes, o prazo, a stack (SQLite, camadas, Docker, Gemini ou modelo local) e a escolha entre dbt e SQL/Python, que ele deixou para a IA.
  - **Erros da IA corrigidos na própria sessão:**
    - Dois números do texto da EDA divergiam do pipeline final: aéreas em jan sem o lote (77,4% → 77,1%) e varejo sem Pix (~17% → 17–19%, ainda abaixo da meta).
    - Um teste esperava 2.140 usuários de Pix numa tabela que conta aprovado ou estornado (2.172). As duas definições ficaram explícitas.
    - O README atribuía ao candidato conferências que a IA tinha feito. Foi reescrito.
    - Avisos do dashboard (parâmetro depreciado, coluna de tipo misto) foram corrigidos.
  - **Avaliação do candidato sobre o desempenho da IA:** o candidato atribui a qualidade e a agilidade desta sessão às configurações do agente que ele já tinha preparado antes: instruções globais e de projeto, regras de permissão e skills. Nesta sessão, atuaram de forma verificável:
    - as instruções de projeto (`AGENTS.md`/`CLAUDE.md`), que exigem registrar o uso de IA neste arquivo;
    - as instruções globais do candidato, que proíbem atribuir autoria à IA em commits e textos gerados;
    - as regras de permissão do ambiente, que bloquearam leitura e escrita de arquivos `.env*` e chamadas de rede não autorizadas. Por isso as variáveis de ambiente foram documentadas no README, em vez de num `.env.example`.

    Nenhuma skill foi acionada explicitamente nesta sessão.
  - **Decisão do candidato sobre a IA local:**
    - O Ollama fica registrado como implementado e não testado, por não ter sido priorizado.
    - O planejamento de tempo focou nos pontos mais críticos, já que o Gemini, provedor indicado no desafio, entregou o necessário de forma gratuita.
  - **Verificações após a entrega inicial:**
    - **Modelo:** a pedido do candidato, o padrão do agente mudou de `gemini-2.5-flash` para `gemini-3.8-flash` (`agent/core.py`, `docker-compose.yml`, `README.md`).
    - **Docker:** com a integração WSL ativada pelo candidato, a IA reconstruiu e subiu o container. O build da imagem rodou o pipeline e os 54 testes, que passaram. Ao recriar o container a partir do shell da IA, a chave do Gemini ficou de fora; o candidato subiu de novo com a chave.
    - **Agente (validação do candidato):** testou o agente com `gemini-3.8-flash` e avaliou o resultado como aceitável. Segundo ele, não inventou dados, as proteções (harness) funcionaram e a resposta veio concisa, em bullet points, direto ao ponto.
  - **Guardrails de qualidade de dados (pedido do candidato):**
    - **Pedido:** depois de rodar `pipeline.eda` e analisar o resultado, o candidato concluiu que o processo estava suscetível a quebrar ou entregar informação errada. Pediu guardrails para novas entradas de dados, um processo escalável e íntegro, e envio de alerta dummy por ser POC.
    - **O que a IA fez:**
      - 48 checks configuráveis em `quality/checks.yml`, com severidades bloqueante, alerta e info, cobrindo entrada, bronze, silver e gold.
      - Executor em `pipeline/quality.py` e notificador plugável com canal dummy em `pipeline/alerts.py`.
      - Publicação atômica do warehouse.
      - Histórico em JSONL e tabela `dq_resultados`, exposta no dashboard e no agente.
      - 9 testes novos com cargas corrompidas.
    - **Decisões da IA para o candidato revisar:**
      - O hash do manifesto deixou de bloquear e virou alerta, porque bloquearia toda carga nova legítima.
      - Problemas conhecidos da v1 ganharam limites calibrados para alertar quando piorarem.
      - A divergência do relatório do operador dispara alerta em toda carga, por ser um problema real em aberto.
    - **Verificado pela IA:** o detector de picos pega exatamente 12/01/2026 quando o lote não é excluído. São 63 testes passando; a suíte passou de ~4 s para ~2 min, porque cada cenário reconstrói o warehouse.
  - **Revisão de segurança e auditabilidade (pedido do candidato):**
    - **Pedido:** antes do commit e do restart do container, o candidato pediu verificar exposição de PII, dados sensíveis e aderência à política de segurança. Pediu também verificar se as informações financeiras do dashboard e do agente (valores a receber, descontos, conversões) são auditáveis no padrão Bacen.
    - **Achados da IA:**
      - não há PII direta nos dados (as ocorrências de "email" são rótulos);
      - o agente conseguia devolver `user_id` e `order_id`, e a recusa dependia só do prompt;
      - as respostas do agente não eram registradas;
      - a porta do container estava aberta em todas as interfaces, sem autenticação;
      - não havia indicação de que os valores são gerenciais;
      - os valores ficam em ponto flutuante;
      - a mensagem de erro do agente mostrava a exceção crua.
    - **Correções:**
      - guarda determinística de identificadores sobre os valores do resultado, que alias não burla;
      - trilha de auditoria `auditoria_agente.jsonl`;
      - rodapé "valores gerenciais, não contábeis" com a versão dos dados no agente e no dashboard;
      - porta publicada só em `127.0.0.1`;
      - mensagem de erro genérica;
      - 7 testes novos;
      - `docs/SEGURANCA_COMPLIANCE.md`.
    - **Não resolvido e documentado:** centavos em inteiro, trilha WORM, autenticação e identidade de quem pergunta, separação de acesso entre camadas, contratação de LLM externa (Res. CMN 4.893/2021), base legal e retenção. A IA ressalvou que a revisão é técnica e não substitui parecer jurídico ou de conformidade.
  - **Validação de número de cartão (pedido do candidato):**
    - **Pedido:** o candidato pediu a validação matemática de número de cartão, para saber se o ID em `carts` é identificador de sistema ou dado de cartão exposto.
    - **Correção de termo:** a IA apontou que `carts` tem `cart_id`, não `card_id`, e incluiu na análise o `account_id` de `cards` e os demais IDs.
    - **Método:** Luhn (mod 10), comprimento de PAN e prefixo de bandeira, em `pipeline/pan_check.py`.
    - **Resultado:**
      - todas as 13 colunas têm 12 dígitos (um PAN tem 13 a 19);
      - passam no Luhn em 9,7–10,3% dos valores, a taxa de acaso;
      - não concentram prefixos de bandeira.
    - **Conclusão:** são identificadores de sistema, não PAN. Teste em `tests/test_pan_check.py`.
  - **Documentação de governança (pedido do candidato):**
    - **Pedido:** o candidato pediu anotar as melhorias futuras de guardrails, criar o documento de classificação de dados e o dicionário de dados, e fazer o commit.
    - **O que a IA fez:**
      - seção "Melhorias futuras de guardrails" no README, com 10 itens priorizados;
      - `docs/CLASSIFICACAO_DADOS.md`, com 4 níveis e classificação por campo, por camada e por saída;
      - `docs/DICIONARIO_DADOS.md`, com as 9 fontes, tipos, nulos e domínios vindos da EDA.
    - **Ressalva da IA:** os níveis de classificação são uma proposta e devem ser alinhados à política da instituição.
  - **Revisão do candidato — pendente**, iniciada após esta entrada. Preencher com o resultado:
    - [x] Números da apresentação e da recomendação conferidos com `python -m pipeline.eda`
    - [x] Pegadinhas da EDA conferidas (amostra)
    - [x] Regras de negócio da silver revisadas pelo candidato. Segundo ele, as regras e os tratamentos foram inferidos com base no README do case e na experiência de desenvolvimento, sem confirmação do negócio. A pedido dele, as 10 regras inferidas foram registradas como `pendente_validacao_negocio` (`catalog/gold.yml` → `meta_regras_inferidas`, citadas pelo agente), e foi criado um benchmark de acurácia contra o relatório do operador (`python -m pipeline.benchmark`). Resultado: varejo 9/9 meses; aéreas e Pix batem em todos os meses exceto jun/26, quando o operador mudou de critério; pontos e transações Pix 100% (contando todos os status, como o operador); R$ Pix com erro de até 0,72% contra os aprovados.
    - [x] Recomendação e afirmações avaliadas pelo candidato
    - [x] Agente testado com chave do Gemini (`gemini-3.8-flash`): resultado aceitável, sem dados inventados, proteções funcionando, resposta concisa
    - [x] Exemplos reais do agente no README:
      - 1 resposta ("resumo financeiro do trimestre"): a IA conferiu os números contra a gold e eles batem ao centavo.
      - 4 recusas executadas pelo candidato:
        - perda nos últimos 30 dias;
        - margem de lucro;
        - top 10 clientes do Pix;
        - quanto o programa está pagando.
      - Avaliação: três recusas corretas. A última é excessiva: o custo pago pelo programa nos resgates existe na gold.
    - **Correção da recusa excessiva:**
      - O candidato verificou na tabela que o dado existe e pediu a correção.
      - A IA acrescentou ao catálogo (`catalog/gold.yml`) a regra "custo do programa = `custo_pontos_reais`; o que não existe é a receita por ponto paga pelo banco nem a margem".
      - No prompt do agente (`agent/core.py`), a IA instruiu responder com a métrica mais próxima, explicando a interpretação, e recusar só quando nenhuma coluna corresponder.
      - Warehouse reconstruído; 54 testes passando.
      - [x] Reteste pelo candidato, depois de a IA reconstruir o container com a chave mantida via `.env`.
        - A pergunta "quanto o programa está pagando?" passou a ser respondida com o custo mensal (`custo_pontos_reais`).
        - O agente explicitou a interpretação e trouxe as ressalvas do lote de 12/01 e da ausência de receita e margem.
        - O candidato avaliou como correto. A IA conferiu os 12 meses contra a gold: batem ao centavo.
    - A resposta do agente revelou um bug no dashboard: o markdown do Streamlit tratava "R$ … R$" como LaTeX e apagava os cifrões. A IA corrigiu, escapando o `$`.
    - [x] `docker compose up --build` executado
    - [x] Repositório revisado contra a restrição de nomes. A IA verificou: 0 ocorrências nos arquivos versionados, nos não versionados e no conteúdo de todo o histórico git; autores dos commits são só o e-mail pessoal do candidato e o autor do commit inicial do case

- **Arquivos criados ou alterados:**
  - `quality/checks.yml`, `pipeline/quality.py`, `pipeline/alerts.py`, `tests/test_quality.py` (guardrails)
  - `README.md`, `AI_LOG.md`, `.gitignore`, `.dockerignore`, `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `pytest.ini`, `setup.cfg`
  - `docs/EDA.md`, `docs/apresentacao.md`, `docs/recomendacao.md`
  - `catalog/gold.yml`, `pipeline/*.py`, `sql/silver/*.sql`, `sql/gold/*.sql`, `tests/*.py`, `agent/*.py`, `app/dashboard.py`
