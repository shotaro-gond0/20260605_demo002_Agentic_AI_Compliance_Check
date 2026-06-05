# Agentic AI リスク評価ツール

議事録テキストからAgentic AIアプリケーションに関する情報を抽出し、EU AI Act（Regulation (EU) 2024/1689）に基づくリスクレベルを自動判定するWebアプリ。

## Run & Operate

- `chainlit run artifacts/ai-risk-app/app.py --port 8000 --host 0.0.0.0` — Chainlit UIを起動
- `pnpm --filter @workspace/api-server run dev` — Node.js APIサーバーを起動（ポート8080）
- `pnpm run typecheck` — TypeScript全体のタイプチェック
- Required env: `OPENAI_API_KEY` — OpenAI API key（gpt-4o使用）

## Stack

- **UI**: Chainlit（Python）
- **Workflow**: LangGraph + LangChain
- **LLM**: OpenAI GPT-4o（via langchain-openai）
- **ファイル解析**: python-docx（Word）、pypdf（PDF）、plain text
- **バックエンドAPI**: Express 5（Node.js）、Drizzle ORM、PostgreSQL
- **フロント共通**: pnpm workspaces、TypeScript 5.9

## Where things live

- `artifacts/ai-risk-app/app.py` — Chainlit UIエントリーポイント（フェーズ管理・UIハンドラー）
- `artifacts/ai-risk-app/graph.py` — LangGraphワークフロー定義（extract_graph、risk_graph）
- `artifacts/ai-risk-app/file_parser.py` — ファイルパーサー（docx/pdf/txt）
- `artifacts/ai-risk-app/.chainlit/config.toml` — Chainlit設定
- `lib/api-spec/openapi.yaml` — OpenAPI仕様（APIサーバー用）

## Architecture decisions

- ChainlitのセッションをAppState TypedDictで管理（LangGraphと同じ型）
- 抽出グラフ・リスク評価グラフを独立したLangGraphとして分離（ステップ間のユーザー編集を可能にするため）
- `on_settings_update`コールバックでフォーム変更を即時セッションに保存
- EU AI Act第6条を主判定根拠とし、第5条・第50条も補助的に参照するプロンプト設計

## Product

1. 議事録ファイル（Word/PDF/TXT）のアップロード
2. LangGraphによるAgentic AI情報抽出（6項目）
3. ChainlitのChatSettings UIで抽出内容を編集・確定
4. EU AI Actに基づくリスクレベル自動判定（第5条・第6条・第50条）
5. 判定結果（リスクレベル + 根拠）の表示

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- Chainlit WorkflowはPYTHONPATH環境変数でapp.pyの依存モジュールパスを指定する必要あり
- ポート8000を使用（artifact.tomlで設定）
- asyncpgパッケージが必要（Chainlit内部依存）
- `chainlit run`は絶対パスで指定すること（相対パスだとCWDに依存して失敗する）

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
