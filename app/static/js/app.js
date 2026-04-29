/* =============================================================================
   SISGEU – Sistema de Gestão Econômica Universitária
   app.js · Lógica de Interface e Gráficos
   Versão: 1.0 · Engenharia de Software 2025
   =============================================================================

   ÍNDICE
   ──────────────────────────────────────────────────────────────────────────────
   1.  AUTENTICAÇÃO
   2.  NAVEGAÇÃO ENTRE PÁGINAS
   3.  MODAIS
   4.  FORMULÁRIOS
       4.1  Seleção de Tipo de Lançamento (Despesa / Receita)
       4.2  Salvamento de Lançamento
       4.3  Salvamento de Meta
   5.  SELETOR DE MÊS (Pills)
   6.  TOAST (Notificações temporárias)
   7.  GRÁFICOS (Chart.js)
       7.1  Configurações padrão compartilhadas
       7.2  Gráfico de Barras – Dashboard (Receitas × Despesas)
       7.3  Gráfico de Rosca – Gastos por Categoria (Dashboard)
       7.4  Gráfico de Rosca – Distribuição do Orçamento
       7.5  Gráfico de Linha – Evolução Mensal (Relatórios)
       7.6  Inicialização centralizada dos gráficos
   ============================================================================= */


/* =============================================================================
   1. AUTENTICAÇÃO
   ============================================================================= */


/* =============================================================================
   2. NAVEGAÇÃO ENTRE PÁGINAS
   ============================================================================= */

/**
 * Alterna entre as páginas da aplicação (SPA – Single Page Application).
 *
 * @param {string} page - Identificador da página (ex.: 'dashboard', 'metas')
 * @param {HTMLElement} el - Elemento de navegação clicado na sidebar
 */
function nav(page, el) {
  // Remove estado ativo de todas as páginas e itens de menu
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  // Ativa a página e o item de menu correspondentes
  document.getElementById('pg-' + page).classList.add('active');
  if (el) el.classList.add('active');

  // Inicializa gráficos específicos de páginas que não estavam visíveis
  if (page === 'orcamento')  setTimeout(initOrcChart,  50);
  if (page === 'relatorios') setTimeout(initLineChart, 50);
}


/* =============================================================================
   3. MODAIS
   ============================================================================= */

/**
 * Abre um modal pelo seu ID.
 * @param {string} id - ID do elemento modal-overlay
 */
function openModal(id) {
  document.getElementById(id).classList.add('open');
}

/**
 * Fecha um modal pelo seu ID.
 * @param {string} id - ID do elemento modal-overlay
 */
function closeModal(id) {
  document.getElementById(id).classList.remove('open');
}

// Fecha o modal ao clicar no backdrop (área escura fora do modal)
document.querySelectorAll('.modal-overlay').forEach(modal => {
  modal.addEventListener('click', e => {
    if (e.target === modal) modal.classList.remove('open');
  });
});


/* =============================================================================
   4. FORMULÁRIOS
   ============================================================================= */

/* 4.1 Seleção de Tipo de Lançamento */

/**
 * Alterna visualmente o tipo de lançamento entre Despesa e Receita.
 * Atualiza as classes dos botões de seleção conforme o tipo escolhido.
 *
 * @param {string} tipo - 'despesa' ou 'receita'
 */
function setTipo(tipo) {
  const btnDespesa = document.getElementById('btn-despesa');
  const btnReceita = document.getElementById('btn-receita');

  btnDespesa.className = 'btn ' + (tipo === 'despesa' ? 'btn-danger'    : 'btn-secondary');
  btnReceita.className = 'btn ' + (tipo === 'receita' ? 'btn-primary'   : 'btn-secondary');
}

/* 4.2 Salvamento de Lançamento */

/**
 * Processa o salvamento de um novo lançamento financeiro.
 * (Protótipo: apenas fecha o modal e exibe confirmação via toast.)
 */
function saveTransaction() {
  closeModal('modal-add');
  showToast('✅ Lançamento salvo com sucesso!');
}

/* 4.3 Salvamento de Meta */

/**
 * Processa a criação de uma nova meta financeira.
 * (Protótipo: apenas fecha o modal e exibe confirmação via toast.)
 */
function saveMeta() {
  closeModal('modal-meta');
  showToast('🎯 Meta criada com sucesso!');
}


/* =============================================================================
   5. SELETOR DE MÊS (Pills)
   ============================================================================= */

/**
 * Seleciona um mês no filtro de período da tela de Lançamentos.
 * Remove o estado ativo dos demais pills e ativa o clicado.
 *
 * @param {HTMLElement} el - Elemento pill clicado
 */
function selectPill(el) {
  document.querySelectorAll('.month-pill').forEach(p => p.classList.remove('active'));
  el.classList.add('active');
  showToast('📅 Filtrando por ' + el.textContent);
}


