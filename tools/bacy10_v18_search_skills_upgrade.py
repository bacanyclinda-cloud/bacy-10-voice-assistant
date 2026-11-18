"""Fast, trustworthy web search that returns useful results directly to BACY-10.

The prior implementation only opened a search homepage, returning no results to
the voice model. This adds a compact HTTPS-backed public search with fallbacks,
and makes browser opening return page text where available.
"""
from pathlib import Path

QUICK_SEARCH = r'''
"""Safe search-only HTTP endpoints with RSS and HTML fallbacks."""
from __future__ import annotations

import html
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser


class SearchUnavailable(Exception):
    """All public search fallbacks failed."""


def _get(url: str, *, timeout: float = 7.0) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; BACY10Search/1.0; Android Assistant)",
        "Accept": "application/rss+xml,text/html;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=timeout) as response:
        payload = response.read(400_000)
    return payload.decode("utf-8", errors="replace")


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", value))).strip()


def parse_bing_rss(xml: str) -> list[dict[str, str]]:
    """Extract independent source URLs and readable summaries, no HTML to LLM."""
    root = ET.fromstring(xml)
    results = []
    for node in root.findall(".//item"):
        title = _clean(node.findtext("title", default=""))
        url = (node.findtext("link", default="") or "").strip()
        description = _clean(node.findtext("description", default=""))
        if title and url.startswith("https://") and len(url) < 2000:
            results.append({"title": title[:220], "url": url,
                            "summary": description[:650]})
    return results[:7]


class _LiteParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.results: list[dict[str, str]] = []
        self._href = ""
        self._text = []

    def handle_starttag(self, tag: str, attrs: list):
        data = dict(attrs)
        if tag == "a" and ("result-link" in data.get("class", "") or
            "result__a" in data.get("class", "")):
            self._href = data.get("href", "")
            self._text = []

    def handle_data(self, data: str):
        if self._href: self._text.append(data)

    def handle_endtag(self, tag: str):
        if tag != "a" or not self._href: return
        url = urllib.parse.urljoin("https://duckduckgo.com/", self._href)
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        if "uddg" in qs: url = qs["uddg"][0]
        title = _clean(" ".join(self._text))
        if url.startswith("https://") and title and len(url) < 2000:
            self.results.append({"title": title[:220], "url": url, "summary": ""})
        self._href = ""
        self._text = []


def search_public_web(query: str) -> dict:
    query = query.strip()[:250]
    if not query:
        raise ValueError("Please say what you want to search for.")
    encoded = urllib.parse.urlencode({"q": query})
    errors = []
    try:
        rss = _get("https://www.bing.com/search?format=rss&" + encoded)
        items = parse_bing_rss(rss)
        if items:
            return {"query": query, "engine": "Bing public RSS",
                    "results": items, "note": "Search result summaries; check each source for accuracy."}
        errors.append("RSS returned no readable results")
    except (OSError, ValueError, ET.ParseError, UnicodeError) as exc:
        errors.append("RSS: " + type(exc).__name__)
    try:
        source = _get("https://lite.duckduckgo.com/lite/?" + encoded)
        parser = _LiteParser()
        parser.feed(source)
        if parser.results:
            return {"query": query, "engine": "DuckDuckGo Lite",
                    "results": parser.results[:7],
                    "note": "These are search results; open primary sources to verify."}
        errors.append("Lite search returned no readable results")
    except (OSError, ValueError, UnicodeError) as exc:
        errors.append("Lite: " + type(exc).__name__)
    raise SearchUnavailable("No search service responded with usable results. " +
                            "; ".join(errors[:2]))
'''

def one(path: Path, old: str, new: str) -> None:
    content=path.read_text(encoding="utf-8")
    if content.count(old)!=1: raise RuntimeError(f"Unexpected source {path} anchor {old[:100]}")
    path.write_text(content.replace(old,new,1),encoding="utf-8")

