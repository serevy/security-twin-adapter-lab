---
id: PDDR-0002
title: Public Localization and Language-Neutral Evidence
decision_date: 2026-10-09
recorded_date: 2026-10-09
decision_status: accepted
delivery_status: implemented
scope:
  - project
  - product
  - process
owners: []
evidence:
  - "Project owner explicitly requested bilingual Pages and this decision record on 2026-10-09 (Asia/Tokyo)"
  - "Issue #3"
  - "PR #7"
  - README.md
  - portal/build.py
  - portal/test_portal.py
related:
  - PDDR-0001
supersedes: []
superseded_by: null
---

# PDDR-0002: Public Localization and Language-Neutral Evidence

## Summary

Use English as the primary language and Japanese as a maintained secondary language
for public-facing human-readable content where practical. Localize presentation only.
Keep machine-readable evidence, identifiers, contract/schema versions, commit SHAs,
artifact digests and provenance language-neutral, with one shared evidence source.

This record preserves the reasoning and its scope. It is not an unconditional Policy
or an instruction to expand disclosure. The explicitly requested operational rule is
also stated in README.md and README.ja.md for contributors.

## Context and observations

The first public Pages portal in PR #7 presents aggregate conformance evidence in
English. The project owner requested a Japanese presentation so Japanese readers can
inspect the same claims and limitations without changing their technical meaning.

Separate evidence per locale could drift, making two languages report different
conformance outcomes. Translating stable identifiers or status values would also break
comparison and automated consumption. PDDR-0001 already limits this repository to the
public behavioral contract, synthetic fixtures and bounded aggregate evidence.

## Options considered

### Option A — English-only portal

- Description: retain one human-readable language.
- Benefits: smallest presentation maintenance cost.
- Costs / constraints: does not meet the requested Japanese accessibility.
- Status: rejected for this portal.

### Option B — Independently localized evidence and pages

- Description: duplicate or translate result JSON for each locale.
- Benefits: each page can use a fully locale-specific data file.
- Costs / constraints: divergent statuses, versions and provenance; additional publication paths.
- Status: rejected.

### Option C — Shared evidence with localized presentation

- Description: one validated snapshot generates English and Japanese HTML; one root result.json serves both.
- Benefits: equal technical claims across languages, traceable provenance and narrow publication surface.
- Costs / constraints: human-readable translations must be maintained and reviewed together.
- Status: selected.

## Decision

The project owner explicitly approved this scope in the PR #7 localization request on
2026-10-09 (Asia/Tokyo):

1. Public-facing human-readable content should use English as primary and Japanese as
   maintained secondary where practical. Pages uses `/` for English and `/ja/` for Japanese,
   with an explicit `English | 日本語` switch on both pages.
2. Localization is confined to the presentation layer: explanations, scenario display
   names, maturity/compatibility, recovery/rollback summaries and disclosure guidance.
3. Scenario IDs, contract/schema versions, commit SHAs, artifact digests/provenance and
   machine statuses such as `PASS`, `FAIL` and `NOT_RUN` remain language-neutral.
4. Conformance evidence must never be duplicated or branched by locale. Both pages are
   generated from the same validated snapshot and link to the single root `result.json`.
5. Future locales must share that evidence source. They require deliberate presentation,
   translation and publication-allowlist changes; no automatic expansion of public output.
6. Preserve the publication allowlist and fail-closed validation. The only added published
   file in this change is `ja/index.html`; logs, raw artifacts and locale JSON remain excluded.
7. Keep the Public Disclosure Boundary unchanged. Translation does not authorize adding,
   inferring or publishing private implementation, decision logic, thresholds or adversarial corpora.
8. Treat PDDR as a scoped decision record, not an unconditional Policy. The operational
   language rule is separately stated in README.md/README.ja.md under the owner's explicit request.

## Delivery and validation

PR #7 implements the bilingual presentation while preserving the existing evidence schema
and source snapshot. Its publication set is exactly:

- `index.html`
- `ja/index.html`
- `style.css`
- `result.json`
- `.nojekyll`

Local portal tests verify shared JSON, unchanged scenario IDs/provenance, translation
coverage, identical machine statuses (including bootstrap/failure/NOT_RUN), unsupported
locale rejection and nested-file allowlisting. Existing artifact trust/digest tests remain.

The existing browser check is extended to English/Japanese at desktop/mobile widths,
including displayed status/ID parity, CSS loading, language-switch destinations, the
single evidence URL, local links and horizontal overflow. Japanese fonts are available
in CI for readable screenshots; no font asset is added to the public site.

Exact CI results and screenshot evidence are reported in PR #7. First live manual Pages
deployment remains the separate post-merge gate of Issue #3; implementation and test
results do not imply that production publication has already occurred.

## Consequences

- English and Japanese readers inspect the same conformance outcomes and source provenance.
- Translation maintenance is part of changes to public explanations where practical.
- Canonical machine values remain stable even when their surrounding labels are translated.
- Additional locales increase presentation work, not the number of evidence sources.
- The public/private disclosure boundary and bounded compatibility claims are unchanged.

## Revisit when

Revisit if translation maintenance is no longer practical, new locales are requested,
contract terminology causes divergent interpretations, evidence ingestion changes, or
publication scope needs an independently reviewed change. Do not infer a global policy
for unrelated projects from this record.

## Evidence

- Explicit project-owner request on 2026-10-09 to extend Issue #3 / PR #7 with these language and evidence requirements.
- PR #7: bilingual portal implementation and validation results.
- README.md and README.ja.md: short contributor-facing operational rules.
- portal/build.py and portal/test_portal.py: shared-evidence rendering and fail-closed publication checks.
- portal/check_browser.mjs: both-locale desktop/mobile checks.

## Related records

- [PDDR-0001: Public Conformance Boundary and Disclosure Policy](PDDR-0001-public-conformance-boundary.md) remains in force within its approved scope; this record does not supersede or widen it.

## 日本語概要

公開の人間向け説明は英語を主、日本語を維持対象の副言語とします。翻訳は表示層に限定し、
検証結果・識別子・契約やスキーマのバージョン・commit SHA・artifact digest・出典情報・status
は言語に依存させません。両ページと将来追加する言語も、一つの検証結果を共有します。

この PDDR は判断の経緯と適用範囲の記録であり、無条件の Policy ではありません。
実務ルールは README にも明記します。日本語対応を理由に非公開情報を推測・追加したり、
公開範囲を広げたりすることは認めません。
