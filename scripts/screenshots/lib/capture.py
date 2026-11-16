"""Capture the UI screenshots of one example from its running local stack.

The pages to capture are listed in ``<domain>/screenshots.json``. For each site the script opens a fresh
browser session, signs in through the stack's Zitadel when the site asks for it, visits each page and
saves a 1280x800 WebP under ``<domain>/screenshots/``. It reports any console error, failed request or
HTTP error status a page produced on this machine; requests to other hosts (map tiles) are not judged.

The stack must already be running (``scripts/deploy.*`` of the generated ``docker-*`` tree) and the
signing-in user must exist and hold the roles the pages need. The password comes from the environment
variable ``CRUFTFREE_SCREENSHOT_PASSWORD`` and never from the command line.

Needs ``playwright`` (and a Chromium: ``playwright install chromium``) and ``pillow``.

Exit codes: 0 every page captured cleanly, 1 captured with problems reported, 2 could not run.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final
from urllib.parse import urlparse

if TYPE_CHECKING:
    from playwright.sync_api import Browser, Page

EXIT_OK: Final = 0
EXIT_PROBLEMS: Final = 1
EXIT_ERROR: Final = 2

MANIFEST_NAME: Final = "screenshots.json"
OUTPUT_DIR: Final = "screenshots"
USER_ENV: Final = "CRUFTFREE_SCREENSHOT_USER"
PASSWORD_ENV: Final = "CRUFTFREE_SCREENSHOT_PASSWORD"
BROWSER_ENV: Final = "CRUFTFREE_BROWSER_EXE"

VIEWPORT: Final = {"width": 1280, "height": 800}
WEBP_QUALITY: Final = 82
DEFAULT_SETTLE_MS: Final = 1500
SIGN_IN_SETTLE_MS: Final = 3000
FILE_PATTERN: Final = re.compile(r"^[a-z0-9][a-z0-9-]*$")
LOCAL_HOSTS: Final = frozenset({"localhost", "127.0.0.1", "::1"})
MAX_PROBLEMS_SHOWN: Final = 24


class ManifestError(ValueError):
    """The manifest of a domain cannot be used."""


class CaptureError(RuntimeError):
    """A site could not be captured at all (sign-in failed, the stack is not answering)."""


@dataclass(frozen=True)
class Shot:
    """One page to capture."""

    path: str
    file: str
    caption: str
    settle_ms: int


@dataclass(frozen=True)
class Site:
    """One web app of the stack."""

    name: str
    url: str
    sign_in: bool
    shots: tuple[Shot, ...]


@dataclass(frozen=True)
class Manifest:
    """What to capture for a domain."""

    hero: str
    sites: tuple[Site, ...]

    @property
    def files(self) -> list[str]:
        """Every screenshot file name (no extension), in manifest order."""
        return [shot.file for site in self.sites for shot in site.shots]


def _field(raw: object, key: str, kind: type, where: str) -> object:
    if not isinstance(raw, dict) or not isinstance(raw.get(key), kind):
        raise ManifestError(f"{where}: '{key}' must be a {kind.__name__}")
    return raw[key]


def _shot(raw: object, where: str) -> Shot:
    path = str(_field(raw, "path", str, where))
    file = str(_field(raw, "file", str, where))
    caption = str(_field(raw, "caption", str, where)).strip()
    if not path.startswith("/"):
        raise ManifestError(f"{where}: 'path' must start with '/'")
    if not FILE_PATTERN.match(file):
        raise ManifestError(f"{where}: 'file' must be lowercase letters, digits and hyphens")
    if not caption:
        raise ManifestError(f"{where}: 'caption' must not be empty")
    settle = raw.get("settleMs", DEFAULT_SETTLE_MS) if isinstance(raw, dict) else DEFAULT_SETTLE_MS
    if not isinstance(settle, int) or settle < 0:
        raise ManifestError(f"{where}: 'settleMs' must be a non-negative integer")
    return Shot(path, file, caption, settle)


def _site(raw: object, where: str) -> Site:
    name = str(_field(raw, "name", str, where))
    url = str(_field(raw, "url", str, where))
    sign_in = bool(_field(raw, "signIn", bool, where))
    shots_raw = _field(raw, "shots", list, where)
    if urlparse(url).scheme not in ("http", "https") or not urlparse(url).netloc:
        raise ManifestError(f"{where}: 'url' must be an http(s) address")
    if not isinstance(shots_raw, list) or not shots_raw:
        raise ManifestError(f"{where}: 'shots' must not be empty")
    shots = tuple(_shot(item, f"{where}.shots[{index}]") for index, item in enumerate(shots_raw))
    return Site(name, url, sign_in, shots)


def parse_manifest(text: str, origin: str) -> Manifest:
    """The manifest in *text*.

    Raises:
        ManifestError: on invalid JSON, a missing or mistyped field, a duplicate file name, or a hero
            that names no screenshot.
    """
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ManifestError(f"{origin}: not valid JSON ({exc})") from exc
    hero = str(_field(raw, "hero", str, origin))
    sites_raw = _field(raw, "sites", list, origin)
    if not isinstance(sites_raw, list) or not sites_raw:
        raise ManifestError(f"{origin}: 'sites' must not be empty")
    manifest = Manifest(hero, tuple(_site(item, f"{origin}.sites[{index}]") for index, item in enumerate(sites_raw)))
    seen: set[str] = set()
    for file in manifest.files:
        if file in seen:
            raise ManifestError(f"{origin}: file name '{file}' is used twice")
        seen.add(file)
    if hero not in seen:
        raise ManifestError(f"{origin}: hero '{hero}' is not one of the screenshots")
    return manifest


def to_webp(png: bytes) -> bytes:
    """*png* re-encoded as a lossy WebP."""
    from PIL import Image

    out = io.BytesIO()
    Image.open(io.BytesIO(png)).convert("RGB").save(out, "WEBP", quality=WEBP_QUALITY, method=6)
    return out.getvalue()


def is_local(url: str) -> bool:
    """Whether *url* points at this machine."""
    return (urlparse(url).hostname or "") in LOCAL_HOSTS


class PageWatch:
    """What a page did wrong while it loaded, among the requests to this machine."""

    def __init__(self, page: Page) -> None:
        self.problems: list[str] = []
        page.on("console", lambda m: self.problems.append(f"console error: {m.text[:140]}") if m.type == "error" else None)
        page.on("requestfailed", lambda r: self._failed(r.url, r.failure))
        page.on("response", lambda r: self._status(r.url, r.status))

    def _failed(self, url: str, failure: str | None) -> None:
        if is_local(url):
            self.problems.append(f"failed request: {url[:100]} {failure}")

    def _status(self, url: str, status: int) -> None:
        if is_local(url) and status >= 400 and "/favicon" not in url:
            self.problems.append(f"HTTP {status}: {url[:100]}")

    def take(self) -> list[str]:
        """The problems seen since the last call."""
        seen, self.problems = sorted(set(self.problems)), []
        return seen


def sign_in(page: Page, site: Site, user: str, password: str) -> None:
    """Sign in to *site* through the identity server it redirects to.

    Raises:
        CaptureError: when the sign-in form is not reached or the page is still the form afterwards.
    """
    page.goto(site.url)
    page.wait_for_load_state("networkidle")
    login_name = page.locator("input[name=loginName]")
    if not login_name.count():
        button = page.get_by_role("button", name="Sign in")
        if button.count():
            button.first.click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1500)
    if not login_name.count():
        raise CaptureError(f"{site.name}: no sign-in form was reached from {site.url}")
    login_name.fill(user)
    page.get_by_role("button", name="Next").click()
    page.wait_for_load_state("networkidle")
    page.fill("input[name=password]", password)
    page.get_by_role("button", name="Next").click()
    page.wait_for_load_state("networkidle")
    skip = page.get_by_role("button", name="Skip")
    if skip.count():
        skip.first.click()
        page.wait_for_load_state("networkidle")
    page.wait_for_timeout(SIGN_IN_SETTLE_MS)
    if page.locator("input[name=loginName]").count() or page.locator("input[name=password]").count():
        raise CaptureError(f"{site.name}: still on the sign-in form after signing in as {user}")


def open_page(page: Page, origin: str, path: str) -> None:
    """Show *path* of the site at *origin*, the way a person moves around it.

    A signed-in session lives in the page's memory, so a full reload of a public page would draw it
    signed out. When the page is already there nothing happens; when the page has a link to *path*
    it is clicked (the app routes in place); otherwise the address is loaded.
    """
    target = origin + path
    if page.url.rstrip("/") == target.rstrip("/"):
        return
    link = page.locator(f'a[href="{path}"]')
    if page.url.startswith(origin) and link.count():
        link.first.click()
    else:
        page.goto(target)


def capture_site(
    browser: Browser, site: Site, credentials: tuple[str, str] | None, out_dir: Path, report: Callable[[str], None]
) -> list[str]:
    """Capture every shot of *site* into *out_dir*; the problems the pages showed, as ``file: problem``.

    Raises:
        CaptureError: when the site needs a sign-in and it fails or no credentials were given.
    """
    if site.sign_in and credentials is None:
        raise CaptureError(f"{site.name}: signs in, but no user and password were given")
    context = browser.new_context(viewport=VIEWPORT)
    try:
        page = context.new_page()
        if site.sign_in and credentials is not None:
            sign_in(page, site, *credentials)
        watch = PageWatch(page)
        origin = "{0.scheme}://{0.netloc}".format(urlparse(site.url))
        problems: list[str] = []
        for shot in site.shots:
            open_page(page, origin, shot.path)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(shot.settle_ms)
            data = to_webp(page.screenshot(type="png"))
            (out_dir / f"{shot.file}.webp").write_bytes(data)
            found = watch.take()
            problems += [f"{shot.file}: {item}" for item in found]
            report(f"  {shot.file}.webp  {len(data) // 1024} KB" + (f"  ({len(found)} problem(s))" if found else ""))
        return problems
    finally:
        context.close()


def gallery_markdown(manifest: Manifest, columns: int = 2) -> str:
    """A gallery of every screenshot for a domain README: a table of *columns* images per row."""
    shots = [shot for site in manifest.sites for shot in site.shots]
    tables: list[str] = []
    for start in range(0, len(shots), columns):
        row = shots[start : start + columns]
        images = [f"![{s.caption}]({OUTPUT_DIR}/{s.file}.webp)" for s in row] + [" "] * (columns - len(row))
        captions = [s.caption for s in row] + [" "] * (columns - len(row))
        tables.append("\n".join([f"| {' | '.join(images)} |", "|" + "---|" * columns, f"| {' | '.join(captions)} |"]))
    return "\n\n".join(tables)


def remove_stale(out_dir: Path, manifest: Manifest) -> list[str]:
    """Delete the ``.webp`` files in *out_dir* that no shot of *manifest* produces; their names."""
    wanted = {f"{name}.webp" for name in manifest.files}
    stale = sorted(path for path in out_dir.glob("*.webp") if path.name not in wanted)
    for path in stale:
        path.unlink()
    return [path.name for path in stale]


def default_repo() -> Path:
    """The repository this script lives in: three folders above ``scripts/screenshots/lib``."""
    return Path(__file__).resolve().parents[3]


def load_manifest(repo: Path, domain: str) -> tuple[Manifest, Path]:
    """The manifest of *domain* and its folder.

    Raises:
        ManifestError: when the domain has no manifest or it is invalid.
    """
    folder = repo / domain
    path = folder / MANIFEST_NAME
    if not path.is_file():
        raise ManifestError(f"{path} does not exist")
    return parse_manifest(path.read_text(encoding="utf-8"), f"{domain}/{MANIFEST_NAME}"), folder


def run(args: argparse.Namespace) -> int:
    """Capture the sites of the domain named in *args*; the exit code."""
    repo = Path(args.repo).resolve() if args.repo else default_repo()
    manifest, folder = load_manifest(repo, args.domain)
    if args.markdown:
        print(gallery_markdown(manifest))
        return EXIT_OK
    user = args.user or os.environ.get(USER_ENV, "")
    password = os.environ.get(PASSWORD_ENV, "")
    credentials = (user, password) if user and password else None
    sites = [site for site in manifest.sites if not args.site or site.name == args.site]
    if not sites:
        raise ManifestError(f"{args.domain} has no site named '{args.site}'")
    from playwright.sync_api import sync_playwright

    out_dir = folder / OUTPUT_DIR
    out_dir.mkdir(exist_ok=True)
    if not args.site:
        for name in remove_stale(out_dir, manifest):
            print(f"Removed {name}: the manifest no longer lists it.")
    problems: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=os.environ.get(BROWSER_ENV) or None, headless=True)
        try:
            for site in sites:
                print(f"{site.name} ({site.url}):")
                problems += capture_site(browser, site, credentials, out_dir, print)
        finally:
            browser.close()
    for item in problems[:MAX_PROBLEMS_SHOWN]:
        print(f"Problem: {item}")
    print(f"{len(problems)} problem(s) on the captured pages.")
    return EXIT_PROBLEMS if problems else EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    """The command line."""
    parser = argparse.ArgumentParser(description="Capture the UI screenshots of an example from its running local stack.")
    parser.add_argument("--domain", help="the example's folder, for example blog-cms")
    parser.add_argument("--site", default="", help="capture only this site of the manifest")
    parser.add_argument("--user", default="", help=f"sign-in user; default: ${USER_ENV}. The password is ${PASSWORD_ENV}.")
    parser.add_argument("--markdown", action="store_true", help="print the README gallery for the manifest and exit")
    parser.add_argument("--repo", default="", help=argparse.SUPPRESS)
    parser.add_argument("--self-test", action="store_true", help="run the script's own checks, then exit")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    args = build_parser().parse_args(argv)
    if args.self_test:
        from selftest import run_self_test

        return run_self_test()
    if not args.domain:
        print("Error: --domain is required.")
        return EXIT_ERROR
    try:
        return run(args)
    except (ManifestError, CaptureError) as exc:
        print(f"Error: {exc}")
        return EXIT_ERROR
    except ImportError as exc:
        print(f"Error: {exc}. Install the requirements: pip install playwright pillow && playwright install chromium")
        return EXIT_ERROR


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    sys.exit(main())
