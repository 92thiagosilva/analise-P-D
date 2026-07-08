import os
import io
import json
import sqlite3
import uuid
import shutil
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from flask import Flask, request, jsonify, render_template, send_file, abort
from dotenv import load_dotenv

load_dotenv()  # lê ANTHROPIC_API_KEY de um arquivo .env local, se existir

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"
DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "analyses.db"


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS team_reports (
            id TEXT PRIMARY KEY,
            manufacturer_id TEXT NOT NULL,
            team TEXT NOT NULL,
            files TEXT DEFAULT '[]',
            analysis TEXT DEFAULT '{}',
            created_at TEXT DEFAULT '',
            FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id) ON DELETE CASCADE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS manufacturers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            country TEXT DEFAULT '',
            founded TEXT DEFAULT '',
            analysis_date TEXT DEFAULT '',
            product_types TEXT DEFAULT '[]',
            score_qualidade REAL DEFAULT 0,
            score_solidez REAL DEFAULT 0,
            score_pos_venda REAL DEFAULT 0,
            score_fit REAL DEFAULT 0,
            score_margem REAL DEFAULT 0,
            score_certificacoes REAL DEFAULT 0,
            score_final REAL DEFAULT 0,
            decision TEXT DEFAULT '',
            summary TEXT DEFAULT '',
            red_flags TEXT DEFAULT '[]',
            positives TEXT DEFAULT '[]',
            products TEXT DEFAULT '[]',
            recommendation TEXT DEFAULT '',
            files TEXT DEFAULT '[]',
            raw_analysis TEXT DEFAULT '{}'
        )
    """)
    # Migração: adiciona colunas de ajuste dos times se não existirem
    existing = {r[1] for r in conn.execute("PRAGMA table_info(manufacturers)").fetchall()}
    if "score_ai" not in existing:
        conn.execute("ALTER TABLE manufacturers ADD COLUMN score_ai REAL DEFAULT 0")
        # Inicializa score_ai com o score_final atual (registros existentes)
        conn.execute("UPDATE manufacturers SET score_ai = score_final WHERE score_ai = 0")
    if "score_team_adj" not in existing:
        conn.execute("ALTER TABLE manufacturers ADD COLUMN score_team_adj REAL DEFAULT 0")
    conn.commit()
    conn.close()


init_db()

ANALYSIS_SYSTEM = """Você é o analista estratégico de portfólio da Fotus Distribuidora Solar.
Sua postura é de sparring intelectual rigoroso: o padrão é "prove que é bom", nunca "parece bom".

REGRAS DE OURO — siga sem exceção:
1. Você está analisando SOMENTE o documento enviado, SEM acesso a fontes externas. Por isso, toda afirmação do fabricante que não seja verificável no próprio documento deve ser tratada como NÃO CONFIRMADA e penalizar o score.
2. Informação ausente = pior cenário. Se o documento não menciona presença no Brasil, assuma que não há. Se não menciona INMETRO, assuma que não tem. Nunca beneficie a dúvida.
3. Marketing sem dados é red flag. Frases como "líder de mercado", "melhor qualidade", "suporte dedicado" sem números, certificados ou evidências concretas REDUZEM o score.
4. Seja conservador nos scores. Um fabricante precisa apresentar evidências sólidas para obter score acima de 7. Score 8+ exige evidência robusta dentro do documento.
5. Retorne SOMENTE JSON válido, sem markdown, sem texto extra."""

ANALYSIS_PROMPT = """Analise o(s) documento(s) do fabricante solar com máximo rigor e ceticismo. Retorne APENAS este JSON (sem markdown):

{
  "manufacturer": {
    "name": "Nome completo do fabricante",
    "commercial_name": "Nome comercial (igual ao name se não houver diferença)",
    "country": "País de origem",
    "founded": "Ano de fundação ou 'Não informado'",
    "size": "Descrição do porte baseada APENAS em dados do documento",
    "revenue": "Faturamento SE mencionado no documento, senão 'Não informado no documento'",
    "capacity": "Capacidade produtiva SE mencionada, senão 'Não informado no documento'",
    "employees": "Número de funcionários SE mencionado, senão 'Não informado no documento'",
    "brazil_presence": "Descreva SOMENTE o que está explícito no documento. Se não mencionar Brasil: 'Sem menção a presença no Brasil'"
  },
  "product_types": ["lista com TODOS os tipos encontrados no documento — veja categorias válidas abaixo"],
  "products": [
    {
      "category": "use exatamente uma das categorias válidas listadas abaixo",
      "technology": "tecnologia principal (TOPCon/HJT/PERC/LFP/NMC/híbrido/etc)",
      "segment": "Residencial / C&I / Utility / Todos",
      "models": [
        {
          "name": "Nome do modelo",
          "power_kw": 0.595,
          "efficiency_pct": 22.5,
          "warranty_product_years": 15,
          "warranty_performance_years": 30,
          "degradation_per_year_pct": 0.4,
          "certifications": ["somente certificações VISÍVEIS no documento"],
          "price_range": "Somente se mencionado no documento",
          "highlights": "Somente destaques com dados concretos no documento"
        }
      ],
      "score": 6.0,
      "recommendation": "✅ Recomendar / ⚠️ Condicional / ❌ Não recomendar",
      "notes": "Observações críticas sobre a linha"
    }
  ],
  "scores": {
    "qualidade_tecnologia": 6.0,
    "solidez_fabricante": 5.0,
    "pos_venda_brasil": 3.0,
    "fit_portfolio": 6.0,
    "potencial_margem": 5.0,
    "certificacoes": 5.0,
    "score_final": 4.95,
    "penalidade_pos_venda": 0.0
  },
  "decision": "AGUARDAR",
  "decision_label": "🔄 AGUARDAR",
  "confidence": "Média — análise baseada somente no documento, sem validação externa",
  "summary": "Resumo de 5-8 linhas RIGOROSO: mencione o que o documento NÃO prova, o que é apenas marketing, e o que genuinamente impressiona. Antecipe as perguntas: 'Se der problema em campo, quem paga?' e 'Por que esse fabricante e não o que já temos?'",
  "red_flags": [
    {"severity": "CRÍTICO", "description": "Descreva problemas graves com evidência do documento"},
    {"severity": "ATENÇÃO", "description": "Descreva pontos de atenção"},
    {"severity": "MONITORAR", "description": "Descreva o que monitorar"}
  ],
  "positives": [
    "Somente pontos positivos com evidência concreta no documento",
    "Nunca incluir afirmações do fabricante sem dado verificável"
  ],
  "recommendation_text": "INICIATIVA: [Nome] — [Categoria]\\nDecisão: [GO/GO CONDICIONAL/AGUARDAR/NO-GO]\\nScore: X.X/10\\n\\nFundamentação:\\n1. [Ponto mais forte A FAVOR — com evidência do documento]\\n2. [Ponto mais forte CONTRA — o que o documento não prova]\\n3. [Fator decisivo da recomendação]\\n\\nPior cenário se entrarmos: [descrever risco máximo em R$]\\nPróximo passo: [ação concreta + prazo]\\nDecisão requerida de: [Thiago / Breno / Diretoria]",
  "pending_info": [
    {
      "info": "O que o documento não respondeu e é crítico para a decisão",
      "impact": "Impacto no score se a resposta for negativa",
      "how_to_get": "Como obter esta informação"
    }
  ],
  "financial": {
    "estimated_monthly_volume": "X un/mês",
    "estimated_avg_price_brl": "R$ X",
    "estimated_annual_revenue_brl": "R$ X/ano",
    "estimated_margin_pct": "X% — baseado em [premissa explícita]",
    "moq": "Somente se mencionado no documento",
    "payback_months": "X meses",
    "working_capital_needed": "R$ X"
  }
}

