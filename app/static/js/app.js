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
function getCSRFToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (meta) return meta.content;

  const name = 'csrftoken=';
  const cookies = document.cookie.split(';');
  for (let cookie of cookies) {
    cookie = cookie.trim();
    if (cookie.startsWith(name)) return cookie.substring(name.length);
  }
  return null;
}

function openTransactionForm(type) {
  closeModal('modal-add');
  if (type === 'income') {
    openModal('modal-add-income');
  } else {
    openModal('modal-add-expense');
  }
}

/* 4.2 Salvamento de Lançamento */

/**
 * Processa o salvamento de um novo lançamento financeiro.
 */
function saveTransaction(type) {
  const isIncome = type === 'income';
  const description = document.getElementById(isIncome ? 'input-description-income' : 'input-description-expense').value.trim();
  const amount = document.getElementById(isIncome ? 'input-amount-income' : 'input-amount-expense').value;
  const date = document.getElementById(isIncome ? 'input-date-income' : 'input-date-expense').value;
  const csrf = getCSRFToken();

  // Para despesas, categoria é obrigatória
  if (!isIncome) {
    const category = document.getElementById('input-category-expense').value;
    if (!description || !amount || !date || !category) {
      showToast('⚠️ Preencha todos os campos antes de salvar.');
      return;
    }
  } else {
    // Para receitas, descrição, valor, data e fonte
    const src = document.getElementById('input-income-source').value;
    if (!description || !amount || !date || !src) {
      showToast('⚠️ Preencha todos os campos antes de salvar.');
      return;
    }
  }

  const payload = {
    type,
    description,
    amount,
    date,
  };

  // Adiciona categoria/fonte conforme o tipo
  if (!isIncome) {
    payload.category = document.getElementById('input-category-expense').value;
    payload.extra = document.getElementById('input-payment-method').value;
  } else {
    // Para receita, deixa em branco ou usa a primeira categoria
    payload.category = ''; // Backend vai usar padrão
    payload.extra = document.getElementById('input-income-source').value;
  }

  fetch('/add-transaction/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrf,
    },
    body: JSON.stringify(payload),
  }).then(async response => {
    if (response.ok) {
      closeModal(type === 'income' ? 'modal-add-income' : 'modal-add-expense');
      showToast('✅ Lançamento salvo com sucesso!');
      setTimeout(() => location.reload(), 1000);
    } else {
      const payload = await response.json().catch(() => null);
      showToast(payload?.error || '❌ Erro ao salvar.');
    }
  }).catch(error => {
    console.error('saveTransaction error:', error);
    showToast('❌ Erro de conexão.');
  });
}

function openEditTransaction(id, type, description, amount, dateStr, categoryIdOrIncomeSource) {
  document.getElementById('edit-tx-id').value = id;
  document.getElementById('edit-tx-type').value = type;
  document.getElementById('edit-tx-description').value = description;
  document.getElementById('edit-tx-amount').value = amount;
  document.getElementById('edit-tx-date').value = dateStr;
  const wrapCat = document.getElementById('edit-tx-wrap-category');
  const wrapSrc = document.getElementById('edit-tx-wrap-income-source');
  const cat = document.getElementById('edit-tx-category');
  const src = document.getElementById('edit-tx-income-source');
  if (type === 'income') {
    if (wrapCat) wrapCat.style.display = 'none';
    if (wrapSrc) wrapSrc.style.display = 'block';
    const v = categoryIdOrIncomeSource || 'Outros';
    if (src) src.value = v;
  } else {
    if (wrapCat) wrapCat.style.display = 'block';
    if (wrapSrc) wrapSrc.style.display = 'none';
    if (cat) cat.value = String(categoryIdOrIncomeSource);
  }
  const title = document.getElementById('edit-tx-title');
  if (title) title.textContent = type === 'income' ? 'Editar receita' : 'Editar despesa';
  openModal('modal-edit-transaction');
}

