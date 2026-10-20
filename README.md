# Case Analytics Engineer · Brain003   
  
Exercício 1. Programa Pontua+

---

# Solução

> Exercício de estudo em repositório pessoal. O enunciado original está mais abaixo, em **Enunciado do case**.

## Como rodar

**Com Docker (um comando).** Sobe o dashboard e o agente em http://localhost:8501. O build da imagem constrói o warehouse e roda os testes; se um número estiver errado, o build falha.

```bash
GEMINI_API_KEY=<sua_chave> docker compose up --build
```

**Sem Docker (Python 3.11+).**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pipeline.build          # CSVs -> warehouse/pontua.db (bronze, silver, gold)
python -m pytest                  # 86 testes (~2 min)
python -m pipeline.eda            # imprime todos os números citados na apresentação
streamlit run app/dashboard.py    # dashboard + agente
```

Os CSVs ficam em `dados/`, como vieram. O build confere o SHA-256 de cada arquivo contra `MANIFESTO_v1.csv` (diferença gera alerta, não bloqueio, para aceitar novas cargas) e roda os guardrails de qualidade descritos abaixo.

**Variáveis de ambiente do agente** (podem ir num `.env`, que está no `.gitignore`):

| Variável | Padrão | Uso |
|---|---|---|
| `LLM_PROVIDER` | `gemini` | `gemini` ou `ollama` |
| `GEMINI_API_KEY` | (vazio) | chave do Gemini (obrigatória para `gemini`) |
| `GEMINI_MODEL` | `gemini-3.8-flash` | modelo do Gemini |
| `OLLAMA_HOST` | `http://localhost:11434` | servidor Ollama local (no Docker: `http://host.docker.internal:11434`) |
| `OLLAMA_MODEL` | `llama3.1` | modelo local |

Sem chave, o dashboard funciona normalmente e só a aba "Pergunte aos dados" mostra o aviso de agente indisponível.

## Entregáveis

| Peça | Onde |
|---|---|
| Apresentação para a diretoria | [docs/apresentacao.md](docs/apresentacao.md) (Markdown compatível com Marp) |
| Prompt para gerar a apresentação em PPT via IA | [docs/prompt_apresentacao_ppt.md](docs/prompt_apresentacao_ppt.md) |
| Recomendação de uma página | [docs/recomendacao.md](docs/recomendacao.md) |
| EDA (entendimento dos dados, pegadinhas, perguntas) | [docs/EDA.md](docs/EDA.md) |
| Código | [pipeline/](pipeline/), [sql/](sql/) |
| Testes | [tests/](tests/) |
| Dashboard | [app/dashboard.py](app/dashboard.py) |
| Catálogo semântico (dashboard + agente) | [catalog/gold.yml](catalog/gold.yml) |
| Agente | [agent/core.py](agent/core.py) |
| Registro de uso de IA | [AI_LOG.md](AI_LOG.md) |
| Segurança, privacidade (LGPD) e auditabilidade | [docs/SEGURANCA_COMPLIANCE.md](docs/SEGURANCA_COMPLIANCE.md) |
| Dicionário de dados (fontes) | [docs/DICIONARIO_DADOS.md](docs/DICIONARIO_DADOS.md) |
| Classificação de dados | [docs/CLASSIFICACAO_DADOS.md](docs/CLASSIFICACAO_DADOS.md) |

## Respostas em resumo

1. **O que aconteceu.** O Pix (27/05/2026, R$ 0,019 por ponto) **somou** volume: os pontos resgatados por mês passaram de ~19–22 M para ~30–33 M, enquanto aéreas e varejo ficaram estáveis em valor absoluto. 56% dos usuários do Pix nunca tinham resgatado antes. **Metas:** aéreas segue acima de 50% (56–59%). Varejo cai para 12–13% e descumpre os 20% desde junho; já estava no limite antes do Pix (19,3% em abril). O Pix é a modalidade **mais cara por ponto** (R$ 0,019, contra 0,015 em aéreas e 0,0139 em varejo).
2. **Afirmações.**
   - CRM: **não se sustenta**. A adoção é de ~18% com ou sem o e-mail de lançamento, e a campanha começou um dia depois do lançamento.
   - Operador (R$ 0,016): **falsa**. É erro de cálculo: o relatório divide o valor dos aprovados pelos pontos de todos os status.
   - Breakage de 40%: **não reproduzível**. Nenhum ponto do programa novo venceu ainda (o primeiro vence em 25/09/2027); o expirado sobre o migrado é 19,8%.
3. **Recomendação.** Recalibrar o Pix (taxa ≤ R$ 0,015 ou teto por cliente) em vez de estimular ou encerrar. Detalhes e números em [docs/recomendacao.md](docs/recomendacao.md).

## Modelagem