═══════════════════════════════════════════════════════════
IDENTIFICAÇÃO DE PRODUTOS — REGRAS OBRIGATÓRIAS
═══════════════════════════════════════════════════════════

CATEGORIAS VÁLIDAS — use exatamente estes nomes:
  "Módulos FV"              → painéis solares fotovoltaicos de qualquer tecnologia
  "Inversores On-Grid"      → inversores string on-grid sem bateria integrada, ligados à rede elétrica
  "Inversores Off-Grid"     → inversores para sistemas isolados, sem conexão à rede elétrica
  "Inversores Híbridos"     → inversores com entrada de bateria integrada / all-in-one / multigrid
  "Microinversores"         → microinversores instalados por módulo (module-level power electronics)
  "BESS Residencial"        → sistemas de armazenamento de energia residencial (até ~30kWh)
  "BESS C&I"                → sistemas de armazenamento comercial/industrial (>30kWh)
  "Carregadores EV AC"      → carregadores veiculares modo 3, wallbox AC
  "Carregadores EV DC"      → carregadores veiculares modo 4, fast charging DC
  "EV + BESS"               → produto integrado que combina carregador EV com armazenamento de bateria
  "Outro"                   → qualquer produto que não se encaixe acima (descreva na tecnologia)

INSTRUÇÕES CRÍTICAS PARA PRODUTOS:
1. PERCORRA TODO O DOCUMENTO em busca de linhas de produto. Não pare no primeiro item encontrado.
2. Se o fabricante tiver 5 linhas diferentes, crie 5 objetos distintos no array "products".
3. Inversor híbrido NÃO é o mesmo que "Inversores String" nem "BESS" — use "Inversores Híbridos".
4. Se um produto combina carregador EV com bateria integrada, use "EV + BESS", não "Carregadores EV AC/DC".
5. O array "product_types" deve ter TODOS os tipos encontrados, sem duplicatas.
6. Nunca agrupe produtos diferentes em uma única categoria por conveniência.

═══════════════════════════════════════════════════════════
CRITÉRIOS DE PONTUAÇÃO — RÉGUA RIGOROSA (0-10 por dimensão)
═══════════════════════════════════════════════════════════

PRINCÍPIO GERAL: na ausência de evidência, pontue para baixo.
Um fabricante desconhecido sem dados verificáveis no documento NÃO pode receber score alto.

──────────────────────────────────────────────────────────
QUALIDADE/TECNOLOGIA (peso 25%)
──────────────────────────────────────────────────────────
9-10: PVEL Top Performers mencionado com evidência; eficiência celular ≥23%(TOPCon) ou ≥24%(HJT); degradação ≤0.4%/ano; histórico de confiabilidade comprovado
7-8: Certificações IEC completas VISÍVEIS no documento; eficiência compatível com mercado 2025-2026; garantia ≥25 anos com termos claros
5-6: Certificações básicas presentes; eficiência dentro do aceitável; garantia 10-25 anos; poucos dados de confiabilidade
3-4: Certificações não visíveis ou apenas mencionadas sem número do certificado; eficiência abaixo da média; garantia ≤10 anos ou com restrições
0-2: Nenhuma certificação comprovada no documento; dados técnicos implausíveis ou contraditórios; qualquer menção a falhas em campo
ATENÇÃO: eficiência declarada acima de 24% para módulos sem prova de tecnologia HJT é red flag de exagero.

──────────────────────────────────────────────────────────
SOLIDEZ DO FABRICANTE (peso 20%)
──────────────────────────────────────────────────────────
9-10: Top-10 global comprovado (JinkoSolar/LONGi/Trina/Canadian/JA Solar/Risen/BYD); receita >USD 3B documentada; capacidade >30GW/ano; >10 anos no mercado
7-8: Fabricante estabelecido; receita USD 500M-3B documentada; capacidade 5-30GW/ano; 5-10 anos no mercado com histórico verificável no documento
5-6: Porte médio com alguns dados financeiros; capacidade 1-5GW/ano; 3-5 anos; dados parcialmente verificáveis
3-4: Fabricante pequeno; <3 anos no mercado ou mudança recente de controle; pouca informação pública no documento
0-2: Sem dados financeiros ou de capacidade; endereço ou histórico não verificável; suspeita de rebranding
ATENÇÃO: se o documento não menciona faturamento, capacidade ou anos no mercado, presuma porte pequeno (score ≤5).