function updateTransaction() {
  const id = document.getElementById('edit-tx-id').value;
  const type = document.getElementById('edit-tx-type').value;
  const description = document.getElementById('edit-tx-description').value.trim();
  const amount = document.getElementById('edit-tx-amount').value;
  const date = document.getElementById('edit-tx-date').value;
  const csrf = getCSRFToken();

  if (!description || !amount || !date) {
    showToast('⚠️ Preencha todos os campos antes de salvar.');
    return;
  }

  const payload = { type, description, amount, date };
  if (type === 'income') {
    const incomeSource = document.getElementById('edit-tx-income-source').value;
    if (!incomeSource) {
      showToast('⚠️ Selecione a fonte de receita.');
      return;
    }
    payload.income_source = incomeSource;
  } else {
    const category = document.getElementById('edit-tx-category').value;
    if (!category) {
      showToast('⚠️ Selecione uma categoria.');
      return;
    }
    payload.category = category;
  }

  fetch(`/update-transaction/${id}/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrf,
    },
    body: JSON.stringify(payload),
  }).then(async response => {
    if (response.ok) {
      closeModal('modal-edit-transaction');
      showToast('✅ Lançamento atualizado!');
      setTimeout(() => location.reload(), 800);
    } else {
      const payloadErr = await response.json().catch(() => null);
      showToast(payloadErr?.error || '❌ Erro ao atualizar.');
    }
  }).catch(error => {
    console.error('updateTransaction error:', error);
    showToast('❌ Erro de conexão.');
  });
}

function openDeleteTransaction(id, description) {
  document.getElementById('delete-tx-id').value = id;
  document.getElementById('delete-tx-description').textContent = description;
  openModal('modal-delete-transaction');
}

function confirmDeleteTransaction() {
  const id = document.getElementById('delete-tx-id').value;
  const csrf = getCSRFToken();
  fetch(`/delete-transaction/${id}/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrf,
    },
    body: '{}',
  }).then(async response => {
    if (response.ok) {
      closeModal('modal-delete-transaction');
      showToast('✅ Lançamento excluído.');
      setTimeout(() => location.reload(), 800);
    } else {
      const payload = await response.json().catch(() => null);
      showToast(payload?.error || '❌ Erro ao excluir.');
    }
  }).catch(error => {
    console.error('confirmDeleteTransaction error:', error);
    showToast('❌ Erro de conexão.');
  });
}

function parseRecurringEditorData() {
  const el = document.getElementById('recurring-data');
  if (!el || !el.textContent) return [];
  try {
    return JSON.parse(el.textContent);
  } catch (e) {
    return [];
  }
}

function ensureRecurringMonthlyDaySelect() {
  const sel = document.getElementById('input-rec-due-monthly');
  if (!sel || sel.options.length >= 31) return;
  sel.innerHTML = '';
  for (let d = 1; d <= 31; d++) {
    const o = document.createElement('option');
    o.value = String(d);
    o.textContent = String(d);
    sel.appendChild(o);
  }
}

function syncRecurringDueVisibility() {
  const freqEl = document.getElementById('input-rec-frequency');
  const wrapM = document.getElementById('wrap-rec-due-monthly');
  const wrapW = document.getElementById('wrap-rec-due-weekly');
  if (!freqEl || !wrapM || !wrapW) return;
  const freq = freqEl.value;
  wrapM.style.display = freq === 'monthly' ? 'block' : 'none';
  wrapW.style.display = freq === 'weekly' ? 'block' : 'none';
}

function syncRecurringTypeVisibility() {
  const tEl = document.getElementById('input-rec-type');
  const wrap = document.getElementById('wrap-rec-income-source');
  if (!tEl || !wrap) return;
  wrap.style.display = tEl.value === 'income' ? 'block' : 'none';
}

function openRecurringModalCreate() {
  ensureRecurringMonthlyDaySelect();
  document.getElementById('input-rec-id').value = '';
  document.getElementById('input-rec-description').value = '';
  document.getElementById('input-rec-amount').value = '';
  document.getElementById('input-rec-type').value = 'expense';
  const cat = document.getElementById('input-rec-category');
  if (cat && cat.options.length) cat.selectedIndex = 0;
  document.getElementById('input-rec-income-source').value = 'Outros';
  document.getElementById('input-rec-frequency').value = 'monthly';
  document.getElementById('input-rec-due-monthly').value = '10';
  document.getElementById('input-rec-due-weekly').value = '0';
  document.getElementById('input-rec-start').value = new Date().toISOString().split('T')[0];
  document.getElementById('input-rec-active').checked = true;
  const titleEl = document.getElementById('modal-recurring-title');
  if (titleEl) titleEl.textContent = 'Nova recorrência';
  syncRecurringDueVisibility();
  syncRecurringTypeVisibility();
  openModal('modal-recurring');
}

