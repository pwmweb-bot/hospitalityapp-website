# hospitalityapp.co.uk

The public marketing site for HospitalityApp — vanilla HTML / CSS, hosted on
20i via Git Version Control.

The product app lives at `my.hospitalityapp.co.uk` (separate Vercel project).

## Editing

**This repo is the source of truth for the marketing site.** Edit the HTML
here directly. (The old `venuebase/apps/marketing/public/` copy is stale and
abandoned — do NOT `cp -R` from it; it would wipe the newer pages.)

To update and deploy:

1. Edit the HTML here, commit to `main`.
2. Run `./scripts/deploy.sh` — it pushes to GitHub, then SSHes to 20i and
   `git pull`s the live web root (`~/site-source`). 20i's own auto-pull has
   been unreliable, so the script makes the server pull explicit.

## Pages

| Route | File |
|---|---|
| `/` | `index.html` |
| `/features` | `features.html` |
| `/pricing` | `pricing.html` |
| `/for/pubs` | `for/pubs.html` |
| `/for/restaurants` | `for/restaurants.html` |
| `/for/cafes` | `for/cafes.html` |
| `/privacy` | `privacy.html` |
| `/terms` | `terms.html` |

`.htaccess` strips `.html` so visitors get the clean URLs above. It also
forces HTTPS, redirects www → apex, sets security headers, and serves
the AASA file with the right Content-Type.

## Deploy on 20i

1. **Create the repo** (you do this on GitHub) — empty, default branch `main`.
2. **Push the contents** of this folder to it.
3. In 20i Stack User Manager → Git Version Control:
   - Repo URL: `https://github.com/<owner>/<repo>.git`
   - Deploy key: 20i shows you a public key — add it to the repo's Deploy Keys (Settings → Deploy keys → Add deploy key) with read-only access.
   - Branch: `main`
   - Deployment path: `/public_html/` (or whichever doc-root the package uses)
4. After the first deploy, visit `https://hospitalityapp.co.uk/` and click
   through every nav link to confirm cleanURLs work.

## Pre-launch checks

- [ ] DNS apex A / AAAA records point at 20i; www CNAME → apex
- [ ] Free SSL certificate issued by 20i (Let's Encrypt)
- [ ] AASA verifies: `curl -I https://hospitalityapp.co.uk/.well-known/apple-app-site-association` returns `Content-Type: application/json`
- [ ] Lighthouse pass on every page (mobile, ≥ 95 across the board)
- [ ] Replace `TEAMID` placeholder in `apple-app-site-association` once Apple Developer is set up
- [ ] Replace `REPLACE_WITH_SHA256_FROM_PLAY_CONSOLE_OR_LOCAL_KEYSTORE` once the Android keystore exists
- [ ] Drop in real screenshots in place of `[ Rota screenshot ]` placeholders on `/features`
- [ ] Generate per-page OG images at `assets/images/og/*.png`
