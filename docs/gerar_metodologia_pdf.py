# -*- coding: utf-8 -*-
"""Gera docs/metodologia-analise-fabricantes.pdf a partir do conteúdo abaixo.
Reflete o comportamento real do código em app.py (ver referências de linha nos comentários)."""

from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    HRFlowable, KeepTogether, ListFlowable, ListItem,
)

OUT_PATH = "metodologia-analise-fabricantes.pdf"

ORANGE = colors.HexColor("#d2560f")
DARK = colors.HexColor("#1a2535")
MUTED = colors.HexColor("#5a7a9a")
LIGHT_BG = colors.HexColor("#f4f6f9")
CODE_BG = colors.HexColor("#1a2535")
CODE_FG = colors.HexColor("#d8eaff")
WARN_BG = colors.HexColor("#fff3e0")
WARN_BORDER = colors.HexColor("#d2560f")
GRID = colors.HexColor("#d9dee5")

styles = getSampleStyleSheet()

styles.add(ParagraphStyle("CoverTitle", fontName="Helvetica-Bold", fontSize=26, leading=32,
                           textColor=DARK, alignment=TA_CENTER, spaceAfter=6))
styles.add(ParagraphStyle("CoverSub", fontName="Helvetica", fontSize=13, leading=18,
                           textColor=MUTED, alignment=TA_CENTER, spaceAfter=4))
styles.add(ParagraphStyle("CoverMeta", fontName="Helvetica", fontSize=10, leading=14,
                           textColor=MUTED, alignment=TA_CENTER))
styles.add(ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=16, leading=20,
                           textColor=ORANGE, spaceBefore=18, spaceAfter=8))
styles.add(ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=12.5, leading=16,
                           textColor=DARK, spaceBefore=12, spaceAfter=6))
styles.add(ParagraphStyle("H3", fontName="Helvetica-Bold", fontSize=10.5, leading=14,
                           textColor=DARK, spaceBefore=8, spaceAfter=4))
styles.add(ParagraphStyle("Body", fontName="Helvetica", fontSize=9.7, leading=14.5,
                           textColor=DARK, alignment=TA_LEFT, spaceAfter=6))
styles.add(ParagraphStyle("BodyItalic", parent=styles["Body"], fontName="Helvetica-Oblique",
                           textColor=MUTED))
styles.add(ParagraphStyle("MyBullet", parent=styles["Body"], leftIndent=10, spaceAfter=3))
styles.add(ParagraphStyle("CodeBlock", fontName="Courier", fontSize=8.3, leading=12,
                           textColor=CODE_FG, backColor=CODE_BG, borderPadding=8,
                           spaceBefore=4, spaceAfter=8))
styles.add(ParagraphStyle("TblHead", fontName="Helvetica-Bold", fontSize=8.7, leading=11,
                           textColor=colors.white))
styles.add(ParagraphStyle("TblCell", fontName="Helvetica", fontSize=8.5, leading=11.5,
                           textColor=DARK))
styles.add(ParagraphStyle("TblCellBold", parent=styles["TblCell"], fontName="Helvetica-Bold"))
styles.add(ParagraphStyle("WarnTitle", fontName="Helvetica-Bold", fontSize=9.5, leading=13,
                           textColor=WARN_BORDER))
styles.add(ParagraphStyle("WarnBody", fontName="Helvetica", fontSize=9, leading=13,
                           textColor=DARK))
styles.add(ParagraphStyle("Footnote", fontName="Helvetica-Oblique", fontSize=7.8, leading=11,
                           textColor=MUTED))


def h1(text):
    return [HRFlowable(width="100%", thickness=1.4, color=ORANGE, spaceBefore=2, spaceAfter=2),
            Paragraph(text, styles["H1"])]


def h2(text):
    return Paragraph(text, styles["H2"])


def h3(text):
    return Paragraph(text, styles["H3"])


def p(text):
    return Paragraph(text, styles["Body"])


def bullets(items):
    return ListFlowable(
        [ListItem(Paragraph(t, styles["MyBullet"]), leftIndent=8, bulletColor=ORANGE) for t in items],
        bulletType="bullet", start="•", leftIndent=14,
    )


def numbered(items):
    return ListFlowable(
        [ListItem(Paragraph(t, styles["MyBullet"])) for t in items],
        bulletType="1", leftIndent=16,
    )


def code(text):
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(escaped.replace("\n", "<br/>"), styles["CodeBlock"])


def warn_box(title, body_text):
    inner = Table(
        [[Paragraph(f"ATENÇÃO — {title}", styles["WarnTitle"])],
         [Paragraph(body_text, styles["WarnBody"])]],
        colWidths=[160 * mm],
    )
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WARN_BG),
        ("BOX", (0, 0), (-1, -1), 1, WARN_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
        ("TOPPADDING", (0, 1), (-1, 1), 2),
    ]))
    return inner


