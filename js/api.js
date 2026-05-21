/* ==========================================================================
   Crawl & Audit Studio - API Connector (api.js)
   ========================================================================== */

const API_BASE = window.location.origin;

// Verify if backend server is responsive
export async function checkBackendConnection() {
    try {
        const response = await fetch(`${API_BASE}/index.html`, { method: 'HEAD', cache: 'no-cache' });
        // If we can reach index.html and aren't in a file:/// context
        if (response.ok && window.location.protocol.startsWith('http')) {
            return true;
        }
        return false;
    } catch (e) {
        return false;
    }
}

// Request API to crawl website
export async function startCrawl(url, depth = 2) {
    try {
        const response = await fetch(`${API_BASE}/api/crawl`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, depth })
        });
        if (!response.ok) throw new Error('API server error');
        return await response.json();
    } catch (error) {
        console.warn('Backend crawler unreachable. Using simulation mode.', error);
        return getSimulatedCrawlData(url);
    }
}

// Request API to execute SEO checklist audit
export async function startSeoAudit(url) {
    try {
        const response = await fetch(`${API_BASE}/api/seo-audit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });
        if (!response.ok) throw new Error('API server error');
        return await response.json();
    } catch (error) {
        console.warn('Backend auditor unreachable. Using simulation mode.', error);
        return getSimulatedSeoData(url);
    }
}

// Request API to scrape images and calculate WebP compressed sizes
export async function startImageExtraction(url, depth = 1) {
    try {
        const response = await fetch(`${API_BASE}/api/extract-images`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, depth })
        });
        if (!response.ok) throw new Error('API server error');
        return await response.json();
    } catch (error) {
        console.warn('Backend image packer unreachable. Using simulation mode.', error);
        return getSimulatedImagesData(url);
    }
}

// Download compressed WebP image assets as a ZIP archive
export async function downloadZip(url, images, crawlResults, seoResults) {
    try {
        const response = await fetch(`${API_BASE}/api/download-zip`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, images, crawl_results: crawlResults, seo_results: seoResults })
        });
        if (!response.ok) throw new Error('API ZIP build error');
        return await response.blob();
    } catch (error) {
        console.error('Failed to compile ZIP archive from backend.', error);
        throw error;
    }
}

// --- Dynamic Simulation / Offline Fallback Generators ---
function getSimulatedCrawlData(url) {
    const isPavitra = url.toLowerCase().includes('pavitraherbal');
    return {
        status: "success",
        simulated: true,
        url: url,
        crawled_pages: [
            url,
            `${url}/about-us.php`,
            `${url}/shop.php`,
            `${url}/contact.php`,
            `${url}/product.php?id=12`
        ],
        broken_links: [
            {
                url: `${url}/blog-insecure-redirect`,
                parent: `${url}/about-us.php`,
                status: 404,
                type: "Broken Link",
                recommendation: "Verify that the endpoint is mapped correctly or add a 301 redirection."
            }
        ],
        broken_images: [
            {
                url: `${url}/images/products/broken_thumbnail.png`,
                parent: `${url}/shop.php`,
                status: 404,
                recommendation: "Ensure that 'broken_thumbnail.png' actually exists in the assets/products/ directory."
            }
        ],
        broken_assets: [
            {
                url: `${url}/assets/css/nonexistent-plugin.css`,
                parent: url,
                status: 404,
                type: "Stylesheet (CSS)",
                recommendation: "Remove reference to unused nonexistent-plugin.css stylesheet in header."
            }
        ],
        code_errors: isPavitra ? [
            {
                page: url,
                type: "Duplicate HTML ID",
                details: "ID 'newsletter-email' is defined 2 times. Affected tags:<br>&bull; <code>&lt;input type=\"email\" id=\"newsletter-email\"&gt;</code> (Header form)<br>&bull; <code>&lt;input type=\"email\" id=\"newsletter-email\"&gt;</code> (Footer form)",
                recommendation: "Change duplicate ID attributes to class names or rename them uniquely."
            },
            {
                page: `${url}/product.php?id=12`,
                type: "PHP Server Warning Log",
                details: "Warning: Undefined array key \"prod_desc\" in C:\\xampp\\htdocs\\pavitra\\product.php on line 42",
                recommendation: "Ensure request params are verified before array extraction (e.g. check isset($_GET['prod_desc']))."
            }
        ] : []
    };
}

function getSimulatedSeoData(url) {
    const isPavitra = url.toLowerCase().includes('pavitraherbal');
    return {
        status: "success",
        simulated: true,
        url: url,
        results: {
            point_1: {
                title: "Meta Description Tag",
                description: "Checks if a meta description tag is present to show structured preview text in search snippets.",
                status: isPavitra ? "FAIL" : "PASS",
                count: isPavitra ? 0 : 1,
                details: isPavitra ? ["No description tag found in HTML <head>."] : ["Meta description is active."]
            },
            point_2: {
                title: "Canonical Link Tag",
                description: "Verifies the presence of rel=\"canonical\" declaring the master page copy and avoiding duplicate index penalties.",
                status: isPavitra ? "FAIL" : "PASS",
                count: isPavitra ? 0 : 1,
                details: isPavitra ? ["No canonical link tag defined in head."] : ["Canonical URL is correctly configured."]
            },
            point_3: {
                title: "Robots Indexing Blocking Directive",
                description: "Ensures \"noindex\" values are omitted from robots directives to prevent blocking engines like Google.",
                status: "PASS",
                count: 0,
                details: ["Page is open for indexing (No blocking noindex directive found)."]
            },
            point_4: {
                title: "Image Alternative (Alt) Text",
                description: "Scans for image elements missing descriptive alt properties, critical for accessibility and image search indexing.",
                status: "WARNING",
                count: isPavitra ? 8 : 2,
                details: isPavitra ? [
                    `${url}/images/logo.png`,
                    `${url}/images/icons/whatsapp-chat.png`,
                    `${url}/images/products/herbal_shampoo.jpg`,
                    `${url}/images/products/aloe_vera_gel.jpg`
                ] : [`${url}/images/unlabeled_banner.png`]
            },
            point_5: {
                title: "Insecure HTTP Link Protocols",
                description: "Finds mixed content anchor links hardcoded with legacy HTTP protocol instead of secure HTTPS.",
                status: isPavitra ? "FAIL" : "PASS",
                count: isPavitra ? 3 : 0,
                details: isPavitra ? [
                    `http://www.pavitraherbal.com/about-us.php`,
                    `http://pavitraherbal.com/gallery.php`
                ] : []
            },
            point_6: {
                title: "Unsafe External Tab Links",
                description: "Checks if links opening in new tabs use rel=\"noopener\" or rel=\"noreferrer\" to prevent tab-nabbing security exploits.",
                status: "WARNING",
                count: isPavitra ? 2 : 0,
                details: isPavitra ? [
                    `https://instagram.com/pavitraherbal`,
                    `https://facebook.com/pavitraherbal`
                ] : []
            },
            point_7: {
                title: "Duplicate Title Tag Presence",
                description: "Validates that there is only one HTML <title> tag. Multiples cause browser confusion and index issues.",
                status: "PASS",
                count: 1,
                details: [isPavitra ? "Pavitra Herbal | Pure Ayurvedic & Natural Products" : "Default Title Tag"]
            },
            point_8: {
                title: "Favicon & Apple Icons",
                description: "Confirms favicon shortcuts are configured in head metadata, enabling browser address bar branding.",
                status: "PASS",
                count: 1,
                details: [`rel='shortcut icon' href='${url}/favicon.ico'`]
            },
            point_9: {
                title: "Descriptive Iframe Titles",
                description: "Ensures inline frames contain a descriptive title attribute to make content identifiable to screen readers.",
                status: isPavitra ? "WARNING" : "PASS",
                count: isPavitra ? 1 : 0,
                details: isPavitra ? [`https://www.google.com/maps/embed?...`] : []
            },
            point_10: {
                title: "Empty Link Elements (No Anchor Text)",
                description: "Flags links with no text or alt-tagged images, which are completely unreadable to crawlers and accessibility engines.",
                status: isPavitra ? "WARNING" : "PASS",
                count: isPavitra ? 4 : 0,
                details: isPavitra ? [
                    `${url}/cart.php`,
                    `${url}/wishlist.php`
                ] : []
            }
        }
    };
}

function getSimulatedImagesData(url) {
    return {
        status: "success",
        simulated: true,
        images: [
            {
                url: `${url}/images/logo.png`,
                original_size: 45120,
                webp_size: 12450,
                savings_bytes: 32670,
                savings_pct: 72.4
            },
            {
                url: `${url}/images/banner.jpg`,
                original_size: 340120,
                webp_size: 98140,
                savings_bytes: 241980,
                savings_pct: 71.1
            },
            {
                url: `${url}/images/products/herbal_shampoo.jpg`,
                original_size: 89450,
                webp_size: 21300,
                savings_bytes: 68150,
                savings_pct: 76.2
            },
            {
                url: `${url}/images/products/aloe_vera_gel.jpg`,
                original_size: 78500,
                webp_size: 19100,
                savings_bytes: 59400,
                savings_pct: 75.7
            }
        ]
    };
}