function openRecurringModalEdit(id) {
  ensureRecurringMonthlyDaySelect();
  const list = parseRecurringEditorData();
  const r = list.find(x => x.id === id);
  if (!r) {
    showToast('❌ Recorrência não encontrada. Atualize a página.');
    return;
  }
  document.getElementById('input-rec-id').value = String(r.id);
  document.getElementById('input-rec-description').value = r.description;
  document.getElementById('input-rec-amount').value = r.amount;
  document.getElementById('input-rec-type').value = r.type;
  document.getElementById('input-rec-category').value = String(r.category_id);
  document.getElementById('input-rec-income-source').value = r.income_source || 'Outros';
  document.getElementById('input-rec-frequency').value = r.frequency;
  if (r.frequency === 'monthly') {
    document.getElementById('input-rec-due-monthly').value = String(r.due_day);
  } else {
    document.getElementById('input-rec-due-weekly').value = String(r.due_day);
  }
  document.getElementById('input-rec-start').value = r.start_date;
  document.getElementById('input-rec-active').checked = !!r.is_active;
  const titleEl = document.getElementById('modal-recurring-title');
  if (titleEl) titleEl.textContent = 'Editar recorrência';
  syncRecurringDueVisibility();
  syncRecurringTypeVisibility();
  openModal('modal-recurring');
}

function currentRecurringDueDay() {
  const freq = document.getElementById('input-rec-frequency').value;
  if (freq === 'monthly') {
    return parseInt(document.getElementById('input-rec-due-monthly').value, 10);
  }
  return parseInt(document.getElementById('input-rec-due-weekly').value, 10);
}

async function saveRecurring() {
  const idVal = document.getElementById('input-rec-id').value.trim();
  const payload = {
    description: document.getElementById('input-rec-description').value.trim(),
    amount: document.getElementById('input-rec-amount').value,
    type: document.getElementById('input-rec-type').value,
    category_id: parseInt(document.getElementById('input-rec-category').value, 10),
    frequency: document.getElementById('input-rec-frequency').value,
    due_day: currentRecurringDueDay(),
    start_date: document.getElementById('input-rec-start').value,
    is_active: document.getElementById('input-rec-active').checked,
  };
  if (idVal) payload.id = parseInt(idVal, 10);
  if (payload.type === 'income') {
    payload.income_source = document.getElementById('input-rec-income-source').value;
  }

  if (!payload.description || !payload.amount || !payload.start_date) {
    showToast('⚠️ Preencha descrição, valor e data inicial.');
    return;
  }

  const csrf = getCSRFToken();
  const response = await fetch('/recurring/save/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (response.ok && data.success) {
    closeModal('modal-recurring');
    showToast('✅ Recorrência salva!');
    setTimeout(() => location.reload(), 600);
  } else {
    showToast('❌ ' + (data.error || 'Erro ao salvar.'));
  }
}

function openDeleteRecurring(id, description) {
  document.getElementById('delete-rec-id').value = id;
  document.getElementById('delete-rec-description').textContent = description;
  openModal('modal-delete-recurring');
}