──────────────────────────────────────────────────────────
PÓS-VENDA BRASIL (peso 20%) — DIMENSÃO CRÍTICA
──────────────────────────────────────────────────────────
9-10: Escritório próprio no Brasil com endereço; equipe técnica local certificada; RMA ≤15 dias documentado; estoque de peças no Brasil
7-8: Representante técnico DEDICADO no Brasil com nome/contato; processo RMA documentado 15-30 dias
5-6: Representante comercial (não técnico) no Brasil; RMA via importação 30-60 dias; suporte remoto apenas
3-4: Sem representação local documentada no Brasil; suporte apenas em inglês/chinês; processo RMA vago
0-2: Nenhuma menção a suporte no Brasil; garantia de execução duvidosa; zero canal de comunicação local definido
REGRA DE PENALIDADE OBRIGATÓRIA: se pos_venda_brasil ≤ 5.0, subtrair 1.0 ponto do score_final. Registre como "penalidade_pos_venda": -1.0 no JSON.
ATENÇÃO: se o documento não menciona nada sobre Brasil, o score desta dimensão é automaticamente ≤3.

──────────────────────────────────────────────────────────
FIT COM PORTFÓLIO FOTUS (peso 15%)
──────────────────────────────────────────────────────────
Gaps prioritários Fotus 2026: BESS residencial/C&I, Carregadores EV com INMETRO, Inversores com melhor pós-venda que atual, Módulos TOPCon Tier-1 com margem melhor
9-10: Preenche gap estratégico claro; não canibaliza nenhum fornecedor atual forte
7-8: Complementa portfólio com diferencial claro; sobreposição gerenciável
5-6: Sobreposição significativa com portfólio atual; justificável como alternativa de negociação
3-4: Alta canibalização de fornecedor atual sem vantagem técnica ou comercial clara
0-2: Duplicação pura; produto fora do escopo da Fotus; nicho sem demanda real dos integradores

──────────────────────────────────────────────────────────
POTENCIAL DE MARGEM (peso 10%)
──────────────────────────────────────────────────────────
Targets mínimos Fotus: Módulos 12%, Inversores string 15%, BESS 18%, Carregadores EV 18%
Targets ideais Fotus: Módulos 18%, Inversores 22%, BESS 30%, Carregadores EV 32%
9-10: Margem estimada acima do target ideal + exclusividade possível + política de preço favorável documentada
7-8: Margem entre target mínimo e ideal; política de preço estável
5-6: Margem no limite do target mínimo; canal concorrido
3-4: Margem abaixo do target mínimo; fabricante comprime distribuidor
0-2: Margem inviável; produto já comoditizado sem diferencial
ATENÇÃO: sem dados de preço no documento, pontue conservadoramente (máximo 5).

──────────────────────────────────────────────────────────
CERTIFICAÇÕES E COMPLIANCE (peso 10%)
──────────────────────────────────────────────────────────
Obrigatórias por categoria:
  Módulos FV: IEC 61215 + IEC 61730 + INMETRO (portaria 004)
  Inversores on-grid: IEC 62116 + IEC 61683 + INMETRO (portaria 357)
  BESS: IEC 62619 + UN 38.3 + INMETRO
  Carregadores EV AC: IEC 61851-1 + INMETRO (portaria 563)
9-10: Todas obrigatórias VISÍVEIS no documento com número de certificado + INMETRO válido
7-8: Todas obrigatórias mencionadas + INMETRO em processo com prazo documentado
5-6: IEC internacionais presentes sem INMETRO; ou INMETRO declarado sem prazo
3-4: Certificações parciais; INMETRO ausente sem qualquer plano mencionado
0-2: Ausência de certificações IEC básicas para produto que requer conexão à rede elétrica

══════════════════════════════════════════════════════════
CÁLCULO DO SCORE FINAL — OBRIGATÓRIO
══════════════════════════════════════════════════════════
score_base = (qualidade×0.25)+(solidez×0.20)+(pos_venda×0.20)+(fit×0.15)+(margem×0.10)+(certificacoes×0.10)
penalidade_pos_venda = -1.0 SE pos_venda_brasil ≤ 5.0, SENÃO 0.0
score_final = score_base + penalidade_pos_venda

DECISÃO baseada no score_final:
≥7.5 → "GO"  |  6.0–7.4 → "GO CONDICIONAL"  |  4.0–5.9 → "AGUARDAR"  |  <4.0 → "NO-GO"

VETO AUTOMÁTICO → "NO-GO" independente do score se qualquer condição:
- pos_venda_brasil ≤ 3.0 sem plano concreto documentado de estruturação no Brasil
- Evidência de fraude, contrafação ou irregularidade fiscal
- Fabricante em falência ou liquidação
- Ausência total de certificação IEC para produto que conecta à rede elétrica
- solidez_fabricante ≤ 2.0

PERGUNTAS QUE O RELATÓRIO DEVE RESPONDER (inclua no summary e recommendation_text):
- "Se esse produto der problema em campo, quem paga o custo de pós-venda?"
- "O fabricante ainda vai existir daqui a 5 anos?"
- "Por que esse fabricante e não o que já temos no portfólio?"
- "Qual o pior cenário financeiro se entrarmos com essa marca?"
"""


TEAM_SYSTEMS = {
    "produtos": (
        "Você é o analista do time de Produtos da Fotus Distribuidora Solar. "
        "Avalia laudos, relatórios e testes físicos de produtos de fabricantes. "
        "Seja técnico, objetivo e aponte divergências entre o declarado e o medido. "
        "Retorne SOMENTE JSON válido, sem markdown."
    ),
    "pricing": (
        "Você é o analista do time de Pricing da Fotus Distribuidora Solar. "
        "Avalia preços, margens, competitividade e potencial comercial de fabricantes. "
        "Ancore toda análise em números concretos (R$, %, payback). "
        "Retorne SOMENTE JSON válido, sem markdown."
    ),
    "supply": (
        "Você é o analista do time de Supply Chain da Fotus Distribuidora Solar. "
        "Avalia cadeia de fornecimento, lead times, MOQ, riscos logísticos e confiabilidade. "
        "Seja prático e aponte riscos operacionais concretos. "
        "Retorne SOMENTE JSON válido, sem markdown."
    ),
}

TEAM_PROMPTS = {
    "produtos": """Analise o(s) relatório(s) de teste/produto do fabricante e retorne este JSON exato:

