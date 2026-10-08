# Conformance portal publication

Issue #3 implements the existing PDDR-0001 Pages boundary. It does not change the adapter
contract or authorize publication of any additional private semantics.

## What the portal means

The portal shows **the latest published snapshot**, not an automatically refreshed view
of the newest workflow. It includes the source run, exact tested commit and UTC run-update
time. A green synthetic fixture does not imply production adapter compatibility, full
validation of the draft contract, or validation of the private runtime.

The initial reviewed `results/latest.json` projects the 14 scenario results from public
artifact `11556585428` (`envoy-web-api-conformance`) of main-branch Envoy Conformance run
[37790026686](https://github.com/serevy/security-twin-adapter-lab/actions/runs/37790026686)
at commit `0f075491f77a9519649f606be99a4e29762eb76a`. The downloaded archive's SHA-256 digest
and GitHub metadata were verified through the same `from_artifact` function used for
future imports. The snapshot is marked `workflow-artifact`; raw archives/logs are not
retained in the repository or site. Public job PASS summaries were also cross-checked.

`results/bootstrap.json` preserves the original bootstrap record. Building it produces
BOOTSTRAP with 0/14 and every check NOT RUN; it cannot produce compatibility or success
claims. FAIL and NOT RUN are distinct, and failed execution/teardown is never an overall PASS.

## Local build and review

Python 3.10+ standard library only; no Jekyll, npm install, Docker or build service needed.
Use a new/empty output directory each time (stale files are rejected):

```bash
python3 -m unittest discover -s portal -p 'test_*.py' -v
python3 portal/build.py --output /tmp/adapter-portal
python3 -m http.server 8080 --directory /tmp/adapter-portal
# Open http://localhost:8080/
```

For bootstrap review:

```bash
python3 portal/build.py --input results/bootstrap.json --output /tmp/adapter-portal-bootstrap
```

The generator emits exactly `index.html`, `style.css`, `result.json` and `.nojekyll`.
It never copies the repository, documentation tree, Docker source, logs, ZIP files or
raw artifact contents. Asset URLs are relative, so the same output works at the project
Pages subpath. Contract/disclosure/PDDR links point to the public repository. Rendering
uses no JavaScript, external fonts, analytics or remote resources; status is text as well
as color, and semantic tables, a skip link and responsive layouts support accessibility.

## First manual deployment

Repository metadata reported `has_pages: true` on 2026-10-08. A successful manual
deployment of this portal still needs to be verified after merge.

After this PR is merged:

1. In repository **Settings → Pages**, choose **GitHub Actions** as the source if Pages
   has not already been enabled. This is a repository setting, not a secret.
2. In **Actions → Deploy Pages → Run workflow**, select `main`.
3. For the first bootstrap deployment, check `bootstrap` and leave `run_id` blank.
   Confirm the workflow and its `github-pages` environment URL succeed.
4. Run it again with `bootstrap` unchecked and `run_id` blank to publish the reviewed
   snapshot. Inspect the displayed run ID, commit and aggregate JSON at the resulting URL.

Expected project URL: `https://serevy.github.io/security-twin-adapter-lab/`.
PR builds validate and upload a three-day preview artifact but **never deploy**. Only a
manual dispatch on `main` reaches the deployment job. No deployment is claimed until
that job succeeds. This keeps the initial manual-deployment gate from Issue #3 explicit.

The build job has only `contents: read` and `actions: read`. The separate deploy job has
only `pages: write` and `id-token: write`. The workflow uses GitHub's built-in token/OIDC,
no repository or environment secret, and pinned actions. It has no workflow-run trigger,
private checkout, package install or Docker invocation.

## Update from an already-public artifact

A new snapshot can be published without rerunning Docker. Choose an existing completed
**Envoy Conformance** run from this public repository's `main` branch (push or manual).
Enter its numeric run ID in manual Deploy Pages, leaving `bootstrap` unchecked.
The importer fetches GitHub run/artifact metadata with the built-in token, verifies the
artifact's SHA-256 digest, then reads only `envoy-web-api.json` from the archive in memory.
It does not extract or execute artifact contents and never publishes the optional log.

Alternatively, with GitHub CLI authenticated locally:

```bash
python3 portal/import_evidence.py --run-id RUN_ID --output results/latest.json
python3 -m unittest discover -s portal -p 'test_*.py' -v
# Review and commit the updated snapshot in a PR.
```

Replace `RUN_ID` with a positive numeric run ID. Local GitHub CLI login is separate from
the secret-free Actions path. Importing does not mutate the source run or rerun its tests.

The importer enforces repository identity/public visibility, same-repository origin,
workflow path/name, completed status, `main` branch, non-PR event, artifact identity and
run/commit correspondence. It rejects expired or oversized artifacts, digest mismatches,
unknown schemas/scenarios/statuses, duplicate JSON keys, extra fields and contradictory
PASS claims. Only fixed scenario identifiers and PASS/FAIL/NOT_RUN cross the boundary.
The public contract is unchanged; `public-conformance-portal-v1` is a site snapshot schema.

A manual import publishes a selected snapshot in that deployment only; it does not commit
back to the repository. To retain it across later default deployments, import and commit
`results/latest.json` through review. Older source artifacts expire after three days;
the reviewed snapshot and its source identifiers remain usable, explicitly dated evidence.
If import or validation fails, deployment is blocked and the previous site remains; a
missing artifact is never silently replaced by green evidence.

## CI cost and maintenance

Portal-only edits trigger this lightweight PR build plus existing Public Boundary/PDDR
checks, without triggering Envoy Docker CI. Main pushes do not redeploy; manual dispatch
provides the explicit first-deploy and evidence-selection gates. No workflow is run just
to refresh a timestamp. Rendering tests cover bootstrap/fail/unknown states, publication
allowlisting, metadata trust checks and artifact projection. The Ubuntu runner’s installed
Chrome additionally checks desktop/mobile layout, CSS loading, exact displayed statuses
and relative links at the project subpath; screenshots are in the PR preview artifact
only, not in the Pages publication. This smoke test uses Node built-ins and installs no
browser or package in CI.
