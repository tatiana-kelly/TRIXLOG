const API = "";

function brl(v) {
  if (v === null || v === undefined) return "—";
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}
function pct(v) {
  if (v === null || v === undefined) return "—";
  return v.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "%";
}
function esc(s) {
  return (s ?? "").toString().replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

async function api(path, opts) {
  const res = await fetch(API + path, opts);
  if (!res.ok) throw new Error(`${path} -> HTTP ${res.status}`);
  return res.json();
}

// ---------------- navegação ----------------
document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((i) => i.classList.remove("active"));
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
    item.classList.add("active");
    document.getElementById("view-" + item.dataset.view).classList.add("active");
    loadView(item.dataset.view);
  });
});

function loadView(view) {
  if (view === "visao-geral") loadVisaoGeral();
  if (view === "decisoes") loadDecisoes();
  if (view === "dre") loadDRE();
  if (view === "rentabilidade") loadRentabilidade();
  if (view === "comparativo") loadComparativo();
  if (view === "desvios") loadDesviosFilters();
  if (view === "conciliacao") loadConciliacao();
  if (view === "rotas") loadRotas();
  if (view === "frota") loadFrota();
  if (view === "terceiros") loadTerceiros();
}

// ---------------- visão geral ----------------
async function loadVisaoGeral() {
  const el = document.getElementById("visao-geral-content");
  try {
    const status = await api("/import/status");
    const meses = await api("/analytics/meses");

    if (status.cte.total === 0) {
      el.innerHTML = emptyState("Nenhum relatório importado ainda.", "Vá em “Importar relatórios” para começar.");
      return;
    }

    const porMesUnidade = status.cte.por_mes_unidade
      .sort((a, b) => (a.mes + a.unidade).localeCompare(b.mes + b.unidade))
      .map((r) => `<tr><td>${esc(r.mes)}</td><td><span class="badge-unidade">${esc(r.unidade || "?")}</span></td><td class="num">${r.quantidade}</td></tr>`)
      .join("");

    const cobertura = status.cobertura_custo;
    const coberturaClasse = cobertura.pct_cobertura >= 50 ? "" : "warn";

    el.innerHTML = `
      <div class="kpi-row">
        <div class="kpi-card"><div class="kpi-label">CT-e importados</div><div class="kpi-value">${status.cte.total}</div></div>
        <div class="kpi-card"><div class="kpi-label">Contas a receber</div><div class="kpi-value">${status.contas_receber.total}</div></div>
        <div class="kpi-card"><div class="kpi-label">Contas a pagar</div><div class="kpi-value">${status.contas_pagar.total}</div></div>
        <div class="kpi-card"><div class="kpi-label">Meses cobertos</div><div class="kpi-value gold">${meses.length}</div></div>
      </div>
      <div class="kpi-row">
        <div class="kpi-card" style="grid-column: span 2">
          <div class="kpi-label">Cobertura de custo — CT-e's com vínculo confirmado</div>
          <div class="kpi-value ${coberturaClasse}">${pct(cobertura.pct_cobertura)}</div>
          <div class="source-note" style="margin:6px 0 0">${cobertura.ctes_com_custo_vinculado} de ${cobertura.ctes_total} CT-e's — o resto aguarda alocação (Camada 0/2) ou conciliação manual, nunca é tratado como custo zero</div>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Mês</th><th>Unidade</th><th style="text-align:right">CT-e's</th></tr></thead>
          <tbody>${porMesUnidade}</tbody>
        </table>
      </div>
      <p class="source-note">fonte: CT-e / Contas a Receber / Contas a Pagar reais, importados via /import/upload</p>
    `;
  } catch (e) {
    el.innerHTML = errorState(e);
  }
}

// ---------------- central de decisões ----------------
async function loadDecisoes() {
  const unidadeSel = document.getElementById("decisoes-unidade");
  if (!unidadeSel.dataset.bound) {
    unidadeSel.addEventListener("change", renderDecisoes);
    unidadeSel.dataset.bound = "1";
  }
  renderDecisoes();
}

