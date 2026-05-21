/* ==========================================================================
   Crawl & Audit Studio - Frontend Dashboard Controller (dashboard.js)
   ========================================================================== */

import {
    checkBackendConnection,
    startCrawl,
    startSeoAudit,
    startImageExtraction,
    downloadZip
} from './api.js';

// Cache scan responses to build zip downloads
let lastCrawlData = null;
let lastSeoData = null;
let lastImagesData = null;

document.addEventListener('DOMContentLoaded', () => {
    // 1. Navigation routing & Hamburger
    setupNavDrawer();

    // 2. Connection status check
    verifyBackend();

    // 3. Register scan handler
    setupScanner();

    // 4. Register Image list selection triggers
    setupImageSelector();
});

/**
 * Handle sidebar page transitions and mobile drawer toggles
 */
function setupNavDrawer() {
    const navItems = document.querySelectorAll('.nav-item');
    const toolViews = document.querySelectorAll('.tool-view');
    const menuToggle = document.getElementById('menu-toggle');
    const appSidebar = document.getElementById('app-sidebar');
    const backdrop = document.getElementById('sidebar-backdrop');

    // Helper to open/close sidebar with backdrop
    function openSidebar() {
        appSidebar.classList.add('open');
        backdrop.classList.add('visible');
        document.body.style.overflow = 'hidden'; // prevent background scroll
    }

    function closeSidebar() {
        appSidebar.classList.remove('open');
        backdrop.classList.remove('visible');
        document.body.style.overflow = '';
    }

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const targetId = item.getAttribute('data-target');
            
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');

            toolViews.forEach(view => {
                if (view.id === targetId) {
                    view.classList.add('active');
                } else {
                    view.classList.remove('active');
                }
            });

            // Collapse drawer on mobile selection
            closeSidebar();
        });
    });

    menuToggle.addEventListener('click', () => {
        if (appSidebar.classList.contains('open')) {
            closeSidebar();
        } else {
            openSidebar();
        }
    });

    // Tap backdrop to close sidebar
    backdrop.addEventListener('click', () => {
        closeSidebar();
    });

    // Handle console log clear
    const clearBtn = document.getElementById('clear-console');
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            const terminal = document.getElementById('log-terminal');
            terminal.innerHTML = '<div class="terminal-line system-line">[SYSTEM] Log console cleared. Ready for next scan.</div>';
            showToast('Logs cleared', '🧹');
        });
    }
}

/**
 * Check if the Python backend is active
 */
async function verifyBackend() {
    const pill = document.getElementById('backend-status');
    const isOnline = await checkBackendConnection();
    
    if (isOnline) {
        pill.className = 'connection-pill status-connected';
        pill.querySelector('.status-text').textContent = 'Backend Active';
        printConsole('[SYSTEM] SiteScope backend server connected successfully.', 'success');
    } else {
        pill.className = 'connection-pill status-offline';
        pill.querySelector('.status-text').textContent = 'Offline (Mock Mode)';
        printConsole('[SYSTEM] Backend server offline. Crawls will use simulation mode.', 'warning');
        printConsole('[SYSTEM] Tip: Run "run_server.bat" to start SiteScope local server.', 'system');
    }
}

/**
 * Start website scan operations
 */