def apply(root: Path) -> None:
    agent=root/"agent/src"
    (agent/"quick_search.py").write_text(QUICK_SEARCH,encoding="utf-8")
    tools=agent/"tools.py"
    one(tools,"from urllib.parse import urlencode",
        "import asyncio\nfrom urllib.parse import urlencode\n"
        "from quick_search import search_public_web, SearchUnavailable")
    old='''        try:
            return await self.browser.open_url(duckduckgo_search_url(query))
        except (BrowserError, ValueError) as exc:
            raise ToolError(str(exc)) from exc'''
    new='''        try:
            # Directly return titles, short summaries and source URLs, rather
            # than only opening a blank search page and making the model guess.
            return await asyncio.wait_for(asyncio.to_thread(search_public_web, query),
                                          timeout=17.0)
        except (SearchUnavailable, TimeoutError, ValueError):
            # Keep a browser fallback for networks that block RSS/Lite endpoints.
            try:
                await self.browser.open_url(duckduckgo_search_url(query))
                data = await self.browser.read_page(max_chars=6000)
                if not data.get("text"):
                    raise BrowserError("No readable search results appeared.")
                return {"query": query, "source": "DuckDuckGo browser fallback",
                        "text": data["text"], "url": data["url"]}
            except (BrowserError, ValueError) as exc:
                raise ToolError(
                    "I couldn't search the web just now. Please try again or name a specific website. "
                    + str(exc)) from exc'''
    one(tools,old,new)
    one(tools,'''            return await self.browser.open_url(url)
        except BrowserError as exc:''',
        '''            result = await self.browser.open_url(url)
            # Fetch useful page content in the same call; a title alone was
            # causing the AI to stop without answering what the page said.
            try:
                visible = await self.browser.read_page(max_chars=5500)
                return {"url": result["url"], "title": result["title"],
                        "text": str(visible.get("text", "")),
                        "truncated": bool(visible.get("truncated", False))}
            except BrowserError:
                return {"url": result["url"], "title": result["title"],
                        "text": "Page opened, but no readable content was available."}
        except BrowserError as exc:''')
    tests=root/"agent/tests/test_quick_search.py"
    tests.write_text('''from quick_search import parse_bing_rss, search_public_web
import pytest

def test_rss_search_parses_independent_citations():
    xml = "<rss><channel><item><title>A flight search result</title><link>https://example.org/airport</link><description>A useful summary.</description></item></channel></rss>"
    found = parse_bing_rss(xml)
    assert found[0]["url"] == "https://example.org/airport"
    assert found[0]["summary"] == "A useful summary."

def test_search_rejects_empty_query():
    with pytest.raises(ValueError):
        search_public_web(" ")
''',encoding="utf-8")
    a=agent/"agent.py"
    one(a, "                        # Tools\n\n                        - If the user names",
        """                        # Research and common-sense skills
                        - Answer basic questions directly from reliable knowledge, without invoking a browser just to speak. Do not apologize or say you do not know for ordinary questions you can explain.
                        - For anything current or location dependent, use search_the_web. It returns actual named results, snippets and source links in a single call, not just a search homepage.
                        - Use result summaries to give a concise first answer, cite the publisher or link when possible, and open the primary source if details are disputed or need confirmation.
                        - Never pretend you accessed a website, created a file or performed a phone action when a tool failed. State the failure briefly and offer an alternative.
                        - If results are unavailable, do not close the voice call; answer from background knowledge when appropriate, clearly marking uncertainty.
                        - Use direct Android tools first for navigation, alarms, apps, calls and messages. Use browser tools for browsing, not for controlling the phone.
                        - For explanations give a simple overview, then step-by-step details and an example when requested. For study topics, offer show_visual_lesson. For image creation use generate_image_with_ai, and PDF use export_pdf_to_phone.
                        - Never fabricate citations, current prices, business hours or factual search results.
                        - Search current information before claiming it is current.

                        # Tools

                        - If the user names""")
    pubspec=root/"mobile/pubspec.yaml"
    one(pubspec,"version: 1.7.0+21","version: 1.8.0+22")
'''