{
  "summary": "Resumo técnico da análise de 4-6 linhas",
  "tests_conducted": [
    {"test": "Nome do teste", "result": "Aprovado/Reprovado/Parcial", "notes": "Observação"}
  ],
  "spec_compliance": "Total / Parcial / Não conforme",
  "divergences": [
    "Divergência entre especificação declarada e resultado medido"
  ],
  "highlights": [
    "Ponto técnico positivo verificado"
  ],
  "risk_level": "Baixo / Médio / Alto",
  "recommendation": "Aprovado / Aprovado com ressalvas / Reprovado",
  "conditions": [
    "Condição para aprovação (se ressalvas)"
  ],
  "notes": "Observações adicionais do time de produtos"
}""",

    "pricing": """Analise o(s) relatório(s) de pricing do fabricante e retorne este JSON exato:

{
  "summary": "Resumo da análise de pricing em 4-6 linhas",
  "cost_price": "Preço de custo identificado (R$ X ou USD X/W)",
  "suggested_sale_price": "Preço de venda sugerido pela Fotus",
  "market_reference_price": "Preço de referência de mercado",
  "estimated_margin_pct": "Margem bruta estimada em %",
  "margin_assessment": "Acima do target / Dentro do target / Abaixo do target",
  "target_margin": "Target mínimo Fotus para esta categoria",
  "moq_financial_impact": "Impacto financeiro do MOQ no capital de giro",
  "competitive_positioning": "Como este produto se posiciona vs. concorrentes no canal",
  "pricing_risks": [
    "Risco de pricing identificado"
  ],
  "opportunities": [
    "Oportunidade comercial identificada"
  ],
  "recommendation": "GO / GO CONDICIONAL / NO-GO",
  "recommendation_rationale": "Justificativa da recomendação em 2-3 linhas",
  "notes": "Observações adicionais do time de pricing"
}""",

    "supply": """Analise o(s) relatório(s) de supply chain do fabricante e retorne este JSON exato:

