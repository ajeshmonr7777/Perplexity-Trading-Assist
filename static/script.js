// Global Variables
let chart, candleSeries;
let currentSymbol = 'SPY';

document.addEventListener('DOMContentLoaded', () => {
    initChart();
    fetchPortfolio();
    fetchWatchlist();
    loadChart(currentSymbol);
});

// --- Navigation ---
function switchTab(tabName) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.nav-links li').forEach(l => l.classList.remove('active'));

    document.getElementById(`${tabName}-view`).classList.add('active');

    // Highlight nav item
    const navItems = document.querySelectorAll('.nav-links li');
    if (tabName === 'dashboard') navItems[0].classList.add('active');
    if (tabName === 'analysis') navItems[1].classList.add('active');
    if (tabName === 'settings') navItems[2].classList.add('active');
}

// --- Charting ---
function initChart() {
    const container = document.getElementById('chart-container');
    chart = LightweightCharts.createChart(container, {
        layout: {
            background: { color: 'transparent' },
            textColor: '#94a3b8',
        },
        grid: {
            vertLines: { color: 'rgba(255, 255, 255, 0.1)' },
            horzLines: { color: 'rgba(255, 255, 255, 0.1)' },
        },
        timeScale: {
            borderColor: 'rgba(255, 255, 255, 0.1)',
        },
        rightPriceScale: {
            borderColor: 'rgba(255, 255, 255, 0.1)',
        },
    });

    candleSeries = chart.addCandlestickSeries({
        upColor: '#10b981',
        downColor: '#ef4444',
        borderVisible: false,
        wickUpColor: '#10b981',
        wickDownColor: '#ef4444',
    });

    // Resize handler
    new ResizeObserver(entries => {
        if (entries.length === 0 || entries[0].target !== container) { return; }
        const newRect = entries[0].contentRect;
        chart.applyOptions({ height: newRect.height, width: newRect.width });
    }).observe(container);
}

async function loadChart(symbolOrPeriod) {
    let period = '1mo';
    if (['1mo', '3mo', '1y'].includes(symbolOrPeriod)) {
        period = symbolOrPeriod;
    } else {
        currentSymbol = symbolOrPeriod;
        document.getElementById('chart-symbol').innerText = currentSymbol;
    }

    // Fetch data
    try {
        const response = await fetch(`/api/market/chart/${currentSymbol}?period=${period}`);
        const data = await response.json();
        candleSeries.setData(data);
    } catch (error) {
        console.error('Error loading chart:', error);
    }
}

// --- Portfolio ---
async function fetchPortfolio() {
    const response = await fetch('/api/portfolio');
    const items = await response.json();

    // Fetch latest AI decisions for all holdings
    let latestAnalyses = {};
    try {
        const analysisResponse = await fetch('/api/analysis/portfolio/latest');
        const analyses = await analysisResponse.json();
        analyses.forEach(a => {
            latestAnalyses[a.symbol] = a;
        });
    } catch (error) {
        console.error('Error fetching analyses:', error);
    }

    const tbody = document.querySelector('#holdings-table tbody');
    tbody.innerHTML = '';

    let totalValue = 0;
    let totalCost = 0;

    items.forEach(item => {
        const value = item.current_price * item.quantity;
        const cost = item.avg_price * item.quantity;
        const pnl = value - cost;
        const pnlColor = pnl >= 0 ? '#10b981' : '#ef4444';

        totalValue += value;
        totalCost += cost;

        // Get AI decision for this symbol
        const analysis = latestAnalyses[item.symbol];
        let decisionBadge = '<span class="decision-badge pending">No Analysis</span>';

        if (analysis && analysis.decision) {
            const decisionClass = analysis.decision;
            const confidence = analysis.confidence || 0;
            decisionBadge = `<span class="decision-badge ${decisionClass}" onclick="viewSymbolHistory('${item.symbol}')" title="Click to view history">${decisionClass} (${confidence}%)</span>`;
        }

        const row = `
            <tr>
                <td>
                    <span class="symbol-link" onclick="viewSymbolHistory('${item.symbol}')" title="Click to view analysis history">
                        ${item.symbol}
                    </span>
                </td>
                <td>${item.quantity}</td>
                <td>$${item.avg_price.toFixed(2)}</td>
                <td>$${item.current_price.toFixed(2)}</td>
                <td>$${value.toFixed(2)}</td>
                <td style="color: ${pnlColor}">${pnl > 0 ? '+' : ''}${pnl.toFixed(2)}</td>
                <td>${decisionBadge}</td>
                <td><button class="action-btn" onclick="deleteAsset(${item.id})"><i class="fa-solid fa-trash"></i></button></td>
            </tr>
        `;
        tbody.innerHTML += row;
    });

    // Update Summaries
    const totalPnl = totalValue - totalCost;
    const totalPnlPercent = totalCost > 0 ? (totalPnl / totalCost * 100) : 0;

    document.getElementById('total-value').innerText = `$${totalValue.toFixed(2)}`;
    const pnlEl = document.getElementById('total-pnl');
    pnlEl.innerText = `${totalPnl > 0 ? '+' : ''}$${totalPnl.toFixed(2)} (${totalPnlPercent.toFixed(2)}%)`;
    pnlEl.style.color = totalPnl >= 0 ? '#10b981' : '#ef4444';
}