function setupScanner() {
    const trigger = document.getElementById('scan-trigger');
    const spinner = document.getElementById('scan-spinner');
    const btnText = document.getElementById('scan-btn-text');

    trigger.addEventListener('click', async () => {
        const urlInput = document.getElementById('target-url').value.trim();
        const depth = parseInt(document.getElementById('crawl-depth').value);

        if (!urlInput) {
            showToast('Please enter a target URL!', '⚠️');
            return;
        }

        // Clean URL
        let url = urlInput;
        if (!url.startsWith('http://') && !url.startsWith('https://')) {
            url = 'https://' + url;
        }

        // Reset previous caches
        lastCrawlData = null;
        lastSeoData = null;
        lastImagesData = null;

        // Toggle loading states
        trigger.disabled = true;
        spinner.classList.remove('hidden');
        btnText.textContent = 'Auditing Site...';

        // Clear view listings
        clearScanListings();

        // Print initial terminal actions
        printConsole(`\n[SYSTEM] Initiating deep crawl for: ${url}`, 'info');
        printConsole(`[SYSTEM] Scan depth settings configured to: ${depth}`, 'info');
        printConsole('[INFO] Step 1: Resolving domains & mapping links map...', 'info');

        try {
            // Run Crawl scan
            printConsole('[INFO] Scanning pages, CSS assets, JS scripts and anchor links...', 'info');
            const crawlData = await startCrawl(url, depth);
            lastCrawlData = crawlData;
            
            if (crawlData.status === 'error') {
                throw new Error(crawlData.message);
            }

            printConsole(`[SUCCESS] Crawl completed. Visited ${crawlData.crawled_pages.length} pages.`, 'success');
            printConsole(`[INFO] Found ${crawlData.broken_links.length} broken links and ${crawlData.broken_images.length} broken images.`, 'warning');
            
            // Run SEO Checklist Audit
            printConsole('[INFO] Step 2: Running 10-Point Technical SEO/DOM Checklist...', 'info');
            const seoData = await startSeoAudit(url);
            lastSeoData = seoData;
            
            printConsole('[SUCCESS] 10-Point Technical DOM audits complete.', 'success');

            // Run Image Converter estimates
            printConsole('[INFO] Step 3: Extracting images and calculating WebP format savings...', 'info');
            const imagesData = await startImageExtraction(url, depth);
            lastImagesData = imagesData;

            printConsole(`[SUCCESS] Found and processed ${imagesData.images.length} legacy images.`, 'success');
            printConsole(`[SYSTEM] Audit complete. Open "SEO & DOM Checklist" or "Image WebP Packer" views.`, 'success');

            // Populate dashboard metrics
            renderMetrics(crawlData);

            // Populate findings logs
            renderCrawlFindings(crawlData);

            // Populate SEO checklist details
            renderSeoChecklist(seoData);

            // Populate WebP image compression items
            renderImagesPacker(imagesData);

            showToast('Technical site audit completed!', '✅');

        } catch (error) {
            printConsole(`[ERROR] Audit process failed: ${error.message}`, 'error');
            showToast('Scan execution failed.', '❌');
        } finally {
            trigger.disabled = false;
            spinner.classList.add('hidden');
            btnText.textContent = 'Audit Website';
        }
    });
}

/**
 * Handle selection checkboxes inside WebP Images Table
 */
function setupImageSelector() {
    const selectAllCheckbox = document.getElementById('select-all-images');
    const tableBody = document.getElementById('webp-images-list');
    const downloadZipBtn = document.getElementById('download-zip-btn');

    selectAllCheckbox.addEventListener('change', () => {
        const checkboxes = tableBody.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(cb => {
            cb.checked = selectAllCheckbox.checked;
        });
    });

    downloadZipBtn.addEventListener('click', async () => {
        const checkedBoxes = tableBody.querySelectorAll('input[type="checkbox"]:checked');
        if (checkedBoxes.length === 0) {
            showToast('Please select at least one image to package!', '⚠️');
            return;
        }

        const selectedUrls = [];
        checkedBoxes.forEach(cb => {
            selectedUrls.push(cb.value);
        });

        const targetUrl = document.getElementById('target-url').value.trim();

        showToast('Compiling ZIP archive...', '📦');
        downloadZipBtn.disabled = true;

        try {
            const blob = await downloadZip(targetUrl, selectedUrls, lastCrawlData, lastSeoData);
            
            // Trigger browser download link
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = `webp_audit_report.zip`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(downloadUrl);
            
            showToast('ZIP downloaded successfully!', '✅');
        } catch (error) {
            console.error(error);
            showToast('Failed to download ZIP archive.', '❌');
        } finally {
            downloadZipBtn.disabled = false;
        }
    });
}

/**
 * Utility: Clear previous view tables/listings
 */
