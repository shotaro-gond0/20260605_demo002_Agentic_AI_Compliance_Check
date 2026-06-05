---
name: Chainlit on Replit
description: Chainlitアプリをartifact workflowとして動かす際の必須設定とハマりポイント
---

# Chainlitをartifact workflowで動かす

**Why:** 相対パス・PYTHONPATH省略・asyncpg不足でワークフローが失敗した経験から。

## artifact.toml の正しい設定

```toml
[services.development]
run = "chainlit run /home/runner/workspace/artifacts/<slug>/app.py --port <PORT> --host 0.0.0.0"

[services.env]
PORT = "<PORT>"
BASE_PATH = "/"
PYTHONPATH = "/home/runner/workspace/artifacts/<slug>"
```

**How to apply:**
- `run`は絶対パスで指定（相対パスはCWDに依存して失敗する）
- PYTHONPATHを設定しないとapp.py内のローカルモジュールimportが失敗
- asyncpgをインストール必須（`pip install asyncpg`）— Chainlit内部依存

## ポート競合
- 既存ワークフローとポートが重複すると `[Errno 98] address already in use` で失敗
- `removeWorkflow`で旧ワークフローを削除してから再起動

## artifact登録の注意
- `createArtifact`はディレクトリが既に存在すると失敗する
- ディレクトリを作成してから登録する場合は先に`rm -rf`してから`createArtifact`を呼ぶ
- `.replit-artifact/artifact.toml`が存在しない状態で`verifyAndReplaceArtifactToml`は使えない