```
dados/*.csv ──► bronze_* ──► silver_* ──► gold_* ──► dashboard / agente
               (texto bruto,  (tipado,     (métricas      + meta_regras, meta_tabelas,
                linhagem)      limpo,       por grão       meta_colunas (catálogo)
                               regras)      declarado)
```

**Ferramenta.** SQLite + SQL puro, orquestrado por um script Python (`pipeline/build.py`). Escolhi não usar dbt: o adaptador SQLite do dbt é pouco mantido e acrescentaria dependências sem ganho para 9 arquivos. O SQL por camada, numerado e com o grão declarado no cabeçalho, dá a mesma legibilidade. O SQLite é um arquivo só, roda em qualquer ambiente e é lido nativamente pelo Python, pelo Streamlit e pelo agente.

**Camadas.**
- **bronze** (`bronze_<arquivo>`): cópia fiel do CSV, tudo `TEXT`, string vazia vira `NULL`, mais `_row_id`, `_source_file` e `_loaded_at`. Nenhuma regra de negócio.
- **silver** (`sql/silver`): tipagem e as regras de limpeza descobertas na EDA. Usuário do pedido via `carts`; usuário do CRM via `device_id`; `modalidade` separando Pix de compra de pontos e produtos de transferências; flag do lote de 12/01/2026.
- **gold** (`sql/gold`): modelos com grão explícito, nomes em português de negócio e métricas já calculadas.

| Modelo gold | Grão | Responde |
|---|---|---|
| `gold_metas_mensal` | mês | metas de aéreas e varejo, em 3 definições |
| `gold_resgates_mensal` | mês × modalidade | volume, usuários, cancelamento, custo por ponto |
| `gold_fct_resgate` | item de resgate | cortes ad hoc (canal, fornecedor, classe de cartão) |
| `gold_dim_usuario` | usuário | cartão atual, migração, adoção do Pix |
| `gold_pontos_mensal` | mês | créditos, resgates, expirações, passivo |
| `gold_conciliacao_operador` | mês | relatório do operador × recálculo |
| `gold_campanha_pix` | grupo de exposição | afirmação do CRM |
| `gold_breakage` | métrica candidata | afirmação do breakage |

**Estrutura para dashboard e agente.** A mesma camada gold serve aos dois:
- **Agregados prontos** (mensais) para o dashboard e para a maioria das perguntas do agente, o que reduz a chance de ele recalcular uma métrica de um jeito diferente do painel.
- **Um fato no grão do item** para perguntas que os agregados não cobrem.
- **Nomes autoexplicativos** (`pontos_aprovados_sem_lote`, `varejo_pct_sem_pix`) e as definições alternativas de meta como colunas, não como lógica escondida no painel.
- **Catálogo semântico** ([catalog/gold.yml](catalog/gold.yml)) com grão, descrição de cada coluna e as regras/ressalvas de negócio. É a fonte única: o build carrega o catálogo no próprio SQLite (`meta_regras`, `meta_tabelas`, `meta_colunas`). **É assim que o agente descobre o que cada campo significa:** o prompt dele é montado a partir dessas tabelas, então documentar uma coluna nova no YAML basta para o agente passar a entendê-la.

**Agente.** Fluxo texto → SQL → resposta ([agent/core.py](agent/core.py)):
1. O LLM recebe o catálogo e devolve um JSON com o SQL a executar ou com uma recusa.
2. O SQL passa por validação determinística: uma única instrução SELECT, só tabelas `gold_*` (bronze, silver e `sqlite_master` são bloqueadas).
3. O SQL roda numa conexão SQLite **somente leitura**, limitada a 200 linhas.
4. O LLM redige a resposta só com o resultado da consulta e acrescenta a ressalva aplicável do catálogo.

O agente recusa perguntas sobre dados pessoais ou individuais, sobre dados que não existem (preço pago pelo banco, margem, datas após a extração) e assuntos fora do programa.

Exemplo real (`gemini-3.8-flash`, resposta resumida):

> **Pergunta:** resumo financeiro do trimestre
>
> **Resposta:** Resumo dos resgates aprovados de jul a set/2026.
> - **Consolidado:** 6.139 itens · 95.379.474 pontos · R$ 1.693.078,49 em produtos · R$ 166.347,63 de copagamento · R$ 1.526.730,86 cobertos por pontos.
> - **Aéreas:** 2.299 itens · 55.631.000 pontos · R$ 834.270,23 · ~R$ 0,0150/ponto.
> - **Pix:** 2.029 itens · 27.713.204 pontos · R$ 526.551,95 · R$ 0,0190/ponto.
> - **Varejo (produtos):** 1.603 itens · 11.048.270 pontos · R$ 153.571,18 · R$ 0,0139/ponto.
> - **Transferência para parceiros:** 208 itens · 987.000 pontos · R$ 12.337,50 · R$ 0,0125/ponto.
> - **Por mês:** jul 30,5 M pontos / R$ 489.078,76 · ago 31,4 M / R$ 502.879,91 · set 33,5 M / R$ 534.772,19.
>
> *Ressalva:* a categoria varejo do sistema inclui transferências para parceiros; a definição contratual ainda não foi confirmada.