{
  "summary": "Resumo da análise de supply em 4-6 linhas",
  "lead_time_days": "Prazo de entrega em dias (porto a porto ou DDP)",
  "moq": "Quantidade/valor mínimo de pedido",
  "stock_availability": "Disponível imediato / Sob encomenda / Limitado / Indisponível",
  "delivery_reliability": "Alta / Média / Baixa — baseado no relatório",
  "incoterm": "Incoterm praticado pelo fabricante (FOB/CIF/DDP/etc)",
  "logistics_risks": [
    "Risco logístico identificado"
  ],
  "supply_strengths": [
    "Ponto forte da cadeia de fornecimento"
  ],
  "supplier_reliability": "Alta / Média / Baixa",
  "after_sales_supply": "Como funciona o fornecimento de peças de reposição",
  "recommended_safety_stock_days": "Estoque de segurança recomendado em dias",
  "recommendation": "GO / GO CONDICIONAL / NO-GO",
  "recommendation_rationale": "Justificativa da recomendação em 2-3 linhas",
  "notes": "Observações adicionais do time de supply"
}""",
}


def calculate_team_adjustment(team_reports_dict: dict) -> float:
    """
    Calcula o ajuste de score com base nos relatórios dos times internos.
    Cada time contribui de -0.5 a +0.5. Total: -1.5 a +1.5.

    Time de Produtos (±0.5):
      Aprovado + Risco Baixo  → +0.5
      Aprovado + Risco Médio  → +0.2
      Aprovado c/ ressalvas   → 0.0  (Risco Alto → -0.2)
      Reprovado               → -0.5

    Time de Pricing (±0.5):
      GO + Acima do target    → +0.5
      GO + Dentro do target   → +0.3
      GO + sem info margem    → +0.1
      GO CONDICIONAL          → 0.0  (Abaixo do target → -0.1)
      NO-GO                   → -0.5

    Time de Supply (±0.5):
      GO + Alta confiab.      → +0.5
      GO + Média confiab.     → +0.3
      GO + sem info           → +0.1
      GO CONDICIONAL          → 0.0  (Baixa confiab. → -0.1)
      NO-GO                   → -0.5
    """
    adj = 0.0

    # ── Produtos ──
    prod = (team_reports_dict.get("produtos") or {}).get("analysis") or {}
    if prod:
        rec  = (prod.get("recommendation") or "").lower()
        risk = (prod.get("risk_level") or "").lower()
        if "reprovado" in rec:
            adj -= 0.5
        elif "ressalva" in rec:
            adj += (-0.2 if "alto" in risk else 0.0)
        elif "aprovado" in rec:
            if "baixo" in risk:
                adj += 0.5
            elif "médio" in risk or "medio" in risk:
                adj += 0.2
            else:
                adj += 0.1

    # ── Pricing ──
    pric = (team_reports_dict.get("pricing") or {}).get("analysis") or {}
    if pric:
        rec    = (pric.get("recommendation") or "").upper()
        margin = (pric.get("margin_assessment") or "").lower()
        if "NO-GO" in rec:
            adj -= 0.5
        elif "CONDICIONAL" in rec:
            adj += (-0.1 if "abaixo" in margin else 0.0)
        elif rec == "GO":
            if "acima" in margin:
                adj += 0.5
            elif "dentro" in margin:
                adj += 0.3
            else:
                adj += 0.1

    # ── Supply ──
    supp = (team_reports_dict.get("supply") or {}).get("analysis") or {}
    if supp:
        rec         = (supp.get("recommendation") or "").upper()
        reliability = (supp.get("delivery_reliability") or "").lower()
        if "NO-GO" in rec:
            adj -= 0.5
        elif "CONDICIONAL" in rec:
            adj += (-0.1 if "baixa" in reliability else 0.0)
        elif rec == "GO":
            if "alta" in reliability:
                adj += 0.5
            elif "média" in reliability or "media" in reliability:
                adj += 0.3
            else:
                adj += 0.1

    return round(adj, 2)


def _recalculate_manufacturer_score(mid: str, conn) -> None:
    """Busca todos os relatórios de times, recalcula o ajuste e atualiza score_final."""
    rows = conn.execute(
        "SELECT team, analysis FROM team_reports WHERE manufacturer_id=?", (mid,)
    ).fetchall()

    team_reports = {}
    for r in rows:
        try:
            analysis = json.loads(r["analysis"] or "{}")
        except Exception:
            analysis = {}
        if analysis:
            team_reports[r["team"]] = {"analysis": analysis}

    adj = calculate_team_adjustment(team_reports)

    row = conn.execute(
        "SELECT score_ai, score_final FROM manufacturers WHERE id=?", (mid,)
    ).fetchone()
    if not row:
        return

    score_ai = row["score_ai"] if row["score_ai"] else row["score_final"]
    new_final = round(min(10.0, max(0.0, score_ai + adj)), 2)
    new_decision = (
        "GO" if new_final >= 7.5
        else "GO CONDICIONAL" if new_final >= 6.0
        else "AGUARDAR" if new_final >= 4.0
        else "NO-GO"
    )

    conn.execute(
        "UPDATE manufacturers SET score_ai=?, score_team_adj=?, score_final=?, decision=? WHERE id=?",
        (score_ai, adj, new_final, new_decision, mid),
    )


MAX_IMAGE_BYTES = 1_500_000   # 1.5 MB — acima disso comprime
MAX_PDF_BYTES   = 8_000_000   # 8 MB — acima disso extrai texto
MAX_PAYLOAD_MB  = 20          # limite de segurança POR CHAMADA à API (a Anthropic recusa requests > 32 MB
                              # depois da codificação base64; 20 MB reais dá margem confortável).
                              # Lotes maiores que isso são divididos em múltiplas chamadas e fundidos — ver _analyze_in_batches.

ALLOWED_UPLOAD_EXTS = {".pdf", ".jpg", ".jpeg", ".png"}


def _safe_filename(name: str) -> str:
    return name.replace("..", "").replace("/", "_").replace("\\", "_")


def _extract_zip(zip_path: Path, dest_dir: Path) -> list[str]:
    """Extrai um .zip (com pastas/subpastas) para dest_dir, mantendo apenas
    arquivos de extensão suportada. O caminho da subpasta é achatado no nome
    do arquivo para evitar colisões e para blindar contra zip-slip."""
    saved = []
    try:
        with zipfile.ZipFile(zip_path) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                member = PurePosixPath(info.filename.replace("\\", "/"))
                if member.suffix.lower() not in ALLOWED_UPLOAD_EXTS:
                    continue
                # remove partes perigosas (".." , raiz absoluta) antes de achatar o caminho
                parts = [p for p in member.parts if p not in ("..", "", ".", "/") and not p.endswith(":")]
                if not parts:
                    continue
                flat_name = _safe_filename("_".join(parts))
                target = dest_dir / flat_name
                counter = 1
                while target.exists():
                    target = dest_dir / f"{target.stem}_{counter}{target.suffix}"
                    counter += 1
                with zf.open(info) as src, open(target, "wb") as out:
                    shutil.copyfileobj(src, out)
                saved.append(target.name)
    except zipfile.BadZipFile:
        pass
    return saved


def _save_uploads(files, dest_dir: Path) -> list[str]:
    """Salva os arquivos enviados no formulário. Arquivos .zip são extraídos
    recursivamente (pastas/subpastas), mantendo apenas PDFs e imagens."""
    saved = []
    for file in files:
        if not file.filename:
            continue
        name = _safe_filename(file.filename)
        if name.lower().endswith(".zip"):
            tmp_zip = dest_dir / f"_upload_{uuid.uuid4().hex}.zip"
            file.save(str(tmp_zip))
            saved.extend(_extract_zip(tmp_zip, dest_dir))
            tmp_zip.unlink(missing_ok=True)
        else:
            file.save(str(dest_dir / name))
            saved.append(name)
    return saved


def _compress_image(data: bytes) -> tuple[bytes, str]:
    """Redimensiona e comprime imagem para JPEG ≤ 1.5 MB."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        # Reduz até caber em MAX_IMAGE_BYTES
        quality = 80
        max_dim = 1920
        while True:
            if max(img.size) > max_dim:
                ratio = max_dim / max(img.size)
                img = img.resize(
                    (int(img.width * ratio), int(img.height * ratio)),
                    Image.LANCZOS,
                )
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            result = buf.getvalue()
            if len(result) <= MAX_IMAGE_BYTES or quality <= 40:
                return result, "image/jpeg"
            quality -= 15
            max_dim = int(max_dim * 0.85)
    except Exception:
        return data[:MAX_IMAGE_BYTES], "image/jpeg"


def _extract_pdf_text(data: bytes, filename: str) -> str | None:
    """Extrai texto de PDF grande para enviar como texto puro."""
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(data))
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"[Página {i+1}]\n{text}")
        return f"=== {filename} (texto extraído — arquivo grande) ===\n\n" + "\n\n".join(pages) if pages else None
    except Exception:
        return None


def _build_file_content_block(fp: Path) -> dict | None:
    """Converte um arquivo em content block para a API, aplicando compressão se necessário."""
    import base64
    if not fp.exists():
        return None
    data = fp.read_bytes()
    ext = fp.suffix.lower()

    if ext == ".pdf":
        # PDFs grandes: extrai texto para não estourar o limite da API
        if len(data) > MAX_PDF_BYTES:
            text = _extract_pdf_text(data, fp.name)
            if text:
                return {"type": "text", "text": text}
            # Não conseguiu extrair texto e arquivo é grande demais
            size_mb = len(data) / 1_048_576
            return {
                "type": "text",
                "text": (
                    f"=== {fp.name} ===\n"
                    f"[AVISO: PDF de {size_mb:.1f} MB — muito grande para enviar diretamente "
                    f"e não foi possível extrair o texto (provavelmente PDF digitalizado/imagem). "
                    f"Use uma versão de menor tamanho ou converta as páginas em imagens separadas.]"
                ),
            }

        # PDFs pequenos: tenta validar com pypdf antes de enviar como document
        # (detecta PDFs corrompidos, protegidos por senha, etc.)
        try:
            import pypdf
            pypdf.PdfReader(io.BytesIO(data))  # apenas valida — não usa o resultado
        except Exception:
            # PDF inválido/ilegível: tenta extrair texto mesmo assim
            text = _extract_pdf_text(data, fp.name)
            if text:
                return {"type": "text", "text": text}
            return None  # ignora silenciosamente arquivo ilegível

        return {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": base64.standard_b64encode(data).decode(),
            },
            "title": fp.name,
        }

    if ext in (".jpg", ".jpeg", ".png"):
        if len(data) > MAX_IMAGE_BYTES:
            data, _ = _compress_image(data)
        media_type = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
        # PNG que ainda ficou grande após compressão → reenvia como JPEG
        if ext == ".png" and len(data) > MAX_IMAGE_BYTES:
            media_type = "image/jpeg"
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64.standard_b64encode(data).decode(),
            },
        }

    # Outros formatos: tenta UTF-8
    try:
        return {"type": "text", "text": f"=== {fp.name} ===\n{data.decode('utf-8')}"}
    except Exception:
        return None