async function addAsset() {
    const symbol = document.getElementById('asset-symbol').value;
    const qty = parseFloat(document.getElementById('asset-qty').value);
    const price = parseFloat(document.getElementById('asset-price').value);

    if (!symbol || !qty || !price) return;

    await fetch('/api/portfolio', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, quantity: qty, avg_price: price })
    });

    closeModal();
    fetchPortfolio();
}

async function deleteAsset(id) {
    if (!confirm('Are you sure?')) return;
    await fetch(`/api/portfolio/${id}`, { method: 'DELETE' });
    fetchPortfolio();
}

// --- Watchlist ---
async function fetchWatchlist() {
    const response = await fetch('/api/watchlist');
    const items = await response.json();
    const list = document.getElementById('watchlist-list');
    list.innerHTML = '';

    items.forEach(item => {
        const li = document.createElement('li');
        li.className = 'watchlist-item';
        li.innerHTML = `
            <span>${item.symbol}</span>
            <span>$${item.current_price.toFixed(2)}</span>
        `;
        li.onclick = () => loadChart(item.symbol);
        list.appendChild(li);
    });
}

async function addToWatchlist() {
    const input = document.getElementById('watchlist-input');
    const symbol = input.value;
    if (!symbol) return;

    await fetch('/api/watchlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, notes: '' })
    });

    input.value = '';
    fetchWatchlist();
}

// --- AI Chat ---
function handleEnter(e) {
    if (e.key === 'Enter') sendAiPrompt();
}

async function sendAiPrompt() {
    const input = document.getElementById('ai-prompt');
    const prompt = input.value;
    if (!prompt) return;

    // Add User Message
    addMessage(prompt, 'user');
    input.value = '';

    // Show Loading
    showLoading();

    // Call Backend
    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: prompt })
        });

        const data = await response.json();
        hideLoading();
        addMessage(data.message, 'system');
    } catch (error) {
        hideLoading();
        addMessage("Error: Could not reach the AI agent.", 'system');
        console.error(error);
    }
}

let loadingInterval;
let loadingSeconds = 0;

function showLoading() {
    const history = document.getElementById('chat-history');
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message system loading-indicator';
    loadingDiv.id = 'ai-loading';

    // Initial content
    loadingDiv.innerHTML = `
        <div class="loading-content">
            <div class="typing-dots">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
            <span id="loading-timer" class="loading-timer">Thinking... (0s)</span>
        </div>
    `;

    history.appendChild(loadingDiv);
    history.scrollTop = history.scrollHeight;

    // Start Timer
    loadingSeconds = 0;
    loadingInterval = setInterval(() => {
        loadingSeconds++;
        const timerSpan = document.getElementById('loading-timer');
        if (timerSpan) {
            timerSpan.innerText = `Thinking... (${loadingSeconds}s)`;
        }
    }, 1000);
}

function hideLoading() {
    const loadingDiv = document.getElementById('ai-loading');
    if (loadingDiv) loadingDiv.remove();
    clearInterval(loadingInterval);
}