Todos os números foram conferidos contra `gold_resgates_mensal` e batem ao centavo. Ponto de melhoria observado: o agente não avisou que o "resumo financeiro" cobre só o custo dos resgates, porque a receita (quanto o banco paga por ponto) não existe nos dados.

Recusas reais (`gemini-3.8-flash`):

| Pergunta | Resposta do agente | Avaliação |
|---|---|---|
| "Qual valor de perda nos últimos 30 dias" | Recusa: não há dado de "perda" (financeira, margem, prejuízo ou operacional); sugere especificar pontos expirados, itens cancelados ou estornos | Correta: termo ambíguo, sem métrica correspondente, e ainda oferece alternativas |
| "Me informe a margem de lucro resultante da ação" | Recusa: margem de lucro e resultado financeiro líquido não constam nas tabelas | Correta: a receita não existe nos dados |
| "Liste os 10 clientes que mais usaram Pix" | Recusa: a política não permite listar ou identificar clientes individualmente | Correta: dados individuais |
| "Quanto o programa está pagando?" | Recusa: o valor pago pelo banco ou pelo programa por ponto não consta; cita o custo por ponto das modalidades (Pix R$ 0,019) | **Parcial:** recusa excessiva. O custo pago pelo programa nos resgates existe (`custo_pontos_reais`). Corrigido (abaixo) |

**Correção da recusa excessiva.** Foi acrescentada ao catálogo a regra "custo do programa = `custo_pontos_reais`; não existe receita por ponto nem margem". O prompt passou a orientar o agente a responder com a métrica mais próxima, dizendo como interpretou a pergunta. A mesma pergunta, depois da correção:

> **Resposta:** A pergunta foi interpretada como o custo mensal dos resgates coberto por pontos (`custo_pontos_reais`).
> - 10/2025: R$ 127.719,07 · 11/2025: R$ 146.871,22 · 12/2025: R$ 177.459,43
> - 01/2026: R$ 1.321.911,95 · 02/2026: R$ 233.786,06 · 03/2026: R$ 280.120,63
> - 04/2026: R$ 277.030,62 · 05/2026: R$ 321.017,52 · 06/2026: R$ 487.390,68
> - 07/2026: R$ 489.078,76 · 08/2026: R$ 502.879,91 · 09/2026: R$ 534.772,19
>
> *Ressalva:* o pico de 01/2026 inclui o lote atípico de aéreas de 12/01/2026. Os valores são o custo coberto por pontos (sem copagamento); não há registro de receita do banco ao programa nem de margem.

Os 12 meses foram conferidos contra `gold_resgates_mensal` e batem ao centavo. A resposta também trouxe sozinha as duas ressalvas relevantes do catálogo: o lote de 12/01 e a ausência de receita.

Respostas com ressalva (`gemini-3.8-flash`, depois das guardas, da trilha de auditoria e das regras inferidas):

> **Pergunta:** Qual o percentual de varejo em setembro?
>
> **Resposta:** Em setembro de 2026 o varejo foi de 12,95% pela categoria do sistema (produtos e transferências para parceiros). Só com produtos de varejo, 12,01%. Excluindo o Pix do denominador, 17,99%.
> *Ressalva:* a meta contratual é de no mínimo 20%; o cálculo padrão inclui transferências em varejo e mantém o Pix na base, pontos que dependem de validação contratual (R02 e R03).
> *Valores gerenciais (não contábeis) · versão dos dados: 20261020T003939287558*

> **Pergunta:** O breakage está em 40%?
>
> **Resposta:** Não. O primeiro vencimento de créditos do programa novo ocorre em 25/09/2027. Métricas observadas:
> - expiração sobre o saldo migrado: 19,78% (única expiração até agora);
> - expiração sobre as saídas (expirados + resgatados): 16,54%;
> - provável origem dos "40%": expirados / resgatados em fev–mai/26 = 37,11%, cálculo que não representa breakage.
>
> *Ressalva:* o breakage do programa novo não é mensurável; nenhum crédito venceu até a extração.
> *Valores gerenciais (não contábeis) · versão dos dados: 20261020T003939287558*

Todos os números foram conferidos contra `gold_metas_mensal` e `gold_breakage` e batem. A primeira resposta citou espontaneamente os ids das regras inferidas pendentes (R02, R03). A segunda tem uma imprecisão de redação: disse que "o breakage do programa novo é atualmente 0". O correto é "não mensurável" (0 pontos expirados porque nada venceu, não uma taxa de 0%). A ressalva final corrige, mas o texto principal deveria ter evitado a afirmação.

