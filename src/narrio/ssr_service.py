"""SSR content scraper service for fetching and parsing web content."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import httpx

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class Article:
    """Article data extracted from SSR source."""

    id: str
    title: str
    summary: str
    url: str


@dataclass
class Source:
    """SSR source containing multiple articles."""

    id: str
    name: str
    avatar: str
    description: str
    articles: list[Article]


class SSRSourceService:
    """Service for managing SSR sources and articles."""

    def __init__(self, config_path: Path | None = None):
        """Initialize the SSR source service.

        Args:
            config_path: Path to the YAML config file. If None, uses default location.
        """
        if config_path is None:
            config_path = Path.cwd().parent / "narrio-backend" / ".ssr-sources.yaml"

        self.config_path = config_path
        self._sources: list[Source] | None = None

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from YAML file."""
        if yaml is None:
            raise RuntimeError(
                "PyYAML is not installed. Install it with: pip install pyyaml"
            )

        if not self.config_path.exists():
            raise FileNotFoundError(f"SSR sources config not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def get_all_sources(self) -> list[Source]:
        """Get all configured SSR sources."""
        if self._sources is not None:
            return self._sources

        config = self._load_config()
        sources = []

        for source_data in config.get("sources", []):
            articles = [
                Article(
                    id=article["id"],
                    title=article["title"],
                    summary=article["summary"],
                    url=article["url"],
                )
                for article in source_data.get("articles", [])
            ]

            source = Source(
                id=source_data["id"],
                name=source_data["name"],
                avatar=source_data["avatar"],
                description=source_data["description"],
                articles=articles,
            )
            sources.append(source)

        self._sources = sources
        return sources

    def get_all_articles(self) -> list[Article]:
        """Get all articles from all sources."""
        sources = self.get_all_sources()
        return [article for source in sources for article in source.articles]

    def get_article_by_url(self, url: str) -> Article | None:
        """Get an article by its URL."""
        for article in self.get_all_articles():
            if article.url == url:
                return article
        return None

    def reload(self) -> None:
        """Reload sources from config file."""
        self._sources = None
        self.get_all_sources()


# Global service instance
_ssr_source_service: SSRSourceService | None = None


def get_source_service() -> SSRSourceService:
    """Get the global SSR source service instance."""
    global _ssr_source_service
    if _ssr_source_service is None:
        _ssr_source_service = SSRSourceService()
    return _ssr_source_service


class SSRContentScraper:
    """Service for scraping content from SSR URLs."""

    def __init__(self):
        """Initialize the SSR content scraper."""
        # Use a more realistic browser User-Agent with randomization
        import random

        user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
        ]

        # Build httpx configuration to avoid proxy issues
        client_kwargs = {
            "timeout": 30.0,
            "verify": False,  # Disable SSL verification for testing
            "headers": {
                "User-Agent": random.choice(user_agents),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0",
            },
        }

        # Only set proxies=None if not already configured via environment
        # This avoids conflicts with SOCKS proxy configurations
        try:
            self._client = httpx.AsyncClient(**client_kwargs)
        except Exception:
            # If proxy issues occur, try without any proxy settings
            client_kwargs.pop("proxies", None)
            self._client = httpx.AsyncClient(**client_kwargs)

        # Site-specific scrapers
        self._site_scrapers = {
            "sspai.com": self._scrape_sspai,
            "fs.blog": self._scrape_fsblog,
            "nesslabs.com": self._scrape_nesslabs,
        }

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def scrape_url(self, url: str) -> dict[str, Any]:
        """Scrape content from a URL.

        Args:
            url: The URL to scrape

        Returns:
            Dictionary containing scraped content with keys:
            - title: Page title
            - content: Main content text
            - cover: Cover image URL (if found)
            - url: Original URL

        Raises:
            httpx.HTTPError: If the request fails
            ValueError: If the URL is invalid
        """
        logger.info(f"Scraping content from: {url}")

        # Check if we have a site-specific scraper
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Remove www. prefix for matching
        if domain.startswith("www."):
            domain = domain[4:]

        # Try site-specific scraper first
        for site_domain, scraper in self._site_scrapers.items():
            if domain == site_domain or domain.endswith("." + site_domain):
                logger.info(f"Using site-specific scraper for: {site_domain}")
                try:
                    return await scraper(url)
                except Exception as e:
                    logger.warning(
                        f"Site-specific scraper failed for {site_domain}: {e}, falling back to generic scraper"
                    )
                    # Fall through to generic scraper

        response = await self._client.get(url, follow_redirects=True)
        response.raise_for_status()

        html_content = response.text
        return self._parse_html(html_content, url)

    async def _scrape_sspai(self, url: str) -> dict[str, Any]:
        """Scrape content from sspai.com (少数派).

        少数派使用 JavaScript 渲染，需要通过其 API 获取内容。
        API 端点：https://sspai.com/api/v1/article/{id}

        Args:
            url: 少数派文章 URL，格式如 https://sspai.com/post/{id}

        Returns:
            Dictionary with title, content, cover, and url
        """
        from urllib.parse import urlparse

        # 提取文章 ID
        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")

        # 支持两种 URL 格式：
        # 1. https://sspai.com/post/{id}
        # 2. https://sspai.com/article/{id}
        article_id = None
        if len(path_parts) >= 2:
            if path_parts[0] in ("post", "article"):
                article_id = path_parts[1]

        if not article_id:
            raise ValueError(f"无法从 URL 提取文章 ID: {url}")

        logger.info(f"Fetching 少数派 article {article_id} from API")

        # 少数派 API 端点
        api_url = f"https://sspai.com/api/v1/article/{article_id}"

        # 使用与主客户端相同的 User-Agent 轮询
        import random

        user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        ]

        response = await self._client.get(
            api_url,
            headers={
                "User-Agent": random.choice(user_agents),
                "Accept": "application/json, text/plain, */*",
                "Referer": url,
            },
        )
        response.raise_for_status()

        data = response.json()

        # 解析 API 响应
        if not data.get("data"):
            raise ValueError(f"少数派 API 返回空数据：{article_id}")

        article_data = data["data"]

        title = article_data.get("title", "Untitled")
        content = article_data.get("content", "")
        cover = article_data.get("banner") or article_data.get("cover_image", "")

        # 如果 cover 是相对路径，转换为绝对路径
        if cover and not cover.startswith("http"):
            cover = f"https://sspai.com{cover}"

        # 内容可能是 HTML 或 Markdown，需要清理
        if content:
            # 如果是 HTML，提取纯文本
            if content.strip().startswith("<"):
                content = self._html_to_text(content)

        return {
            "title": title,
            "content": content or "No content available",
            "cover": cover
            or "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?q=80&w=800&auto=format&fit=crop",
            "url": url,
        }

    async def _scrape_fsblog(self, url: str) -> dict[str, Any]:
        """Scrape content from fs.blog (Farnam Street).

        Farnam Street uses standard WordPress structure with Genesis theme.
        Content is in div.entry-content.entry-content-single.

        Args:
            url: Farnam Street article URL

        Returns:
            Dictionary with title, content, cover, and url
        """
        from bs4 import BeautifulSoup

        logger.info(f"Fetching Farnam Street article: {url}")

        response = await self._client.get(url, follow_redirects=True)
        response.raise_for_status()

        html_content = response.text
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract title from h1.entry-title
        title_tag = soup.find("h1", class_="entry-title")
        if title_tag:
            title = title_tag.get_text(strip=True)
        else:
            # Fall back to og:title or title tag
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                title = og_title["content"].strip()
            else:
                title_tag = soup.find("title")
                title = title_tag.string.strip() if title_tag and title_tag.string else "Untitled"

        # Extract content from div.entry-content.entry-content-single
        content_div = soup.find("div", class_="entry-content")
        if content_div:
            # Remove unwanted elements
            for element in content_div(["script", "style", "nav", "footer"]):
                element.decompose()

            # Get text content
            content = content_div.get_text(separator=" ", strip=True)
            # Clean up whitespace
            content = " ".join(content.split())
            # Truncate if too long
            if len(content) > 5000:
                content = content[:5000] + "..."
        else:
            content = "No content available"

        # Extract cover image from og:image
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            cover = og_image["content"].strip()
        else:
            # Try to find image in content
            cover = None
            if content_div:
                img = content_div.find("img", src=True)
                if img:
                    from urllib.parse import urljoin

                    cover = urljoin(url, img["src"])

        if not cover:
            cover = "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?q=80&w=800&auto=format&fit=crop"

        return {
            "title": title,
            "content": content,
            "cover": cover,
            "url": url,
        }

    async def _scrape_nesslabs(self, url: str) -> dict[str, Any]:
        """Scrape content from nesslabs.com.

        Ness Labs uses WordPress with Genesis theme.
        Content is in div.entry-content, title in h1.

        Args:
            url: Ness Labs article URL

        Returns:
            Dictionary with title, content, cover, and url
        """
        from bs4 import BeautifulSoup

        logger.info(f"Fetching Ness Labs article: {url}")

        response = await self._client.get(url, follow_redirects=True)
        response.raise_for_status()

        html_content = response.text
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract title from h1
        h1_tag = soup.find("h1", class_="entry-title")
        if h1_tag:
            title = h1_tag.get_text(strip=True)
        else:
            # Fall back to og:title or title tag
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                title = og_title["content"].strip()
            else:
                title_tag = soup.find("title")
                title = title_tag.string.strip() if title_tag and title_tag.string else "Untitled"

        # Extract content from div.entry-content
        content_div = soup.find("div", class_="entry-content")
        if content_div:
            # Remove unwanted elements
            for element in content_div(["script", "style", "nav", "footer"]):
                element.decompose()

            # Get text content
            content = content_div.get_text(separator=" ", strip=True)
            # Clean up whitespace
            content = " ".join(content.split())
            # Truncate if too long
            if len(content) > 5000:
                content = content[:5000] + "..."
        else:
            content = "No content available"

        # Extract cover image from og:image or article featured image
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            cover = og_image["content"].strip()
        else:
            # Try to find image in content
            cover = None
            if content_div:
                img = content_div.find("img", src=True)
                if img:
                    from urllib.parse import urljoin

                    cover = urljoin(url, img["src"])

        if not cover:
            cover = "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?q=80&w=800&auto=format&fit=crop"

        return {
            "title": title,
            "content": content,
            "cover": cover,
            "url": url,
        }

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(separator=" ", strip=True)

    def _parse_html(self, html: str, url: str) -> dict[str, Any]:
        """Parse HTML content and extract main content using BeautifulSoup.

        Args:
            html: Raw HTML content
            url: Source URL for resolving relative links

        Returns:
            Dictionary with title, content, cover, and url
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")

        # Extract title
        title = self._extract_title_bs4(soup)

        # Extract main content
        content = self._extract_content_bs4(soup)

        # Extract cover image
        cover = self._extract_cover_image_bs4(soup, url)

        return {
            "title": title,
            "content": content,
            "cover": cover,
            "url": url,
        }

    def _extract_title_bs4(self, soup: Any) -> str:
        """Extract page title using BeautifulSoup."""
        # Try <title> tag
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            return title_tag.string.strip()

        # Try <h1> tag
        h1_tag = soup.find("h1")
        if h1_tag:
            return h1_tag.get_text(strip=True)

        # Try og:title meta tag
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()

        # Try twitter:title
        twitter_title = soup.find("meta", attrs={"name": "twitter:title"})
        if twitter_title and twitter_title.get("content"):
            return twitter_title["content"].strip()

        return "Untitled"

    def _extract_content_bs4(self, soup: Any) -> str:
        """Extract main content using BeautifulSoup."""
        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        # Try to find article element
        article = soup.find("article")
        if article:
            content = article.get_text(separator=" ", strip=True)
            if len(content) > 100:
                return content[:5000] + ("..." if len(content) > 5000 else "")

        # Try to find main content by common class names
        for class_name in [
            "content",
            "article-content",
            "post-content",
            "entry-content",
            "main-content",
        ]:
            content_div = soup.find("div", class_=class_name)
            if content_div:
                content = content_div.get_text(separator=" ", strip=True)
                if len(content) > 100:
                    return content[:5000] + ("..." if len(content) > 5000 else "")

        # Fall back to body content
        body = soup.find("body")
        if body:
            content = body.get_text(separator=" ", strip=True)
        else:
            content = soup.get_text(separator=" ", strip=True)

        # Clean up whitespace
        content = " ".join(content.split())

        # Truncate if too long
        if len(content) > 5000:
            content = content[:5000] + "..."

        return content

    def _extract_cover_image_bs4(self, soup: Any, url: str) -> str:
        """Extract cover/og:image using BeautifulSoup."""
        from urllib.parse import urljoin

        # Try og:image meta tag
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            return urljoin(url, og_image["content"].strip())

        # Try twitter:image
        twitter_image = soup.find("meta", attrs={"name": "twitter:image"})
        if twitter_image and twitter_image.get("content"):
            return urljoin(url, twitter_image["content"].strip())

        # Try to find images with cover-related keywords
        for img in soup.find_all("img", src=True)[:10]:
            src = img["src"]
            if any(
                keyword in src.lower()
                for keyword in ["cover", "hero", "featured", "main", "banner"]
            ):
                return urljoin(url, src)

        # Return the first significant image (prefer larger ones)
        for img in soup.find_all("img", src=True)[:20]:
            src = img["src"]
            # Skip tiny images (likely icons)
            if any(
                skip in src.lower()
                for skip in ["icon", "logo", "avatar", "thumb", "sprite"]
            ):
                continue
            return urljoin(url, src)

        # Default placeholder
        return "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?q=80&w=800&auto=format&fit=crop"


# Global scraper instance
_scraper: SSRContentScraper | None = None


def get_scraper() -> SSRContentScraper:
    """Get the global SSR scraper instance."""
    global _scraper
    if _scraper is None:
        _scraper = SSRContentScraper()
    return _scraper
