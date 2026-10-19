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
  - **Não verificado pela IA:** chamada real ao Gemini (não havia chave) e build da imagem Docker (Docker indisponível no WSL).
  - **Revisão do candidato — pendente**, iniciada após esta entrada. Preencher com o resultado:
    - [ ] Números da apresentação e da recomendação conferidos com `python -m pipeline.eda`
    - [ ] Pegadinhas da EDA conferidas (amostra)
    - [ ] Regras de negócio da silver revisadas (modalidade, status APROVADO como resgate efetivado, lote de 12/01)
    - [ ] Recomendação e afirmações avaliadas: concorda, discorda ou ajusta
    - [ ] Agente testado com chave do Gemini, com exemplos reais registrados no README
    - [ ] `docker compose up --build` executado
    - [ ] Repositório revisado contra a restrição de nomes

- **Arquivos criados ou alterados:**
  - `README.md`, `AI_LOG.md`, `.gitignore`, `.dockerignore`, `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `pytest.ini`, `setup.cfg`
  - `docs/EDA.md`, `docs/apresentacao.md`, `docs/recomendacao.md`
  - `catalog/gold.yml`, `pipeline/*.py`, `sql/silver/*.sql`, `sql/gold/*.sql`, `tests/*.py`, `agent/*.py`, `app/dashboard.py`