def simple_table(header, rows, col_widths, header_bg=DARK):
    data = [[Paragraph(h, styles["TblHead"]) for h in header]]
    for row in rows:
        data.append([Paragraph(str(c), styles["TblCell"]) for c in row])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("GRID", (0, 0), (-1, -1), 0.5, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
    ]))
    return t


def rubric_dimension(title, weight, rows, extra_notes=None):
    story = [h3(f"{title} — peso {weight}")]
    tbl = simple_table(
        ["Faixa", "Critério para atribuir a nota"],
        rows,
        col_widths=[22 * mm, 138 * mm],
        header_bg=colors.HexColor("#334155"),
    )
    story.append(tbl)
    if extra_notes:
        for n in extra_notes:
            story.append(Paragraph(f"<i>{n}</i>", styles["BodyItalic"]))
    story.append(Spacer(1, 6))
    return story


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(GRID)
    canvas.line(18 * mm, 15 * mm, A4[0] - 18 * mm, 15 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 11 * mm, "Fotus Distribuidora Solar — Documentação interna | Uso exclusivo P&D / Coordenação de Produtos")
    canvas.drawRightString(A4[0] - 18 * mm, 11 * mm, f"Página {doc.page}")
    canvas.restoreState()


story = []

# ── CAPA ─────────────────────────────────────────────────────────────────────
story.append(Spacer(1, 60 * mm))
story.append(Paragraph("Metodologia de Análise de Fabricantes", styles["CoverTitle"]))
story.append(Paragraph("Regras de Negócio, Metodologia de Análise e de Pontuação", styles["CoverSub"]))
story.append(Spacer(1, 10 * mm))
story.append(Paragraph("Aplicação interna de triagem e avaliação de fabricantes para o portfólio da Fotus Distribuidora Solar", styles["CoverMeta"]))
story.append(Spacer(1, 30 * mm))
story.append(Paragraph(f"Documento preparado para revisão do time de P&amp;D<br/>Gerado em {date.today().strftime('%d/%m/%Y')} · referente ao código-fonte vigente do app (app.py)", styles["CoverMeta"]))
story.append(PageBreak())

# ── 1. INTRODUÇÃO ────────────────────────────────────────────────────────────
story += h1("1. Introdução e Objetivo")
story.append(p(
    "Esta aplicação é uma ferramenta interna da Fotus para triar e avaliar potenciais fabricantes "
    "(módulos, inversores, BESS, carregadores EV) antes de decisões de entrada de portfólio. O usuário "
    "envia os documentos comerciais/técnicos do fabricante (datasheets, manuais, certificados, registros "
    "INMETRO, apresentações comerciais) e a aplicação usa um modelo de linguagem (Claude, da Anthropic) "
    "para produzir uma análise crítica estruturada, com pontuação em 6 dimensões, uma decisão recomendada "
    "(GO / GO CONDICIONAL / AGUARDAR / NO-GO) e um relatório executivo."
))
story.append(p(
    "Este documento descreve <b>exatamente</b> as regras de negócio implementadas hoje no código-fonte — "
    "a régua de pontuação, os pesos, as fórmulas, os critérios de decisão e as regras de ajuste por times "
    "internos — para que o responsável por P&amp;D possa avaliar criticamente a metodologia atual e propor "
    "ajustes com base na experiência de campo da equipe."
))

# ── 2. VISÃO GERAL DO FLUXO ──────────────────────────────────────────────────
story += h1("2. Visão Geral do Fluxo")
story.append(numbered([
    "Upload de 1 ou mais documentos de um fabricante (PDF, JPG, PNG, ou um .zip com pastas/subpastas, que é extraído automaticamente).",
    "Os arquivos são preparados para envio à IA: imagens grandes são comprimidas, PDFs muito grandes têm o texto extraído em vez de enviados como binário (ver seção 7).",
    "A IA analisa os documentos com um prompt fixo e rigoroso (seção 3) e retorna um JSON estruturado com perfil do fabricante, produtos identificados, notas por dimensão, red flags, pontos positivos e recomendação.",
    "O backend recalcula o score final e a decisão a partir das notas por dimensão retornadas (não confia cegamente no score que a própria IA disse ter calculado — ver seção 5).",
    "O resultado é salvo em um banco local (SQLite) e passa a aparecer no ranking do dashboard.",
    "Times internos (Produtos, Pricing, Supply Chain) podem opcionalmente enviar seus próprios documentos, gerando uma segunda camada de análise que ajusta o score final para cima ou para baixo (seção 6).",
    "A qualquer momento é possível comparar dois fabricantes lado a lado ou exportar um relatório em PDF por fabricante.",
]))