function addMessage(text, type) {
    const history = document.getElementById('chat-history');
    const msg = document.createElement('div');
    msg.className = `message ${type}`;

    // Parse markdown for system messages
    if (type === 'system') {
        const rawText = text || "";
        try {
            // Check if marked is available
            if (typeof marked !== 'undefined' && marked.parse) {
                const htmlContent = marked.parse(rawText);
                msg.innerHTML = htmlContent;
            } else {
                console.error("MARKED NOT FOUND");
                msg.innerText = rawText;
            }
        } catch (e) {
            console.error("MARKDOWN ERROR:", e);
            msg.innerText = rawText;
        }
    } else {
        msg.innerText = text;
    }

    history.appendChild(msg);
    history.scrollTop = history.scrollHeight;
}

// --- Modals ---
function openAddAssetModal() {
    document.getElementById('add-asset-modal').style.display = 'flex';
}

function closeModal() {
    document.getElementById('add-asset-modal').style.display = 'none';
}

// ============================================================================
// 3-AGENT INTERFACE FUNCTIONS - MODAL BASED
// ============================================================================

// Open Agent Modal
function openAgentModal(agentName) {
    const modal = document.getElementById(`${agentName}-modal`);
    if (modal) {
        modal.classList.add('active');
    }
}

// Close Agent Modal
function closeAgentModal() {
    document.querySelectorAll('.agent-modal').forEach(modal => {
        modal.classList.remove('active');
    });
}

// Close modal when clicking outside
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('agent-modal')) {
        closeAgentModal();
    }
});

// Close modal on ESC key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeAgentModal();
    }
});

// ============================================================================
// AGENT 1: PORTFOLIO ANALYZER
// ============================================================================

let schedulerRunning = false;
let schedulerStatusInterval = null;

// Toggle scheduler on/off
async function toggleScheduler() {
    const button = document.getElementById('scheduler-toggle');
    const badge = document.getElementById('scheduler-status-badge');

    if (schedulerRunning) {
        // Stop scheduler
        const response = await fetch('/api/scheduler/stop', { method: 'POST' });
        const data = await response.json();

        schedulerRunning = false;
        button.innerHTML = '<i class="fa-solid fa-play"></i> Start Auto-Analysis';
        badge.className = 'status-badge stopped';
        badge.textContent = '● Stopped';

        clearInterval(schedulerStatusInterval);
    } else {
        // Start scheduler
        const response = await fetch('/api/scheduler/start', { method: 'POST' });
        const data = await response.json();

        schedulerRunning = true;
        button.innerHTML = '<i class="fa-solid fa-stop"></i> Stop Auto-Analysis';
        badge.className = 'status-badge running';
        badge.textContent = '● Running';

        // Start status polling
        schedulerStatusInterval = setInterval(updateSchedulerStatus, 5000);
        updateSchedulerStatus();
    }
}

// Update scheduler interval
async function updateSchedulerInterval() {
    const interval = document.getElementById('scheduler-interval').value;

    await fetch('/api/scheduler/configure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ interval_minutes: parseInt(interval) })
    });
}

// Run analysis now
async function runAnalysisNow() {
    const content = document.getElementById('portfolio-analysis-content');
    content.innerHTML = '<div class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i><p>Analyzing portfolio...</p></div>';

    try {
        const response = await fetch('/api/scheduler/run-now', { method: 'POST' });
        const data = await response.json();

        displayPortfolioAnalysis(data);
    } catch (error) {
        content.innerHTML = '<div class="empty-state"><i class="fa-solid fa-exclamation-triangle"></i><p>Error running analysis</p></div>';
    }
}

// Update scheduler status
async function updateSchedulerStatus() {
    const response = await fetch('/api/scheduler/status');
    const data = await response.json();

    // Update last run and next run times
    document.getElementById('last-run-time').textContent =
        `Last Run: ${data.last_run ? new Date(data.last_run).toLocaleString() : 'Never'}`;
    document.getElementById('next-run-time').textContent =
        `Next Run: ${data.next_run ? new Date(data.next_run).toLocaleString() : '-'}`;

    // Fetch latest analysis if available
    if (data.has_latest_analysis) {
        const analysisResponse = await fetch('/api/scheduler/latest');
        const analysisData = await analysisResponse.json();
        displayPortfolioAnalysis(analysisData);
    }
}