## Testes

São 86 testes (`python -m pytest`, ~2 min), que reconstroem o warehouse do zero a partir dos CSVs:
- **Carga:** contagem de linhas por arquivo = manifesto. O hash é verificado no build.
- **Chaves:** unicidade e não nulidade da chave de cada modelo silver/gold; grão de `gold_resgates_mensal`.
- **Integridade referencial:** item → pedido, ledger → cartões, um cartão mais recente por usuário, códigos de operação conhecidos, nenhum usuário sem resolução.
- **Conciliações que garantem os números:**
  - resgate no ledger = `paid_points` dos itens aprovados e estornados (323.423.650);
  - estorno no ledger = itens estornados + estornos parciais;
  - `redeemed_points` = `paid_points` por item;
  - reservas que se anulam;
  - agregados mensais = fato;
  - saldo acumulado = soma do ledger;
  - percentuais somam 100.
- **Valores de referência da apresentação:** taxa do Pix, metas de abril, junho e setembro, lote de 12/01, grupos da campanha, critério do relatório do operador.
- **Segurança do agente:** o validador de SQL bloqueia DML, DDL, múltiplas instruções e tabelas fora da gold.

## Guardrails de qualidade de dados

Os problemas encontrados na EDA mostram que este processo quebra com facilidade ou, pior, entrega número errado sem quebrar. Exemplos:
- um status novo sumiria das métricas;
- um timestamp em UTC deslocaria o mês;
- uma carga reenviada duplicaria resgates.

Por isso o build passa por guardrails a cada camada.

```
CSVs ─► entrada (arquivo existe, hash) ─► bronze (contrato de colunas, chaves, domínios, formatos)
     ─► silver (integridade, resolução de usuário, sinais) ─► gold (conciliações, anomalias)
     ─► tudo ok? ── sim ─► publica o warehouse (troca atômica do arquivo)
                    não ─► interrompe, mantém a versão anterior, dispara alerta
```

- **Escalável:** os 48 checks ficam em [quality/checks.yml](quality/checks.yml). Cada um é um SQL que devolve um número, com uma regra (`igual`, `max` ou `min`) e uma severidade. Para criar um check novo basta acrescentar uma entrada no YAML, sem mexer em código.
- **Severidades:**
  - **bloqueante**: interrompe a carga. Usada para contrato, chaves, domínios, formato de data e conciliações.
  - **alerta**: avisa e segue. Usada para mudança de taxa do Pix, picos de volume, divergência do relatório do operador e piora de problemas conhecidos.
  - **info**: só registra.
- **Problemas conhecidos calibrados:** os problemas da v1 têm limites calibrados para alertar quando **piorarem**. Exemplos: contas com saldo negativo (7,5%, limite de 8%) e expiração de migração sem crédito (22,9%, limite de 25%).
- **Integridade:** o build escreve num arquivo temporário e só faz `os.replace` se nada bloqueante falhar. Dashboard e agente nunca leem uma carga quebrada.
- **Alerta (POC):** canal dummy em [pipeline/alerts.py](pipeline/alerts.py), que grava em `warehouse/alertas.jsonl` e imprime no stderr. Para usar Slack ou e-mail, basta implementar `Notifier` e escolher o canal por `DQ_ALERT_CHANNEL`.
- **Observabilidade:**
  - os resultados da última carga ficam em `dq_resultados`, no próprio warehouse, e aparecem na aba "Qualidade de dados" do dashboard;
  - o agente também consulta `dq_resultados` e pode citar alertas ao responder;
  - o histórico de todas as execuções, inclusive as interrompidas, fica em `warehouse/dq_historico.jsonl`.
- **Na v1:** 48 checks, nenhum bloqueante falha. Um alerta real dispara: o relatório do operador diverge 22,7% nos pontos Pix.
- **Detector de picos:** valida dias com mais de 10× a mediana diária da modalidade. Sem a exclusão do lote conhecido, ele pega exatamente 12/01/2026 (1.520 itens contra a mediana de 21) e nenhum outro dia.
- **Testes ([tests/test_quality.py](tests/test_quality.py)):** simulam cargas corrompidas e verificam que a carga é bloqueada, que o warehouse anterior fica intacto e que o alerta é gerado. Cenários: status novo, coluna renomeada, item duplicado, timestamp em UTC e arquivo ausente. Também simulam uma mudança da taxa do Pix e verificam que ela só gera alerta e publica.

### Melhorias futuras de guardrails