# ── 3. PAPEL DA IA ───────────────────────────────────────────────────────────
story += h1("3. O Papel da Inteligência Artificial")
story.append(p(
    "Toda a análise principal é feita por um modelo Claude (identificado no código como "
    "<font face='Courier'>claude-sonnet-4-6</font>), orientado por um <i>system prompt</i> que define "
    "explicitamente a postura esperada: a de um analista cético, não um vendedor otimista."
))
story.append(h3("Postura definida no prompt (\"Regras de Ouro\")"))
story.append(p("O prompt instrui a IA a seguir, sem exceção, os 5 princípios abaixo:"))
story.append(numbered([
    "<b>Análise cega:</b> a IA só enxerga o(s) documento(s) enviado(s) — sem busca externa. Qualquer afirmação do fabricante que não seja verificável no próprio documento deve ser tratada como NÃO CONFIRMADA e penalizar o score.",
    "<b>Ausência de informação = pior cenário:</b> se o documento não menciona presença no Brasil, assume-se que não há; se não menciona INMETRO, assume-se que não tem certificação. A dúvida nunca beneficia o fabricante.",
    "<b>Marketing sem dado é red flag:</b> frases como \"líder de mercado\" ou \"suporte dedicado\" sem números, certificados ou evidências concretas reduzem o score em vez de contar a favor.",
    "<b>Conservadorismo nos scores:</b> um score acima de 7 exige evidências sólidas no documento; score 8+ exige evidência robusta.",
    "<b>Saída estritamente estruturada:</b> a IA deve retornar somente JSON válido, sem texto ou markdown ao redor — é assim que o backend consegue interpretar a resposta de forma confiável.",
]))
story.append(warn_box(
    "Implicação de design a ponderar",
    "Como a análise não acessa fontes externas, ela não confirma se a empresa realmente existe, não cruza "
    "CNPJ com a Receita Federal, não verifica se o registro INMETRO citado está de fato ativo na base do "
    "INMETRO, e não pesquisa notícias de fraude/falência. Um documento bem produzido e citando números "
    "plausíveis (mesmo que forjados) pode obter um score artificialmente alto. Essa é uma limitação de "
    "escopo deliberada (velocidade e custo), mas é um ponto central para o P&amp;D avaliar se vale a pena "
    "evoluir para uma segunda etapa de verificação externa (ex.: busca na web, consulta a bases públicas)."
))

# ── 4. ESTRUTURA DE DADOS ────────────────────────────────────────────────────
story += h1("4. Estrutura de Dados Extraída da Análise")
story.append(p("Para cada fabricante, a IA é obrigada a devolver um JSON com os seguintes blocos:"))

story.append(h3("4.1 Perfil do fabricante"))
story.append(simple_table(
    ["Campo", "Conteúdo esperado"],
    [
        ["name / commercial_name", "Nome completo e nome comercial do fabricante"],
        ["country / founded", "País de origem e ano de fundação (ou \"Não informado\")"],
        ["size", "Descrição do porte, baseada só em dados do documento — hoje exibida na aplicação como \"Sobre a Marca\""],
        ["revenue / capacity / employees", "Faturamento, capacidade produtiva e nº de funcionários, só se mencionados no documento"],
        ["brazil_presence", "Descrição da presença no Brasil — texto fixo \"Sem menção a presença no Brasil\" se o documento não citar nada"],
    ],
    col_widths=[42 * mm, 118 * mm],
))

story.append(h3("4.2 Categorias de produto válidas"))
story.append(p("A IA é instruída a classificar cada linha de produto em exatamente uma destas categorias:"))
story.append(simple_table(
    ["Categoria", "Definição"],
    [
        ["Módulos FV", "Painéis solares fotovoltaicos de qualquer tecnologia"],
        ["Inversores On-Grid", "Inversores string on-grid sem bateria integrada, ligados à rede"],
        ["Inversores Off-Grid", "Inversores para sistemas isolados, sem conexão à rede"],
        ["Inversores Híbridos", "Inversores com entrada de bateria integrada / all-in-one / multigrid"],
        ["Microinversores", "Microinversores por módulo (module-level power electronics)"],
        ["BESS Residencial", "Armazenamento residencial (até ~30 kWh)"],
        ["BESS C&amp;I", "Armazenamento comercial/industrial (acima de 30 kWh)"],
        ["Carregadores EV AC", "Carregadores veiculares modo 3, wallbox AC"],
        ["Carregadores EV DC", "Carregadores veiculares modo 4, fast charging DC"],
        ["EV + BESS", "Produto integrado que combina carregador EV com bateria"],
        ["Outro", "Qualquer produto fora das categorias acima"],
    ],
    col_widths=[38 * mm, 122 * mm],
))
story.append(p(
    "Regra importante: a IA é instruída a <b>percorrer todo o documento</b> em busca de linhas de produto "
    "(não parar no primeiro item) e a nunca agrupar produtos diferentes em uma categoria por conveniência — "
    "um fabricante com 5 linhas distintas deve gerar 5 entradas na lista de produtos."
))