// Display portfolio analysis results
function displayPortfolioAnalysis(data) {
    const content = document.getElementById('portfolio-analysis-content');

    if (data.error) {
        content.innerHTML = `<div class="empty-state"><i class="fa-solid fa-exclamation-triangle"></i><p>${data.error}</p></div>`;
        return;
    }

    // Parse the analysis text and display it
    content.innerHTML = `
        <div class="analysis-timestamp">
            <small>Analysis from ${new Date(data.timestamp).toLocaleString()}</small>
        </div>
        <div class="analysis-text">
            ${marked.parse(data.analysis)}
        </div>
    `;
}

// ============================================================================
// AGENT 2: STOCK SCREENER
// ============================================================================

function handleScreenerEnter(e) {
    if (e.key === 'Enter') screenStock();
}

async function screenStock() {
    const symbol = document.getElementById('screener-symbol').value.toUpperCase();
    if (!symbol) return;

    const resultsDiv = document.getElementById('screener-results');
    resultsDiv.innerHTML = '<div class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i><p>Analyzing ' + symbol + '...</p></div>';

    try {
        const response = await fetch('/api/ai/stock-screener', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol })
        });

        const data = await response.json();

        if (data.error) {
            resultsDiv.innerHTML = `<div class="empty-state"><i class="fa-solid fa-exclamation-triangle"></i><p>${data.error}</p></div>`;
            return;
        }

        displayScreenerResults(data);
    } catch (error) {
        resultsDiv.innerHTML = '<div class="empty-state"><i class="fa-solid fa-exclamation-triangle"></i><p>Error analyzing stock</p></div>';
    }
}

function displayScreenerResults(data) {
    const resultsDiv = document.getElementById('screener-results');

    const recommendationClass = data.recommendation.toLowerCase();
    const confidenceColor = data.confidence >= 70 ? '#10b981' : data.confidence >= 50 ? '#fbbf24' : '#ef4444';

    resultsDiv.innerHTML = `
        <div class="screener-result-card">
            <div class="result-header">
                <div>
                    <div class="result-symbol">${data.symbol}</div>
                    <div class="result-price">$${data.technical_data.current_price.toFixed(2)}</div>
                </div>
                <div class="action-badge ${recommendationClass}">${data.recommendation}</div>
            </div>
            
            <div class="recommendation-box">
                <div class="recommendation-label">Recommendation</div>
                <div class="recommendation-value">${data.recommendation}</div>
            </div>
            
            <div class="confidence-box">
                <div class="recommendation-label">Confidence</div>
                <div class="confidence-percentage" style="color: ${confidenceColor}">${data.confidence}%</div>
                <div class="confidence-progress">
                    <div class="confidence-fill" style="width: ${data.confidence}%"></div>
                </div>
            </div>
            
            <div class="reasoning-box">
                <h4>Analysis</h4>
                ${marked.parse(data.reasoning)}
            </div>
            
            <div class="technical-grid">
                <div class="technical-item">
                    <div class="technical-label">Trend</div>
                    <div class="technical-value">${data.technical_data.trend}</div>
                </div>
                <div class="technical-item">
                    <div class="technical-label">RSI</div>
                    <div class="technical-value">${data.technical_data.rsi.toFixed(2)}</div>
                </div>
                <div class="technical-item">
                    <div class="technical-label">MACD</div>
                    <div class="technical-value">${data.technical_data.macd.trend}</div>
                </div>
                <div class="technical-item">
                    <div class="technical-label">Score</div>
                    <div class="technical-value">${data.score}/100</div>
                </div>
                <div class="technical-item">
                    <div class="technical-label">Market Regime</div>
                    <div class="technical-value">${data.market_regime}</div>
                </div>
                <div class="technical-item">
                    <div class="technical-label">Support</div>
                    <div class="technical-value">$${data.technical_data.support.toFixed(2)}</div>
                </div>
            </div>
        </div>
    `;
}

// ============================================================================
// AGENT 3: QUERY ASSISTANT
// ============================================================================

async function sendQueryAssistant() {
    const input = document.getElementById('ai-prompt');
    const prompt = input.value;
    if (!prompt) return;

    // Add User Message
    addMessage(prompt, 'user');
    input.value = '';

    // Show Loading
    showLoading();


    // Call Backend
    try {
        const response = await fetch('/api/ai/query-assistant', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: prompt })
        });

        const data = await response.json();
        hideLoading();
        addMessage(data.response, 'system');
    } catch (error) {
        hideLoading();
        addMessage("Error: Could not reach the AI agent.", 'system');
        console.error(error);
    }
}