const SEVERIDADE_META = {
  critico: { luz: "alert", label: "CRÍTICO" },
  atencao: { luz: "pending", label: "ATENÇÃO" },
  informacao: { luz: "ok", label: "INFORMAÇÃO" },
};

async function renderDecisoes() {
  const el = document.getElementById("decisoes-content");
  const unidade = document.getElementById("decisoes-unidade").value;
  el.innerHTML = scanning("Sincronizando dado");
  try {
    const decisoes = await api(`/analytics/decisoes${unidade ? "?unidade=" + unidade : ""}`);
    if (!decisoes.length) {
      el.innerHTML = emptyState("Nenhuma decisão prioritária no momento.", "Nenhum cliente com margem confirmada negativa nem desvio material detectado.");
      return;
    }

    el.innerHTML = decisoes
      .map((d) => {
        const sev = SEVERIDADE_META[d.severidade] || SEVERIDADE_META.informacao;
        const hipoteses = d.hipoteses_causa.map((h) => `<li>${esc(h)}</li>`).join("");
        const acoes = d.acoes_possiveis
          .map((a) => `<li${a === d.acao_recomendada ? ' class="decisao-recomendada"' : ""}>${esc(a)}</li>`)
          .join("");
        return `
        <div class="decisao-card decisao-card--${d.severidade}">
          <div class="decisao-top">
            <span class="pill pill--${d.severidade === "critico" ? "danger" : d.severidade === "atencao" ? "warn" : "ok"}">
              <span class="radar-light radar-light--${sev.luz}"></span>${sev.label}
            </span>
            <span class="decisao-impacto">${brl(d.impacto_reais)}</span>
          </div>
          <div class="decisao-situacao">${esc(d.situacao)}</div>
          <div class="decisao-grid">
            <div><span class="decisao-label">Evidência</span><p>${esc(d.evidencia)}</p></div>
            <div><span class="decisao-label">Onde está concentrado</span><p>${esc(d.onde)}</p></div>
            <div><span class="decisao-label">Consequência de não agir</span><p>${esc(d.consequencia)}</p></div>
            <div><span class="decisao-label">Dado faltante</span><p>${esc(d.dado_faltante)}</p></div>
          </div>
          <div class="decisao-hipoteses">
            <span class="decisao-label">Hipóteses de causa (confiança: ${esc(d.confianca)} — não são fato confirmado)</span>
            <ul>${hipoteses}</ul>
          </div>
          <div class="decisao-hipoteses">
            <span class="decisao-label">Ações possíveis — recomendada em destaque</span>
            <ul>${acoes}</ul>
          </div>
          <div class="decisao-footer">
            <span>Dono: <strong>${esc(d.dono_papel)}</strong></span>
            <span>KPI de validação: ${esc(d.kpi_validacao)}</span>
          </div>
        </div>`;
      })
      .join("");
  } catch (e) {
    el.innerHTML = errorState(e);
  }
}

// ---------------- DRE gerencial ----------------
async function loadDRE() {
  const mesSel = document.getElementById("dre-mes");
  const unidadeSel = document.getElementById("dre-unidade");
  if (!mesSel.dataset.loaded) {
    await populateMonthSelect(mesSel, { includeEmpty: true });
    mesSel.insertAdjacentHTML("afterbegin", `<option value="">Todo o período</option>`);
    mesSel.value = "";
    mesSel.dataset.loaded = "1";
    mesSel.addEventListener("change", renderDRE);
    unidadeSel.addEventListener("change", renderDRE);
  }
  renderDRE();
}

function linhaDRE(label, valor, { destaque, indent } = {}) {
  return `<tr class="${destaque ? "dre-subtotal" : ""}">
    <td style="${indent ? "padding-left:28px;color:var(--ink-dim)" : ""}">${esc(label)}</td>
    <td class="num">${brl(valor)}</td>
  </tr>`;
}