def _check_payload_size(content: list) -> None:
    """Levanta erro claro se o payload de UM lote exceder o limite seguro por chamada."""
    total = 0
    for block in content:
        src = (block.get("source") or {})
        b64 = src.get("data", "")
        total += len(b64) * 3 // 4  # base64 → bytes reais
        total += len(block.get("text", "").encode())
    total_mb = total / 1_048_576
    if total_mb > MAX_PAYLOAD_MB:
        raise ValueError(
            f"Arquivo(s) muito grande(s): um único documento excede {MAX_PAYLOAD_MB} MB mesmo após "
            "compressão/extração de texto. Reduza o tamanho desse arquivo específico."
        )


def _split_into_batches(file_paths: list, max_mb: float = MAX_PAYLOAD_MB) -> list[list]:
    """Agrupa arquivos em lotes que cabem no limite de payload por chamada à API,
    permitindo processar um número e volume arbitrário de arquivos em múltiplas
    chamadas sequenciais que depois são fundidas em uma única análise."""
    max_bytes = max_mb * 1_048_576
    batches, current, current_size = [], [], 0

    for fp in file_paths:
        p = Path(fp)
        try:
            size = p.stat().st_size
        except OSError:
            size = 0
        # PDFs grandes viram texto extraído (bem menor); estima ~15% do tamanho original.
        # Imagens grandes são comprimidas para MAX_IMAGE_BYTES antes do envio.
        if p.suffix.lower() == ".pdf" and size > MAX_PDF_BYTES:
            est_size = size * 0.15
        elif p.suffix.lower() in (".jpg", ".jpeg", ".png") and size > MAX_IMAGE_BYTES:
            est_size = MAX_IMAGE_BYTES
        else:
            est_size = size

        if current and (current_size + est_size) > max_bytes:
            batches.append(current)
            current, current_size = [], 0

        current.append(fp)
        current_size += est_size

    if current:
        batches.append(current)
    return batches


MERGE_INSTRUCTIONS = """Você já produziu uma análise PARCIAL deste mesmo caso com base em um lote anterior \
de documentos (não incluídos nesta mensagem). A análise parcial está abaixo, em JSON:

{prev_json}

Agora você recebeu o lote {batch_num} de {total_batches} — NOVOS documentos do MESMO caso. Sua tarefa:
1. Leia os novos documentos com o mesmo rigor e ceticismo de sempre.
2. Combine as evidências dos novos documentos com a análise parcial anterior — NÃO descarte o que já foi levantado.
3. Se os novos documentos trouxerem itens adicionais (produtos, testes, etc.), acrescente-os às listas correspondentes, sem duplicar os já existentes.
4. Recalcule os valores/scores considerando TODAS as evidências acumuladas (antigas + novas).
5. Retorne o JSON CONSOLIDADO completo, no MESMO formato do schema pedido — nunca retorne apenas o delta.

=== NOVOS DOCUMENTOS ==="""


def _analyze_in_batches(file_paths, *, system_prompt, task_prompt, model="claude-sonnet-4-6",
                         max_tokens=8000, context_prefix_text=None, required_keys=None):
    """Roda a análise em múltiplas chamadas sequenciais (uma por lote de arquivos que
    cabe no limite seguro de payload) e funde os resultados numa única análise JSON.

    required_keys: chaves de topo que a resposta final DEVE conter. Se a IA cortar a
    resposta por tamanho (fabricante com catálogo grande = JSON de saída grande), o texto
    ainda pode ser um JSON válido, só que incompleto — sem essa checagem isso resulta em
    scores zerados salvos silenciosamente. Preferimos falhar alto e claro."""
    import anthropic as ant

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("Configure a variável de ambiente ANTHROPIC_API_KEY")

    client = ant.Anthropic(api_key=api_key)
    batches = _split_into_batches(file_paths)
    if not batches:
        raise ValueError("Nenhum arquivo válido para análise")

    previous = None
    any_batch_processed = False

    for i, batch in enumerate(batches):
        file_blocks = []
        for fp in batch:
            block = _build_file_content_block(Path(fp))
            if block:
                file_blocks.append(block)

        if not file_blocks:
            continue  # lote sem conteúdo aproveitável (arquivos ilegíveis) — pula sem chamar a API

        content = []
        if context_prefix_text:
            content.append({"type": "text", "text": context_prefix_text})
        if previous is not None:
            content.append({
                "type": "text",
                "text": MERGE_INSTRUCTIONS.format(
                    prev_json=json.dumps(previous, ensure_ascii=False, indent=2),
                    batch_num=i + 1, total_batches=len(batches),
                ),
            })
        content.extend(file_blocks)
        content.append({"type": "text", "text": task_prompt})
        _check_payload_size(content)

        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": content}],
        )
        any_batch_processed = True

        if resp.stop_reason == "max_tokens":
            raise ValueError(
                f"A resposta da IA foi CORTADA por exceder o limite de tamanho de saída "
                f"(lote {i + 1}/{len(batches)}). Isso costuma acontecer quando há muitos "
                "produtos/modelos para descrever de uma vez. Envie os documentos deste "
                "fabricante em lotes menores (ex.: 10-15 arquivos por vez, usando "
                "'Adicionar Arquivos') para evitar respostas truncadas."
            )

        text = resp.content[0].text.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1:
            raise ValueError("JSON não encontrado na resposta da IA")
        json_str = text[start:end]
        try:
            previous = json.loads(json_str)
        except json.JSONDecodeError:
            from json_repair import repair_json
            previous = json.loads(repair_json(json_str))

        if required_keys:
            missing = [k for k in required_keys if k not in previous]
            if missing:
                raise ValueError(
                    f"A resposta da IA veio incompleta (faltando: {', '.join(missing)}) no lote "
                    f"{i + 1}/{len(batches)}. Provavelmente o texto foi cortado por tamanho. Envie "
                    "os documentos deste fabricante em lotes menores (ex.: 10-15 arquivos por vez)."
                )

    if not any_batch_processed:
        raise ValueError("Nenhum arquivo válido para análise")
    return previous