story.append(h3("4.3 Estrutura de cada produto/modelo"))
story.append(p(
    "Para cada linha de produto: categoria, tecnologia principal, segmento (Residencial/C&amp;I/Utility/Todos) "
    "e uma lista de modelos, cada um com potência, eficiência, garantias de produto e de performance, "
    "degradação anual, certificações visíveis no documento, faixa de preço (se houver) e destaques com dado "
    "concreto. Cada linha de produto recebe também uma nota própria (0–10) e uma recomendação "
    "(Recomendar / Condicional / Não recomendar)."
))

story.append(h3("4.4 Demais campos do relatório"))
story.append(bullets([
    "<b>Resumo executivo</b> — 5 a 8 linhas, obrigatoriamente rigoroso: o que o documento NÃO prova, o que é só marketing, e o que genuinamente impressiona.",
    "<b>Red flags</b> — classificadas em CRÍTICO / ATENÇÃO / MONITORAR.",
    "<b>Pontos positivos</b> — só com evidência concreta no documento (nunca uma afirmação não verificável do fabricante).",
    "<b>Texto de recomendação</b> — segue um formato fixo (iniciativa, decisão, score, fundamentação a favor/contra, pior cenário financeiro, próximo passo e quem deve decidir).",
    "<b>Informações pendentes</b> — o que o documento não respondeu e é crítico, o impacto no score se a resposta for negativa, e como obter a informação.",
    "<b>Estimativas financeiras</b> — volume mensal, preço médio, receita anual, margem, MOQ, payback e capital de giro necessário, sempre que possível ancorados em premissas explícitas.",
]))

story.append(PageBreak())

# ── 5. METODOLOGIA DE PONTUAÇÃO ──────────────────────────────────────────────
story += h1("5. Metodologia de Pontuação — a Régua de Avaliação")
story.append(p(
    "A nota final é composta por 6 dimensões, cada uma pontuada de 0 a 10, com pesos fixos. "
    "O princípio geral declarado no prompt é: <b>na ausência de evidência, pontue para baixo</b> "
    "— um fabricante desconhecido sem dados verificáveis no documento não pode receber nota alta."
))
story.append(simple_table(
    ["Dimensão", "Peso"],
    [
        ["Qualidade / Tecnologia", "25%"],
        ["Solidez do Fabricante", "20%"],
        ["Pós-venda Brasil (dimensão crítica)", "20%"],
        ["Fit com Portfólio Fotus", "15%"],
        ["Potencial de Margem", "10%"],
        ["Certificações e Compliance", "10%"],
    ],
    col_widths=[120 * mm, 40 * mm],
))
story.append(Spacer(1, 4))

story += rubric_dimension("5.1 Qualidade / Tecnologia", "25%", [
    ["9–10", "PVEL Top Performers com evidência; eficiência celular ≥23% (TOPCon) ou ≥24% (HJT); degradação ≤0,4%/ano; histórico de confiabilidade comprovado"],
    ["7–8", "Certificações IEC completas visíveis no documento; eficiência compatível com o mercado 2025–2026; garantia ≥25 anos com termos claros"],
    ["5–6", "Certificações básicas presentes; eficiência aceitável; garantia entre 10 e 25 anos; poucos dados de confiabilidade"],
    ["3–4", "Certificações não visíveis ou só mencionadas sem número; eficiência abaixo da média; garantia ≤10 anos ou com restrições"],
    ["0–2", "Nenhuma certificação comprovada; dados técnicos implausíveis/contraditórios; qualquer menção a falhas em campo"],
], extra_notes=["Atenção: eficiência declarada acima de 24% para módulos sem prova de tecnologia HJT é tratada como red flag de exagero."])

story += rubric_dimension("5.2 Solidez do Fabricante", "20%", [
    ["9–10", "Top-10 global comprovado (JinkoSolar / LONGi / Trina / Canadian / JA Solar / Risen / BYD); receita > USD 3 bi documentada; capacidade > 30 GW/ano; > 10 anos de mercado"],
    ["7–8", "Fabricante estabelecido; receita USD 500 mi–3 bi documentada; capacidade 5–30 GW/ano; 5–10 anos com histórico verificável"],
    ["5–6", "Porte médio com alguns dados financeiros; capacidade 1–5 GW/ano; 3–5 anos; dados parcialmente verificáveis"],
    ["3–4", "Fabricante pequeno; < 3 anos ou mudança recente de controle; pouca informação pública"],
    ["0–2", "Sem dados financeiros ou de capacidade; endereço/histórico não verificável; suspeita de rebranding"],
], extra_notes=["Atenção: se o documento não menciona faturamento, capacidade ou anos de mercado, presume-se porte pequeno (nota ≤5)."])

