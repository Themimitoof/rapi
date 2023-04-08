import enum
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, cast
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from pydantic import BaseModel, Field, PrivateAttr
from rapi.model.post import Post

log = logging.getLogger(__name__)


class ExportFormats(enum.Enum):
    atom = "atom"
    rss = "rss"
    json = "json"


class Site(BaseModel):
    home: Optional[str]
    site_name: Optional[str]
    description: Optional[str]
    favicon: Optional[str]
    timezone: Optional[str]

    url: str
    api_url: Optional[str]

    posts: List[Post] = Field(default=[])
    export_formats: List[ExportFormats]
    """List of formats rapi will export for this website."""

    _homepage_content: BeautifulSoup = PrivateAttr()
    _feed: FeedGenerator = PrivateAttr()

    def retrieve_site_data(self) -> None:
        self._retrieve_favicon_url()
        self._retrieve_site_info()
        self._retrieve_posts()

    def _retrieve_api_url(self):
        # First try with the default ``wp-json`` route.
        api_url = self.url.lstrip("/") + "/wp-json"
        resp = httpx.get(api_url, follow_redirects=True)

        if not resp.is_error:
            self.api_url = api_url
            return

        # If the default url doesn't work, parse the homepage and try to get
        # the URL of the API.
        if not self._homepage_content:
            resp = httpx.get(self.url, follow_redirects=True)
            self._homepage_content = BeautifulSoup(resp.content)

        api_tag = self._homepage_content.find("link", {"rel": "https://api.w.org/"})

        if api_tag:
            api_url = api_tag.attrs["href"]  # type: ignore
            resp = httpx.get(api_url, follow_redirects=True)

            if not resp.is_error:
                self.api_url = api_url
                return

        raise Exception("Unable to find a working API for %r", self)

    def _retrieve_favicon_url(self):
        favicon_url = self.url.lstrip("/") + "/favicon.ico"
        resp = httpx.get(favicon_url)

        if not resp.is_error:
            self.favicon = favicon_url
            return

        if not self._homepage_content:
            resp = httpx.get(self.url, follow_redirects=True)
            self._homepage_content = BeautifulSoup(resp.content)

        favicon_tag = self._homepage_content.find("link", {"rel", "icon"})

        if favicon_tag:
            self.favicon = favicon_url.attrs["href"]  # type: ignore
            return

    def _retrieve_site_info(self):
        if not self.api_url:
            self._retrieve_api_url()

        resp = httpx.get(cast(str, self.api_url), follow_redirects=True)

        if resp.is_error:
            resp.raise_for_status()

        content = resp.json()

        self.home = content["home"]
        self.site_name = content["name"]
        self.description = content["description"]
        self.timezone = content["timezone_string"]

    def _retrieve_posts(self, per_page: int = 10):
        if not self.api_url:
            self._retrieve_api_url()

        api_url = cast(str, self.api_url).rstrip("/")
        posts_url = f"{api_url}/wp/v2/posts?per_page={per_page}"
        resp = httpx.get(posts_url, follow_redirects=True)

        if resp.is_error:
            resp.raise_for_status()

        posts = resp.json()

        for p in posts:
            if p["status"] != "publish":
                continue

            featured_image = ""
            tz = ZoneInfo(self.timezone or "UTC")
            published_at = datetime.fromisoformat(p["date"]).replace(tzinfo=tz)
            modified_at = datetime.fromisoformat(p["modified"]).replace(tzinfo=tz)
            author = ""

            if published_at == modified_at:
                modified_at = None

            if p.get("featured_media"):
                image_id = p["featured_media"]
                image_metadata = httpx.get(
                    f"{api_url}/wp/v2/media/{image_id}", follow_redirects=True
                )

                if not image_metadata.is_error:
                    featured_image = image_metadata.json()["source_url"]

            author_id = p["author"]
            author_metadata = httpx.get(f"{api_url}/wp/v2/users/{author_id}")

            if author_metadata.is_error:
                author = f"'{self.site_name}' team"
            else:
                author = author_metadata.json()["name"]

            log.info(
                "Adding post %r by %r for %r", p["title"]["rendered"], author, self.url
            )
            self.posts.append(
                Post(
                    author=author,
                    content=p["content"]["rendered"],
                    featured_image=featured_image,
                    id=p["id"],
                    link=p["link"],
                    modified_at=modified_at,
                    published_at=published_at,
                    title=p["title"]["rendered"],
                )
            )

    def build_feed(self) -> FeedGenerator:
        feed = FeedGenerator()

        feed.id(self.url)
        feed.link({"href": self.home, "rel": "self"})

        feed.title(self.site_name)
        feed.description(self.description)

        feed.icon(self.favicon)
        feed.image(self.favicon)

        feed.generator("Rapi: https://github.com/themimitoof/rapi")

        for post in self.posts:
            fp = feed.add_entry()
            fp.id(post.id)
            fp.author({"name": post.author})
            fp.link(href=post.link)
            fp.title(post.title)

            content = post.content
            if post.featured_image:
                content = f'<img src="{post.featured_image}"><br/><br/>{post.content}'

            fp.content(content, type="CDATA")
            fp.pubDate(post.published_at)
            if post.modified_at:
                fp.updated(post.modified_at)

        self._feed = feed
        return feed

    # -- Feed generation

    @property
    def rss_feed(self) -> str:
        feed = getattr(self, "_feed", None)
        if not feed:
            feed = self.build_feed()

        return feed.rss_str(pretty=True).decode()

    @property
    def atom_feed(self) -> str:
        feed = getattr(self, "_feed", None)
        if not feed:
            feed = self.build_feed()

        return feed.atom_str(pretty=True).decode()

    @property
    def json_feed(self) -> str:
        raise NotImplementedError()

    def write_feeds(self, dest: Path):
        def write_feed(path: Path, content: str):
            log.info("Writing %s", path)
            with open(path, "w") as f:
                f.writelines(content)

        site_domain = cast(str, urlparse(self.url).hostname).replace(".", "-")
        for export_format in self.export_formats:
            if export_format == ExportFormats.atom:
                filename = f"atom-{site_domain}.xml"
                write_feed(Path.resolve(Path(dest, filename)), self.atom_feed)

            if export_format == ExportFormats.rss:
                filename = f"rss-{site_domain}.xml"
                write_feed(Path.resolve(Path(dest, filename)), self.rss_feed)

            if export_format == ExportFormats.json:
                filename = f"{site_domain}.json"
                write_feed(Path.resolve(Path(dest, filename)), self.json_feed)