Ainda não implementadas, em ordem de prioridade:
1. **Detecção de número de cartão como bloqueante.** Rodar o Luhn de `pipeline/pan_check.py` em toda carga e barrar colunas com valores de 13–19 dígitos e taxa de Luhn acima de 90%. O mesmo vale para padrões de CPF e e-mail em campos livres, como `event_properties`.
2. **k-anonimato no agente.** Além de bloquear identificadores, recusar resultados agregados com grupos de menos de 10 usuários.
3. **Limites estatísticos dinâmicos.** Trocar os limites fixos (8%, 25%, 10× a mediana) por bandas calculadas no histórico `dq_historico.jsonl` (média ± k desvios, sazonalidade por dia da semana).
4. **Checks de frescor e completude por data de extração,** com SLA de chegada por arquivo e alerta de atraso.
5. **Carga incremental com idempotência:** chave de deduplicação por arquivo e período, com quarentena das linhas rejeitadas em vez de bloquear a carga inteira.
6. **Valores monetários em centavos inteiros** já na silver, com checks de soma ao centavo.
7. **Contratos versionados** (schema em JSON Schema ou similar) acordados com os donos dos sistemas de origem, com alerta de mudança antes da carga.
8. **Canal de alerta real** (Slack, e-mail, PagerDuty) com deduplicação e reconhecimento, para que problemas conhecidos não gerem ruído a cada carga.
9. **Trilha de auditoria imutável** (WORM) e identidade do usuário via SSO em cada registro.
10. **Execução agendada e observável** (orquestrador com histórico, retries e painel de SLA).

## Segurança e auditabilidade

Detalhes e lacunas para produção em [docs/SEGURANCA_COMPLIANCE.md](docs/SEGURANCA_COMPLIANCE.md). Em resumo:
- **Nenhum dado pessoal direto nos dados.** Os IDs pseudonimizados não saem pelo agente: uma guarda determinística bloqueia o resultado se ele contiver um ID real de cliente ou pedido, antes de enviar à LLM.
- **Trilha de auditoria do agente** em `warehouse/auditoria_agente.jsonl`. Cada pergunta registra modelo, versão dos dados, SQL, hash do resultado, resposta e status.
- **Indicação de origem e versão:** dashboard e respostas mostram "valores gerenciais, não contábeis" e a versão dos dados (`run_id`).
- **Rede e erros:** a porta do container fica só em `127.0.0.1`; o erro do agente não expõe detalhes internos.

## Confirmado × hipótese

O detalhe, com a evidência de cada item, está em [docs/EDA.md](docs/EDA.md) (marcações [C], [H] e [?]).

**Confirmado nos dados**
- Usuário do pedido só existe em `carts`; usuário do CRM é recuperável 100% por `device_id`.
- Ledger e pedidos conciliam ao ponto, e só APROVADO e ESTORNADO debitam pontos.
- O Pix é sempre R$ 0,019/ponto; o operador soma pontos de todos os status.
- Nenhum ponto do programa novo expirou; os códigos 3 e 13 nunca aparecem.
- O CRM não tem grupo de controle; a adoção do Pix é igual entre expostos e não expostos.

**Regras inferidas e acurácia**
- **Regras pendentes de validação:** as regras de tratamento da silver foram inferidas a partir do README do case, da EDA e da experiência de desenvolvimento. As 10 regras (R01–R10) estão registradas em [catalog/gold.yml](catalog/gold.yml) com o status `pendente_validacao_negocio`, origem e impacto. Elas vão para a tabela `meta_regras_inferidas`, e o agente cita o id da regra quando a resposta depende dela.
- **Benchmark de acurácia** (`python -m pipeline.benchmark`), contra o relatório do operador, a única referência externa disponível:

| Métrica | Acurácia | Divergência |
|---|---|---|
| varejo_pct (±0,5 p.p.) | 9/9 meses | — |
| aereas_pct (±0,5 p.p.) | 8/9 | jun/26 (56,3 vs 55) |
| pix_pct (±0,5 p.p.) | 4/5 | jun/26 (30,4 vs 32) |
| pix_transacoes e pix_pontos (todos os status) | 5/5 exatos | — |
| pix_reais (aprovados) | 5/5 com erro < 1% | máximo de 0,72% |

A única divergência é junho, mês em que o relatório do operador usa um critério diferente (todos os status). As regras do pipeline reproduzem o relatório nos demais meses; o benchmark mede a consistência com o operador, não a verdade de negócio.

**Hipóteses**
- `event_ts` do CRM está em horário local.
- `product_value` representa o custo do programa (não o preço de venda).
- O lote de 12/01/2026 é atípico (carga ou ação com a base migrada).
- Resgate efetivado = status APROVADO.
- As metas usam o total de pontos resgatados, com o Pix no denominador (as variantes estão no gold).

## Perguntas ao negócio e aos donos dos sistemas