story += rubric_dimension("5.3 Pós-venda Brasil (dimensão crítica)", "20%", [
    ["9–10", "Escritório próprio no Brasil com endereço; equipe técnica local certificada; RMA ≤15 dias documentado; estoque de peças no Brasil"],
    ["7–8", "Representante técnico dedicado no Brasil, com nome/contato; processo de RMA documentado em 15–30 dias"],
    ["5–6", "Representante comercial (não técnico) no Brasil; RMA via importação em 30–60 dias; suporte remoto apenas"],
    ["3–4", "Sem representação local documentada; suporte só em inglês/chinês; processo de RMA vago"],
    ["0–2", "Nenhuma menção a suporte no Brasil; garantia de execução duvidosa; nenhum canal local definido"],
], extra_notes=[
    "Regra de penalidade obrigatória: se a nota de pós-venda Brasil for ≤ 5,0, o sistema subtrai 1,0 ponto do score final (independentemente das demais notas).",
    "Se o documento não menciona nada sobre o Brasil, a nota desta dimensão é automaticamente ≤3.",
])

story += rubric_dimension("5.4 Fit com Portfólio Fotus", "15%", [
    ["9–10", "Preenche gap estratégico claro; não canibaliza nenhum fornecedor atual forte"],
    ["7–8", "Complementa o portfólio com diferencial claro; sobreposição gerenciável"],
    ["5–6", "Sobreposição significativa com portfólio atual; justificável como alternativa de negociação"],
    ["3–4", "Alta canibalização de fornecedor atual sem vantagem técnica/comercial clara"],
    ["0–2", "Duplicação pura; produto fora do escopo da Fotus; nicho sem demanda real dos integradores"],
], extra_notes=["Gaps prioritários definidos hoje no prompt: BESS residencial/C&amp;I, carregadores EV com INMETRO, inversores com pós-venda melhor que o atual, módulos TOPCon Tier-1 com margem melhor."])

story += rubric_dimension("5.5 Potencial de Margem", "10%", [
    ["9–10", "Margem acima do target ideal + exclusividade possível + política de preço favorável documentada"],
    ["7–8", "Margem entre o target mínimo e o ideal; política de preço estável"],
    ["5–6", "Margem no limite do target mínimo; canal concorrido"],
    ["3–4", "Margem abaixo do target mínimo; fabricante comprime o distribuidor"],
    ["0–2", "Margem inviável; produto já comoditizado sem diferencial"],
], extra_notes=[
    "Targets mínimos hoje no prompt: Módulos 12% · Inversores string 15% · BESS 18% · Carregadores EV 18%.",
    "Targets ideais: Módulos 18% · Inversores 22% · BESS 30% · Carregadores EV 32%.",
    "Sem dados de preço no documento, a nota deve ser conservadora (máximo 5).",
])

story += rubric_dimension("5.6 Certificações e Compliance", "10%", [
    ["9–10", "Todas as certificações obrigatórias visíveis com nº de certificado + INMETRO válido"],
    ["7–8", "Todas obrigatórias mencionadas + INMETRO em processo com prazo documentado"],
    ["5–6", "IEC internacionais presentes sem INMETRO; ou INMETRO declarado sem prazo"],
    ["3–4", "Certificações parciais; INMETRO ausente sem qualquer plano mencionado"],
    ["0–2", "Ausência de certificações IEC básicas para produto que se conecta à rede elétrica"],
], extra_notes=[
    "Obrigatórias por categoria hoje no prompt — Módulos FV: IEC 61215 + IEC 61730 + INMETRO (portaria 004). "
    "Inversores on-grid: IEC 62116 + IEC 61683 + INMETRO (portaria 357). BESS: IEC 62619 + UN 38.3 + INMETRO. "
    "Carregadores EV AC: IEC 61851-1 + INMETRO (portaria 563).",
])

story.append(PageBreak())
story.append(h2("5.7 Fórmula do score final"))
story.append(code(
    "score_base = (qualidade × 0.25) + (solidez × 0.20) + (pos_venda × 0.20)\n"
    "           + (fit × 0.15) + (margem × 0.10) + (certificacoes × 0.10)\n\n"
    "penalidade_pos_venda = -1.0  SE pos_venda_brasil <= 5.0,  SENAO 0.0\n\n"
    "score_final = score_base + penalidade_pos_venda"
))
story.append(p(
    "Importante: o backend <b>não confia apenas no score que a própria IA devolveu</b> no JSON — ele recalcula "
    "o score final e a penalidade de pós-venda a partir das 6 notas por dimensão, como camada de segurança "
    "contra erro aritmético do modelo."
))

story.append(h2("5.8 Faixas de decisão"))
story.append(simple_table(
    ["Faixa de score", "Decisão", "Significado apresentado ao usuário"],
    [
        ["≥ 7,5", "GO", "Recomendar entrada imediata no portfólio — fabricante aprovado em todas as dimensões críticas"],
        ["6,0 – 7,4", "GO CONDICIONAL", "Entrar no portfólio com condições específicas a negociar (ex.: garantia, suporte local, MOQ)"],
        ["4,0 – 5,9", "AGUARDAR", "Não entrar agora — necessita mais dados, visita técnica ou melhoria do fabricante"],
        ["< 4,0", "NO-GO", "Não recomendar — riscos críticos (pós-venda, solidez, certificações) inviabilizam a entrada"],
    ],
    col_widths=[28 * mm, 32 * mm, 100 * mm],
))

