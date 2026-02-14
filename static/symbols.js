
document.addEventListener('DOMContentLoaded', async () => {
    const urlParams = new URLSearchParams(window.location.search);
    const marketType = urlParams.get('market') || 'us';
    const grid = document.getElementById('symbols-grid');
    const title = document.getElementById('market-title');

    if (!grid) return; // Not on symbols page (e.g. imported elsewhere)

    // Show loading state
    grid.innerHTML = '<div class="loading" style="grid-column: 1/-1; text-align:center; padding:2rem; color:var(--text-secondary);"><i class="fa-solid fa-spinner fa-spin"></i> Loading symbols...</div>';

    try {
        // Fetch from backend API which reads from symbols.yaml
        const response = await fetch(`/api/symbols/all?market=${marketType}`);
        const data = await response.json();

        if (!data || data.length === 0) {
            if (title) title.textContent = "Market Not Found";
            grid.innerHTML = `<div class="empty-state" style="grid-column: 1/-1; text-align:center;">No symbols found for category '${marketType}'</div>`;
            return;
        }

        const market = data[0]; // API returns list of markets

        if (title) title.textContent = market.name;

        // Render symbols grid
        grid.innerHTML = market.symbols.map(item => `
            <div class="symbol-card glass" onclick="window.location.href='analysis.html?symbol=${item.symbol}&market=${marketType}'">
                <div class="symbol-header">
                    <h3>${item.symbol}</h3>
                    <i class="fa-solid fa-arrow-right" style="font-size: 0.9rem; opacity: 0.7;"></i>
                </div>
                <p>${item.name}</p>
                <div style="margin-top:auto; padding-top:1rem;">
                    <button class="analyze-btn-sm" style="width:100%; padding:0.5rem; background:rgba(255,255,255,0.1); border:none; border-radius:6px; color:white; cursor:pointer;">
                        <i class="fa-solid fa-magnifying-glass-chart"></i> Analyze
                    </button>
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error("Error fetching symbols:", error);
        grid.innerHTML = '<div class="error" style="grid-column: 1/-1; text-align:center;">Failed to load market data. Please make sure the backend is running.</div>';
    }
});
