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
| `search_text` | FTS5 keyword search |
| `search_semantic` | Vector similarity search |
| `list_translations` | Show available translations (`web`, `kjv`) |
| `list_books` | List books for a translation |

Books are identified by OSIS ID (e.g. `Gen`, `Matt`, `Rev`).

## Adding more translations

```bash
.venv/bin/python scripts/ingest.py --file data/my.xml --translation abc --name "My Translation"
```