function clearScanListings() {
    document.getElementById('stat-visited').textContent = '0';
    document.getElementById('stat-broken-links').textContent = '0';
    document.getElementById('stat-broken-assets').textContent = '0';
    document.getElementById('stat-code-errors').textContent = '0';

    document.getElementById('crawled-issues-list').innerHTML = `
        <div class="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <circle cx="12" cy="12" r="10"></circle>
                <path d="M12 16v-4M12 8h.01"></path>
            </svg>
            <p>Auditing site in progress...</p>
        </div>
    `;

    document.getElementById('seo-checklist').innerHTML = `
        <div class="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M9 11l3 3L22 4"></path>
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
            </svg>
            <p>Audit in progress...</p>
        </div>
    `;

    document.getElementById('webp-images-list').innerHTML = `
        <tr>
            <td colspan="6">
                <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                        <circle cx="8.5" cy="8.5" r="1.5"></circle>
                        <polyline points="21 15 16 10 5 21"></polyline>
                    </svg>
                    <p>Scraping images in progress...</p>
                </div>
            </td>
        </tr>
    `;

    document.getElementById('download-zip-btn').classList.add('hidden');
}

/**
 * Utility: Print line message inside Log Terminal console
 */
function printConsole(text, type = 'system') {
    const terminal = document.getElementById('log-terminal');
    const line = document.createElement('div');
    line.className = `terminal-line ${type}-line`;
    line.innerHTML = text.replace(/\n/g, '<br>');
    terminal.appendChild(line);
    terminal.scrollTop = terminal.scrollHeight;
}

/**
 * Dynamic Renderers: Populate stats counters
 */
function renderMetrics(crawl) {
    document.getElementById('stat-visited').textContent = crawl.crawled_pages.length;
    document.getElementById('stat-broken-links').textContent = crawl.broken_links.length;
    document.getElementById('stat-broken-assets').textContent = crawl.broken_assets.length;
    document.getElementById('stat-code-errors').textContent = crawl.code_errors.length;
}

/**
 * Dynamic Renderers: Render crawled page links/resources problems
 */