def analyze_team_report(file_paths, team, mfr_name, mfr_summary):
    context = (
        f"=== CONTEXTO: Fabricante analisado ===\n"
        f"Nome: {mfr_name}\n"
        f"Resumo da análise principal:\n{mfr_summary}\n\n"
        f"=== DOCUMENTOS DO TIME DE {team.upper()} ==="
    )
    return _analyze_in_batches(
        file_paths,
        system_prompt=TEAM_SYSTEMS[team],
        task_prompt=TEAM_PROMPTS[team],
        max_tokens=6000,
        context_prefix_text=context,
        required_keys=["summary", "recommendation"],
    )


def analyze_files(file_paths):
    return _analyze_in_batches(
        file_paths,
        system_prompt=ANALYSIS_SYSTEM,
        task_prompt=ANALYSIS_PROMPT,
        max_tokens=16000,
        required_keys=["manufacturer", "scores", "decision", "summary"],
    )


def row_to_dict(row):
    if not row:
        return None
    d = dict(row)
    for f in ["product_types", "red_flags", "positives", "products", "files"]:
        try:
            d[f] = json.loads(d.get(f) or "[]")
        except Exception:
            d[f] = []
    try:
        d["raw_analysis"] = json.loads(d.get("raw_analysis") or "{}")
    except Exception:
        d["raw_analysis"] = {}
    return d


# ── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/report/<mid>")
def report(mid):
    conn = get_db()
    row = conn.execute("SELECT * FROM manufacturers WHERE id=?", (mid,)).fetchone()
    tr_rows = conn.execute(
        "SELECT * FROM team_reports WHERE manufacturer_id=?", (mid,)
    ).fetchall()
    conn.close()
    m = row_to_dict(row)
    if not m:
        return "Fabricante não encontrado", 404
    team_reports = {}
    for r in tr_rows:
        d = dict(r)
        try:
            d["files"] = json.loads(d.get("files") or "[]")
        except Exception:
            d["files"] = []
        try:
            d["analysis"] = json.loads(d.get("analysis") or "{}")
        except Exception:
            d["analysis"] = {}
        team_reports[d["team"]] = d
    return render_template("report.html", m=m, team_reports=team_reports)


@app.route("/api/manufacturers", methods=["GET"])
def list_manufacturers():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM manufacturers ORDER BY score_final DESC"
    ).fetchall()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows])


@app.route("/api/manufacturers/<mid>", methods=["GET"])
def get_manufacturer(mid):
    conn = get_db()
    row = conn.execute("SELECT * FROM manufacturers WHERE id=?", (mid,)).fetchone()
    conn.close()
    m = row_to_dict(row)
    if not m:
        return jsonify({"error": "Not found"}), 404
    return jsonify(m)


@app.route("/api/manufacturers/<mid>", methods=["DELETE"])
def delete_manufacturer(mid):
    conn = get_db()
    conn.execute("DELETE FROM manufacturers WHERE id=?", (mid,))
    conn.commit()
    conn.close()
    d = UPLOAD_DIR / mid
    if d.exists():
        shutil.rmtree(str(d))
    return jsonify({"ok": True})


