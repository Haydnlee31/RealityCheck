# RealityCheck demo companion

A standalone, read-only site for the IBM Bob 2.0 hackathon prototype. It explains the workflow and presents recorded evidence; it does not run Bob, pytest, or the RealityCheck verifier in the browser.

## Preview locally

From the repository root:

```bash
python3 -m http.server 4173 --bind 127.0.0.1 --directory demo
```

Open <http://localhost:4173>. No package installation, build step, backend, credentials, or environment variables are required.

## Files

| Path | Purpose |
| --- | --- |
| `index.html` | Complete static story, workflow disclosures, case studies, comparison, and source links |
| `styles.css` | Responsive layout, keyboard focus styles, and reduced-motion support |
| `script.js` | Finding/phase selection, Scenario 2 column controls, and optional video links |
| `config.js` | The single demo video URL setting |
| `assets/evidence.js` | Generated presentation data from actual execution records |
| `assets/sessions/` | Unmodified copies of the seven Bob session screenshots |
| `evidence/` | Byte-for-byte copies of reports, evidence records, logs, manifests, tests, and source documents |
| `evidence/source-manifest.json` | Source Git commit and SHA-256 hashes of the 62 copied evidence artifacts |
| `tools/export_evidence.py` | Optional export utility; reads the parent repository and writes only inside `demo/` |

The workflow disclosures, case-study matrix, verdict limitations, screenshot links, and report links remain usable without JavaScript. JavaScript adds the execution explorer and phase filters.

## Evidence and scope

The bundle was exported from `b6f64bb` (`final-submission`):

- **RC-001:** `runs/rc-001/evidence.json`, `report-v2.md`, the protected manifest, and the original reproduction, repaired verification, and baseline execution artifacts.
- **RC-002 / RC-003:** `runs/rc-002/evidence-rc002.json`, `evidence-rc003.json`, their reports and protected manifest, and the reproduction/verification artifacts with their shared baseline.
- The three accepted regression test files; `docs/application-contract.md`, `docs/source-notes.md`, and `docs/evaluation.md`.
- All seven PNGs from `bob_sessions/`.

The page preserves the distinction between the three Scenario 2 defects and AC-006, which already passed and remained a preservation guard. The identifier `"053636"` is explicitly synthetic and contract-derived.

The Bob-only control successfully repaired AC-001. Its final screenshot shows 0.607 Bobcoins; the RC-001 screenshot shows 2.43 at an **intermediate** checkpoint, not the complete task cost. The site makes no speedup, accuracy, productivity, production-safety, or statistical-superiority claims. Subprocess durations in the explorer are recorded test durations, not end-to-end workflow timings.

Historical absolute workspace paths and abbreviated patch fields remain in the copied original records. Those fields are historical provenance, not paths used to run this site. Historical protected manifests apply to their contemporaneous checkpoints, not to the present repository after later tooling changes. Downloaded Markdown reports are original source artifacts, not rewritten web reports.

To regenerate presentation copies after deliberately selecting the desired source checkpoint, run from the repository root:

```bash
python3 demo/tools/export_evidence.py
```

This command does not execute tests or modify the original evidence. It overwrites the presentation copies in `demo/`. Review the source commit and resulting demo diff before publishing a refreshed bundle.

## Optional demo video

Edit only `DEMO_VIDEO_URL` in `config.js` and set it to the final HTTPS video URL. An empty or invalid value keeps both video buttons hidden. No placeholder video or invented URL is published.

## Publish with Git and Vercel

From the repository root:

```bash
git add demo
git commit -m "add RealityCheck hosted demo"
git push origin main
```

1. Sign into Vercel with GitHub.
2. Choose **Add New → Project**, then import `Haydnlee31/RealityCheck`.
3. Set **Root Directory** to `demo`.
4. Set **Framework Preset** to **Other**.
5. Override **Build Command** with an empty value to skip a build.
6. Use **Output Directory** `.` (or its default for an Other project without a `public/` folder).
7. Leave **Install Command** empty and add no environment variables.
8. Deploy, then check the production URL in an incognito window. Check the evidence controls, local artifact links, screenshots, and mobile layout.
9. Use the final `https://…vercel.app` URL as the Devpost Demo Application URL.

These settings follow [Vercel's static build configuration documentation](https://vercel.com/docs/builds/configure-a-build). No `vercel.json` is needed. The committed bundle is self-contained; the export utility is not a deployment step.

## Validation

Local validation completed:

- JavaScript syntax checks passed for all three scripts.
- All 36 HTML references and the generated execution links resolve; IDs are unique.
- All 62 artifact copies and seven screenshot copies match their originals byte for byte.
- All 78 demo files are served correctly by the local HTTP server; the three public GitHub destinations return HTTP 200.
- All nine finding/phase selections show the recorded outcomes and test counts. The RC-003 reproduction retains two failures and its one passing guard.
- Scenario 2 filters and keyboard-operated workflow/gallery disclosures work. The unconfigured video links remain hidden. No browser console errors were observed in the normal preview.
- Chrome layouts were inspected at 1440, 1024, 768, and 390px, with no horizontal page overflow.
- All 109 pre-existing tracked repository files retain their original SHA-256 hashes.

The no-JavaScript fallback and reduced-motion rules were reviewed in source; they were not separately exercised in a browser with those settings enabled. The existing Python application and verifier are outside this presentation-only change; their tests were not rerun for this static site.
