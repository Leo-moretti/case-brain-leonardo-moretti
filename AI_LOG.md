# Registro de uso de IA

Uma entrada por sessão, da mais antiga para a mais recente. Formato e regras em `AGENTS.md`.


### 2026-10-19T19:49-03:00 · Claude Code (Claude Opus 5.5)
- **Pedido:** retomar o case (a conversa anterior não ficou registrada) e fazer EDA detalhada com perguntas técnicas, do case e de negócio; montar o warehouse SQLite com bronze/silver/gold, testes, Docker, dashboard e agente (Gemini ou modelo local), reprodutível, com último commit até 22h; não citar nenhum empregador ou cliente.
- **O que a IA fez ou sugeriu:** conferiu os hashes contra o manifesto; perfilou os 9 CSVs e cruzou chaves com DuckDB em scripts temporários. Encontrou:
  - `orders.user_id` vazio;
  - Cashback misturando Pix e compra de pontos;
  - varejo incluindo transferências para parceiros;
  - lote de 1.520 resgates aéreos em 12/01/2026;
  - expiração de migração inconsistente com `valid_until`;
  - CRM sem grupo de controle;
  - relatório do operador somando pontos de todos os status.

  Escreveu `docs/EDA.md`, o pipeline SQL (sem dbt, por simplicidade), o catálogo semântico carregado no SQLite, 54 testes, o dashboard Streamlit, o agente texto→SQL restrito à gold com conexão somente leitura, o Dockerfile/compose, a apresentação, a recomendação e o README.
- **O que o candidato conferiu, corrigiu ou rejeitou:** pediu que nenhum nome de empregador ou cliente aparecesse no repositório (a IA verificou com `git grep` antes do commit). Correções da própria sessão:
  - números da EDA divergentes do pipeline (aéreas jan sem lote 77,4%→77,1%; varejo sem Pix ~17%→17–19%);
  - teste com definição errada de usuário Pix (2.140 vs 2.172);
  - README que atribuía ao candidato conferências feitas pela IA, reescrito.

  Não verificado no ambiente: chamada real ao Gemini (sem chave) e build da imagem Docker (Docker indisponível no WSL).
- **Arquivos criados ou alterados:** `README.md`, `AI_LOG.md`, `.gitignore`, `.dockerignore`, `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `pytest.ini`, `setup.cfg`, `docs/EDA.md`, `docs/apresentacao.md`, `docs/recomendacao.md`, `catalog/gold.yml`, `pipeline/*.py`, `sql/silver/*.sql`, `sql/gold/*.sql`, `tests/*.py`, `agent/*.py`, `app/dashboard.py`.
