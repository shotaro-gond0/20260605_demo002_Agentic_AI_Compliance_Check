# 🤖 Agentic AI リスク評価ツール

議事録テキストから Agentic AI アプリケーションに関する情報を自動抽出し、**EU AI Act（Regulation (EU) 2024/1689）** に基づくリスクレベルを判定する Web アプリです。

---

## 概要 / Overview

会議の議事録ファイル（Word・PDF・テキスト）をアップロードするだけで、以下を自動実行します：

1. **情報抽出** — GPT-4o が議事録から Agentic AI アプリの概要・利用者・データ種別などを抽出
2. **内容確認・編集** — 抽出結果を UI 上で手動修正可能
3. **リスク判定** — EU AI Act 第5条・第6条・第50条に基づいてリスクレベルを自動判定
4. **結果表示** — リスクレベルと詳細な判定根拠を表示

---

## スタック / Tech Stack

| レイヤー | 技術 |
|----------|------|
| UI | Gradio（Python） |
| AI ワークフロー | LangGraph + LangChain |
| LLM | OpenAI GPT-4o |
| ファイル解析 | python-docx（Word）、pypdf（PDF）、plain text |
| バックエンド API | Express 5（Node.js）、Drizzle ORM、PostgreSQL |
| パッケージ管理 | pnpm workspaces、TypeScript 5.9 |

---

## ディレクトリ構成 / Directory Structure

```
.
├── artifacts/
│   ├── ai-risk-app/          # Gradio UI + LangGraph ワークフロー（Python）
│   │   ├── app.py            # UI エントリーポイント
│   │   ├── graph.py          # LangGraph 定義（extract_graph / risk_graph）
│   │   └── file_parser.py    # ファイルパーサー（docx / pdf / txt）
│   ├── api-server/           # Express バックエンド API（Node.js）
│   └── mockup-sandbox/       # デザインプレビュー用サンドボックス
├── lib/
│   └── api-spec/
│       └── openapi.yaml      # OpenAPI 仕様
├── .env.example              # 必要な環境変数のサンプル
└── pnpm-workspace.yaml       # pnpm ワークスペース設定
```

---

## セットアップ手順 / Getting Started

### 前提条件 / Prerequisites

- **Python 3.11+**
- **Node.js 20+**
- **pnpm 9+**
- **PostgreSQL**（API サーバーを使う場合）
- **OpenAI API キー**

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd <repository-name>
```

### 2. 環境変数の設定

`.env.example` をコピーして `.env` を作成し、値を設定してください：

```bash
cp .env.example .env
```

次のセクション「[環境変数一覧](#環境変数一覧--environment-variables)」を参照してください。

### 3. Python 依存パッケージのインストール

```bash
pip install gradio langgraph langchain langchain-openai python-docx pypdf
```

### 4. Node.js 依存パッケージのインストール

```bash
pnpm install
```

### 5. データベースのセットアップ（オプション）

API サーバーを使用する場合は PostgreSQL データベースを作成し、`DATABASE_URL` を `.env` に設定してください。スキーマの適用は `lib/db` パッケージのマイグレーションスクリプトで行います（プロジェクト固有の手順に従ってください）。

---

## 起動方法 / Running the App

### AI リスク評価 UI（Gradio）

```bash
python artifacts/ai-risk-app/app.py
```

または環境変数でポートを指定：

```bash
PORT=8000 python artifacts/ai-risk-app/app.py
```

ブラウザで `http://localhost:8000` にアクセスしてください。

### API サーバー（オプション）

`PORT` 環境変数が必須です（未設定の場合は起動に失敗します）：

```bash
PORT=8080 pnpm --filter @workspace/api-server run dev
```

API は `http://localhost:8080/api` で起動します。

### TypeScript 型チェック

```bash
pnpm run typecheck
```

---

## 環境変数一覧 / Environment Variables

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `OPENAI_API_KEY` | ✅ 必須 | OpenAI API キー（GPT-4o 使用） |
| `DATABASE_URL` | API 使用時 | PostgreSQL 接続文字列 |
| `PORT` | 任意 | UI サーバーのポート番号（デフォルト: `8000`） |

---

## 使い方 / Usage

1. **ファイルアップロード** — `.docx`・`.pdf`・`.txt` 形式の議事録ファイルを選択
2. **情報抽出** — 「📄 情報を抽出する」ボタンをクリック（GPT-4o が自動解析）
3. **内容確認・編集** — 抽出された6項目を確認し、必要に応じて編集
4. **リスク評価** — 「⚖️ リスク評価を実行する」ボタンをクリック
5. **結果確認** — リスクレベルと EU AI Act の根拠条文を確認

### リスクレベルの分類

| アイコン | レベル | 説明 |
|----------|--------|------|
| 🚫 | 禁止（Prohibited） | EU AI Act 第5条により禁止される実践 |
| 🔴 | 高リスク（High-Risk） | 第6条により高リスク AI システムに分類 |
| 🟠 | 透明性義務あり | 第50条の透明性義務が適用 |
| 🟡 | 限定リスク | 特定の義務はあるが高リスクには非該当 |
| 🟢 | 最小リスク | 規制上の義務がほとんどない |

---

## アーキテクチャ / Architecture

```
議事録ファイル
    │
    ▼
file_parser.py ── テキスト抽出（docx / pdf / txt）
    │
    ▼
extract_graph（LangGraph）── GPT-4o で6項目を抽出
    │
    ▼
Gradio UI ── ユーザーが内容を確認・編集
    │
    ▼
risk_graph（LangGraph）── EU AI Act に基づきリスク判定
    │
    ▼
判定結果（リスクレベル + 根拠条文）
```

- 抽出グラフ・リスク評価グラフを **独立した LangGraph** として分離することで、ステップ間のユーザー編集を可能にしています。
- EU AI Act **第6条**を主な判定根拠とし、第5条・第50条も補助的に参照するプロンプト設計です。

---

## 参照 / References

- [EU AI Act — Regulation (EU) 2024/1689](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Gradio Documentation](https://www.gradio.app/docs/)
- [OpenAI API Documentation](https://platform.openai.com/docs)

---

## ライセンス / License

MIT License
