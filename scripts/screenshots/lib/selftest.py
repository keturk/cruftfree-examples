"""Checks of the screenshot script: manifest validation, and a real capture of a local page.

The capture check starts a Chromium (``playwright install chromium``) against a page served from
this machine on a free port; nothing else is contacted.
"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Final

import capture

PAGE: Final = (
    b"<!doctype html><title>t</title><body style='background:#fff'><h1>Self test</h1>"
    b"<a href='/two' onclick=\"event.preventDefault();history.pushState({},'','/two')\">two</a></body>"
)


class Page(BaseHTTPRequestHandler):
    """Serves one page for every path."""

    def do_GET(self) -> None:  # noqa: N802 - the name http.server dispatches on
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(PAGE)))
        self.end_headers()
        self.wfile.write(PAGE)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        """Stay quiet."""


@contextlib.contextmanager
def local_page() -> Iterator[str]:
    """The address of a running page server."""
    server = HTTPServer(("127.0.0.1", 0), Page)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://localhost:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def manifest_text(**changes: object) -> str:
    """A valid manifest with *changes* applied to its first shot, or to the top level for 'hero' and 'sites'."""
    shot = {"path": "/", "file": "home", "caption": "The home page"}
    site = {"name": "web", "url": "http://localhost:4200", "signIn": False, "shots": [shot]}
    document: dict[str, object] = {"hero": "home", "sites": [site]}
    for key, value in changes.items():
        if key in document:
            document[key] = value
        else:
            shot[key] = value  # type: ignore[assignment]
    return json.dumps(document)


class Report:
    """Collects the checks and prints one line each."""

    def __init__(self) -> None:
        self.failed = 0

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  [{detail}]"))
        self.failed += 0 if ok else 1


def manifest_checks(report: Report) -> None:
    """Valid and invalid manifests."""
    report.check("a valid manifest parses", capture.parse_manifest(manifest_text(), "t").files == ["home"])
    refused = {
        "a path without a slash": manifest_text(path="home"),
        "a file name with a capital": manifest_text(file="Home", hero="Home"),
        "an empty caption": manifest_text(caption="  "),
        "a hero that names no shot": manifest_text(hero="other"),
        "no sites": manifest_text(sites=[]),
        "not JSON": "{",
    }
    for name, text in refused.items():
        try:
            capture.parse_manifest(text, "t")
            report.check(f"refused: {name}", False, "no error")
        except capture.ManifestError:
            report.check(f"refused: {name}", True)
    twice = json.loads(manifest_text())
    twice["sites"][0]["shots"].append(dict(twice["sites"][0]["shots"][0]))
    try:
        capture.parse_manifest(json.dumps(twice), "t")
        report.check("refused: a file name used twice", False, "no error")
    except capture.ManifestError:
        report.check("refused: a file name used twice", True)
    parsed = capture.parse_manifest(manifest_text(), "t")
    report.check("the gallery names each image", "![The home page](screenshots/home.webp)" in capture.gallery_markdown(parsed))
    report.check("local hosts are judged, others are not", capture.is_local("http://localhost:4200/x")
                 and not capture.is_local("https://tile.openstreetmap.org/1.png"))


def navigation_checks(report: Report, address: str) -> None:
    """A page with a link is reached by clicking it (the page's memory survives); one without is loaded."""
    import os

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=os.environ.get(capture.BROWSER_ENV) or None, headless=True)
        try:
            page = browser.new_page()
            page.goto(address + "/")
            page.evaluate("window.__marker = 1")
            capture.open_page(page, address, "/")
            report.check("the page already shown is left alone", page.evaluate("window.__marker") == 1)
            capture.open_page(page, address, "/two")
            report.check("a linked page is reached by clicking", page.url.endswith("/two") and page.evaluate("window.__marker") == 1)
            capture.open_page(page, address, "/unlinked")
            report.check("an unlinked page is loaded", page.url.endswith("/unlinked") and page.evaluate("window.__marker") is None)
        finally:
            browser.close()


def capture_checks(report: Report) -> None:
    """A real capture of a local page."""
    from PIL import Image
    from playwright.sync_api import sync_playwright

    with local_page() as address, tempfile.TemporaryDirectory(prefix="screenshots-selftest-") as scratch:
        text = manifest_text().replace("http://localhost:4200", address)
        site = capture.parse_manifest(text, "t").sites[0]
        out = Path(scratch)
        with sync_playwright() as playwright:
            import os

            browser = playwright.chromium.launch(executable_path=os.environ.get(capture.BROWSER_ENV) or None, headless=True)
            try:
                problems = capture.capture_site(browser, site, None, out, lambda line: None)
            finally:
                browser.close()
        image_file = out / "home.webp"
        report.check("the page was captured as a file", image_file.is_file() and image_file.stat().st_size > 0)
        if image_file.is_file():
            image = Image.open(io.BytesIO(image_file.read_bytes()))
            report.check("the image is a 1280x800 WebP", image.format == "WEBP" and image.size == (1280, 800), f"{image.format} {image.size}")
        report.check("a clean page reports no problem", problems == [], str(problems))
        (out / "old-shot.webp").write_bytes(b"x")
        (out / "notes.txt").write_text("keep", encoding="utf-8")
        removed = capture.remove_stale(out, capture.parse_manifest(text, "t"))
        report.check("only an unlisted image is removed", removed == ["old-shot.webp"] and image_file.is_file()
                     and (out / "notes.txt").is_file(), str(removed))
        navigation_checks(report, address)
        try:
            capture.capture_site(None, capture.Site("s", address, True, site.shots), None, out, print)  # type: ignore[arg-type]
            report.check("a signing-in site without credentials is refused", False, "no error")
        except capture.CaptureError:
            report.check("a signing-in site without credentials is refused", True)


def run_self_test() -> int:
    """Run every check; the exit code is 0 when all pass."""
    report = Report()
    print("Manifest:")
    manifest_checks(report)
    print("Capture:")
    capture_checks(report)
    print("All checks passed." if report.failed == 0 else f"{report.failed} check(s) failed.")
    return capture.EXIT_OK if report.failed == 0 else capture.EXIT_ERROR