async function renderDRE() {
  const el = document.getElementById("dre-content");
  const mes = document.getElementById("dre-mes").value;
  const unidade = document.getElementById("dre-unidade").value;
  el.innerHTML = scanning("Sincronizando dado");
  try {
    const qs = new URLSearchParams();
    if (mes) qs.set("mes", mes);
    if (unidade) qs.set("unidade", unidade);
    const d = await api(`/analytics/dre?${qs.toString()}`);

    if (!d.receita_operacional) {
      el.innerHTML = emptyState("Nenhum CT-e neste período/unidade.");
      return;
    }

    const despesasRows = Object.entries(d.despesas_operacionais)
      .map(([label, valor]) => linhaDRE(label, -valor, { indent: true }))
      .join("");

    const pendenteAlerta =
      d.custo_frete_terceiro_pendente.qtd_ctes > 0
        ? `<p class="dre-pendente-note"><span class="radar-light radar-light--pending"></span>${d.custo_frete_terceiro_pendente.qtd_ctes} CT-e's (${brl(d.custo_frete_terceiro_pendente.receita)} em receita) ainda sem custo de frete terceiro confirmado — <strong>não entraram no cálculo abaixo</strong>, não são custo zero. Margem de contribuição considera só ${pct(d.pct_receita_com_custo_terceiro_confirmado)} da receita com custo confirmado.</p>`
        : "";

    el.innerHTML = `
      <div class="kpi-row">
        <div class="kpi-card"><div class="kpi-label">Receita operacional</div><div class="kpi-value">${brl(d.receita_operacional)}</div></div>
        <div class="kpi-card"><div class="kpi-label">Margem de contribuição</div><div class="kpi-value ${d.margem_contribuicao >= 0 ? "gold" : "warn"}">${brl(d.margem_contribuicao)}</div></div>
        <div class="kpi-card"><div class="kpi-label">Resultado gerencial</div><div class="kpi-value ${d.resultado_gerencial >= 0 ? "gold" : "warn"}">${brl(d.resultado_gerencial)}</div></div>
        <div class="kpi-card"><div class="kpi-label">Receita c/ custo terceiro confirmado</div><div class="kpi-value">${pct(d.pct_receita_com_custo_terceiro_confirmado)}</div></div>
      </div>
      ${pendenteAlerta}
      <div class="table-wrap">
        <table class="dre-table">
          <tbody>
            ${linhaDRE("Receita Operacional (CT-e)", d.receita_operacional, { destaque: true })}
            ${linhaDRE("Custo direto — frete terceiro (confirmado)", -d.custo_frete_terceiro_confirmado, { indent: true })}
            ${linhaDRE("Combustível (frota própria)", -d.combustivel, { indent: true })}
            ${linhaDRE("Manutenção (frota própria)", -d.manutencao, { indent: true })}
            ${linhaDRE("= Margem de Contribuição Operacional", d.margem_contribuicao, { destaque: true })}
            ${despesasRows}
            ${linhaDRE("= Resultado Operacional Gerencial", d.resultado_operacional, { destaque: true })}
            ${linhaDRE("Despesas financeiras", -d.despesas_financeiras, { indent: true })}
            ${linhaDRE("= Resultado Gerencial", d.resultado_gerencial, { destaque: true })}
          </tbody>
        </table>
      </div>
      <p class="source-note">mês: ${mes ? esc(mes) : "todo o período"} · unidade: ${unidade ? esc(unidade) : "matriz + filial"} · fonte: CT-e + Contas a Pagar reais + Cost Allocation Engine</p>
    `;
  } catch (e) {
    el.innerHTML = errorState(e);
  }
}

// ---------------- rentabilidade ----------------
async function populateMonthSelect(select, { includeEmpty } = {}) {
  const meses = await api("/analytics/meses");
  select.innerHTML = meses.map((m) => `<option value="${m}">${m}</option>`).join("");
  if (meses.length) select.value = meses[meses.length - 1];
  return meses;
}

async function loadRentabilidade() {
  const mesSel = document.getElementById("rent-mes");
  const unidadeSel = document.getElementById("rent-unidade");
  if (!mesSel.dataset.loaded) {
    await populateMonthSelect(mesSel);
    mesSel.dataset.loaded = "1";
    mesSel.addEventListener("change", renderRentabilidade);
    unidadeSel.addEventListener("change", renderRentabilidade);
  }
  renderRentabilidade();
}