async function confirmDeleteRecurring() {
  const id = document.getElementById('delete-rec-id').value;
  const csrf = getCSRFToken();
  const response = await fetch(`/recurring/delete/${id}/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
    body: '{}',
  });
  const data = await response.json().catch(() => ({}));
  if (response.ok && data.success) {
    closeModal('modal-delete-recurring');
    showToast('✅ Recorrência excluída.');
    setTimeout(() => location.reload(), 600);
  } else {
    showToast('❌ ' + (data.error || 'Erro ao excluir.'));
  }
}

/* 4.3 Salvamento de Meta */

/**
 * Processa a criação de uma nova meta financeira.
 * (Protótipo: apenas fecha o modal e exibe confirmação via toast.)
 */
function saveMeta() {
  const name = document.getElementById('input-meta-name').value.trim();
  const target = document.getElementById('input-meta-target').value;
  const deadlineMonth = document.getElementById('input-prazo').value;
  const icon = document.getElementById('input-meta-icon').value;
  const csrf = getCSRFToken();

  if (!name || !target) {
    showToast('⚠️ Nome e valor alvo são obrigatórios.');
    return;
  }

  const deadline = deadlineMonth ? `${deadlineMonth}-01` : '';

  fetch('/save-goal/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrf,
    },
    body: JSON.stringify({
      name,
      target_amount: target,
      deadline,
      icon,
    }),
  }).then(async response => {
    if (response.ok) {
      closeModal('modal-meta');
      showToast('🎯 Meta criada com sucesso!');
      setTimeout(() => location.reload(), 1000);
    } else {
      const payload = await response.json().catch(() => null);
      showToast(payload?.error || '❌ Erro ao salvar a meta.');
    }
  }).catch(error => {
    console.error('saveMeta error:', error);
    showToast('❌ Erro de conexão.');
  });
}

/* 4.3.1 Editar Meta */

/**
 * Abre o modal de edição para uma meta específica.
 */
function openEditMetaModal(goalId, name, target, deadline, icon) {
  document.getElementById('edit-meta-id').value = goalId;
  document.getElementById('edit-meta-name').value = name;
  document.getElementById('edit-meta-target').value = target;
  document.getElementById('edit-meta-prazo').value = deadline;
  document.getElementById('edit-meta-icon').value = icon;
  openModal('modal-edit-meta');
}

/**
 * Processa a atualização de uma meta financeira.
 */
function updateMeta() {
  const id = document.getElementById('edit-meta-id').value;
  const name = document.getElementById('edit-meta-name').value.trim();
  const target = document.getElementById('edit-meta-target').value;
  const deadlineMonth = document.getElementById('edit-meta-prazo').value;
  const icon = document.getElementById('edit-meta-icon').value;
  const csrf = getCSRFToken();

  if (!name || !target) {
    showToast('⚠️ Nome e valor alvo são obrigatórios.');
    return;
  }

  const deadline = deadlineMonth ? `${deadlineMonth}-01` : '';

  fetch(`/update-goal/${id}/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrf,
    },
    body: JSON.stringify({
      name,
      target_amount: target,
      deadline,
      icon,
    }),
  }).then(async response => {
    if (response.ok) {
      closeModal('modal-edit-meta');
      showToast('🎯 Meta atualizada com sucesso!');
      setTimeout(() => location.reload(), 1000);
    } else {
      const payload = await response.json().catch(() => null);
      showToast(payload?.error || '❌ Erro ao atualizar a meta.');
    }
  }).catch(error => {
    console.error('updateMeta error:', error);
    showToast('❌ Erro de conexão.');
  });
}

/* 4.3.2 Excluir Meta */

/**
 * Abre o modal de confirmação de exclusão para uma meta específica.
 */
function openDeleteMetaModal(goalId, name) {
  document.getElementById('delete-meta-id').value = goalId;
  document.getElementById('delete-meta-name').textContent = name;
  openModal('modal-delete-meta');
}

/**
 * Confirma e processa a exclusão de uma meta financeira.
 */
function confirmDeleteMeta() {
  const id = document.getElementById('delete-meta-id').value;
  const csrf = getCSRFToken();

  fetch(`/delete-goal/${id}/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrf,
    },
  }).then(async response => {
    if (response.ok) {
      closeModal('modal-delete-meta');
      showToast('🗑️ Meta excluída com sucesso!');
      setTimeout(() => location.reload(), 1000);
    } else {
      const payload = await response.json().catch(() => null);
      showToast(payload?.error || '❌ Erro ao excluir a meta.');
    }
  }).catch(error => {
    console.error('confirmDeleteMeta error:', error);
    showToast('❌ Erro de conexão.');
  });
}

/* 4.3.3 Editar Depósito */

/**
 * Abre o modal de edição para um depósito específico.
 */
function openEditDepositModal(depositId, amount, date, goalId, goalName) {
  document.getElementById('edit-deposit-id').value = depositId;
  document.getElementById('edit-deposit-goal-id').value = goalId;
  document.getElementById('edit-deposit-amount').value = amount;
  document.getElementById('edit-deposit-date').value = date;
  document.querySelector('#modal-edit-deposit .modal-title').textContent = `Editar Depósito em ${goalName}`;
  openModal('modal-edit-deposit');
}

/**
 * Processa a atualização de um depósito.
 */
function updateDeposit() {
  const depositId = document.getElementById('edit-deposit-id').value;
  const goalId = document.getElementById('edit-deposit-goal-id').value;
  const amount = document.getElementById('edit-deposit-amount').value;
  const date = document.getElementById('edit-deposit-date').value;
  const csrf = getCSRFToken();

  if (!amount || amount <= 0) {
    showToast('⚠️ Valor do depósito deve ser maior que zero.');
    return;
  }

  fetch(`/update-deposit/${depositId}/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrf,
    },
    body: JSON.stringify({
      amount: amount,
      date: date,
      goal_id: goalId,
    }),
  }).then(async response => {
    if (response.ok) {
      closeModal('modal-edit-deposit');
      showToast('💰 Depósito atualizado com sucesso!');
      setTimeout(() => location.reload(), 1000);
    } else {
      const payload = await response.json().catch(() => null);
      showToast(payload?.error || '❌ Erro ao atualizar o depósito.');
    }
  }).catch(error => {
    console.error('updateDeposit error:', error);
    showToast('❌ Erro de conexão.');
  });
}

