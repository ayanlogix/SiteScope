import os
import sys
import json
import re
import zipfile
import urllib3
from io import BytesIO
from urllib.parse import urljoin, urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from bs4 import BeautifulSoup
from PIL import Image

# Disable warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PORT = 8085

class CrawlAuditHandler(BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        # Prevent server log spam in stderr to keep outputs clean
        pass

    def end_headers(self):
        # Enable CORS
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        # Static files serving logic
        if path == "/" or path == "":
            path = "/index.html"
            
        # Clean path relative to workspace
        local_path = "." + path
        
        if os.path.exists(local_path) and os.path.isfile(local_path):
            self.send_response(200)
            
            # Content types
            if path.endswith(".html"):
                self.send_header("Content-Type", "text/html; charset=utf-8")
            elif path.endswith(".css"):
                self.send_header("Content-Type", "text/css; charset=utf-8")
            elif path.endswith(".js"):
                self.send_header("Content-Type", "application/javascript; charset=utf-8")
            elif path.endswith(".png"):
                self.send_header("Content-Type", "image/png")
            elif path.endswith(".jpg") or path.endswith(".jpeg"):
                self.send_header("Content-Type", "image/jpeg")
            elif path.endswith(".webp"):
                self.send_header("Content-Type", "image/webp")
            else:
                self.send_header("Content-Type", "application/octet-stream")
                
            self.end_headers()
            with open(local_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def do_POST(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        # Read post body
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b""
        
        try:
            params = json.loads(post_data.decode('utf-8')) if post_data else {}
        except Exception:
            params = {}
            
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        
        if path == "/api/crawl":
            response_data = self.handle_crawl(params)
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            
        elif path == "/api/seo-audit":
            response_data = self.handle_seo_audit(params)
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            
        elif path == "/api/extract-images":
            response_data = self.handle_extract_images(params)
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            
        elif path == "/api/download-zip":
            # For downloading zip file, content type should be zip
            self.send_response(200)
            self.send_header('Content-Type', 'application/zip')
            self.send_header('Content-Disposition', 'attachment; filename="site_webp_audit.zip"')
            self.end_headers()
            zip_data = self.handle_download_zip(params)
            self.wfile.write(zip_data)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode('utf-8'))

    # --- Crawling Handler ---
    def handle_crawl(self, params):
        start_url = params.get("url", "").strip()
        max_depth = int(params.get("depth", 2))
        
        if not start_url:
            return {"status": "error", "message": "Missing target URL"}
            
        if not (start_url.startswith("http://") or start_url.startswith("https://")):
            start_url = "https://" + start_url
            
        domain = urlparse(start_url).netloc
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        visited_pages = set()
        to_visit = [(start_url, 0)]
        
        broken_links = []
        broken_images = []
        broken_assets = []
        code_errors = []
        
        checked_assets = set()
        
        # Regex flags for server issues
        php_text_pattern = re.compile(r"(?:Fatal error|Parse error|Warning|Notice):\s+.*?\s+in\s+.*?\s+on\s+line\s+\d+", re.IGNORECASE)
        php_html_pattern = re.compile(r"<b>(?:Fatal error|Parse error|Warning|Notice)</b>:\s+.*?\s+in\s+<b>.*?\s+on\s+line\s+<b>\d+</b>", re.IGNORECASE)
        db_error_pattern = re.compile(r"(?:SQLSTATE\[[a-zA-Z0-9]+\]|mysqli_sql_exception|PDOException|database error)", re.IGNORECASE)

        def is_internal(url):
            return urlparse(url).netloc == domain

        def check_url(url):
            try:
                res = session.head(url, timeout=5, verify=False, allow_redirects=True)
                if res.status_code in [404, 405]:
                    res = session.get(url, timeout=5, verify=False)
                return res.status_code
            except Exception:
                return 0

        while to_visit:
            current_url, depth = to_visit.pop(0)
            
            if current_url in visited_pages or depth > max_depth:
                continue
                
            visited_pages.add(current_url)
            
            try:
                response = session.get(current_url, timeout=10, verify=False)
                if response.status_code != 200:
                    broken_links.append({
                        "url": current_url,
                        "parent": current_url,
                        "status": response.status_code,
                        "type": "Broken Page Link",
                        "recommendation": f"Page returned non-200 HTTP code. Fix the routing or page at {current_url}."
                    })
                    continue
            except Exception as e:
                broken_links.append({
                    "url": current_url,
                    "parent": current_url,
                    "status": "Failed Connection",
                    "type": "Connection Issue",
                    "recommendation": f"Failed to connect: {str(e)}"
                })
                continue
                
            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 1. Look for Server-Side Bugs/Errors
            html_matches = php_html_pattern.findall(html_content)
            for match in html_matches:
                clean_text = BeautifulSoup(match, 'html.parser').get_text()
                code_errors.append({
                    "page": current_url,
                    "type": "PHP Server HTML Error",
                    "details": clean_text,
                    "recommendation": "Fix php script syntax or check include files."
                })
            
            text_matches = php_text_pattern.findall(html_content)
            for match in text_matches:
                code_errors.append({
                    "page": current_url,
                    "type": "PHP Server Text Error",
                    "details": match,
                    "recommendation": "Fix syntax error or PHP code execution failures."
                })
                
            db_matches = db_error_pattern.findall(html_content)
            for match in db_matches:
                snippet_match = re.search(r"(.{0,50}" + re.escape(match) + r".{0,100})", html_content, re.IGNORECASE)
                snippet = snippet_match.group(0).strip() if snippet_match else match
                code_errors.append({
                    "page": current_url,
                    "type": "Database Connection/Query Bug",
                    "details": snippet,
                    "recommendation": "Fix SQL query formatting or restore database connection."
                })

            # 2. Check for Duplicate HTML Element IDs
            id_elements = {}
            for element in soup.find_all(id=True):
                el_id = element['id'].strip()
                if el_id:
                    if el_id not in id_elements:
                        id_elements[el_id] = []
                    tag_str = str(element)
                    closing_idx = tag_str.find('>')
                    opening_tag = tag_str[:closing_idx + 1] if closing_idx != -1 else tag_str[:80]
                    id_elements[el_id].append(opening_tag)

            for el_id, tags in id_elements.items():
                if len(tags) > 1:
                    code_errors.append({
                        "page": current_url,
                        "type": "Duplicate HTML ID",
                        "details": f"ID '{el_id}' is defined {len(tags)} times. Affected tags:<br>" + "<br>".join([f"&bull; <code>{t.replace('<', '&lt;').replace('>', '&gt;')}</code>" for t in tags]),
                        "recommendation": "Standard HTML requires unique IDs. Change duplicates to classes or rename them."
                    })

            # 3. Check stylesheet assets
            for link in soup.find_all('link', rel='stylesheet', href=True):
                href = link['href'].strip()
                if href:
                    full_asset_url = urljoin(current_url, href)
                    if full_asset_url not in checked_assets:
                        checked_assets.add(full_asset_url)
                        status = check_url(full_asset_url)
                        if status != 200:
                            broken_assets.append({
                                "url": full_asset_url,
                                "parent": current_url,
                                "status": status,
                                "type": "Stylesheet (CSS)",
                                "recommendation": f"CSS stylesheet at {full_asset_url} returned status {status}. Verify file path."
                            })

            # 4. Check JS scripts
            for script in soup.find_all('script', src=True):
                src = script['src'].strip()
                if src and not src.startswith('javascript:'):
                    full_asset_url = urljoin(current_url, src)
                    if full_asset_url not in checked_assets:
                        checked_assets.add(full_asset_url)
                        status = check_url(full_asset_url)
                        if status != 200:
                            broken_assets.append({
                                "url": full_asset_url,
                                "parent": current_url,
                                "status": status,
                                "type": "JavaScript Script",
                                "recommendation": f"JavaScript file at {full_asset_url} returned status {status}. Verify file path."
                            })

            # 5. Check images
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src') or ''
                if not src:
                    broken_images.append({
                        "url": "(Missing src attribute)",
                        "parent": current_url,
                        "status": "N/A",
                        "recommendation": "Add a valid src attribute to the img tag."
                    })
                    continue
                full_img_url = urljoin(current_url, src)
                if full_img_url not in checked_assets:
                    checked_assets.add(full_img_url)
                    status = check_url(full_img_url)
                    if status != 200:
                        broken_images.append({
                            "url": full_img_url,
                            "parent": current_url,
                            "status": status,
                            "recommendation": f"Image at {full_img_url} returned status {status}. Confirm file exists."
                        })

            # 6. Gather links for internal crawling
            if depth < max_depth:
                for a in soup.find_all('a', href=True):
                    href = a['href'].strip()
                    if not href or href.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
                        continue
                    full_link_url = urljoin(current_url, href)
                    clean_link = full_link_url.split('#')[0].split('?')[0].rstrip('/')
                    
                    if is_internal(clean_link):
                        if clean_link not in visited_pages and not any(clean_link.lower().endswith(ext) for ext in ['.pdf', '.zip', '.jpg', '.png', '.jpeg', '.webp']):
                            to_visit.append((clean_link, depth + 1))
                    else:
                        # Verify external links as broken links check
                        if full_link_url not in checked_assets:
                            checked_assets.add(full_link_url)
                            # Simple status check for external links
                            status = check_url(full_link_url)
                            if status != 200:
                                broken_links.append({
                                    "url": full_link_url,
                                    "parent": current_url,
                                    "status": status,
                                    "type": "External Hyperlink",
                                    "recommendation": f"External link to {full_link_url} returned status {status}. Double check URL."
                                })

        return {
            "status": "success",
            "url": start_url,
            "crawled_pages": list(visited_pages),
            "broken_links": broken_links,
            "broken_images": broken_images,
            "broken_assets": broken_assets,
            "code_errors": code_errors
        }

    # --- SEO Audit Handler ---
    def handle_seo_audit(self, params):
        target_url = params.get("url", "").strip()
        if not target_url:
            return {"status": "error", "message": "Missing target URL"}
            
        if not (target_url.startswith("http://") or target_url.startswith("https://")):
            target_url = "https://" + target_url

        try:
            response = requests.get(target_url, timeout=12, verify=False)
            response.raise_for_status()
        except Exception as e:
            return {"status": "error", "message": f"Could not fetch website: {str(e)}"}

        soup = BeautifulSoup(response.text, 'html.parser')
        results = {}

        # Point 1: Meta Description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        desc_content = meta_desc.get('content', '').strip() if meta_desc else None
        results['point_1'] = {
            'title': 'Meta Description Tag',
            'description': 'Checks if a meta description tag is present to show structured preview text in search snippets.',
            'status': 'PASS' if desc_content else 'FAIL',
            'count': 1 if desc_content else 0,
            'details': [desc_content] if desc_content else ["No description tag found in <head>."]
        }

        # Point 2: Canonical URL Link
        canonical = soup.find('link', rel='canonical')
        canonical_href = canonical.get('href', '').strip() if canonical else None
        results['point_2'] = {
            'title': 'Canonical Link Tag',
            'description': 'Verifies the presence of rel="canonical" declaring the master page copy and avoiding duplicate index penalties.',
            'status': 'PASS' if canonical_href else 'FAIL',
            'count': 1 if canonical_href else 0,
            'details': [canonical_href] if canonical_href else ["No canonical link tag defined in head."]
        }

        # Point 3: Robots directives
        robots_meta = soup.find('meta', attrs={'name': 'robots'})
        robots_content = robots_meta.get('content', '').lower() if robots_meta else ''
        is_blocked = 'noindex' in robots_content or 'none' in robots_content
        results['point_3'] = {
            'title': 'Robots Indexing Blocking Directive',
            'description': 'Ensures "noindex" values are omitted from robots directives to prevent blocking engines like Google.',
            'status': 'FAIL' if is_blocked else 'PASS',
            'count': 1 if is_blocked else 0,
            'details': [f"Robots content: '{robots_meta.get('content')}' blocking indexing!"] if is_blocked else ["Page is open for indexing (No blocking noindex directive found)."]
        }

        # Point 4: Alt properties on images
        img_tags = soup.find_all('img')
        missing_alts = []
        for img in img_tags:
            if not img.has_attr('alt') or not img.get('alt', '').strip():
                src = img.get('src') or img.get('data-src') or 'unknown-src'
                missing_alts.append(src)
        results['point_4'] = {
            'title': 'Image Alternative (Alt) Text',
            'description': 'Scans for image elements missing descriptive alt properties, critical for accessibility and image search indexing.',
            'status': 'WARNING' if missing_alts else 'PASS',
            'count': len(missing_alts),
            'details': missing_alts[:10]
        }

        # Point 5: Insecure HTTP links
        insecure_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('http://'):
                insecure_links.append(href)
        results['point_5'] = {
            'title': 'Insecure HTTP Link Protocols',
            'description': 'Finds mixed content anchor links hardcoded with legacy HTTP protocol instead of secure HTTPS.',
            'status': 'FAIL' if insecure_links else 'PASS',
            'count': len(insecure_links),
            'details': insecure_links[:10]
        }

        # Point 6: Target="_blank" noopener
        unsafe_links = []
        for a in soup.find_all('a', href=True, target=True):
            if a['target'] == '_blank':
                rel = a.get('rel', '')
                if not rel or ('noopener' not in rel.lower() and 'noreferrer' not in rel.lower()):
                    unsafe_links.append(a['href'])
        results['point_6'] = {
            'title': 'Unsafe External Tab Links',
            'description': 'Checks if links opening in new tabs use rel="noopener" or rel="noreferrer" to prevent tab-nabbing security exploits.',
            'status': 'WARNING' if unsafe_links else 'PASS',
            'count': len(unsafe_links),
            'details': unsafe_links[:10]
        }

        # Point 7: Duplicate Title Tags
        title_tags = soup.find_all('title')
        title_count = len(title_tags)
        results['point_7'] = {
            'title': 'Duplicate Title Tag Presence',
            'description': 'Validates that there is only one HTML <title> tag. Multiples cause browser confusion and index issues.',
            'status': 'PASS' if title_count <= 1 else 'FAIL',
            'count': title_count,
            'details': [t.text for t in title_tags] if title_count > 0 else ["No title tag found!"]
        }

        # Point 8: Favicons
        favicon_links = soup.find_all('link', rel=lambda x: x and any(k in x.lower() for k in ['icon', 'shortcut']))
        results['point_8'] = {
            'title': 'Favicon & Apple Icons',
            'description': 'Confirms favicon shortcuts are configured in head metadata, enabling browser address bar branding.',
            'status': 'PASS' if favicon_links else 'WARNING',
            'count': len(favicon_links),
            'details': [f"rel='{l.get('rel')}' href='{l.get('href')}'" for l in favicon_links[:5]]
        }

        # Point 9: Descriptive iframe titles
        iframes = soup.find_all('iframe')
        missing_iframe_titles = []
        for iframe in iframes:
            if not iframe.has_attr('title') or not iframe.get('title', '').strip():
                src = iframe.get('src') or 'unknown-src'
                missing_iframe_titles.append(src)
        results['point_9'] = {
            'title': 'Descriptive Iframe Titles',
            'description': 'Ensures inline frames contain a descriptive title attribute to make content identifiable to screen readers.',
            'status': 'WARNING' if missing_iframe_titles else 'PASS',
            'count': len(missing_iframe_titles),
            'details': missing_iframe_titles[:10]
        }

        # Point 10: Empty Anchor links
        empty_links = []
        for a in soup.find_all('a', href=True):
            text = a.get_text(strip=True)
            has_alt_img = False
            for img in a.find_all('img'):
                if img.get('alt', '').strip():
                    has_alt_img = True
                    break
            if not text and not has_alt_img:
                empty_links.append(a['href'])
        results['point_10'] = {
            'title': 'Empty Link Elements (No Anchor Text)',
            'description': 'Flags links with no text or alt-tagged images, which are completely unreadable to crawlers and accessibility engines.',
            'status': 'WARNING' if empty_links else 'PASS',
            'count': len(empty_links),
            'details': empty_links[:10]
        }

        return {
            "status": "success",
            "url": target_url,
            "results": results
        }

    # --- Extract Images and WebP Savings Handler ---
    def handle_extract_images(self, params):
        start_url = params.get("url", "").strip()
        max_depth = int(params.get("depth", 1)) # Default 1 to save processing speed
        
        if not start_url:
            return {"status": "error", "message": "Missing target URL"}
            
        if not (start_url.startswith("http://") or start_url.startswith("https://")):
            start_url = "https://" + start_url

        domain = urlparse(start_url).netloc
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        })
        
        visited_pages = set()
        all_img_urls = set()
        to_crawl = [(start_url, 0)]
        
        # Scrape pages to collect image URLs
        while to_crawl:
            url, depth = to_crawl.pop(0)
            if url in visited_pages or depth > max_depth:
                continue
            visited_pages.add(url)
            
            try:
                res = session.get(url, timeout=10, verify=False)
                if res.status_code != 200 or 'text/html' not in res.headers.get('Content-Type', ''):
                    continue
                    
                soup = BeautifulSoup(res.text, 'html.parser')
                
                # Image tags
                for img in soup.find_all(['img', 'source']):
                    src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('srcset')
                    if src:
                        if ',' in src:
                            src = src.split(',')[0].strip().split(' ')[0]
                        full_src = urljoin(url, src)
                        # Filter to standard extensions
                        if any(full_src.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']):
                            all_img_urls.add(full_src)
                            
                # Internal links to crawl more
                if depth < max_depth:
                    for a in soup.find_all('a', href=True):
                        link = urljoin(url, a['href'])
                        clean_link = link.split('#')[0].rstrip('/')
                        if urlparse(clean_link).netloc == domain:
                            if clean_link not in visited_pages and not any(clean_link.lower().endswith(ext) for ext in ['.pdf', '.zip', '.jpg', '.png', '.jpeg', '.webp']):
                                to_crawl.append((clean_link, depth + 1))
            except Exception:
                pass

        # Calculate WebP sizes and savings
        images_stats = []
        for img_url in sorted(list(all_img_urls))[:40]: # Cap at 40 images to prevent execution timeouts
            try:
                # Fetch image binary
                img_res = session.get(img_url, timeout=10, verify=False)
                if img_res.status_code != 200 or 'image' not in img_res.headers.get('Content-Type', ''):
                    continue
                    
                original_bytes = len(img_res.content)
                
                # Convert to WebP in memory
                img = Image.open(BytesIO(img_res.content))
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGBA")
                else:
                    img = img.convert("RGB")
                    
                webp_io = BytesIO()
                img.save(webp_io, format="WEBP", quality=80)
                webp_bytes = len(webp_io.getvalue())
                
                savings = original_bytes - webp_bytes
                savings_pct = (savings / original_bytes) * 100 if original_bytes > 0 else 0
                
                images_stats.append({
                    "url": img_url,
                    "original_size": original_bytes,
                    "webp_size": webp_bytes,
                    "savings_bytes": savings,
                    "savings_pct": round(savings_pct, 1)
                })
            except Exception:
                pass
                
        return {
            "status": "success",
            "images": images_stats
        }

    # --- ZIP Packer & Report Exporter ---
    def handle_download_zip(self, params):
        url = params.get("url", "").strip()
        selected_images = params.get("images", []) # List of image URLs
        crawl_results = params.get("crawl_results", {})
        seo_results = params.get("seo_results", {})
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # 1. Package selected images
            for i, img_url in enumerate(selected_images):
                try:
                    img_res = session.get(img_url, timeout=10, verify=False)
                    if img_res.status_code == 200:
                        parsed_url = urlparse(img_url)
                        base_name = os.path.basename(parsed_url.path)
                        if not base_name:
                            base_name = f"image_{i}"
                        
                        clean_name = re.sub(r'[^a-zA-Z0-9._-]', '', base_name)
                        name_part = os.path.splitext(clean_name)[0]
                        if not name_part:
                            name_part = f"image_{i}"
                            
                        # Convert to webp
                        img = Image.open(BytesIO(img_res.content))
                        if img.mode in ("RGBA", "P"):
                            img = img.convert("RGBA")
                        else:
                            img = img.convert("RGB")
                            
                        webp_io = BytesIO()
                        img.save(webp_io, format="WEBP", quality=80)
                        
                        zip_file.writestr(f"webp_images/{name_part}.webp", webp_io.getvalue())
                except Exception:
                    pass

            # 2. Write HTML Audit Report
            html_report = self.generate_html_report_string(url, crawl_results, seo_results)
            zip_file.writestr("audit_report.html", html_report.encode('utf-8'))
            
        return zip_buffer.getvalue()

    def generate_html_report_string(self, url, crawl, seo):
        # Generates a premium flat-themed self-contained HTML report file
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SiteScope Audit Report - {urlparse(url).netloc}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #0b0f19;
            color: #f3f4f6;
            margin: 0;
            padding: 30px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}
        h1 {{
            font-size: 2.2rem;
            color: #ffffff;
            margin-bottom: 5px;
            border-bottom: 2px solid #1f2937;
            padding-bottom: 10px;
        }}
        .meta-text {{
            color: #9ca3af;
            font-size: 0.95rem;
            margin-bottom: 30px;
        }}
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .card {{
            background-color: #111827;
            border: 1px solid #1f2937;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .card .value {{
            font-size: 2rem;
            font-weight: bold;
            color: #3b82f6;
        }}
        .card .label {{
            font-size: 0.85rem;
            color: #9ca3af;
            text-transform: uppercase;
            margin-top: 5px;
        }}
        .section-title {{
            font-size: 1.5rem;
            color: #ffffff;
            margin-top: 40px;
            margin-bottom: 20px;
            border-left: 4px solid #6366f1;
            padding-left: 10px;
        }}
        .issue-card {{
            background-color: #111827;
            border: 1px solid #1f2937;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
        }}
        .issue-card.fail {{ border-left: 4px solid #ef4444; }}
        .issue-card.warn {{ border-left: 4px solid #f59e0b; }}
        .issue-card.pass {{ border-left: 4px solid #10b981; }}
        .issue-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .issue-title {{
            font-size: 1.15rem;
            font-weight: 600;
            color: #ffffff;
        }}
        .badge {{
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: bold;
            text-transform: uppercase;
        }}
        .badge.fail {{ background-color: rgba(239, 68, 68, 0.15); color: #ef4444; }}
        .badge.warn {{ background-color: rgba(245, 158, 11, 0.15); color: #f59e0b; }}
        .badge.pass {{ background-color: rgba(16, 185, 129, 0.15); color: #10b981; }}
        .issue-details {{
            font-family: monospace;
            font-size: 0.85rem;
            background-color: #060913;
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
            overflow-x: auto;
        }}
        .recommendation {{
            font-size: 0.9rem;
            color: #cbd5e1;
            margin-top: 10px;
        }}
        @media print {{
            body {{
                background-color: #ffffff;
                color: #000000;
                padding: 0;
            }}
            .card, .issue-card {{
                border: 1px solid #d1d5db;
                background-color: #f9fafb;
                page-break-inside: avoid;
            }}
            h1, .section-title, .issue-title {{
                color: #000000;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Technical Site Audit Report</h1>
        <div class="meta-text">Target URL: {url} | Generated by SiteScope — Web Crawler &amp; SEO Auditor</div>
        
        <div class="summary-cards">
            <div class="card">
                <div class="value">{len(crawl.get('crawled_pages', []))}</div>
                <div class="label">Pages Crawled</div>
            </div>
            <div class="card">
                <div class="value" style="color: #ef4444;">{len(crawl.get('broken_links', [])) + len(crawl.get('broken_images', []))}</div>
                <div class="label">Broken Assets</div>
            </div>
            <div class="card">
                <div class="value" style="color: #f59e0b;">{len(crawl.get('code_errors', []))}</div>
                <div class="label">Syntax & DOM Bugs</div>
            </div>
        </div>

        <div class="section-title">10-Point Technical SEO & DOM Checks</div>
        """
        
        for key, res in sorted(seo.get("results", {}).items(), key=lambda x: int(x[0].split('_')[1])):
            status_class = res['status'].lower()
            badge_html = f"<span class='badge {status_class}'>{res['status']}</span>"
            details_html = ""
            if res['details']:
                items = "".join([f"<li>{item}</li>" for item in res['details']])
                details_html = f"<div class='issue-details'><ul>{items}</ul></div>"
                
            html += f"""
            <div class="issue-card {status_class}">
                <div class="issue-header">
                    <span class="issue-title">{res['title']}</span>
                    {badge_html}
                </div>
                <div style="color: #9ca3af; font-size: 0.9rem;">{res['description']}</div>
                {details_html}
            </div>
            """
            
        html += """
    </div>
</body>
</html>
"""
        return html

def run(server_class=HTTPServer, handler_class=CrawlAuditHandler):
    server_address = ('', PORT)
    httpd = server_class(server_address, handler_class)
    print(f"🚀 Crawl & Audit Studio Server active on http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Crawl & Audit Studio Server...")
        httpd.server_close()

if __name__ == "__main__":
    run()
