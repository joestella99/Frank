# 🐾 Frank — your autonomous desktop job hunter

Frank is a tiny black Labrador / long-haired German Shepherd mix who wanders around your Windows desktop and fetches promising job opportunities. **Frank does not stop hunting when your laptop closes.**

## Architecture

- **Cloud hunter:** GitHub Actions wakes up every 30 minutes (best effort), checks public employer job feeds, scores openings for NYC / US-remote software engineering, technical product, automation and sports-tech, and saves deduplicated matches in `data/jobs.json`.
- **Desktop companion:** small transparent, always-on-top animated Frank walks around the screen, periodically syncs the saved job feed, barks for genuinely new matches, and opens your personal job stash.
- **Stash:** local SQLite tracks your saved, applied, and ignored statuses. Only public job postings go into the GitHub-hosted JSON feed.
- **Optional remote notifications:** a Discord webhook secret can send fresh strong matches to your phone even when the laptop is off.

## Get started

1. In GitHub open **Settings → Actions → General**, and allow Actions to run. Under Workflow permissions allow read and write access for `GITHUB_TOKEN` if needed.
2. Open **Actions → Frank hunts for jobs → Run workflow** once. The scheduled workflow also runs automatically; GitHub's cron is approximate, and public repos may have schedules disabled after long inactivity.
3. To run the desktop pet on Windows, install Python 3.10+ and run `INSTALL_AND_RUN.bat`.
4. Double-click Frank to open his job stash, or right-click for controls.

**Optional:** Add the repository Actions secret `FRANK_DISCORD_WEBHOOK` to receive high-quality find alerts on your phone. Don't put webhook URLs or personal credentials in the code or `boards.json`.

## Customize Frank

Edit `boards.json` to add public ATS job boards. Supported `provider` values: `greenhouse`, `lever`, and `ashby`. Frank only scans published openings; no scraping of LinkedIn pages and no automatic applications.

Frank defaults to NYC / NYC hybrid and potentially eligible US-remote jobs. Remote eligibility is not guaranteed: always verify the role on the original employer page. Initial sources are a starter list, not exhaustive job-market coverage; some may move or become unavailable.

## Development

```bash
python -m unittest discover -s tests -v
python cloud_hunt.py
python desktop.py
```

The cloud scan uses only the Python standard library. The desktop requires Pillow (`requirements.txt`). All network failures are logged and don't destroy the existing stash. The desktop can be quit from the right-click menu.

## Privacy & limitations

- Your repository is public. The feed contains **public job metadata**, not resumes, account credentials, or your local application statuses.
- A scheduled GitHub Action can run while the laptop is off, but delivery is not real-time and depends on GitHub Actions being enabled.
- The local mascot only walks/barks when Frank is running on your computer.
- No roles are guaranteed; Frank prioritizes newly discovered, plausible fits.