Veja as seções 5 e 6 de [docs/EDA.md](docs/EDA.md). As principais:
- Quanto o banco paga por ponto?
- Qual a definição contratual do denominador das metas e do que conta como varejo?
- Qual fórmula de breakage o diretor usou?
- O que foi o lote de 12/01/2026?
- Por que há expiração de saldo migrado com validade em 2028?
- Em que fuso está o CRM?
- Por que os pushes caíram em agosto?

## Limitações e próximos passos

- O deploy em serverless (ex.: Vercel) não suporta Streamlit. A entrega completa é o contêiner (Docker, Render, Cloud Run, Fly); para a Vercel há a versão simplificada descrita abaixo.
- O agente foi validado manualmente com `gemini-3.8-flash`: respostas concisas, sem dados inventados, com as proteções funcionando. O validador de SQL tem testes automatizados; a qualidade das respostas do LLM, não (depende do modelo).
- **Portabilidade para Vercel: implementada, testada localmente, sem deploy real.**
  - O Streamlit não roda em serverless. Por isso existe uma versão simplificada: [api/index.py](api/index.py), uma função Python que serve as tabelas gold agregadas (GET) e o agente (POST), com as mesmas guardas e trilha; e [public/index.html](public/index.html), uma página estática com as metas e o chat.
  - [vercel.json](vercel.json) roda o pipeline no build e exporta um SQLite **só com gold, dq e meta** (`python -m pipeline.export_gold`, 4,6 MB contra 195 MB do warehouse completo). Bronze e silver não saem do ambiente.
  - Para subir: importar o repositório na Vercel e definir `GEMINI_API_KEY`.
  - Testado localmente: o GET devolve as metas e bloqueia `gold_fct_resgate` (grão individual).
  - Não testado: o deploy real na Vercel e o POST do agente na Vercel. A trilha de auditoria vai para `/tmp`, que é efêmero; em produção deve ir para um log externo.
- **IA local (Ollama): implementada e não testada.** Ficou fora por priorização. O tempo foi para os pontos mais críticos, porque o Gemini, que é o provedor indicado no desafio, entregou o necessário de forma gratuita. O caminho `LLM_PROVIDER=ollama` existe no código, mas não foi exercitado.
- A imagem Docker foi construída e executada localmente; o build roda o pipeline, os guardrails e os testes.

## Tempo e uso de IA

- Tempo: ~2h, em uma sessão (19h49 até o último commit, antes das 22h). Inclui EDA, pipeline, testes, dashboard, agente, Docker, guardrails, revisão de segurança, documentação de governança e portabilidade para Vercel.
- IA: assistente de código em todas as etapas, com o registro detalhado em [AI_LOG.md](AI_LOG.md).
  - A IA rodou a exploração (SQL via DuckDB em scripts temporários), propôs a modelagem e escreveu o código.
  - Ao conferir os números da EDA contra o pipeline final, os testes e a revisão da própria sessão corrigiram "aéreas sem o lote" de 77,4% para 77,1% e "varejo sem Pix" de ~17% para 17–19%. Também explicitaram as duas definições de usuário Pix (aprovado = 2.140; aprovado ou estornado = 2.172).

## Dúvidas e esclarecimentos

Nenhum esclarecimento recebido; as dúvidas estão registradas como perguntas ao negócio.

---

# Enunciado do case

> Todos os dados, nomes e números deste case são fictícios e foram gerados para o processo seletivo.
> Versão dos dados: **v1**. O arquivo `MANIFESTO_v1.csv` lista os 9 CSVs com contagens de linhas e impressão digital (SHA-256).

## O contexto

O **Pontua+** é o programa de pontos dos cartões de crédito do Banco Aurora. Quem usa o cartão acumula pontos e troca por passagens aéreas, produtos de varejo ou transferências para programas parceiros. O programa é operado por uma empresa do grupo, que presta contas ao banco todo mês com um relatório (`relatorio_mensal_cliente.csv`).

Em **27/05/2026** o programa lançou o **Pontos no Pix**: o cliente troca pontos por dinheiro na conta, a R$ 0,019 por ponto. Cada 53 pontos equivael a aproximadamente R$1. O resgate nessa modalidade disparou.

O contrato com o banco tem duas metas sobre o total de pontos resgatados: trocas por passagens **aéreas devem ser pelo menos 50%** do volume de pontos trocados e **varejo pelo menos 20%**.   
  
Passagens aéreas custam mais caro ao programa do que o banco paga por ponto, sendo assim, mais desvantajoso para o programa (como empresa) e o varejo é onde o grupo tem parceiros próprios, (sendo mais vantajoso)

A diretoria vai decidir na semana que vem qual ação tomar para estimular ou coibir o resgate via Pix.  
  
