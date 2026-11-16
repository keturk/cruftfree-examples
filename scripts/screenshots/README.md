# Screenshots

The UI screenshots in each `<domain>/screenshots/` are made by one script from a list in
`<domain>/screenshots.json`. Run it against the example's local Docker stack to refresh them.

`screenshots.ps1` / `screenshots.sh` are thin wrappers around [`lib/capture.py`](lib/capture.py).

## Needs

- Python 3.11 or newer with `playwright` and `pillow`, and a Chromium:
  `pip install playwright pillow` then `playwright install chromium`. `CRUFTFREE_BROWSER_EXE` names a
  browser executable to use instead.
- The example's `docker-*` stack running, from a tree you generated (see the top-level README).
- A user in the stack's Zitadel with the roles the pages need (the domain README says which roles exist).
  Give it an invented name: it shows in the avatar and on pages that list people.

## Run

```powershell
$env:CRUFTFREE_SCREENSHOT_USER = "alex.morgan@example.com"
$env:CRUFTFREE_SCREENSHOT_PASSWORD = "..."       # never on the command line
scripts/screenshots/screenshots.ps1 -Domain blog-cms
scripts/screenshots/screenshots.ps1 -Domain blog-cms -Site studio     # one site only
scripts/screenshots/screenshots.ps1 -Domain blog-cms -Markdown        # print the README gallery
scripts/screenshots/screenshots.ps1 -Domain blog-cms -UpdateReadme    # write it into blog-cms/README.md
scripts/screenshots/screenshots.ps1 -SelfTest
```

```bash
CRUFTFREE_SCREENSHOT_USER=alex.morgan@example.com CRUFTFREE_SCREENSHOT_PASSWORD=... \
    scripts/screenshots/screenshots.sh --domain blog-cms
```

Each site is opened in a fresh browser session at 1280x800 and signed in when the manifest says so. Every
image is saved as WebP (about 20 to 60 KB). A full run, with no `-Site`, removes images the manifest no
longer lists. Console errors, failed requests and HTTP errors from this machine are printed and give exit
code 1; requests to other hosts (map tiles) are not judged. Exit codes: 0 clean, 1 captured with problems,
2 could not run.

For clean pictures start from fresh volumes (`docker compose down -v`, then deploy), so the data is the seed
data and no earlier test user shows on a page.

## The manifest

```json
{
  "hero": "reader-articles",
  "sites": [
    {
      "name": "reader",
      "url": "http://localhost:4200",
      "signIn": false,
      "shots": [
        {"path": "/", "file": "reader-articles", "caption": "Reader: the articles, with search"}
      ]
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `hero` | The `file` shown for this application in the top-level README. |
| `sites[].url` | The web app's address in the running stack. |
| `sites[].signIn` | `true` signs in through the identity server first; `false` shows the public view. |
| `shots[].path` | The page, starting with `/`. |
| `shots[].file` | The image name: lowercase letters, digits and hyphens, unique in the domain. |
| `shots[].caption` | Shown under the image in the gallery. |
| `shots[].settleMs` | Optional wait after the page loads, default 1500. |

Pick pages that have content in the seed data: an empty list tells a visitor nothing.