/* =============================================================================
   6. TOAST (Notificações temporárias)
   ============================================================================= */

/**
 * Exibe uma notificação temporária (toast) na parte inferior da tela.
 * A notificação desaparece automaticamente após 3 segundos.
 *
 * @param {string} msg - Mensagem a ser exibida (suporta emojis)
 */
function showToast(msg) {
  const toast = document.getElementById('toast');
  document.getElementById('toast-msg').textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 3000);
}


/* =============================================================================
   7. GRÁFICOS (Chart.js)
   ============================================================================= */

/* 7.1 Configurações padrão compartilhadas */

/**
 * Objeto de configurações visuais padrão do Chart.js,
 * alinhado ao tema escuro do SISGEU.
 */
const CHART_DEFAULTS = {
  tickColor:  '#656d76',   /* Cor dos rótulos dos eixos       */
  labelColor: '#8d96a0',   /* Cor dos itens de legenda        */
  gridColor:  'rgba(255, 255, 255, 0.04)',  /* Linhas de grade sutis */
  fontSize:   9,
  legendSize: 10,
};

/* 7.2 Gráfico de Barras – Dashboard (Receitas × Despesas) */

/**
 * Inicializa o gráfico de barras agrupadas na tela de Dashboard.
 * Compara receitas e despesas dos últimos 6 meses.
 * Utiliza a propriedade _chartInst para evitar instâncias duplicadas.
 */
function initBarDashChart() {
  const canvas = document.getElementById('chartBarDash');
  if (!canvas || canvas._chartInst) return;

  canvas._chartInst = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: ['Out/24', 'Nov/24', 'Dez/24', 'Jan/25', 'Fev/25', 'Mar/25'],
      datasets: [
        {
          label: 'Receitas',
          data: [1450, 1650, 2100, 1450, 1850, 1850],
          backgroundColor: 'rgba(63, 185, 80, 0.7)',
          borderRadius: 4,
        },
        {
          label: 'Despesas',
          data: [1520, 1400, 1890, 1230, 1046, 1003],
          backgroundColor: 'rgba(248, 81, 73, 0.6)',
          borderRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: {
            color: CHART_DEFAULTS.labelColor,
            font: { size: CHART_DEFAULTS.legendSize },
          },
        },
      },
      scales: {
        x: {
          ticks: { color: CHART_DEFAULTS.tickColor, font: { size: CHART_DEFAULTS.fontSize } },
          grid:  { color: CHART_DEFAULTS.gridColor },
        },
        y: {
          ticks: {
            color: CHART_DEFAULTS.tickColor,
            font:  { size: CHART_DEFAULTS.fontSize },
            callback: v => 'R$' + v,
          },
          grid: { color: CHART_DEFAULTS.gridColor },
        },
      },
    },
  });
}

/* 7.3 Gráfico de Rosca – Gastos por Categoria (Dashboard) */

/**
 * Inicializa o gráfico de rosca com a distribuição de gastos
 * por categoria no mês atual, exibido no Dashboard.
 */
function initDoughnutDashChart() {
  const canvas = document.getElementById('chartDoughnut');
  if (!canvas || canvas._chartInst) return;

  canvas._chartInst = new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: ['Moradia', 'Alimentação', 'Lazer', 'Educação', 'Transporte', 'Outros'],
      datasets: [
        {
          data: [300, 280, 190, 89, 75, 69],
          backgroundColor: [
            '#58a6ff',  /* Moradia      – azul   */
            '#d29922',  /* Alimentação  – amarelo */
            '#bc8cff',  /* Lazer        – roxo   */
            '#3fb950',  /* Educação     – verde  */
            '#e3b341',  /* Transporte   – laranja */
            '#f85149',  /* Outros       – vermelho */
          ],
          borderWidth: 0,
          hoverOffset: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '65%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color:    CHART_DEFAULTS.labelColor,
            font:     { size: 9 },
            padding:  8,
            boxWidth: 10,
          },
        },
      },
    },
  });
}

/* 7.4 Gráfico de Rosca – Distribuição do Orçamento */

/**
 * Inicializa (ou reinicializa) o gráfico de rosca na tela de Orçamento,
 * mostrando a proporção dos limites definidos por categoria.
 * Destrói instância anterior para evitar duplicatas ao navegar.
 */