async function renderRentabilidade() {
  const el = document.getElementById("rentabilidade-content");
  const mes = document.getElementById("rent-mes").value;
  const unidade = document.getElementById("rent-unidade").value;
  if (!mes) { el.innerHTML = emptyState("Sem meses disponíveis.", "Importe relatórios primeiro."); return; }

  el.innerHTML = scanning("Sincronizando dado");
  try {
    const dados = await api(`/analytics/rentabilidade-mensal?mes=${mes}${unidade ? "&unidade=" + unidade : ""}`);
    if (!dados.length) { el.innerHTML = emptyState("Nenhum CT-e neste mês/unidade."); return; }

    const receitaTotal = dados.reduce((s, d) => s + d.receita_total, 0);
    const margemConhecida = dados.reduce((s, d) => s + d.margem_total, 0);
    const viagensAlocadas = dados.reduce((s, d) => s + d.viagens_com_custo_alocado, 0);
    const viagensPendentes = dados.reduce((s, d) => s + d.viagens_pendentes, 0);

    const rows = dados
      .map(
        (d) => `
      <tr>
        <td>${esc(d.cliente)}</td>
        <td class="num">${brl(d.receita_total)}</td>
        <td class="num">${d.viagens_com_custo_alocado ? brl(d.custo_alocado_total) : "—"}</td>
        <td class="num">${margemCell(d)}</td>
        <td class="num">${d.pct_custo_nao_alocado > 50 ? `<span class="pill pill--warn"><span class="radar-light radar-light--pending"></span>${pct(d.pct_custo_nao_alocado)} pendente</span>` : pct(d.pct_custo_nao_alocado)}</td>
      </tr>`
      )
      .join("");

    el.innerHTML = `
      <div class="kpi-row">
        <div class="kpi-card"><div class="kpi-label">Receita do mês</div><div class="kpi-value">${brl(receitaTotal)}</div></div>
        <div class="kpi-card"><div class="kpi-label">Margem confirmada</div><div class="kpi-value gold">${brl(margemConhecida)}</div></div>
        <div class="kpi-card"><div class="kpi-label">Viagens com custo alocado</div><div class="kpi-value">${viagensAlocadas}</div></div>
        <div class="kpi-card"><div class="kpi-label">Viagens pendentes</div><div class="kpi-value warn">${viagensPendentes}</div></div>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Cliente</th><th style="text-align:right">Receita</th><th style="text-align:right">Custo alocado</th><th style="text-align:right">Margem</th><th style="text-align:right">% pendente</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <p class="source-note">mês: ${esc(mes)} · unidade: ${unidade ? esc(unidade) : "matriz + filial"} · fonte: CT-e real + Cost Allocation Engine</p>
    `;
  } catch (e) {
    el.innerHTML = errorState(e);
  }
}

// ---------------- comparativo ----------------
async function loadComparativo() {
  const unidadeSel = document.getElementById("comp-unidade");
  if (!unidadeSel.dataset.bound) {
    unidadeSel.addEventListener("change", renderComparativo);
    unidadeSel.dataset.bound = "1";
  }
  renderComparativo();
}

async function renderComparativo() {
  const el = document.getElementById("comparativo-content");
  const unidade = document.getElementById("comp-unidade").value;
  el.innerHTML = scanning("Sincronizando dado");
  try {
    const meses = await api("/analytics/meses");
    if (!meses.length) { el.innerHTML = emptyState("Sem meses disponíveis."); return; }

    const dados = await api(`/analytics/comparativo?meses=${meses.join(",")}${unidade ? "&unidade=" + unidade : ""}`);
    const rows = dados
      .map((d) => {
        const cells = meses
          .map((m) => {
            const v = d.por_mes[m];
            return `<td class="num">${v ? brl(v.receita_total) : "—"}</td>`;
          })
          .join("");
        return `<tr><td>${esc(d.cliente)}</td>${cells}</tr>`;
      })
      .join("");

    el.innerHTML = `
      <div class="table-wrap">
        <table>
          <thead><tr><th>Cliente</th>${meses.map((m) => `<th style="text-align:right">${m}</th>`).join("")}</tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <p class="source-note">receita por cliente (CTe.Total) — unidade: ${unidade ? esc(unidade) : "matriz + filial"}</p>
    `;
  } catch (e) {
    el.innerHTML = errorState(e);
  }
}

