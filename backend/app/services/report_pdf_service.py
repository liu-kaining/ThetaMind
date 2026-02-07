"""Report PDF generation (EquityCompass-style: server-side Playwright)."""

import asyncio
import html
import logging
from io import BytesIO

import markdown as md_lib

logger = logging.getLogger(__name__)

# EC-style markdown-content CSS (from EquityCompass reports/detail.html)
MARKDOWN_CSS = """
.markdown-content {
  line-height: 1.8;
  color: #2c3e50;
  font-size: 15px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  padding: 2rem;
  max-width: 100%;
}
.markdown-content > *:first-child { margin-top: 0; padding-top: 0; }
.markdown-content h1 { font-size: 2.2rem; font-weight: 700; margin-top: 0; margin-bottom: 1.5rem; padding-bottom: 0.8rem; border-bottom: 3px solid #3182ce; color: #1a202c; }
.markdown-content h2 { font-size: 1.8rem; font-weight: 700; margin-top: 2.5rem; margin-bottom: 1.5rem; padding-bottom: 0.5rem; border-bottom: 2px solid #e2e8f0; color: #2d3748; }
.markdown-content h3 { font-size: 1.5rem; font-weight: 700; margin-top: 2rem; margin-bottom: 1rem; color: #4a5568; border-left: 4px solid #3182ce; padding-left: 1rem; }
.markdown-content h4, .markdown-content h5, .markdown-content h6 { font-size: 1.2rem; margin-top: 1.5rem; margin-bottom: 0.75rem; color: #718096; }
.markdown-content p { margin-bottom: 1.5rem; line-height: 1.8; color: #2d3748; text-align: justify; }
.markdown-content ul, .markdown-content ol { margin-bottom: 1.5rem; padding-left: 2.5rem; }
.markdown-content li { margin-bottom: 0.8rem; line-height: 1.7; color: #2d3748; }
.markdown-content ul li::before { content: "•"; color: #3182ce; font-weight: bold; }
.markdown-content strong { font-weight: 700; color: #1a202c; }
.markdown-content em { font-style: italic; color: #4a5568; }
.markdown-content code { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 0.3rem 0.6rem; border-radius: 4px; font-family: ui-monospace, monospace; font-size: 0.9em; }
.markdown-content pre { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1.5rem; border-radius: 8px; overflow-x: auto; margin: 2rem 0; }
.markdown-content pre code { background: none; padding: 0; }
.markdown-content blockquote { border-left: 5px solid #3182ce; padding: 1.5rem 2rem; margin: 2rem 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 0 8px 8px 0; font-style: italic; }
.markdown-content table { width: 100%; border-collapse: collapse; margin: 2rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; }
.markdown-content th, .markdown-content td { border: 1px solid #e2e8f0; padding: 1rem; text-align: left; }
.markdown-content th { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-weight: 600; }
.markdown-content tr:nth-child(even) { background-color: #f7fafc; }
.markdown-content hr { margin: 1.5rem 0; border-color: #e2e8f0; }
.report-header { text-align: center; margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 2px solid #e2e8f0; }
.report-header h1 { font-size: 1.75rem; margin: 0; border: none; padding: 0; }
.report-meta { font-size: 0.9rem; color: #718096; margin-top: 0.5rem; }
"""


def _markdown_to_html(content: str) -> str:
    """Convert markdown to HTML (GFM)."""
    return md_lib.markdown(
        content,
        extensions=["extra", "nl2br", "sane_lists", "tables", "fenced_code"],
    )


def _build_report_html(report_content: str, model_used: str, created_at: str) -> str:
    """Build full HTML document for report (EC-style)."""
    body_html = _markdown_to_html(report_content or "")
    if not body_html.strip().startswith("<"):
        body_html = f"<p>{html.escape(body_html)}</p>"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>ThetaMind Strategy Report</title>
  <style>{MARKDOWN_CSS}</style>
</head>
<body style="margin:0;padding:0;background:#fff;">
  <div class="report-header">
    <h1>ThetaMind AI Analysis Report</h1>
    <div class="report-meta">Model: {html.escape(model_used or "N/A")} · Generated: {html.escape(created_at)}</div>
  </div>
  <div class="markdown-content">
    {body_html}
  </div>
</body>
</html>"""


def _generate_pdf_sync(html_content: str) -> bytes:
    """Generate PDF from HTML using Playwright (sync, run in thread)."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-setuid-sandbox",
            ],
        )
        page = browser.new_page()
        page.set_default_timeout(30000)  # 30s max for set_content / pdf
        # Use domcontentloaded: networkidle can hang for local HTML (no network requests)
        page.set_content(html_content, wait_until="domcontentloaded")
        pdf_bytes = page.pdf(
            format="A4",
            margin={"top": "20mm", "right": "15mm", "bottom": "20mm", "left": "15mm"},
            print_background=True,
        )
        browser.close()
    return pdf_bytes


async def generate_report_pdf(report_content: str, model_used: str, created_at: str) -> bytes:
    """Generate PDF bytes for a report (EC-style). Runs Playwright in thread pool.
    Timeout: 90s to avoid hanging if Chromium fails to launch.
    """
    html_content = _build_report_html(report_content, model_used, created_at)
    loop = asyncio.get_event_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, _generate_pdf_sync, html_content),
            timeout=90.0,
        )
    except asyncio.TimeoutError:
        logger.error("PDF generation timed out after 90s (Playwright/Chromium may be slow or stuck)")
        raise