/**
 * Abre o modal de exclusão de depósito.
 */
function openDeleteDepositModal(depositId, amount, date, goalName) {
  document.getElementById('delete-deposit-id').value = depositId;
  document.getElementById('delete-deposit-info').textContent = `Valor: R$ ${parseFloat(amount).toFixed(2)} | Data: ${new Date(date).toLocaleDateString('pt-BR')} | Meta: ${goalName}`;
  openModal('modal-delete-deposit');
}

/**
 * Processa a exclusão de um depósito.
 */
function deleteDeposit() {
  const depositId = document.getElementById('delete-deposit-id').value;
  const csrf = getCSRFToken();

  fetch(`/delete-deposit/${depositId}/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrf,
    },
    body: JSON.stringify({}),
  }).then(async response => {
    if (response.ok) {
      closeModal('modal-delete-deposit');
      showToast('🗑️ Depósito excluído com sucesso!');
      setTimeout(() => location.reload(), 1000);
    } else {
      const payload = await response.json().catch(() => null);
      showToast(payload?.error || '❌ Erro ao excluir o depósito.');
    }
  }).catch(error => {
    console.error('deleteDeposit error:', error);
    showToast('❌ Erro de conexão.');
  });
}

/* 4.4 Depositar na Meta */

/**
 * Abre o modal de depósito para uma meta específica.
 */
function openDepositModal(goalId, goalName) {
  document.getElementById('input-deposit-goal-id').value = goalId;
  document.querySelector('#modal-deposit .modal-title').textContent = `Depositar em ${goalName}`;
  openModal('modal-deposit');
}

/**
 * Processa o depósito em uma meta financeira.
 */
function saveDeposit() {
  const goalId = document.getElementById('input-deposit-goal-id').value;
  const amount = document.getElementById('input-deposit-amount').value;
  const csrf = getCSRFToken();

  if (!amount || parseFloat(amount) <= 0) {
    showToast('⚠️ Insira um valor válido para o depósito.');
    return;
  }

  fetch('/deposit-goal/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrf,
    },
    body: JSON.stringify({
      goal_id: goalId,
      deposit_amount: amount,
    }),
  }).then(async response => {
    if (response.ok) {
      closeModal('modal-deposit');
      showToast('💰 Depósito realizado com sucesso!');
      setTimeout(() => location.reload(), 1000);
    } else {
      const payload = await response.json().catch(() => null);
      showToast(payload?.error || '❌ Erro ao depositar.');
    }
  }).catch(error => {
    console.error('saveDeposit error:', error);
    showToast('❌ Erro de conexão.');
  });
}

function markAlertsRead() {
  const csrf = document.querySelector('meta[name="csrf-token"]').content;
  fetch('/mark-alerts-read/', {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrf,
    },
  }).then(response => {
    if (response.ok) {
      showToast('✅ Todos os alertas foram lidos!');
      setTimeout(() => location.reload(), 800);
    }
  });
}

// =====================================================
// FUNCIONALIDADES DA PÁGINA DE ORÇAMENTO
// =====================================================

// Aguardar o DOM carregar completamente
document.addEventListener('DOMContentLoaded', function() {
  console.log('DOM carregado - inicializando funcionalidades de orçamento');
  
  // Inicializar paletas de emojis
  initEmojiPalettes();
  
  // Event listener para o botão salvar categoria
  const saveButton = document.getElementById('btn-save-category');
  if (saveButton) {
    saveButton.addEventListener('click', saveCategory);
    console.log('Event listener adicionado ao botão salvar categoria');
  } else {
    console.log('Botão salvar categoria não encontrado na página atual');
  }

  // Event listener para o botão atualizar categoria
  const updateButton = document.getElementById('btn-update-category');
  if (updateButton) {
    updateButton.addEventListener('click', updateCategory);
    console.log('Event listener adicionado ao botão atualizar categoria');
  }

  // Event listener para o botão confirmar exclusão
  const deleteButton = document.getElementById('btn-confirm-delete');
  if (deleteButton) {
    deleteButton.addEventListener('click', confirmDeleteCategory);
    console.log('Event listener adicionado ao botão confirmar exclusão');
  }

  const deleteTxButton = document.getElementById('btn-confirm-delete-transaction');
  if (deleteTxButton) {
    deleteTxButton.addEventListener('click', confirmDeleteTransaction);
  }
});

// Inicializar paletas de emojis com event listeners
function initEmojiPalettes() {
  console.log('Inicializando paletas de emojis');
  
  // Paleta de adicionar categoria
  const addPalette = document.getElementById('input-category-icon');
  if (addPalette) {
    const emojiButtons = addPalette.querySelectorAll('.emoji-btn');
    emojiButtons.forEach(btn => {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        selectEmoji(this, 'input-category-icon-value');
      });
    });
    // Selecionar o primeiro emoji por padrão
    if (emojiButtons.length > 0) {
      emojiButtons[0].classList.add('selected');
    }
  }
  
  // Paleta de editar categoria
  const editPalette = document.getElementById('edit-category-icon');
  if (editPalette) {
    const emojiButtons = editPalette.querySelectorAll('.emoji-btn');
    emojiButtons.forEach(btn => {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        selectEmoji(this, 'edit-category-icon-value');
      });
    });
  }
}

// Função para selecionar emoji na paleta
function selectEmoji(button, inputId) {
  console.log('Emoji selecionado:', button.dataset.emoji);
  
  // Remover seleção anterior
  const palette = button.parentElement;
  palette.querySelectorAll('.emoji-btn').forEach(btn => {
    btn.classList.remove('selected');
  });
  
  // Adicionar seleção ao botão clicado
  button.classList.add('selected');
  
  // Atualizar valor do input hidden
  document.getElementById(inputId).value = button.dataset.emoji;
}

// Função para reabrir modal de edição com emoji selecionado
function openEditModal(categoryId, categoryName, categoryIcon) {
  console.log('Abrindo modal de edição com emoji:', categoryIcon);
  
  // Preencher dados
  document.getElementById('edit-category-id').value = categoryId;
  document.getElementById('edit-category-name').value = categoryName;
  document.getElementById('edit-category-icon-value').value = categoryIcon;
  
  // Selecionar emoji na paleta
  const editPalette = document.getElementById('edit-category-icon');
  const emojiButtons = editPalette.querySelectorAll('.emoji-btn');
  emojiButtons.forEach(btn => {
    btn.classList.remove('selected');
    if (btn.dataset.emoji === categoryIcon) {
      btn.classList.add('selected');
    }
  });
  
  openModal('modal-edit-category');
}

// Envio do formulário de adicionar categoria
async function saveCategory() {
  console.log('Função saveCategory chamada');
  
  const name = document.getElementById('input-category-name').value.trim();
  const icon = document.getElementById('input-category-icon-value').value || '🎯';

  console.log('Nome:', name);
  console.log('Ícone:', icon);

  if (!name) {
    showToast('⚠️ Por favor, preencha o nome da categoria');
    return;
  }

  try {
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    console.log('CSRF Token encontrado:', csrfToken);
    
    const formData = new FormData();
    formData.append('name', name);
    formData.append('icon', icon);
    formData.append('csrfmiddlewaretoken', csrfToken);

    console.log('Dados do FormData:');
    for (let [key, value] of formData.entries()) {
      console.log(key, ':', value);
    }

    console.log('Enviando requisição para: /orcamento/add-category/');
    
    const response = await fetch('/orcamento/add-category/', {
      method: 'POST',
      body: formData,
      headers: {
        'X-CSRFToken': csrfToken,
      },
    });

    console.log('Status da resposta:', response.status);
    
    const data = await response.json();
    console.log('Dados da resposta:', data);

    if (data.success) {
      console.log('Sucesso! Fechando modal e recarregando página...');
      closeModal('modal-add-category');
      document.getElementById('input-category-name').value = '';
      document.getElementById('input-category-icon-value').value = '🎯';
      showToast('✅ Categoria criada com sucesso!');
      setTimeout(() => location.reload(), 1000);
    } else {
      const errorMsg = data.errors?.name?.[0] || data.errors?.icon?.[0] || 'Erro desconhecido';
      showToast('❌ Erro ao adicionar categoria: ' + errorMsg);
    }
  } catch (error) {
    console.error('Erro na requisição:', error);
    showToast('❌ Erro na comunicação com o servidor');
  }
}

// Função para abrir modal de edição de categoria
function editCategory(categoryId, categoryName, categoryIcon) {
  console.log('Abrindo modal de edição para categoria:', categoryId, categoryName, categoryIcon);
  openEditModal(categoryId, categoryName, categoryIcon);
}

// Função para atualizar categoria
async function updateCategory() {
  console.log('Função updateCategory chamada');
  
  const categoryId = document.getElementById('edit-category-id').value;
  const name = document.getElementById('edit-category-name').value.trim();
  const icon = document.getElementById('edit-category-icon-value').value || '🎯';

  console.log('ID:', categoryId, 'Nome:', name, 'Ícone:', icon);

  if (!name) {
    showToast('⚠️ Por favor, preencha o nome da categoria');
    return;
  }

  try {
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    
    const formData = new FormData();
    formData.append('category_id', categoryId);
    formData.append('name', name);
    formData.append('icon', icon);
    formData.append('csrfmiddlewaretoken', csrfToken);

    console.log('Enviando requisição para: /orcamento/edit-category/');
    
    const response = await fetch('/orcamento/edit-category/', {
      method: 'POST',
      body: formData,
      headers: {
        'X-CSRFToken': csrfToken,
      },
    });

    console.log('Status da resposta:', response.status);
    
    const data = await response.json();
    console.log('Dados da resposta:', data);

    if (data.success) {
      console.log('Sucesso! Fechando modal e recarregando página...');
      closeModal('modal-edit-category');
      showToast('✅ Categoria atualizada com sucesso!');
      setTimeout(() => location.reload(), 1000);
    } else {
      const errorMsg = data.errors?.name?.[0] || data.errors?.icon?.[0] || data.error || 'Erro desconhecido';
      showToast('❌ Erro ao atualizar categoria: ' + errorMsg);
    }
  } catch (error) {
    console.error('Erro na requisição:', error);
    showToast('❌ Erro na comunicação com o servidor');
  }
}

// Função para abrir modal de confirmação de exclusão
function deleteCategory(categoryId, categoryName) {
  console.log('Abrindo modal de exclusão para categoria:', categoryId, categoryName);
  
  document.getElementById('delete-category-id').value = categoryId;
  document.getElementById('delete-category-name').textContent = categoryName;
  
  openModal('modal-delete-category');
}

// Função para confirmar exclusão de categoria
async function confirmDeleteCategory() {
  console.log('Função confirmDeleteCategory chamada');
  
  const categoryId = document.getElementById('delete-category-id').value;

  try {
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    
    const formData = new FormData();
    formData.append('category_id', categoryId);
    formData.append('csrfmiddlewaretoken', csrfToken);

    console.log('Enviando requisição para: /orcamento/delete-category/');
    
    const response = await fetch('/orcamento/delete-category/', {
      method: 'POST',
      body: formData,
      headers: {
        'X-CSRFToken': csrfToken,
      },
    });

    console.log('Status da resposta:', response.status);
    
    const data = await response.json();
    console.log('Dados da resposta:', data);

    if (data.success) {
      console.log('Sucesso! Fechando modal e recarregando página...');
      closeModal('modal-delete-category');
      showToast('✅ ' + data.message);
      setTimeout(() => location.reload(), 1000);
    } else {
      showToast('❌ Erro ao excluir categoria: ' + data.error);
    }
  } catch (error) {
    console.error('Erro na requisição:', error);
    showToast('❌ Erro na comunicação com o servidor');
  }
}


/* =============================================================================
   5. SELETOR DE MÊS (Pills)
   ============================================================================= */

/**
 * Seleciona um mês no filtro de período da tela de Lançamentos.
 * Remove o estado ativo dos demais pills e ativa o clicado.
 * data-ym vazio = mostrar todas as linhas com classe .tx-row.
 *
 * @param {HTMLElement} el - Elemento pill clicado
 */
function selectPill(el) {
  document.querySelectorAll('.month-pill').forEach(p => p.classList.remove('active'));
  el.classList.add('active');
  const ym = el.getAttribute('data-ym') || '';
  const page = document.getElementById('pg-lancamentos');
  if (!page) return;
  page.querySelectorAll('tr.tx-row').forEach(row => {
    const rowYm = row.getAttribute('data-ym') || '';
    row.style.display = !ym || rowYm === ym ? '' : 'none';
  });
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
      labels: barLabels,
      datasets: [
        {
          label: 'Receitas',
          data: barIncome,
          backgroundColor: 'rgba(63, 185, 80, 0.7)',
          borderRadius: 4,
        },
        {
          label: 'Despesas',
          data: barExpenses,
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
      labels: doughnutLabels,
      datasets: [
        {
          data: doughnutData,
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

  if (canvas._chartInst) canvas._chartInst.destroy();

  const labels = typeof orcamento_labels !== 'undefined' ? orcamento_labels : [];
  const data = typeof orcamento_values !== 'undefined' ? orcamento_values : [];

  canvas._chartInst = new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [
        {
          data: data,
          backgroundColor: [
            '#58a6ff',
            '#d29922',
            '#f85149',
            '#3fb950',
            '#e3b341',
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
 * exibindo receitas, despesas e saldo mês a mês no período com lançamentos.
 */
function initLineChart() {
  const canvas = document.getElementById('chartLine');
  if (!canvas) return;

  if (canvas._chartInst) canvas._chartInst.destroy();

  const labels = typeof line_labels !== 'undefined' ? line_labels : ['Out/24', 'Nov/24', 'Dez/24', 'Jan/25', 'Fev/25', 'Mar/25'];
  const income = typeof line_income !== 'undefined' ? line_income : [1450, 1650, 2100, 1450, 1850, 1850];
  const expense = typeof line_expense !== 'undefined' ? line_expense : [1520, 1400, 1890, 1230, 1046, 1003];
  const balance = typeof line_balance !== 'undefined' ? line_balance : [-70, 250, 210, 220, 804, 847];

  canvas._chartInst = new Chart(canvas, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Receitas',
          data: income,
          borderColor:     '#3fb950',
          backgroundColor: 'rgba(63, 185, 80, 0.1)',
          tension:     0.4,
          fill:        true,
          pointRadius: 4,
        },
        {
          label: 'Despesas',
          data: expense,
          borderColor:     '#f85149',
          backgroundColor: 'rgba(248, 81, 73, 0.1)',
          tension:     0.4,
          fill:        true,
          pointRadius: 4,
        },
        {
          label: 'Saldo',
          data: balance,
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
  if (document.getElementById('chartBarDash')) initBarDashChart();
  if (document.getElementById('chartDoughnut')) initDoughnutDashChart();
  if (document.getElementById('chartOrcamento')) initOrcChart();
  if (document.getElementById('chartLine')) initLineChart();
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

  // Função para toggle das metas concluídas
  window.toggleMetasConcluidas = function() {
    const section = document.getElementById('metas-concluidas-section');
    if (section.style.display === 'none') {
      section.style.display = 'block';
    } else {
      section.style.display = 'none';
    }
  };

  // Inicializa gráficos de acordo com a página atual
  if (document.getElementById('chartBarDash'))  { initBarDashChart();     }
  if (document.getElementById('chartDoughnut')) { initDoughnutDashChart();}
  if (document.getElementById('chartOrcamento')){ initOrcChart();         }
  if (document.getElementById('chartLine'))     { initLineChart();        }

  ensureRecurringMonthlyDaySelect();
  const recFreq = document.getElementById('input-rec-frequency');
  if (recFreq) recFreq.addEventListener('change', syncRecurringDueVisibility);
  const recType = document.getElementById('input-rec-type');
  if (recType) recType.addEventListener('change', syncRecurringTypeVisibility);

  // Login e cadastro são tratados pelo Django (POST de formulário).
  // Não há interceptação de clique aqui.
});