@app.route("/api/analyze", methods=["POST"])
def analyze():
    mid = request.form.get("manufacturer_id", "").strip() or str(uuid.uuid4())
    upload_dir = UPLOAD_DIR / mid
    upload_dir.mkdir(exist_ok=True)

    saved = _save_uploads(request.files.getlist("files"), upload_dir)

    if not saved:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    all_files = [f for f in upload_dir.iterdir() if f.is_file()]

    try:
        analysis = analyze_files([str(f) for f in all_files])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    all_names = [f.name for f in all_files]
    scores = analysis.get("scores", {})

    # Garante penalidade de pós-venda mesmo se o modelo não aplicou
    pos_venda = float(scores.get("pos_venda_brasil", 0))
    score_base = (
        float(scores.get("qualidade_tecnologia", 0)) * 0.25
        + float(scores.get("solidez_fabricante", 0)) * 0.20
        + pos_venda * 0.20
        + float(scores.get("fit_portfolio", 0)) * 0.15
        + float(scores.get("potencial_margem", 0)) * 0.10
        + float(scores.get("certificacoes", 0)) * 0.10
    )
    penalidade = -1.0 if pos_venda <= 5.0 else 0.0
    score_final_calc = round(max(0.0, score_base + penalidade), 2)

    # Corrige decisão se necessário
    if score_final_calc >= 7.5:
        decision_calc = "GO"
    elif score_final_calc >= 6.0:
        decision_calc = "GO CONDICIONAL"
    elif score_final_calc >= 4.0:
        decision_calc = "AGUARDAR"
    else:
        decision_calc = "NO-GO"

    conn = get_db()
    exists = conn.execute("SELECT score_team_adj FROM manufacturers WHERE id=?", (mid,)).fetchone()

    # Preserva o ajuste dos times se o fabricante já existe; reinicia se é novo
    current_team_adj = float(exists["score_team_adj"]) if exists else 0.0
    score_with_teams = round(min(10.0, max(0.0, score_final_calc + current_team_adj)), 2)
    decision_final = (
        "GO" if score_with_teams >= 7.5
        else "GO CONDICIONAL" if score_with_teams >= 6.0
        else "AGUARDAR" if score_with_teams >= 4.0
        else "NO-GO"
    )

    vals = (
        analysis["manufacturer"]["name"],
        analysis["manufacturer"].get("country", ""),
        analysis["manufacturer"].get("founded", ""),
        datetime.now().strftime("%Y-%m-%d"),
        json.dumps(analysis.get("product_types", [])),
        float(scores.get("qualidade_tecnologia", 0)),
        float(scores.get("solidez_fabricante", 0)),
        pos_venda,
        float(scores.get("fit_portfolio", 0)),
        float(scores.get("potencial_margem", 0)),
        float(scores.get("certificacoes", 0)),
        score_with_teams,
        decision_final,
        analysis.get("summary", ""),
        json.dumps(analysis.get("red_flags", [])),
        json.dumps(analysis.get("positives", [])),
        json.dumps(analysis.get("products", [])),
        analysis.get("recommendation_text", ""),
        json.dumps(all_names),
        json.dumps(analysis),
        score_final_calc,        # score_ai — score puro da IA sem times
        current_team_adj,        # score_team_adj — mantém ajuste existente
    )

    if exists:
        conn.execute(
            """UPDATE manufacturers SET name=?,country=?,founded=?,analysis_date=?,
            product_types=?,score_qualidade=?,score_solidez=?,score_pos_venda=?,score_fit=?,
            score_margem=?,score_certificacoes=?,score_final=?,decision=?,summary=?,
            red_flags=?,positives=?,products=?,recommendation=?,files=?,raw_analysis=?,
            score_ai=?,score_team_adj=?
            WHERE id=?""",
            vals + (mid,),
        )
    else:
        conn.execute(
            """INSERT INTO manufacturers (id,name,country,founded,analysis_date,
            product_types,score_qualidade,score_solidez,score_pos_venda,score_fit,
            score_margem,score_certificacoes,score_final,decision,summary,red_flags,
            positives,products,recommendation,files,raw_analysis,score_ai,score_team_adj)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (mid,) + vals,
        )

    conn.commit()
    conn.close()

    return jsonify({"id": mid, "analysis": analysis})


@app.route("/api/manufacturers/<mid>/file/<path:filename>", methods=["GET"])
def download_file(mid, filename):
    # Impede path traversal
    safe_name = Path(filename).name
    file_path = UPLOAD_DIR / mid / safe_name
    if not file_path.exists() or not file_path.is_file():
        abort(404)
    return send_file(str(file_path), as_attachment=True, download_name=safe_name)


@app.route("/api/compare/<id1>/<id2>", methods=["GET"])
def compare(id1, id2):
    conn = get_db()
    r1 = conn.execute(
        "SELECT * FROM manufacturers WHERE id=?", (id1,)
    ).fetchone()
    r2 = conn.execute(
        "SELECT * FROM manufacturers WHERE id=?", (id2,)
    ).fetchone()
    conn.close()
    m1, m2 = row_to_dict(r1), row_to_dict(r2)
    if not m1 or not m2:
        return jsonify({"error": "Fabricante não encontrado"}), 404
    return jsonify({"m1": m1, "m2": m2})


@app.route("/api/manufacturers/<mid>/team-reports", methods=["GET"])
def get_team_reports(mid):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM team_reports WHERE manufacturer_id=? ORDER BY created_at DESC", (mid,)
    ).fetchall()
    conn.close()
    result = {}
    for r in rows:
        d = dict(r)
        try:
            d["files"] = json.loads(d.get("files") or "[]")
        except Exception:
            d["files"] = []
        try:
            d["analysis"] = json.loads(d.get("analysis") or "{}")
        except Exception:
            d["analysis"] = {}
        result[d["team"]] = d
    return jsonify(result)


@app.route("/api/manufacturers/<mid>/team-report/<team>", methods=["POST"])
def upload_team_report(mid, team):
    if team not in ("produtos", "pricing", "supply"):
        return jsonify({"error": "Time inválido"}), 400

    conn = get_db()
    mfr = conn.execute("SELECT name, summary FROM manufacturers WHERE id=?", (mid,)).fetchone()
    conn.close()
    if not mfr:
        return jsonify({"error": "Fabricante não encontrado"}), 404

    upload_dir = UPLOAD_DIR / mid / "team" / team
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved = _save_uploads(request.files.getlist("files"), upload_dir)

    if not saved:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    all_file_paths = [p for p in upload_dir.iterdir() if p.is_file()]
    all_files = [str(p) for p in all_file_paths]
    all_names = [p.name for p in all_file_paths]

    try:
        analysis = analyze_team_report(
            all_files, team,
            mfr["name"], mfr["summary"] or ""
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    report_id = str(uuid.uuid4())
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM team_reports WHERE manufacturer_id=? AND team=?", (mid, team)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE team_reports SET files=?, analysis=?, created_at=? WHERE manufacturer_id=? AND team=?",
            (json.dumps(all_names), json.dumps(analysis), now, mid, team)
        )
    else:
        conn.execute(
            "INSERT INTO team_reports (id, manufacturer_id, team, files, analysis, created_at) VALUES (?,?,?,?,?,?)",
            (report_id, mid, team, json.dumps(all_names), json.dumps(analysis), now)
        )
    _recalculate_manufacturer_score(mid, conn)
    conn.commit()
    conn.close()

    # Retorna score atualizado junto com análise
    conn2 = get_db()
    updated = conn2.execute(
        "SELECT score_final, score_ai, score_team_adj, decision FROM manufacturers WHERE id=?", (mid,)
    ).fetchone()
    conn2.close()
    return jsonify({
        "team": team,
        "analysis": analysis,
        "score_final": updated["score_final"] if updated else None,
        "score_ai": updated["score_ai"] if updated else None,
        "score_team_adj": updated["score_team_adj"] if updated else None,
        "decision": updated["decision"] if updated else None,
    })


@app.route("/api/manufacturers/<mid>/team-report/<team>", methods=["DELETE"])
def delete_team_report(mid, team):
    conn = get_db()
    conn.execute(
        "DELETE FROM team_reports WHERE manufacturer_id=? AND team=?", (mid, team)
    )
    _recalculate_manufacturer_score(mid, conn)
    conn.commit()
    conn.close()
    d = UPLOAD_DIR / mid / "team" / team
    if d.exists():
        shutil.rmtree(str(d))
    return jsonify({"ok": True})


if __name__ == "__main__":
    import threading
    import webbrowser

    threading.Timer(1.5, lambda: webbrowser.open("http://localhost:5000")).start()
    app.run(debug=False, port=5000, use_reloader=False)
