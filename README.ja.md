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

**Bootstrap / pre-v1.**

現時点でproduction adapter compatibilityは主張しません。

## PDDR

公開境界に関する継続的な判断は [docs/records](docs/records/) に記録し、[PDDR Kit](https://github.com/serevy/pddr-kit) を使用します。

ローカル検証:

```bash
python .pddr/pddr.py validate
```

## License

Licenseはpublic/commercial boundaryの確認後に選定します。