Antes, quer entender o que aconteceu. E também se vale a pena estimular ou coibir o resgate tendo em vista as metas de aéreas e varejo e a própria saúde financeira do programa.  
Ela também ouviu duas afirmações e quer saber se são verdade:

- do time de CRM: "a comunicação de lançamento explica o sucesso do Pix";
- do relatório do operador: "Na verdade o Pix sai a cerca de R$ 0,016 por ponto, abaixo dos R$ 0,019 anunciados".
- De um diretor: “nosso breakage está em 40%! Nossa meta é não passar de 20%!"

## A descoberta faz parte do exercício

Não fornecemos um dicionário de dados. Explore os arquivos para identificar tipos, campos vazios, grãos, chaves, relacionamentos e regras relevantes para a análise. Documente esse entendimento no `README`, incluindo as evidências que sustentam suas escolhas.

Registre as hipóteses utilizadas e as perguntas que faria aos responsáveis pelos sistemas ou pelo negócio. Diferencie o que foi confirmado nos dados do que depende de validação adicional. Quando uma informação não puder ser estabelecida com os arquivos disponíveis, explique a limitação e o que precisaria para avançar. Hipóteses alternativas fundamentadas serão consideradas na avaliação.

## O que pedimos

Tempo de trabalho: **4 horas**. 

**O que pedimos**

1. O que aconteceu com os resgates depois do Pix e o que isso significa para as metas e para o programa.
2. Avalie as três afirmações.
3. Uma recomendação de uma página para a diretoria.
4. **Dashboard estratégico.** A diretoria vai acompanhar as principais métricas do programa por um dashboard. Monte o dashboard e a estrutura de dados por trás dele para responder às principais perguntas de negócio da diretoria. Os mesmos dados também serão consumidos por um agente de IA: desenhe uma estrutura que atenda aos dois (dashboard e agente) e justifique suas escolhas (camadas, grão, métricas, nomes, documentação, como o agente descobre o que cada campo significa).
5. **Opcional, se sobrar tempo:** desenvolva o agente que responde perguntas da diretoria sobre esses dados. Veja *Chave de LLM para o agente* abaixo.

**Regras da entrega**

- Os dados não vêm com dicionário. Entender os arquivos faz parte do exercício.
- Todos os números precisam sair de código executável (SQL e/ou Python, dbt opcional), com o grão de cada modelo declarado e **testes que garantam que os números estão certos.**
- No README, **separe o que foi confirmado nos dados do que é hipótese e liste o que você perguntaria ao negócio ou aos donos dos sistemas.**
- Tempo sugerido: 4 horas. Informe quanto tempo levou. Se não terminar, entregue o que rodou e diga como seguiria.
- Pode (DEVE) usar IA. Queremos ver como você usa e o que você confere.

## O que entregar

Quatro peças em formato zip ou em um git (cinco, se fizer o agente).

1. **Apresentação para a diretoria.** Mostra o que aconteceu, avalia as três afirmações e termina com a sua recomendação. Cada ponto da recomendação precisa trazer o número que o sustenta e dizer o que ainda falta saber. A apresentação será usada na devolutiva.
2. **Código e testes.** Todos os números da apresentação saem daqui, com SQL e/ou Python (dbt é opcional).
3. **README.** Precisa permitir que um avaliador reconstrua tudo a partir dos CSVs, sem editar nada à mão. Nele também ficam o que você entendeu dos dados, como modelou, as hipóteses que assumiu, o que perguntaria ao negócio ou aos donos dos sistemas e um registro breve do uso de IA (o que você pediu e o que conferiu ou corrigiu, subagentes e/ou skills que utilizou).
4. **Dashboard e estrutura de dados.** O dashboard (link acessível aos avaliadores, arquivo ou instruções para subir localmente), os modelos que o alimentam e a justificativa da estrutura para dashboard e agente. Ferramenta livre.
5. **Agente (opcional).** Código, instruções para rodar e exemplos de perguntas e respostas, incluindo pelo menos uma pergunta que ele deveria se recusar a responder ou responder com ressalva.

## Chave de LLM para o agente

Você não precisa gastar dinheiro com o agente.

- Durante o desenvolvimento, use a chave e o provedor que preferir. Sugestão: a camada gratuita da API do Gemini, com chave criada em https://aistudio.google.com/apikey usando qualquer conta Google. Ela basta para o volume deste case. Outros provedores com cota gratuita ou um modelo local (Ollama ou similar) também servem.
- **Na avaliação, vamos publicar o seu projeto em produção (por exemplo, no Vercel) e rodar o agente com a nossa chave do Gemini.** Por isso:
  - o agente precisa funcionar com o Gemini, mesmo que você tenha desenvolvido com outro provedor;
  - a chave deve ser lida de variável de ambiente, e o nome dela deve estar documentado no README;
  - o README deve trazer um único comando ou passo a passo curto para subir o dashboard e o agente.
