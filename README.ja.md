# Security Twin Adapter Lab

[English](README.md) | **日本語**

> **境界付きセキュリティアダプタのための公開Conformance Lab**

**継続的に確かめる。必要最小限に介入する。意図的に復旧する。**

Security Twin Adapter Lab は、セキュリティアダプタの相互運用性を公開・再現可能な形で検証するためのテスト環境です。

このリポジトリは、private な Enterprise Security Twin 本体の公開版・縮小コピーではありません。

ここで公開するのは、アダプタが何を主張できるか、何を拒否すべきか、失敗をどう可視化し、どう復旧を確認するかという**公開可能な境界**です。検知回避に使える内部ロジックや意思決定実装は公開対象にしません。

## ここに置くもの

- 公開アダプタ契約;
- synthetic fixture / scenario;
- bounded reference adapter;
- Docker / Envoy test range;
- conformance workflow;
- machine-readable な公開テスト結果;
- GitHub Pages の仕様・互換性情報。

## ここに置かないもの

- private なdecision threshold / weight / heuristic / model prompt;
- 検知回避に使えるdecision boundary;
- private adversarial corpus;
- production credential や private repository token;
- public CI からの private source checkout;
- 無制限なprivileged control path。

fixture、trace、結果、実装詳細を追加する前に [PUBLIC_DISCLOSURE_BOUNDARY.md](PUBLIC_DISCLOSURE_BOUNDARY.md) を確認してください。

## 初期ロードマップ

1. disclosure / conformance boundary を固定;
2. Adapter Contract v1 を公開;
3. secret不要のpublic CIを構築;
4. GitHub Pages に小さなconformance portalを公開;
5. Envoy / Web API reference rangeを追加;
6. scoped containment / TTL rollback / partial failure / verified recovery を検証;
7. policy authorityをadapterへ移さず、他adapter familyへ展開。

## Public contract principle

Adapterがadvertiseするのは**技術的に可能なcapability**であり、policy authorityではありません。

Conformant actuator は、すでにauthorizeされた bounded request のみを受け取り、platform制約に応じてさらに狭めることはできますが、scopeやauthorityを広げることはできません。

このpublic contractは**観測可能な挙動と適合条件**を記述します。private runtime ABI、scoring logic、detection implementationの公開コピーではありません。

## Status

**Pre-v1 / synthetic reference fixture.**

現時点でproduction adapter compatibilityは主張しません。

## PDDR

公開境界に関する継続的な判断は [docs/records](docs/records/) に記録し、[PDDR Kit](https://github.com/serevy/pddr-kit) を使用します。

ローカル検証:

```bash
python .pddr/pddr.py validate
```

## License

Licenseはpublic/commercial boundaryの確認後に選定します。

## Envoy 参照環境の実行

Linux/macOS の Docker Compose v2 と Python 3.10+ で実行できます。

```bash
python3 scripts/run_envoy_conformance.py
```

セッション・ルート限定の制限、TTL 上限・自動期限切れ、明示的 rollback、
部分失敗、復旧の別途検証、制御用コンテナ停止を合成データで検証します。
終了時は環境を片付け、`results/envoy-web-api.json` に公開適合結果を出力します。
[構成・検証項目・公開範囲・手動手順](docs/envoy-range.md) を参照してください。
private 実装・判定ロジックを再現するものではありません。

## 公開 conformance ポータル

[GitHub Pages 日本語版](https://serevy.github.io/security-twin-adapter-lab/ja/) は初回の手動デプロイ後に公開されます。
公開済み集約結果・シナリオ別 PASS/FAIL/NOT RUN・rollback／復旧の検証結果を、
出典 run と対象 commit 付きで表示します。最新の公開スナップショットであり、
本番互換性や private 実装の検証を示すものではありません。
[ビルド・公開・結果更新手順](docs/portal.md) を参照してください。

## 公開コンテンツの言語と検証結果の実務ルール

人間向けの公開コンテンツは英語を主、日本語を維持対象の副言語とし、実用的な範囲で両方を更新します。
翻訳は表示層に限定し、機械可読な検証結果、識別子、契約・スキーマのバージョン、出典情報は
言語非依存に保ちます。言語別の結果 JSON を作ったり、公開範囲を広げたりしないでください。
Pages は `/` が英語、`/ja/` が日本語で、同じ `result.json` を参照します。
ポータルの説明を変更するときは両言語の表示と検証を更新してください。

[PDDR-0002](docs/records/PDDR-0002-public-localization-and-language-neutral-evidence.md) は
判断の理由と範囲を記録します。PDDR を無条件の Policy と解釈せず、この実務ルールを明示的に適用します。
