// Get symbol and market from URL
const urlParams = new URLSearchParams(window.location.search);
const symbol = urlParams.get('symbol') || 'AAPL';
const marketType = urlParams.get('market') || 'us';

// Update page title
document.getElementById('symbol-title').textContent = `${symbol} Analysis`;

// Setup back button
document.getElementById('back-btn').onclick = () => {
    window.location.href = `symbols.html?market=${marketType}`;
};

let analysisData = null;

// Run analysis
async function runAnalysis() {
    const loadingState = document.getElementById('loading-state');
    const content = document.getElementById('analysis-content');
    const analyzeBtn = document.getElementById('analyze-btn');

    loadingState.style.display = 'flex';
    content.style.display = 'none';
    analyzeBtn.disabled = true;

    try {
        // Check for mode
        const urlMode = new URLSearchParams(window.location.search).get('mode') || 'standard';
        const response = await fetch(`/api/analysis/symbol/${symbol}?mode=${urlMode}`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error(`Analysis failed: ${response.statusText}`);
        }

        analysisData = await response.json();

        if (analysisData.error) {
            throw new Error(analysisData.error);
        }

        displayAnalysis(analysisData);

        loadingState.style.display = 'none';
        content.style.display = 'block';
        analyzeBtn.disabled = false;

    } catch (error) {
        console.error('Analysis error:', error);
        loadingState.innerHTML = `
            <i class="fa-solid fa-triangle-exclamation"></i>
            <p>Error: ${error.message}</p>
            <button onclick="runAnalysis()">Retry</button>
        `;
        analyzeBtn.disabled = false;
    }
}

// Helper function to convert **text** to <strong>text</strong>
function formatBoldText(text) {
    return text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
}

// Handle Holding Mode (coming from Dashboard)
const mode = urlParams.get('mode');
if (mode === 'holding') {
    document.title = 'Portfolio Analysis - PerplexTrade';
    // Update Sidebar
    document.querySelector('nav a[href="markets.html"]').classList.remove('active');
    document.querySelector('nav a[href="index.html"]').classList.add('active');
}