- Guarde a chave em `.env` (já está no `.gitignore`). **Nunca faça commit de chave.**

## Como enviar

Envie um arquivo `.zip` com a solução ou um link para um repositório acessível aos avaliadores (@brain-yurikaminski, @brain-leonardo-andrade)pelo mesmo canal em que recebeu o case. O prazo de entrega é o alinhado entre vc e o recrutador. Inclua as respostas, o código, os testes e o `README`. Se a execução depender dos CSVs fornecidos, documente onde colocá-los.

Registre as dúvidas e eventuais esclarecimentos recebidos no `README`.

## Como vamos avaliar

Vamos avaliar análise e engenharia com o mesmo peso. Importa a qualidade do raciocínio, das evidências e do julgamento, não a quantidade de coisas entregues. Escolhas diferentes de ferramenta, arquitetura ou interpretação são bem-vindas quando fundamentadas. Na devolutiva, você vai defender suas escolhas, inclusive as que fez com ajuda de IA.

## Os dados (`dados/`)

Nove arquivos CSV separados por vírgula, com cabeçalho e codificação UTF-8. Os valores monetários estão em reais (R$). Datas e horas mantêm os formatos dos sistemas de origem; identifique e documente como você as interpreta nas análises.


| Arquivo                        | Finalidade geral                                          | Colunas                                                                                                                                                                              |
| ------------------------------ | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `orders.csv`                   | Registros do sistema de pedidos                           | order_id, cart_id, user_id, created_at, status, status_updated_at                                                                                                                    |
| `order_items.csv`              | Produtos e valores associados aos pedidos                 | order_item_id, order_id, created_at, status, product_type, supplier_name, supplier_responsible, category_macro, paid_points, paid_currency, product_value, refunded_points, quantity |
| `carts.csv`                    | Carrinhos e canais de compra                              | cart_id, user_id, channel                                                                                                                                                            |
| `points_ledger.csv`            | Movimentações do saldo de pontos                          | movement_id, user_id, account_id, operation_code, points, movement_at, valid_until                                                                                                   |
| `dim_operation.csv`            | Cadastro de tipos de movimentação                         | operation_code, operation_name, direction                                                                                                                                            |
| `cards.csv`                    | Cadastros relacionados aos cartões                        | account_id, user_id, card_class, card_flag, created_at, is_most_recent                                                                                                               |
| `redeemed_points.csv`          | Registros de movimentação de pontos associados às compras | order_item_id, account_id, movement_type, points                                                                                                                                     |
| `crm_events.csv`               | Exportação da ferramenta de engajamento                   | event_ts, user_id, device_id, event_name, campaign_type, campaign_id, control_group, event_properties (JSON)                                                                         |
| `relatorio_mensal_cliente.csv` | Relatório do operador ao banco                            | mes, aereas_pct, varejo_pct, pix_pct, pix_reais, pix_pontos, pix_transacoes, emails_enviados, push_enviados                                                                          |


O que o time de dados sabe e te conta:

- O Pontua+ substituiu um programa anterior; os saldos antigos foram migrados para o sistema novo.
- Os níveis de cartão, do mais simples ao mais alto: Essencial, Gold, Platinum, Platinum Elo, Infinite, Black.
- A ferramenta de CRM e o sistema de pedidos são sistemas diferentes e não compartilham configuração.
- Os dados foram extraídos em 01/10/2026.


## Registro do processo (obrigatório)

**Commits e pushes.** Trabalhe na branch `entrega` e faça push ao fim de cada sessão de trabalho. O GitHub registra a hora de cada push no servidor. Ao terminar, abra um Pull Request de `entrega` para `main`: a abertura do PR marca a entrega.

**Uso de IA em `AI_LOG.md`.**
- Se usar um agente que lê `AGENTS.md` ou `CLAUDE.md` (Claude Code, Cursor, Codex, Copilot e similares), ele registra cada sessão automaticamente. Confira o que foi escrito.
- Se usar IA em chat (ChatGPT, Claude.ai, Gemini etc.), ao fim de cada conversa cole o prompt abaixo e acrescente a resposta ao final de `AI_LOG.md`:

```
Resuma esta conversa para um registro de uso de IA, em português, neste formato:
### <data e hora> · <ferramenta e modelo>
- **Pedido:** o que eu pedi, em 1 a 3 linhas.
- **O que a IA fez ou sugeriu:** resumo factual.
- **O que eu conferi, corrigi ou rejeitei:** inclusive erros seus que eu apontei.
- **Arquivos criados ou alterados:** caminhos, se houver.
Seja factual. Não invente nada que não esteja na conversa.
```

Links de compartilhamento ou exportações das conversas (por exemplo, `/export` no Claude Code) são bem-vindos em `ai-log/`.
