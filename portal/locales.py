"""Presentation strings only. Evidence values and identifiers are never translated."""
from evidence import SCENARIOS

EN = {
    'scenarios': SCENARIOS,
    'source': 'Evidence source', 'artifact': 'Public artifact', 'run': 'Workflow run',
    'commit': 'Tested commit', 'updated': 'Run updated (UTC)', 'outcome': 'Workflow outcome',
    'headline': 'Published synthetic evidence',
    'detail': 'This is the latest published snapshot, not a live status feed. The tested commit and source run identify exactly what was verified.',
    'no_evidence': 'No runtime evidence has been published in this snapshot. Bootstrap does not establish compatibility.',
    'bootstrap_headline': 'Bootstrap · awaiting evidence',
    'bootstrap_detail': 'The public contract is a draft. Runtime checks remain NOT_RUN until public evidence is imported and reviewed.',
    'execution_failure': 'Execution failure', 'language_label': 'Language',
}
JA = {
    'scenarios': {
        'baseline_availability': '通常時の可用性',
        'scoped_containment': 'セッション単位の限定的な制限',
        'unrelated_session_survival': '無関係なセッションの通信継続',
        'ttl_bound': 'TTL の上限',
        'automatic_expiry': '有効期限による自動解除',
        'explicit_rollback': '明示的なロールバック',
        'partial_failure_visibility': '部分失敗の可視化',
        'verified_clean_recovery': '制限がない状態への復旧確認',
        'provider_unavailable': 'プロバイダーの利用不能',
        'rollback_failure': 'ロールバックの失敗',
        'recovery_verification_failure': '復旧確認の失敗',
        'technical_preflight': '技術的な事前検証',
        'control_plane_unavailable': '制御系の利用不能',
        'restart_clean_recovery': '再起動後の状態・通信の復旧確認',
    },
    'source': '検証結果の出典', 'artifact': '公開 artifact', 'run': 'ワークフロー実行',
    'commit': '検証対象の commit', 'updated': '実行情報の更新日時（UTC）', 'outcome': 'ワークフローの結果',
    'headline': '公開済みの合成環境での検証結果',
    'detail': '最後に公開したスナップショットです。最新の実行状況を自動更新する表示ではありません。何を検証したかは、対象 commit と出典の実行情報で確認できます。',
    'no_evidence': 'このスナップショットには実行時の検証結果がまだ公開されていません。初期状態の表示は互換性の確認を意味しません。',
    'bootstrap_headline': '初期状態 · 検証結果の公開待ち',
    'bootstrap_detail': '公開契約は草案です。公開済みの検証結果を取り込んでレビューするまで、各項目は NOT_RUN のままです。',
    'execution_failure': '実行処理の失敗', 'language_label': '言語',
}
LOCALES = {'en': EN, 'ja': JA}