// ============================================================================
// PER-SYMBOL ANALYSIS FUNCTIONS
// ============================================================================

// Analyze all holdings
async function analyzeAllHoldings() {
    const button = event.target;
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Analyzing...';
    button.disabled = true;

    try {
        const response = await fetch('/api/analysis/portfolio/run-all', {
            method: 'POST'
        });

        const data = await response.json();

        // Show success message
        if (data.analyzed > 0) {
            alert(`✅ Analyzed ${data.analyzed} symbols successfully!${data.failed > 0 ? `\n⚠️ ${data.failed} failed` : ''}`);
            // Refresh portfolio to show new decisions
            fetchPortfolio();
        } else {
            alert('⚠️ No symbols were analyzed. Check if you have holdings.');
        }
    } catch (error) {
        console.error('Error analyzing holdings:', error);
        alert('❌ Error analyzing holdings. Please try again.');
    } finally {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

// View symbol analysis history in TABLE format
async function viewSymbolHistory(symbol) {
    // Open modal
    const modal = document.getElementById('analysis-history-modal');
    modal.classList.add('active');

    // Update modal title
    document.getElementById('history-symbol').textContent = symbol;

    // Show loading
    const content = document.getElementById('analysis-history-content');
    content.innerHTML = '<div class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i><p>Loading history...</p></div>';

    try {
        const response = await fetch(`/api/analysis/symbol/${symbol}/history?limit=20`);
        const history = await response.json();

        if (history.length === 0) {
            content.innerHTML = '<div class="empty-state"><i class="fa-solid fa-clock"></i><p>No analysis history yet. Click "Analyze All" to start.</p></div>';
            return;
        }

        // Build TABLE instead of timeline
        let tableHTML = `
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="border-bottom: 2px solid rgba(255,255,255,0.2);">
                        <th style="padding: 1rem; text-align: left; color: var(--text-secondary);">Time</th>
                        <th style="padding: 1rem; text-align: left; color: var(--text-secondary);">Decision</th>
                        <th style="padding: 1rem; text-align: left; color: var(--text-secondary);">Confidence</th>
                        <th style="padding: 1rem; text-align: left; color: var(--text-secondary);">Reason</th>
                    </tr>
                </thead>
                <tbody>
        `;

        history.forEach(item => {
            const time = new Date(item.analyzed_at).toLocaleString();
            const decisionColor =
                item.decision === 'BUY' ? '#10b981' :
                    item.decision === 'SELL' ? '#ef4444' :
                        '#fbbf24';

            // Truncate reasoning for table view
            const shortReason = item.reasoning.length > 150
                ? item.reasoning.substring(0, 150) + '...'
                : item.reasoning;

            tableHTML += `
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.1);">
                    <td style="padding: 1rem; color: var(--text-secondary); font-size: 0.9rem;">
                        ${time}<br>
                        <small style="color: var(--text-secondary); opacity: 0.7;">Price: $${item.current_price.toFixed(2)}</small>
                    </td>
                    <td style="padding: 1rem;">
                        <span style="
                            background: ${decisionColor}22;
                            color: ${decisionColor};
                            padding: 0.4rem 0.8rem;
                            border-radius: 6px;
                            font-weight: 600;
                            border: 1px solid ${decisionColor};
                        ">${item.decision}</span>
                    </td>
                    <td style="padding: 1rem; font-size: 1.1rem; font-weight: 600; color: ${decisionColor};">
                        ${item.confidence}%
                    </td>
                    <td style="padding: 1rem; line-height: 1.5; color: var(--text-primary);">
                        ${shortReason}
                    </td>
                </tr>
            `;
        });

        tableHTML += `
                </tbody>
            </table>
        `;

        content.innerHTML = tableHTML;

    } catch (error) {
        console.error('Error fetching history:', error);
        content.innerHTML = '<div class="empty-state"><i class="fa-solid fa-exclamation-triangle"></i><p>Error loading history</p></div>';
    }
}

// Close analysis history modal
function closeAnalysisHistory() {
    const modal = document.getElementById('analysis-history-modal');
    modal.classList.remove('active');
}

// Auto-refresh portfolio every 15 minutes (optional)
// Uncomment to enable:
// setInterval(() => {
//     fetchPortfolio();
// }, 15 * 60 * 1000);