// ---------------- desvios ----------------
async function loadDesviosFilters() {
  const anteriorSel = document.getElementById("desvio-mes-anterior");
  const atualSel = document.getElementById("desvio-mes-atual");
  if (!anteriorSel.dataset.loaded) {
    const meses = await populateMonthSelect(anteriorSel);
    await populateMonthSelect(atualSel);
    if (meses.length >= 2) {
      anteriorSel.value = meses[meses.length - 2];
      atualSel.value = meses[meses.length - 1];
    }
    anteriorSel.dataset.loaded = "1";
    document.getElementById("desvio-buscar").addEventListener("click", renderDesvios);
  }
  document.getElementById("desvios-content").innerHTML = emptyState("Escolha os dois meses e clique em “Detectar desvios”.");
}

async function renderDesvios() {
  const el = document.getElementById("desvios-content");
  const mesAnterior = document.getElementById("desvio-mes-anterior").value;
  const mesAtual = document.getElementById("desvio-mes-atual").value;
  const unidade = document.getElementById("desvio-unidade").value;
  el.innerHTML = scanning("Sincronizando dado");
  try {
    const dados = await api(
      `/analytics/desvios?mes_atual=${mesAtual}&mes_anterior=${mesAnterior}${unidade ? "&unidade=" + unidade : ""}`
    );
    if (!dados.length) {
      el.innerHTML = emptyState("Nenhum desvio material encontrado entre esses dois meses.");
      return;
    }
    const rows = dados
      .map(
        (d) => `
      <tr>
        <td>${esc(d.cliente)}</td>
        <td class="num">${brl(d.receita_anterior)}</td>
        <td class="num">${brl(d.receita_atual)}</td>
        <td class="num">${d.variacao_absoluta >= 0 ? "+" : ""}${brl(d.variacao_absoluta)}</td>
        <td class="num">${d.variacao_percentual >= 0 ? "+" : ""}${pct(d.variacao_percentual)}</td>
        <td><span class="pill ${d.tipo === "queda_receita" ? "pill--danger" : "pill--ok"}"><span class="radar-light ${d.tipo === "queda_receita" ? "radar-light--alert" : "radar-light--ok"}"></span>${d.tipo === "queda_receita" ? "queda" : "aumento"}</span></td>
      </tr>`
      )
      .join("");
    el.innerHTML = `
      <div class="table-wrap">
        <table>
          <thead><tr><th>Cliente</th><th style="text-align:right">${mesAnterior}</th><th style="text-align:right">${mesAtual}</th><th style="text-align:right">Variação R$</th><th style="text-align:right">Variação %</th><th>Tipo</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <p class="source-note">ordenado por maior impacto absoluto. Causa provável não é atribuída aqui — é trabalho do Investigador.</p>
    `;
  } catch (e) {
    el.innerHTML = errorState(e);
  }
}

