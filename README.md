# GitHub Explorer — LaxmanNepal/github

A lightweight, static-hosted directory for discovering public GitHub repositories. It includes a global discovery page, a Nepal-focused view, dedicated Hidden Apps, Games, Android, Windows and Web directories, metadata search, composable filters, sorting in both directions, progressive rendering with infinite-scroll assistance, project actions, browser-local favourites, and scheduled indexing.

## Routes and deployment
- Global directory: /github/ on the LaxmanNepal project site.
- Nepal directory: /github/githubnepal/ on that same project site.
- Hidden open-source Android apps: /github/hiddenapps/.
- Mobile games: /github/games/.
- Android apps and games: /github/android/.
- Windows apps: /github/windows/.
- Web apps: /github/web/.
- Repository: https://github.com/LaxmanNepal/github

The Pages workflow deploys this repository as a project site. The exact live URL is determined by GitHub Pages settings and any custom domain configured there. Verify that setting before treating a custom domain as canonical; update canonical metadata, sitemap.xml and robots.txt if the actual origin differs.

## Architecture
- index.html and githubnepal/index.html: page entry points.
- assets/css/app.css and assets/js/app.js: shared responsive interface and client-side search/filter/sort.
- data/projects.json: generated, versioned dataset.
- data/index-report.json: latest indexing report.
- scripts/build_index.py: discovery, normalization, classification and validation.
- config/categories.json: canonical category labels.
- config/nepali-creators.json: manually reviewed creator/repository allowlist.
- .github/workflows/refresh-index.yml: daily scheduled and manual refresh.
- .github/workflows/pages.yml: static GitHub Pages deployment.

## Data collection and limits
The indexer uses GitHub's documented REST Search API and multiple query families. Search limits each query to 1,000 results and imposes rate limits. Queries overlap and are deduplicated by case-insensitive full_name. This is a curated discovery index, not every public repository on GitHub. Adjust SEARCH_QUERIES and MAX_PAGES_PER_QUERY in scripts/build_index.py to change coverage. The daily workflow requests up to two 100-result pages per query, including F-Droid/FOSS/privacy, Android, game, Windows and web-app discovery queries. The Hidden Apps page only shows Android projects whose GitHub metadata includes a recognized SPDX license and matching FOSS/hidden-app signals; this is a curated discovery view, not a guarantee that every qualifying app on GitHub is indexed.

The workflow uses the automatically provided GITHUB_TOKEN secret; it is never sent to the browser. The token is used to commit generated data. Failed searches are reported; if every query fails, the script exits without replacing the existing dataset. Run Actions → Refresh repository index → Run workflow to trigger an update.

## Categories
Categories are inferred from repository topics, description, name and language using keyword rules in categories_for(). Repositories can have multiple categories. This is approximate classification, not human review.

## Nepal directory and evidence
The Nepal view includes repositories marked Nepal-related by metadata/topics or entries in the reviewed allowlist. A Nepal-specific project is not proof that its creator is Nepali. Only an entry in config/nepali-creators.json marks a creator/repository as verified by manual review. Add entries only when public, reliable evidence supports the connection. Do not infer nationality from a person's name. Metadata-based entries are labelled as Nepal-related, not as verified Nepali creators.

Example allowlist structure: { "creators": ["verified-public-github-login"], "repositories": ["owner/repository"] }.

## Usefulness score
The indexer computes a 0–100 heuristic using repository activity recency (up to 30 points), logarithmic stars (up to 20), logarithmic forks (up to 10), documentation signal (up to 15), latest-release signal (up to 10), and an HTTPS homepage/demo signal (up to 10). This is a sorting aid, not a quality guarantee. Stars are not user counts. The lightweight indexer preserves README/release signals from the prior dataset when available; it does not make per-repository requests for every release and README on each refresh, so signals can be incomplete for new entries. A homepage URL is not proof that the site is live or functional.

## Local development
Serve over HTTP because browsers may block fetches from file URLs. Run: python -m http.server 8000. Open http://localhost:8000/ and http://localhost:8000/githubnepal/.

Generate data locally with Python 3.10+ and no third-party packages: MAX_PAGES_PER_QUERY=1 python scripts/build_index.py. Set GITHUB_TOKEN if unauthenticated limits are insufficient. Never put tokens in HTML, JavaScript or committed configuration.

## Deployment setup
1. Open repository Settings → Pages.
2. Set the deployment source to GitHub Actions.
3. Ensure Actions are allowed.
4. Run Deploy GitHub Explorer or push to main.
5. Check the workflow deployment URL and directly open both directory paths.
6. Verify any custom domain before treating it as canonical.

## Troubleshooting
- Empty directory: run Refresh repository index manually and inspect logs/data/index-report.json.
- API rate limit: wait for reset or reduce query pages.
- Pages 404: enable Pages with GitHub Actions and inspect the deployment workflow.
- JSON issue: run python -m json.tool data/projects.json.
- No Nepal entries: add confirmed projects or verified creators to the allowlist; do not guess nationality.

## Validation
Run python -m py_compile scripts/build_index.py, python -m json.tool data/projects.json, and the same json.tool check for config/categories.json and config/nepali-creators.json. The deployment workflow checks the dataset structure. The indexer validates unique IDs/names, required fields, numeric star counts, timestamps and demo URLs before replacing the dataset.

## Current limitations
- Search coverage is bounded by query strategy, Search API limits and quotas.
- Search covers metadata, not complete README text or source code.
- Homepage URLs are not live-checked.
- Release and README signals can be missing.
- No browser-side GitHub token, per-card API calls, or embedded demo websites are used.
- The initial dataset is empty rather than fabricated. Run the index workflow to fetch real repository data.