function initOrcChart() {
  const canvas = document.getElementById('chartOrcamento');
  if (!canvas) return;

  // Destrói instância anterior se existir
  if (canvas._chartInst) canvas._chartInst.destroy();

  canvas._chartInst = new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: ['Moradia', 'Alimentação', 'Lazer', 'Educação', 'Transporte'],
      datasets: [
        {
          data: [600, 350, 200, 200, 150],
          backgroundColor: [
            '#58a6ff',  /* Moradia      */
            '#d29922',  /* Alimentação  */
            '#f85149',  /* Lazer        */
            '#3fb950',  /* Educação     */
            '#e3b341',  /* Transporte   */
          ],
          borderWidth: 0,
          hoverOffset: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '60%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color:    CHART_DEFAULTS.labelColor,
            font:     { size: 9 },
            padding:  8,
            boxWidth: 10,
          },
        },
      },
    },
  });
}

/* 7.5 Gráfico de Linha – Evolução Mensal (Relatórios) */

/**
 * Inicializa (ou reinicializa) o gráfico de linha na tela de Relatórios,
 * exibindo a evolução de receitas, despesas e saldo nos últimos 6 meses.
 */
function initLineChart() {
  const canvas = document.getElementById('chartLine');
  if (!canvas) return;

  if (canvas._chartInst) canvas._chartInst.destroy();

  canvas._chartInst = new Chart(canvas, {
    type: 'line',
    data: {
      labels: ['Out/24', 'Nov/24', 'Dez/24', 'Jan/25', 'Fev/25', 'Mar/25'],
      datasets: [
        {
          label: 'Receitas',
          data: [1450, 1650, 2100, 1450, 1850, 1850],
          borderColor:     '#3fb950',
          backgroundColor: 'rgba(63, 185, 80, 0.1)',
          tension:     0.4,
          fill:        true,
          pointRadius: 4,
        },
        {
          label: 'Despesas',
          data: [1520, 1400, 1890, 1230, 1046, 1003],
          borderColor:     '#f85149',
          backgroundColor: 'rgba(248, 81, 73, 0.1)',
          tension:     0.4,
          fill:        true,
          pointRadius: 4,
        },
        {
          label: 'Saldo',
          data: [-70, 250, 210, 220, 804, 847],
          borderColor:     '#58a6ff',
          backgroundColor: 'rgba(88, 166, 255, 0.05)',
          tension:      0.4,
          fill:         false,
          pointRadius:  4,
          borderDash:   [4, 3],  /* Linha tracejada para diferenciar do saldo */
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: {
            color: CHART_DEFAULTS.labelColor,
            font:  { size: CHART_DEFAULTS.legendSize },
          },
        },
      },
      scales: {
        x: {
          ticks: { color: CHART_DEFAULTS.tickColor, font: { size: CHART_DEFAULTS.fontSize } },
          grid:  { color: CHART_DEFAULTS.gridColor },
        },
        y: {
          ticks: {
            color: CHART_DEFAULTS.tickColor,
            font:  { size: CHART_DEFAULTS.fontSize },
            callback: v => 'R$' + v,
          },
          grid: { color: CHART_DEFAULTS.gridColor },
        },
      },
    },
  });
}

/* 7.6 Inicialização centralizada dos gráficos */

/**
 * Ponto de entrada para todos os gráficos do dashboard.
 * Chamado logo após o login do usuário.
 * Gráficos de outras telas (Orçamento, Relatórios) são inicializados
 * sob demanda na função nav().
 */
function initCharts() {
  initBarDashChart();
  initDoughnutDashChart();
  initOrcChart();
  initLineChart();
}


/* =============================================================================
   8. INICIALIZAÇÃO POR PÁGINA (Multi-page Django)
   ============================================================================= */

document.addEventListener('DOMContentLoaded', function () {

  // Preenche data atual no subtítulo do dashboard
  const dashSub = document.getElementById('dashboard-sub');
  if (dashSub) {
    const agora = new Date();
    const meses = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                   'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
    dashSub.textContent = meses[agora.getMonth()] + ' ' + agora.getFullYear() + ' · Atualizado agora';
  }

  // Preenche data de hoje nos inputs de data dos modais
  const inputData = document.getElementById('input-data');
  if (inputData) {
    const hoje = new Date().toISOString().split('T')[0];
    inputData.value = hoje;
  }

  // Preenche mês atual no input de prazo das metas
  const inputPrazo = document.getElementById('input-prazo');
  if (inputPrazo) {
    const agora = new Date();
    const ano = agora.getFullYear();
    const mes = String(agora.getMonth() + 1).padStart(2, '0');
    inputPrazo.value = ano + '-' + mes;
  }

  // Inicializa gráficos de acordo com a página atual
  if (document.getElementById('chartBarDash'))  { initBarDashChart();     }
  if (document.getElementById('chartDoughnut')) { initDoughnutDashChart();}
  if (document.getElementById('chartOrcamento')){ initOrcChart();         }
  if (document.getElementById('chartLine'))     { initLineChart();        }

  // Login e cadastro são tratados pelo Django (POST de formulário).
  // Não há interceptação de clique aqui.
});