// ---------------- conciliação ----------------
async function loadConciliacao() {
  const el = document.getElementById("conciliacao-content");
  el.innerHTML = scanning("Sincronizando dado");
  try {
    const pendentes = await api("/reconciliation/pending");
    if (!pendentes.length) {
      el.innerHTML = emptyState("Fila vazia — nada pendente de conciliação manual agora.");
      return;
    }
    el.innerHTML = pendentes
      .map((p) => {
        const candidatos = (p.candidatos || [])
          .map(
            (c) => `
          <div class="candidato-row">
            <span>Contrato ${esc(c.contrato_numero)} — ${esc(c.fornecedor_nome || "fornecedor não identificado")} — ${c.valor_total_contrato !== null ? brl(c.valor_total_contrato) : "valor desconhecido"}</span>
            <button data-link="${p.id}" data-contrato="${esc(c.contrato_numero)}" class="resolver-btn">Vincular</button>
          </div>`
          )
          .join("");
        return `
        <div class="recon-card">
          <div class="recon-top">
            <span class="recon-cte"><span class="radar-light radar-light--pending"></span>CT-e ${esc(p.cte_numero)} <span class="badge-unidade">${esc(p.unidade || "?")}</span></span>
            <span class="recon-meta">${esc(p.mes_referencia || "")} · ${esc(p.cliente || "")} · ${p.receita !== null ? brl(p.receita) : ""}</span>
          </div>
          ${candidatos || '<p class="recon-no-candidate"><span class="radar-light radar-light--unknown" style="margin-right:7px"></span>Nenhum candidato automático — buscar manualmente ou marcar sem custo de terceiro.</p>'}
          <button data-link="${p.id}" data-contrato="" class="resolver-btn secondary" style="margin-top:8px">Sem custo de terceiro identificável</button>
        </div>`;
      })
      .join("");

    document.querySelectorAll(".resolver-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        btn.disabled = true;
        try {
          await api(`/reconciliation/${btn.dataset.link}/resolve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ contrato_transporte_numero: btn.dataset.contrato || null, resolved_by: "torre-de-controle-ui" }),
          });
          loadConciliacao();
        } catch (e) {
          alert("Erro ao vincular: " + e.message);
          btn.disabled = false;
        }
      });
    });
  } catch (e) {
    el.innerHTML = errorState(e);
  }
}

// ---------------- rotas ----------------
async function loadRotas() {
  const mesSel = document.getElementById("rotas-mes");
  const unidadeSel = document.getElementById("rotas-unidade");
  if (!mesSel.dataset.loaded) {
    await populateMonthSelect(mesSel);
    mesSel.insertAdjacentHTML("afterbegin", `<option value="">Todo o período</option>`);
    mesSel.value = "";
    mesSel.dataset.loaded = "1";
    mesSel.addEventListener("change", renderRotas);
    unidadeSel.addEventListener("change", renderRotas);
  }
  renderRotas();
}

async function renderRotas() {
  const el = document.getElementById("rotas-content");
  const mes = document.getElementById("rotas-mes").value;
  const unidade = document.getElementById("rotas-unidade").value;
  el.innerHTML = scanning("Sincronizando dado");
  try {
    const qs = new URLSearchParams();
    if (mes) qs.set("mes", mes);
    if (unidade) qs.set("unidade", unidade);
    const rotas = await api(`/analytics/rotas?${qs.toString()}`);
    if (!rotas.length) {
      el.innerHTML = emptyState("Nenhuma rota encontrada neste período/unidade.");
      return;
    }

    const rows = rotas
      .map(
        (r) => `
      <tr>
        <td>${esc(r.origem)} → ${esc(r.destino)}</td>
        <td class="num">${r.qtd_ctes}</td>
        <td class="num">${brl(r.receita_total)}</td>
        <td class="num">${r.viagens_com_custo_alocado ? brl(r.custo_alocado_total) : "—"}</td>
        <td class="num">${margemCell({ viagens_com_custo_alocado: r.viagens_com_custo_alocado, margem_total: r.margem_total })}</td>
      </tr>`
      )
      .join("");

    el.innerHTML = `
      <div class="table-wrap">
        <table>
          <thead><tr><th>Rota</th><th style="text-align:right">CT-e's</th><th style="text-align:right">Receita</th><th style="text-align:right">Custo alocado</th><th style="text-align:right">Margem</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <p class="source-note">rota = local de coleta → local de entrega do CT-e · mês: ${mes ? esc(mes) : "todo o período"} · unidade: ${unidade ? esc(unidade) : "matriz + filial"}</p>
    `;
  } catch (e) {
    el.innerHTML = errorState(e);
  }
}

// ---------------- frota própria ----------------
async function loadFrota() {
  const el = document.getElementById("frota-content");
  el.innerHTML = scanning("Sincronizando dado");
  try {
    const dados = await api("/analytics/frota");
    if (!dados.veiculos.length) {
      el.innerHTML = emptyState("Nenhum veículo de frota própria encontrado no dado importado.");
      return;
    }

    const receitaTotal = dados.veiculos.reduce((s, v) => s + v.receita_total, 0);
    const viagensTotal = dados.veiculos.reduce((s, v) => s + v.viagens, 0);

    const rows = dados.veiculos
      .map(
        (v) => `
      <tr>
        <td><span class="mono">${esc(v.placa)}</span></td>
        <td>${v.unidades.map((u) => `<span class="badge-unidade">${esc(u)}</span>`).join(" ")}</td>
        <td class="num">${v.viagens}</td>
        <td class="num">${brl(v.receita_total)}</td>
        <td class="num">${custoIndeterminavelCell()}</td>
        <td class="num">${custoIndeterminavelCell()}</td>
        <td class="num">${custoIndeterminavelCell()}</td>
      </tr>`
      )
      .join("");

    const agregados = dados.custos_operacionais_agregados
      .map(
        (c) => `
      <tr>
        <td>${c.categoria === "combustivel" ? "Combustível" : "Manutenção de frota"}</td>
        <td><span class="badge-unidade">${esc(c.unidade || "?")}</span></td>
        <td class="num">${c.linhas}</td>
        <td class="num">${brl(c.valor_total)}</td>
      </tr>`
      )
      .join("");

    el.innerHTML = `
      <div class="kpi-row">
        <div class="kpi-card"><div class="kpi-label">Veículos próprios</div><div class="kpi-value">${dados.veiculos.length}</div></div>
        <div class="kpi-card"><div class="kpi-label">Viagens</div><div class="kpi-value">${viagensTotal}</div></div>
        <div class="kpi-card"><div class="kpi-label">Receita total</div><div class="kpi-value gold">${brl(receitaTotal)}</div></div>
        <div class="kpi-card"><div class="kpi-label">Custo direto por veículo</div><div class="kpi-value warn">não determinável</div></div>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Placa</th><th>Unidade</th><th style="text-align:right">Viagens</th><th style="text-align:right">Receita</th><th style="text-align:right">Combustível</th><th style="text-align:right">Manutenção</th><th style="text-align:right">Pedágio</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <p class="source-note">receita: CTe.veiculo_placa (real) · custo direto por veículo: aguardando relatório com chave de placa — ver nota acima</p>

      <div class="page-header" style="margin-top:32px"><div class="page-title" style="font-size:1rem">Custo operacional real — só agregado, nunca por placa</div></div>
      <p class="page-sub">O que existe hoje em Contas a Pagar, sem chave de veículo. Mostrado por transparência, não usado no cálculo por placa acima.</p>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Categoria</th><th>Unidade</th><th style="text-align:right">Lançamentos</th><th style="text-align:right">Valor</th></tr></thead>
          <tbody>${agregados}</tbody>
        </table>
      </div>
    `;
  } catch (e) {
    el.innerHTML = errorState(e);
  }
}

function custoIndeterminavelCell() {
  return `<span class="margem-cell"><span class="radar-light radar-light--unknown"></span><span class="margem-indeterminavel">não determinável</span></span>`;
}

// ---------------- terceiros ----------------
async function loadTerceiros() {
  const mesSel = document.getElementById("terceiros-mes");
  const unidadeSel = document.getElementById("terceiros-unidade");
  if (!mesSel.dataset.loaded) {
    await populateMonthSelect(mesSel);
    mesSel.insertAdjacentHTML("afterbegin", `<option value="">Todo o período</option>`);
    mesSel.value = "";
    mesSel.dataset.loaded = "1";
    mesSel.addEventListener("change", renderTerceiros);
    unidadeSel.addEventListener("change", renderTerceiros);
  }
  renderTerceiros();
}

async function renderTerceiros() {
  const el = document.getElementById("terceiros-content");
  const mes = document.getElementById("terceiros-mes").value;
  const unidade = document.getElementById("terceiros-unidade").value;
  el.innerHTML = scanning("Sincronizando dado");
  try {
    const qs = new URLSearchParams();
    if (mes) qs.set("mes", mes);
    if (unidade) qs.set("unidade", unidade);
    const terceiros = await api(`/analytics/terceiros?${qs.toString()}`);
    if (!terceiros.length) {
      el.innerHTML = emptyState("Nenhum transportador terceiro encontrado neste período/unidade.");
      return;
    }

    const receitaTotal = terceiros.reduce((s, t) => s + t.receita_total, 0);

    const rows = terceiros
      .map(
        (t) => `
      <tr>
        <td>${esc(t.proprietario)}</td>
        <td class="num">${t.qtd_ctes}</td>
        <td class="num">${brl(t.receita_total)}</td>
        <td class="num">${t.viagens_com_custo_alocado ? brl(t.custo_alocado_total) : "—"}</td>
        <td class="num">${margemCell({ viagens_com_custo_alocado: t.viagens_com_custo_alocado, margem_total: t.margem_total })}</td>
      </tr>`
      )
      .join("");

    el.innerHTML = `
      <div class="kpi-row">
        <div class="kpi-card"><div class="kpi-label">Transportadores terceiros</div><div class="kpi-value">${terceiros.length}</div></div>
        <div class="kpi-card"><div class="kpi-label">Receita operada por terceiros</div><div class="kpi-value gold">${brl(receitaTotal)}</div></div>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Transportador / Proprietário</th><th style="text-align:right">CT-e's</th><th style="text-align:right">Receita</th><th style="text-align:right">Custo (frete terceiro)</th><th style="text-align:right">Margem</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <p class="source-note">mês: ${mes ? esc(mes) : "todo o período"} · unidade: ${unidade ? esc(unidade) : "matriz + filial"} · exclui frota própria</p>
    `;
  } catch (e) {
    el.innerHTML = errorState(e);
  }
}

// ---------------- importar ----------------
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const uploadLog = document.getElementById("upload-log");

dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("dragover"); });
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  if (e.dataTransfer.files.length) uploadFiles(e.dataTransfer.files);
});
fileInput.addEventListener("change", () => {
  if (fileInput.files.length) uploadFiles(fileInput.files);
});

async function uploadFiles(fileList) {
  const form = new FormData();
  for (const f of fileList) form.append("files", f);

  uploadLog.textContent = `Enviando ${fileList.length} arquivo(s)…`;
  try {
    const res = await fetch("/import/upload", { method: "POST", body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(JSON.stringify(data));

    let out = data.arquivos
      .map((a) => {
        if (a.erro) return `✕ ${a.arquivo}: ${a.erro}`;
        return `✓ ${a.arquivo}  [${a.tipo_detectado} / ${a.unidade_detectada || "?"}]  importados=${a.importados}  já_importados=${a.ja_importados_antes}  rejeitados=${a.rejeitados}`;
      })
      .join("\n");
    out += `\n\nCost Allocation Engine — contratos: ${data.contratos_transporte_construidos}\n${JSON.stringify(data.camada2_cost_allocation, null, 2)}`;
    uploadLog.textContent = out;
  } catch (e) {
    uploadLog.textContent = "Erro na importação: " + e.message;
  }
}

// ---------------- helpers ----------------

// Margem: nunca um R$0 mudo. Confirmada = luz verde + valor. Não determinável
// (custo de terceiro ainda sem alocação confirmada) = luz âmbar oca + rótulo
// explícito — mesmo vocabulário de "pendente" usado na fila de conciliação.
function margemCell(d) {
  if (d.viagens_com_custo_alocado) {
    return `<span class="margem-cell"><span class="radar-light radar-light--ok"></span>${brl(d.margem_total)}</span>`;
  }
  return `<span class="margem-cell"><span class="radar-light radar-light--pending"></span><span class="margem-indeterminavel">não determinável</span></span>`;
}

function scanning(label) {
  return `<div class="scanning"><span class="radar-light radar-light--pending"></span>${esc(label)}…</div>`;
}

function emptyState(title, sub) {
  return `<div class="empty-state">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.3"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1" fill="currentColor" stroke="none"/><path d="M12 3 L12 6 M12 18 L12 21 M3 12 L6 12 M18 12 L21 12"/></svg>
    <div>${esc(title)}</div>
    ${sub ? `<div style="font-size:0.82rem;margin-top:4px;color:var(--ink-tertiary)">${esc(sub)}</div>` : ""}
  </div>`;
}
function errorState(e) {
  return `<div class="empty-state">
    <span class="radar-light radar-light--alert" style="width:12px;height:12px;margin-bottom:14px"></span>
    <div style="color:var(--status-alert)">Erro ao carregar: ${esc(e.message)}</div>
  </div>`;
}

// carga inicial
loadVisaoGeral();
