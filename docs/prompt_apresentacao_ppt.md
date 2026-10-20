# Prompt para gerar a apresentação (PPT) via IA

Copie o bloco abaixo numa ferramenta de IA que gere slides. Todos os números vêm de `python -m pipeline.eda` e `python -m pipeline.benchmark` e estão cobertos por testes; o conteúdo-base é [apresentacao.md](apresentacao.md).

---

```
Crie uma apresentação executiva em PowerPoint (16:9), em português do Brasil, para a diretoria de um programa
de pontos de cartão de crédito fictício chamado "Pontua+". A apresentação será usada numa reunião de decisão
e numa devolutiva técnica.

REGRAS OBRIGATÓRIAS
- Use SOMENTE os números abaixo. Não arredonde de forma diferente, não invente, não estime nada novo.
- Não cite nomes de empresas reais, consultorias, clientes ou pessoas. Os nomes do programa e dos parceiros são fictícios.
- Toda página com valor financeiro leva no rodapé: "Valores gerenciais, não contábeis · dados de 01/10/2025 a 30/09/2026".
- Cada recomendação traz o número que a sustenta e o que ainda falta saber.
- Estilo: limpo, corporativo, muito espaço em branco, no máximo 5 bullets por slide e 1 gráfico por slide.
  Paleta neutra (azul-escuro, cinza, um destaque em laranja para alertas). Títulos que afirmam a conclusão
  (ex.: "O Pix somou volume, não roubou volume"), não títulos genéricos.
- Inclua notas do apresentador em cada slide (2 a 4 frases explicando o raciocínio).

ROTEIRO (11 slides)

1. Capa
   "Pontua+ · Pontos no Pix: o que aconteceu, o que é verdade e o que fazer"
   Subtítulo: "Dados de 01/10/2025 a 30/09/2026 · extração em 01/10/2026"

2. Resumo executivo (3 mensagens)
   - O Pix somou volume e ativou clientes parados, mas é a modalidade mais cara por ponto.
   - Aéreas cumpre a meta; varejo descumpre desde junho.
   - Das três afirmações ouvidas pela diretoria, nenhuma se sustenta como foi dita.
   Recomendação em uma linha: recalibrar o Pix (taxa ou teto), não estimular nem encerrar.

3. "O Pix somou volume, não roubou volume"
   - Lançado em 27/05/2026; taxa de R$ 0,019 por ponto em 100% das 3.292 transações.
   - Pontos resgatados (aprovados) por mês: fev 15,9 M · mar 19,1 M · abr 18,8 M · mai 21,5 M ·
     jun 30,4 M · jul 30,5 M · ago 31,4 M · set 33,5 M.
   - Aéreas estáveis em valor absoluto (jun 17,1 M · set 19,8 M pontos).
   - 2.140 usuários usaram Pix; 1.195 (56%) nunca tinham resgatado antes.
   - Cancelamento + inválido: Pix 13,0% vs 6,9% nas demais modalidades.
   Gráfico: barras empilhadas por mês e modalidade (aéreas, varejo, Pix).

4. "Aéreas cumpre a meta; varejo está abaixo desde junho"
   Tabela de participação nos pontos resgatados:
   | Mês | Aéreas | Varejo | Pix |
   | abr/26 | 80,73% | 19,27% | 0% |
   | jun/26 | 56,31% | 13,33% | 30,36% |
   | jul/26 | 57,91% | 12,75% | 29,34% |
   | ago/26 | 57,99% | 12,13% | 29,88% |
   | set/26 | 59,02% | 12,95% | 28,03% |
   Metas: aéreas >= 50%; varejo >= 20%.
   - Varejo já estava no limite antes do Pix (abr = 19,27%).
   - Sem o Pix no denominador: aéreas 81–83%, varejo 17–19% (ainda abaixo de 20%).
   - Jan/26 mostra aéreas em 96,74% por causa de um lote atípico em 12/01 (sem o lote: 77,1%).
   Gráfico: linhas de aéreas e varejo com as linhas de meta em 50% e 20%.
   A confirmar: o Pix entra no denominador? Transferências para parceiros contam como varejo?

5. "O Pix é o ponto mais caro para o programa"
   Custo por ponto (líquido do copagamento do cliente):
   | Pix | R$ 0,0190 | Aéreas | R$ 0,0150 | Varejo (produtos) | R$ 0,0139 | Transferência para parceiros | R$ 0,0125 |
   - Custo coberto por pontos no 3º tri/26: R$ 1.526.730,86 (jul R$ 489.078,76 · ago R$ 502.879,91 · set R$ 534.772,19).
   - Passivo de pontos em aberto: 377,7 milhões de pontos.
   A confirmar: quanto o banco paga por ponto (receita) — sem isso não há margem.
   Gráfico: barras horizontais de custo por ponto.

6. Afirmação 1 — CRM: "a comunicação de lançamento explica o sucesso do Pix" → NÃO SE SUSTENTA
   | Grupo | Adoção do Pix |
   | Não recebeu o e-mail | 18,0% |
   | Recebeu, não abriu | 18,3% |
   | Recebeu e abriu | 17,8% |
   - A campanha começou em 28/05 às 13h, um dia depois do lançamento; 20 resgates Pix vieram antes.
   - 489 usuários usaram Pix sem nunca receber a campanha.
   - Grupos comparáveis: ~32% já resgatavam antes, em todos eles.
   Ressalva: não há grupo de controle formal; evidência observacional.

7. Afirmação 2 — Operador: "o Pix sai a ~R$ 0,016 por ponto" → FALSA
   - Taxa real: R$ 0,019 em todas as 3.292 transações.
   - O relatório divide o R$ dos Pix aprovados pelos pontos de TODOS os status (inclusive cancelados).
   - Jun/26: 10.709.419 pontos reportados = todos os status; aprovados = 9.215.135.
   - Benchmark: nossos números reproduzem o relatório em todos os meses, exceto junho, quando o operador muda de critério.

8. Afirmação 3 — Diretor: "breakage em 40%" → NÃO REPRODUZÍVEL E AINDA NÃO MENSURÁVEL
   - Nenhum ponto do programa novo expirou; o primeiro vence em 25/09/2027.
   - Expirado sobre migrado (programa anterior): 19,78%.
   - Expirado / resgatado em fev–mai/26 = 37,11% — provável origem do "40%", mas não é breakage.
   - Inconsistência: o saldo migrado vale até 31/03/2028, mas expira desde jan/26.

9. Recomendação (tabela com 3 colunas: Ação | Número que sustenta | O que falta saber)
   1. Recalibrar o Pix: taxa <= R$ 0,015 ou teto mensal por cliente | Pix R$ 0,019 vs aéreas R$ 0,015 | preço pago pelo banco por ponto
   2. Manter o Pix como ativação | 56% dos usuários do Pix eram inativos | se passaram a usar mais o cartão
   3. Plano comercial de varejo | varejo 12–13% vs meta de 20% | definição contratual das metas
   4. Corrigir o relatório do operador | R$ 0,016 é erro de cálculo | regra oficial de status
   5. Grupo de controle nas próximas campanhas | adoção igual com e sem e-mail | —
   6. Redefinir a métrica de breakage | 40% não se reproduz | fórmula usada pelo diretor
   7. Auditar o lote de 12/01/2026 | 1.520 resgates de aéreas em 24 h (76 M pontos) | carga do programa anterior ou ação comercial?

10. Confiabilidade dos números
   - Pipeline reprodutível (CSV → bronze → silver → gold), 86 testes automatizados, ledger e pedidos conciliam ao ponto (323.423.650 pontos).
   - 48 guardrails de qualidade bloqueiam cargas quebradas e alertam desvios.
   - 10 regras de tratamento inferidas, pendentes de validação com o negócio.
   - Dashboard e agente de IA com trilha de auditoria e sem exposição de dados individuais.

11. Próximos passos e perguntas ao negócio
   - Quanto o banco paga por ponto?
   - Definição contratual do denominador das metas e do que conta como varejo.
   - Fórmula do breakage usada pelo diretor.
   - O que foi o lote de 12/01/2026?
   - Validar as 10 regras inferidas (R01–R10).
```
