
// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ============================================================================
// AUTOCOMPLETE SEARCH
// ============================================================================
class SymbolSearch {
    constructor(inputId, resultsId) {
        this.input = document.getElementById(inputId);
        this.results = document.getElementById(resultsId);

        if (!this.input || !this.results) return;

        this.input.addEventListener('input', debounce((e) => this.handleInput(e), 300));

        // Hide results when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.input.contains(e.target) && !this.results.contains(e.target)) {
                this.results.style.display = 'none';
            }
        });

        // Focus input shows results if value exists
        this.input.addEventListener('focus', () => {
            if (this.input.value.trim().length > 0) {
                this.results.style.display = 'block';
            }
        });
    }

    async handleInput(e) {
        const query = e.target.value.trim();
        if (query.length < 1) {
            this.results.style.display = 'none';
            return;
        }

        try {
            const response = await fetch(`/api/symbols/search?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            this.renderResults(data);
        } catch (error) {
            console.error('Search error:', error);
        }
    }

    renderResults(data) {
        if (!data || data.length === 0) {
            this.results.innerHTML = '<div class="search-item disabled">No results found</div>';
            this.results.style.display = 'block';
            return;
        }

        this.results.innerHTML = data.map(item => `
            <div class="search-item" onclick="selectSymbol('${item.symbol}', '${item.market_code}')">
                <div class="symbol-code">${item.symbol}</div>
                <div class="symbol-name">${item.name}</div>
                <div class="symbol-market">${item.market || ''}</div>
            </div>
        `).join('');

        this.results.style.display = 'block';
    }
}

function selectSymbol(symbol, market) {
    window.location.href = `analysis.html?symbol=${symbol}&market=${market || 'custom'}`;
}

// ============================================================================
// BROWSE DROPDOWN MENU (Cascading)
// ============================================================================
let browseData = null;

async function toggleBrowseMenu() {
    const dropdown = document.getElementById('browse-dropdown');

    // Toggle visibility
    if (dropdown.style.display === 'block') {
        dropdown.style.display = 'none';
        return;
    }

    // Close other dropdowns (like search results)
    const searchRes = document.getElementById('search-results');
    if (searchRes) searchRes.style.display = 'none';

    dropdown.style.display = 'block';

    if (!browseData) {
        dropdown.innerHTML = '<div class="menu-loading"><i class="fa-solid fa-spinner fa-spin"></i> Loading...</div>';
        try {
            const response = await fetch('/api/symbols/all');
            browseData = await response.json();
            renderBrowseMenu();
        } catch (error) {
            dropdown.innerHTML = '<div class="menu-error">Failed to load</div>';
        }
    } else {
        renderBrowseMenu();
    }
}

function renderBrowseMenu() {
    const dropdown = document.getElementById('browse-dropdown');

    dropdown.innerHTML = browseData.map(market => `
        <div class="menu-item">
            <div class="menu-item-content">
                <span class="menu-label">${market.name}</span>
                <i class="fa-solid fa-chevron-right menu-arrow"></i>
            </div>
            
            <!-- Submenu -->
            <div class="submenu">
                <div class="submenu-header">${market.name}</div>
                <div class="submenu-scroll">
                    ${market.symbols.map(sym => `
                        <div class="submenu-item" onclick="selectSymbol('${sym.symbol}', '${market.code}')">
                            <span class="sym-code">${sym.symbol}</span>
                            <span class="sym-name">${sym.name}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>
    `).join('');
}

// Close menu when clicking outside
document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('browse-dropdown');
    // Find the toggle button in the browse module container
    const btn = document.querySelector('.browse-module button');

    if (dropdown && dropdown.style.display === 'block') {
        // If click is NOT inside dropdown AND NOT inside button
        if (!dropdown.contains(e.target) && (!btn || !btn.contains(e.target))) {
            dropdown.style.display = 'none';
        }
    }
});

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    // Only if elements exist
    if (document.getElementById('custom-symbol')) {
        new SymbolSearch('custom-symbol', 'search-results');
    }
});