function renderCrawlFindings(crawl) {
    const list = document.getElementById('crawled-issues-list');
    list.innerHTML = '';

    const totalIssues = crawl.broken_links.length + crawl.broken_images.length + crawl.broken_assets.length + crawl.code_errors.length;

    if (totalIssues === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color: var(--accent-emerald);">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
                <p style="font-weight: 600; color: var(--accent-emerald);">Congratulations! No crawler issues detected!</p>
                <p>Website structure, page links, asset attachments, and server responses are 100% healthy.</p>
            </div>
        `;
        return;
    }

    // 1. PHP / server code errors
    crawl.code_errors.forEach(err => {
        const item = document.createElement('div');
        item.className = 'issue-item';
        item.innerHTML = `
            <div class="issue-meta">
                <span class="issue-type type-code-error">Code/DOM Bug</span>
                <span class="issue-page">${getBasename(err.page)}</span>
            </div>
            <div class="issue-details">${err.details}</div>
            <div class="issue-recommend"><strong>Fix Required:</strong> ${err.recommendation}</div>
        `;
        list.appendChild(item);
    });

    // 2. Broken links
    crawl.broken_links.forEach(link => {
        const item = document.createElement('div');
        item.className = 'issue-item';
        item.innerHTML = `
            <div class="issue-meta">
                <span class="issue-type type-broken-link">Broken Link (${link.status || 'Fail'})</span>
                <span class="issue-page">${getBasename(link.parent)}</span>
            </div>
            <div class="issue-details">Link target: <code>${link.url}</code></div>
            <div class="issue-recommend"><strong>Fix Required:</strong> ${link.recommendation}</div>
        `;
        list.appendChild(item);
    });

    // 3. Broken images
    crawl.broken_images.forEach(img => {
        const item = document.createElement('div');
        item.className = 'issue-item';
        item.innerHTML = `
            <div class="issue-meta">
                <span class="issue-type type-broken-link">Broken Image (${img.status || 'Fail'})</span>
                <span class="issue-page">${getBasename(img.parent)}</span>
            </div>
            <div class="issue-details">Image target: <code>${img.url}</code></div>
            <div class="issue-recommend"><strong>Fix Required:</strong> ${img.recommendation}</div>
        `;
        list.appendChild(item);
    });

    // 4. Broken assets
    crawl.broken_assets.forEach(asset => {
        const item = document.createElement('div');
        item.className = 'issue-item';
        item.innerHTML = `
            <div class="issue-meta">
                <span class="issue-type type-broken-asset">Broken Dependency (${asset.status || 'Fail'})</span>
                <span class="issue-page">${getBasename(asset.parent)}</span>
            </div>
            <div class="issue-details">File type: ${asset.type} | Target: <code>${asset.url}</code></div>
            <div class="issue-recommend"><strong>Fix Required:</strong> ${asset.recommendation}</div>
        `;
        list.appendChild(item);
    });
}

/**
 * Dynamic Renderers: Generate SEO checklists nodes
 */
function renderSeoChecklist(seo) {
    const list = document.getElementById('seo-checklist');
    list.innerHTML = '';

    for (const key in seo.results) {
        const res = seo.results[key];
        const card = document.createElement('div');
        card.className = 'audit-card';
        
        const detailsLi = res.details.map(item => `<li>${escapeHtml(item)}</li>`).join('');
        
        card.innerHTML = `
            <div class="audit-card-header">
                <div class="audit-title-group">
                    <span class="audit-status-badge status-badge-${res.status.toLowerCase()}">${res.status}</span>
                    <span class="audit-title">${res.title}</span>
                </div>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="audit-arrow-icon">
                    <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
            </div>
            <div class="audit-card-body">
                <div class="audit-body-content">
                    <p class="audit-desc">${res.description}</p>
                    <div class="audit-details-code">
                        <strong>Details / Findings (${res.count} detected):</strong>
                        <ul style="margin-top: 8px; padding-left: 20px;">
                            ${detailsLi}
                        </ul>
                    </div>
                </div>
            </div>
        `;
        
        // Setup accordion toggler
        card.querySelector('.audit-card-header').addEventListener('click', () => {
            card.classList.toggle('open');
        });

        list.appendChild(card);
    }
}

/**
 * Dynamic Renderers: Render list of images for optimization
 */
function renderImagesPacker(imagesData) {
    const tbody = document.getElementById('webp-images-list');
    tbody.innerHTML = '';

    if (imagesData.images.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6">
                    <div class="empty-state">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                            <circle cx="8.5" cy="8.5" r="1.5"></circle>
                            <polyline points="21 15 16 10 5 21"></polyline>
                        </svg>
                        <p>No PNG/JPG files found to compress on this website.</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    imagesData.images.forEach(img => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="checkbox" value="${img.url}" checked></td>
            <td class="img-url-cell">${img.url}</td>
            <td>${formatBytes(img.original_size)}</td>
            <td>${formatBytes(img.webp_size)}</td>
            <td class="savings-pct-green">${img.savings_pct}%</td>
            <td><span class="audit-status-badge status-badge-pass">WEBP Ready</span></td>
        `;
        tbody.appendChild(tr);
    });

    // Reveal ZIP download button
    document.getElementById('download-zip-btn').classList.remove('hidden');
}

/**
 * Helper: Show a toast alert popup
 */
export function showToast(message, emoji = '✨') {
    const wrapper = document.getElementById('toast-wrapper');
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `<span>${emoji}</span><span>${message}</span>`;
    wrapper.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px) scale(0.95)';
        toast.style.transition = 'opacity 0.25s, transform 0.25s';
        setTimeout(() => wrapper.removeChild(toast), 250);
    }, 3000);
}
window.showToast = showToast; // Bind to window for global debug

/**
 * Helpers: General String & format helpers
 */
function getBasename(url) {
    try {
        const path = new URL(url).pathname;
        const base = path.substring(path.lastIndexOf('/') + 1);
        return base || 'index.html';
    } catch (e) {
        return url;
    }
}

function formatBytes(bytes, decimals = 1) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function escapeHtml(text) {
    if (!text) return '';
    return text.toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