function displayAnalysis(data) {
    // Update Title with Context
    const titleEl = document.getElementById('symbol-title');
    if (data.holding_context) {
        titleEl.innerHTML = `<i class="fa-solid fa-briefcase"></i> ${data.symbol} Position Analysis`;
    } else {
        titleEl.textContent = `${data.symbol} Analysis`;
    }

    // Decision Badge
    const decision = data.recommendation || 'HOLD';
    const confidence = data.confidence || 50;
    const decisionBadge = document.getElementById('decision-badge');
    decisionBadge.textContent = decision;
    decisionBadge.className = `decision-badge-large ${decision.toLowerCase()}`;

    // Confidence Meter
    const confidenceText = document.getElementById('confidence-text');
    document.getElementById('confidence-fill').style.width = `${confidence}%`;
    confidenceText.textContent = `${confidence}%`;

    // Color code the confidence text
    if (decision === 'BUY') confidenceText.style.color = '#10b981'; // Success Green
    else if (decision === 'SELL') confidenceText.style.color = '#ef4444'; // Danger Red
    else confidenceText.style.color = '#f59e0b'; // Warning Orange

    // Inject Holding Context Card if available
    const contentDiv = document.getElementById('analysis-content');
    const existingHolding = document.getElementById('holding-section');
    if (existingHolding) existingHolding.remove();

    if (data.holding_context) {
        const holding = data.holding_context;
        const sideColor = holding.side === 'BUY' ? '#10b981' : '#ef4444';

        // Calculate PnL roughly (backend has exact but we can calc here)
        let pnl = (data.technical_data.current_price - holding.avg_price) * holding.quantity;
        if (holding.side === 'SELL') pnl = (holding.avg_price - data.technical_data.current_price) * holding.quantity;

        const pnlColor = pnl >= 0 ? '#10b981' : '#ef4444';
        const pnlSign = pnl >= 0 ? '+' : '';

        const holdingDiv = document.createElement('div');
        holdingDiv.id = 'holding-section';
        holdingDiv.className = 'analysis-section glass';
        holdingDiv.style.borderLeft = `4px solid ${sideColor}`;
        holdingDiv.innerHTML = `
            <h2><i class="fa-solid fa-wallet"></i> Your Position</h2>
            <div class="decision-display" style="justify-content: space-around; gap: 2rem;">
                <div style="text-align: center;">
                    <div style="font-size: 0.9rem; color: #94a3b8; margin-bottom: 0.5rem;">SIDE</div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: ${sideColor};">${holding.side}</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 0.9rem; color: #94a3b8; margin-bottom: 0.5rem;">QUANTITY</div>
                    <div style="font-size: 1.5rem; font-weight: 600;">${holding.quantity}</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 0.9rem; color: #94a3b8; margin-bottom: 0.5rem;">AVG PRICE</div>
                    <div style="font-size: 1.5rem; font-weight: 600;">$${holding.avg_price.toFixed(2)}</div>
                </div>
                 <div style="text-align: center;">
                    <div style="font-size: 0.9rem; color: #94a3b8; margin-bottom: 0.5rem;">UNREALIZED P&L</div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: ${pnlColor};">${pnlSign}$${pnl.toFixed(2)}</div>
                </div>
            </div>
        `;
        contentDiv.insertBefore(holdingDiv, contentDiv.firstChild);
    }

    // Parse reasoning for sections
    const reasoning = data.reasoning || '';

    // Extract Market Sentiment
    const sentimentMatch = reasoning.match(/\*\*Market Sentiment\*\*:?\s*([\s\S]*?)(?=\n\*\*|$)/i);
    const sentiment = sentimentMatch ? formatBoldText(sentimentMatch[1].trim()) : 'Not available';
    document.getElementById('sentiment-content').innerHTML = `<p>${sentiment}</p>`;

    // Extract Key Headlines
    const headlinesMatch = reasoning.match(/\*\*Key Headlines\*\*:?\s*([\s\S]*?)(?=\n\*\*|$)/i);
    if (headlinesMatch) {
        const headlines = formatBoldText(headlinesMatch[1].trim());
        document.getElementById('sentiment-content').innerHTML += `<div class="headlines">${headlines.replace(/\n/g, '<br>')}</div>`;
    }

    // Extract Upcoming Catalysts
    const catalystsMatch = reasoning.match(/\*\*Upcoming Catalysts\*\*:?\s*([\s\S]*?)(?=\n\*\*|$)/i);
    const catalysts = catalystsMatch ? formatBoldText(catalystsMatch[1].trim()) : 'None identified';
    document.getElementById('catalysts-content').innerHTML = `<p>${catalysts.replace(/\n/g, '<br>')}</p>`;

    // Extract Technical Outlook
    const technicalMatch = reasoning.match(/\*\*Technical Outlook\*\*:?\s*([\s\S]*?)(?=\n\*\*|$)/i);
    const technical = technicalMatch ? formatBoldText(technicalMatch[1].trim()) : data.technical_data ?
        `Trend: ${data.technical_data.trend}, RSI: ${data.technical_data.rsi}, MACD: ${data.technical_data.macd?.trend}` :
        'Not available';
    document.getElementById('technical-content').innerHTML = `<p>${technical.replace(/\n/g, '<br>')}</p>`;

    // Extract ONLY Detailed Reasoning paragraph (3-4 sentences after the heading)
    const detailedMatch = reasoning.match(/\*\*Detailed Reasoning\*\*:?\s*(?:\([^)]+\):?)?\s*([\s\S]*?)(?=\n\*\*Price Targets|\n\*\*Hold Duration|\n\*\*|$)/i);
    const detailed = detailedMatch ? formatBoldText(detailedMatch[1].trim()) : formatBoldText(reasoning);
    document.getElementById('reasoning-content').innerHTML = `<p>${detailed.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>')}</p>`;

    // Show Full AI Response
    document.getElementById('raw-response').textContent = reasoning;

    // Show the Prompt (if available)
    if (data.full_prompt) {
        document.getElementById('prompt-content').textContent = data.full_prompt;
    } else {
        document.getElementById('prompt-content').textContent = 'Prompt not available for this analysis.';
    }
}

// Auto-run analysis on page load
runAnalysis();