story.append(h2("5.9 Vetos automáticos (força NO-GO independentemente do score)"))
story.append(bullets([
    "Pós-venda Brasil ≤ 3,0 sem plano concreto documentado de estruturação no Brasil",
    "Evidência de fraude, contrafação ou irregularidade fiscal",
    "Fabricante em falência ou liquidação",
    "Ausência total de certificação IEC para produto que se conecta à rede elétrica",
    "Solidez do fabricante ≤ 2,0",
]))
story.append(warn_box(
    "Gap entre prompt e código — ponto central para revisão do P&amp;D",
    "Essas regras de veto existem hoje <b>apenas como instrução textual para a IA</b>, dentro do prompt. "
    "O código do backend (rotina que recalcula o score final) <b>não verifica programaticamente</b> nenhuma "
    "dessas condições — ele decide a faixa (GO / CONDICIONAL / AGUARDAR / NO-GO) só a partir do valor numérico "
    "do score final recalculado. Ou seja: se a IA \"esquecer\" de aplicar um veto (por exemplo, não perceber uma "
    "menção a falência no meio de um documento longo), nada no código impede que o sistema salve uma decisão "
    "diferente de NO-GO mesmo com uma condição de veto presente. Recomenda-se avaliar se esses vetos devem "
    "virar checagens explícitas no backend (ou pelo menos um campo de alerta separado revisado manualmente)."
))

story.append(h2("5.10 Perguntas que todo relatório deve responder"))
story.append(p("O prompt exige que o resumo e o texto de recomendação sempre antecipem estas 4 perguntas:"))
story.append(bullets([
    "\"Se esse produto der problema em campo, quem paga o custo de pós-venda?\"",
    "\"O fabricante ainda vai existir daqui a 5 anos?\"",
    "\"Por que esse fabricante e não o que já temos no portfólio?\"",
    "\"Qual o pior cenário financeiro se entrarmos com essa marca?\"",
]))

story.append(PageBreak())

# ── 6. AJUSTE POR TIMES INTERNOS ─────────────────────────────────────────────
story += h1("6. Camada de Ajuste por Times Internos")
story.append(p(
    "Além da análise principal (feita a partir dos documentos comerciais do fabricante), a aplicação permite "
    "que três times internos enviem seus próprios documentos para uma segunda camada de análise por IA, "
    "cada um com um prompt e um schema de saída próprios: <b>Produtos</b> (laudos e testes físicos), "
    "<b>Pricing</b> (preços, margens, competitividade) e <b>Supply Chain</b> (lead time, MOQ, risco logístico)."
))
story.append(p(
    "Cada time contribui um ajuste de <b>-0,5 a +0,5</b> sobre o score final, com base em regras "
    "determinísticas aplicadas ao resultado da análise daquele time:"
))
story.append(simple_table(
    ["Time", "Condição", "Ajuste"],
    [
        ["Produtos", "Aprovado + risco baixo", "+0,5"],
        ["Produtos", "Aprovado + risco médio", "+0,2"],
        ["Produtos", "Aprovado + risco alto", "+0,1"],
        ["Produtos", "Aprovado com ressalvas + risco alto", "-0,2"],
        ["Produtos", "Aprovado com ressalvas (demais casos)", "0,0"],
        ["Produtos", "Reprovado", "-0,5"],
        ["Pricing", "GO + margem acima do target", "+0,5"],
        ["Pricing", "GO + margem dentro do target", "+0,3"],
        ["Pricing", "GO + sem info de margem", "+0,1"],
        ["Pricing", "GO CONDICIONAL + margem abaixo do target", "-0,1"],
        ["Pricing", "GO CONDICIONAL (demais casos)", "0,0"],
        ["Pricing", "NO-GO", "-0,5"],
        ["Supply", "GO + confiabilidade alta", "+0,5"],
        ["Supply", "GO + confiabilidade média", "+0,3"],
        ["Supply", "GO + sem info", "+0,1"],
        ["Supply", "GO CONDICIONAL + confiabilidade baixa", "-0,1"],
        ["Supply", "GO CONDICIONAL (demais casos)", "0,0"],
        ["Supply", "NO-GO", "-0,5"],
    ],
    col_widths=[28 * mm, 108 * mm, 24 * mm],
))
story.append(Spacer(1, 4))
story.append(p("O ajuste combinado dos 3 times pode variar de <b>-1,5 a +1,5</b>. A fórmula final é:"))
story.append(code(
    "score_ai        = score calculado só com a análise principal (IA), sem ajuste de times\n"
    "score_team_adj  = soma dos ajustes dos times que já enviaram relatório\n"
    "score_final     = min(10, max(0, score_ai + score_team_adj))\n\n"
    "Decisão final recalculada nas mesmas faixas da seção 5.8, usando o score_final ajustado."
))
story.append(p(
    "O ajuste é recalculado automaticamente sempre que um time envia ou exclui seu relatório — não é "
    "preciso reprocessar a análise principal para isso."
))
story.append(warn_box(
    "Fragilidade da lógica de ajuste",
    "As regras acima dependem de <i>correspondência de texto</i> nos campos <font face='Courier'>recommendation</font>, "
    "<font face='Courier'>risk_level</font>, <font face='Courier'>margin_assessment</font> e "
    "<font face='Courier'>delivery_reliability</font> gerados livremente pela IA (por exemplo, o código procura "
    "a palavra \"aprovado\" ou \"baixo\" dentro do texto). Se o modelo variar a fraseação de forma que o "
    "prompt não previu, o ajuste correspondente pode simplesmente não ser aplicado (fica em 0,0) sem qualquer aviso."
))

