# Bible MCP

Experimental local MCP server providing Bible study tools to AI agents/applications (like Claude Code, Claude Desktop, Codex, AnythingLLM, etc.) via [FastMCP](https://github.com/jlowin/fastmcp). SQLite backend with full-text and semantic search across WEB and KJV translations.

Although this was inspired by a [joke post](https://bsky.app/profile/alexkraieski.bsky.social/post/3mhlcfsxais2k) I made on Bluesky, giving AI strucutured access to the Bible is important if tasks require accurate citations of scripture. There's no tolerance for hallucinating something "like the Bible." 

## Setup

```bash
python setup.py
```

This creates a virtualenv, installs dependencies, and builds the database with embeddings. Embedding generation takes a few minutes per translation.

> Requires Python 3.11+.

## Claude Desktop config

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "bible": {
      "command": "/path/to/bible-mcp/.venv/bin/python",
      "args": ["/path/to/bible-mcp/server.py"],
      "env": { "BIBLE_DB_PATH": "/path/to/bible-mcp/bible.db" }
    }
  }
}
```

`setup.py` prints the exact paths to use when it finishes.

## Tools

| Tool | Description |
|---|---|
| `get_verse` | Exact verse lookup by reference |
| `get_passage` | Range of verses from a chapter |
| `get_cross_references` | TSK-derived cross-references for a verse, with optional vote-count filtering |
| `search_text` | FTS5 keyword search |
| `search_semantic` | Vector similarity search |
| `list_translations` | Show available translations (`web`, `kjv`) |
| `list_books` | List books for a translation |

Books are identified by OSIS ID (e.g. `Gen`, `Matt`, `Rev`).

## Cross-references

Cross-reference data is **not bundled** — fetch and load it separately after the initial setup:

```bash
.venv/bin/python scripts/ingest_cross_references.py
```

This downloads the dataset from OpenBible.info (~4 MB), parses it, and writes into the local `bible.db`. Re-running the command is safe (existing data is replaced).

### Attribution

Cross-reference data sourced from **[OpenBible.info](https://openbible.info)** ([CC BY 4.0](https://openbible.info/source.htm)), derived from the public-domain *Treasury of Scripture Knowledge*. The dataset is not bundled with this project; users run the ingestion script to populate it locally.

## Adding more translations

```bash
.venv/bin/python scripts/ingest.py --file data/my.xml --translation abc --name "My Translation"
```