story.append(PageBreak())

# ── 7. PROCESSAMENTO DE ARQUIVOS ─────────────────────────────────────────────
story += h1("7. Processamento e Engenharia de Documentos")
story.append(p(
    "Esta seção documenta as regras técnicas que preparam os arquivos antes de enviá-los à IA — relevantes "
    "para entender por que uma análise pode demorar mais, custar mais chamadas de IA, ou falhar."
))
story.append(h3("7.1 Formatos aceitos"))
story.append(bullets([
    "PDF, JPG, PNG — enviados diretamente.",
    "ZIP — extraído automaticamente, inclusive com pastas e subpastas; só os arquivos PDF/imagem contidos são aproveitados, os demais são ignorados. Proteção contra \"zip-slip\" (entradas maliciosas tentando escrever fora da pasta de destino) embutida na extração.",
]))
story.append(h3("7.2 Compressão e conversão automática"))
story.append(bullets([
    "Imagens acima de 1,5 MB são redimensionadas e recomprimidas em JPEG até caber no limite.",
    "PDFs acima de 8 MB têm o texto extraído e enviado como texto puro (em vez do arquivo binário completo) — mais leve, mas a IA deixa de \"ver\" imagens/diagramas desse PDF especificamente.",
    "PDFs corrompidos, protegidos por senha ou digitalizados sem camada de texto: o sistema tenta extrair texto como fallback; se não conseguir, o arquivo é ignorado silenciosamente (não interrompe a análise dos demais documentos).",
]))
story.append(h3("7.3 Processamento em lotes para grandes volumes"))
story.append(p(
    "A API da Anthropic recusa requisições cujo payload (após a codificação base64 dos arquivos) ultrapasse "
    "cerca de 32 MB. Por isso, o sistema usa um limite de segurança de <b>20 MB reais por chamada</b>. Quando "
    "o conjunto de documentos de um fabricante excede esse limite, os arquivos são divididos automaticamente "
    "em lotes sequenciais: cada lote é enviado em uma chamada separada à IA, que recebe a análise parcial do "
    "lote anterior e a funde com as novas evidências, devolvendo uma análise única e consolidada ao final. "
    "Isso permite processar um número praticamente ilimitado de documentos por fabricante, ao custo de mais "
    "tempo de processamento e mais chamadas de IA (mais custo)."
))
story.append(h3("7.4 Proteção contra respostas truncadas"))
story.append(p(
    "Um incidente real já foi identificado e corrigido: um fabricante com mais de 40 documentos gerou uma "
    "resposta da IA tão extensa (muitos produtos/modelos para descrever) que a resposta foi cortada pelo "
    "limite de tokens de saída antes de chegar aos campos de score — e o sistema, na versão anterior, salvava "
    "essa análise incompleta com todas as notas zeradas e decisão NO-GO, sem avisar ninguém."
))
story.append(p("A correção aplicada tem duas camadas:"))
story.append(numbered([
    "O limite de tokens de saída da análise principal foi elevado (de 8.000 para 16.000 tokens) para reduzir a chance de corte em fabricantes com catálogos grandes.",
    "O sistema agora verifica se a resposta foi cortada pelo limite de tamanho e se os campos obrigatórios do schema (perfil, notas, decisão, resumo) realmente vieram preenchidos — se não vieram, a análise falha com uma mensagem clara pedindo para reenviar os documentos em lotes menores, em vez de salvar silenciosamente um resultado incompleto.",
]))

story.append(PageBreak())

# ── 8. PERSISTÊNCIA ───────────────────────────────────────────────────────────
story += h1("8. Persistência de Dados e Ciclo de Vida")
story.append(p(
    "Os dados são armazenados em um banco SQLite local (<font face='Courier'>data/analyses.db</font>), com "
    "duas tabelas principais: <font face='Courier'>manufacturers</font> (uma linha por fabricante analisado) "
    "e <font face='Courier'>team_reports</font> (uma linha por relatório de time interno)."
))
story.append(simple_table(
    ["Campo", "Significado"],
    [
        ["score_ai", "Score calculado só pela análise principal da IA, sem ajuste de times"],
        ["score_team_adj", "Soma dos ajustes aplicados pelos times internos (-1,5 a +1,5)"],
        ["score_final", "score_ai + score_team_adj, limitado entre 0 e 10 — é o que aparece no dashboard"],
    ],
    col_widths=[38 * mm, 122 * mm],
))
story.append(p(
    "Ponto relevante: quando novos arquivos são adicionados a um fabricante já existente (\"Adicionar "
    "Arquivos\"), a análise principal é <b>refeita do zero considerando todos os arquivos daquele fabricante "
    "acumulados até então</b> (os antigos + os novos) — não é uma atualização incremental apenas com o "
    "arquivo novo. O ajuste dos times, por outro lado, é preservado e não precisa ser refeito."
))
story.append(p(
    "A exclusão de um fabricante é <b>permanente e imediata</b> — remove o registro do banco e todos os "
    "arquivos enviados, sem lixeira ou possibilidade de desfazer pela interface."
))

# ── 9. DASHBOARD ──────────────────────────────────────────────────────────────
story += h1("9. Funcionalidades do Dashboard")
story.append(bullets([
    "<b>Ranking geral</b> de fabricantes, ordenado por score final, com filtros por tipo de produto e por decisão, e busca por nome/país.",
    "<b>Indicadores agregados</b>: total de fabricantes analisados, score médio, melhor avaliado, proporção aprovada (GO + GO CONDICIONAL) sobre o total.",
    "<b>Painel de detalhe</b> por fabricante: perfil resumido (\"Sobre a Marca\"), resumo executivo, scorecard com gráfico radar, produtos avaliados, red flags, pontos positivos, dados financeiros estimados, informações pendentes, arquivos anexados para download, e as análises dos times internos.",
    "<b>Comparação lado a lado</b> entre dois fabricantes (radar comparativo e diferença por dimensão).",
    "<b>Exportação de relatório em PDF</b> por fabricante, com o mesmo conteúdo estruturado do painel de detalhe, pronto para impressão/compartilhamento.",
]))

story.append(PageBreak())

# ── 10. LIMITAÇÕES E PONTOS PARA O P&D ───────────────────────────────────────
story += h1("10. Limitações Conhecidas e Pontos para Ponderação do P&amp;D")
story.append(p(
    "Esta seção reúne, de forma direta, os principais gaps e escolhas de design identificados na "
    "metodologia atual — como pontos de partida para a revisão crítica do responsável por P&amp;D:"
))
story.append(numbered([
    "<b>Vetos automáticos não são reforçados em código</b> (seção 5.9) — dependem inteiramente de a IA aplicar corretamente a regra textual do prompt. Vale avaliar se esses vetos devem virar checagens programáticas.",
    "<b>Análise 100% cega a fontes externas</b> — não há verificação de CNPJ, situação do registro INMETRO, notícias de fraude ou falência. É uma limitação de escopo deliberada, mas aumenta o risco de um documento bem produzido (porém enganoso) obter score alto.",
    "<b>\"Potencial de Margem\" e \"Fit Portfólio\" tendem a ficar sistematicamente baixos ou pouco discriminantes</b>, porque dependem de dados (preço, MOQ) raramente presentes nos documentos comerciais dos fabricantes.",
    "<b>O ajuste dos times internos depende de correspondência de palavras-chave</b> no texto livre gerado pela IA (ex.: procurar \"aprovado\"/\"reprovado\" na resposta) — sensível a variações de fraseado que o prompt não previu.",
    "<b>Reprocessamento não incremental</b> — adicionar novos arquivos a um fabricante existente refaz a análise de todos os documentos anteriores também, o que cresce o custo e o tempo de processamento com o total acumulado de documentos, não apenas com os novos.",
    "<b>Fabricantes com catálogos muito grandes</b> dependem de múltiplas chamadas de IA encadeadas (seção 7.3) — mais lotes significam mais custo de tokens e mais chances de pequenas inconsistências entre o que foi \"lembrado\" de um lote para o outro.",
    "<b>Sem controle de acesso</b> — qualquer pessoa com acesso à aplicação pode excluir uma análise de forma permanente e imediata.",
    "<b>Parâmetros fixos no código-fonte</b> — pesos das dimensões, faixas de decisão, modelo de IA usado e limites de tokens estão hoje embutidos diretamente no código; não existe um arquivo de configuração externo para ajustá-los sem alterar o app.py.",
]))
story.append(Spacer(1, 8))
story.append(p(
    "Este documento foi preparado para apoiar exatamente esse tipo de ponderação: os critérios, pesos e "
    "regras acima refletem escolhas de um primeiro desenho da metodologia e podem — e devem — ser "
    "revisados à luz da experiência prática da equipe de P&amp;D e de Produtos."
))

doc = SimpleDocTemplate(
    OUT_PATH, pagesize=A4,
    leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=20 * mm,
    title="Metodologia de Análise de Fabricantes — Fotus Solar",
    author="Fotus Distribuidora Solar",
)
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("PDF gerado em:", OUT_PATH)
