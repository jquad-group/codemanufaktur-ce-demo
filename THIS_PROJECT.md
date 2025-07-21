## FEATURE:

> **📋 Projektübersicht:** Diese Datei beschreibt WAS gebaut werden soll. Für technische Implementierungsdetails siehe [GUIDELINES.md](./GUIDELINES.md)

**MCP Server für Supabase Database Integration**

Entwicklung eines Model Context Protocol (MCP) Servers, der es Claude und anderen AI-Assistenten ermöglicht, sicher und effizient mit Supabase-Datenbanken zu interagieren. Der Server bietet High-Level-Tools für Datenbankoperationen mit eingebauter Sicherheit durch Row Level Security (RLS) und Pydantic-Validierung.

**Hauptfunktionen:**
- Tabellen-Abfragen mit Filtern und Paginierung
- Sichere Dateninserts und Updates
- Schema-Introspection und Metadaten
- Row Level Security (RLS) Integration
- Echtzeit-Datenabonnements (geplant)
- Dateispeicher-Integration (geplant)

## EXAMPLES:

**Verfügbare MCP Tools:**

1. **`query_table`** - Tabellen abfragen mit optionalen Filtern
   ```python
   # Beispiel: Alle aktiven Benutzer mit Limit
   query_table("users", limit=50, filters={"status": "active"})
   ```

2. **`insert_record`** - Neue Datensätze einfügen
   ```python
   # Beispiel: Neuen Benutzer anlegen
   insert_record("users", {"name": "Max Mustermann", "email": "max@example.com"})
   ```

3. **`describe_table`** - Tabellenschema anzeigen
   ```python
   # Beispiel: Schema der Users-Tabelle
   describe_table("users")
   ```

4. **`list_tables`** - Verfügbare Tabellen auflisten
   ```python
   # Beispiel: Alle zugänglichen Tabellen
   list_tables()
   ```

5. **`update_record`** - Datensätze aktualisieren
   ```python
   # Beispiel: Benutzerstatus ändern
   update_record("users", filters={"id": 123}, updates={"status": "inactive"})
   ```

**Claude Desktop Integration:**
```json
{
  "mcpServers": {
    "supabase-database": {
      "command": "uv",
      "args": ["--directory", "/pfad/zu/projekt", "run", "python", "src/mcp_server.py"],
      "env": {
        "SUPABASE_URL": "https://ihr-projekt.supabase.co",
        "SUPABASE_ANON_KEY": "ihr-anon-key"
      }
    }
  }
}
```

> **💡 Vollständige Code-Beispiele:** Detaillierte Implementierungen aller Tools finden Sie in [GUIDELINES.md - Tool Implementation Pattern](./GUIDELINES.md#tool-implementation-pattern)

## DOCUMENTATION:

**Erforderliche Dokumentation für die Entwicklung:**

📖 **Projekt-Dokumentation:**
- **[GUIDELINES.md](./GUIDELINES.md)** - Technische Implementierungsrichtlinien für dieses Projekt

🌐 **Externe Dokumentation:**

1. **Supabase Python Client Documentation**
   - https://supabase.com/docs/reference/python/introduction
   - https://github.com/supabase/supabase-py

2. **Model Context Protocol (MCP) Documentation**
   - https://modelcontextprotocol.io/introduction
   - https://github.com/modelcontextprotocol/python-sdk

3. **FastMCP Framework**
   - https://github.com/modelcontextprotocol/python-sdk (FastMCP examples)
   - https://modelcontextprotocol.io/quickstart/server

4. **Supabase Row Level Security (RLS)**
   - https://supabase.com/docs/guides/auth/row-level-security
   - https://supabase.com/docs/guides/database/postgres/row-level-security

5. **Pydantic Validation**
   - https://docs.pydantic.dev/latest/
   - https://docs.pydantic.dev/latest/concepts/validators/

6. **Python asyncio & typing**
   - https://docs.python.org/3/library/asyncio.html
   - https://docs.python.org/3/library/typing.html

## OTHER CONSIDERATIONS:

**Wichtige Überlegungen und häufige Fallstricke:**

1. **Sicherheit (KRITISCH):**
   - ❌ **Fallstrick:** Direkte SQL-Injection durch ungefilterte Eingaben
   - ✅ **Lösung:** Immer Pydantic-Schemas für Input-Validierung verwenden
   - ✅ **Lösung:** Supabase RLS-Policies für Datenzugriffskontrolle nutzen
   - ❌ **Fallstrick:** Service Role Key in Produktionsumgebung exponieren

2. **MCP-spezifische Gotchas:**
   - ❌ **Fallstrick:** `print()` Statements in stdio-basierten MCP Servern (korrumpiert JSON-RPC)
   - ✅ **Lösung:** Immer `logging` für Debug-Ausgaben verwenden
   - ❌ **Fallstrick:** Rückgabe von `List[TextContent]` statt einfachen Strings in FastMCP
   - ✅ **Lösung:** FastMCP konvertiert automatisch strings zu TextContent

3. **Supabase-spezifische Überlegungen:**
   - ❌ **Fallstrick:** Vergessen von RLS-Policies → Alle Daten für alle Benutzer sichtbar
   - ✅ **Lösung:** RLS immer aktivieren und testen mit verschiedenen Benutzerkontexten
   - ❌ **Fallstrick:** Anon Key vs Service Role Key Verwirrung
   - ✅ **Lösung:** Anon Key für normale Operationen, Service Role nur für Admin-Tasks

4. **Entwicklungsworkflow:**
   - ✅ **Testing:** Immer `uv run mcp dev src/mcp_server.py` für lokales Testen verwenden
   - ✅ **Installation:** `uv run mcp install` für Claude Desktop Integration
   - ❌ **Fallstrick:** Vergessen von absoluten Pfaden in Claude Desktop Konfiguration
   - ✅ **Dependencies:** `uv add "mcp[cli]" supabase python-dotenv pydantic`
   - 📖 **Vollständige Workflow-Details:** Siehe [GUIDELINES.md - Local Development Workflow](./GUIDELINES.md#local-development-workflow)

5. **Performance & Limits:**
   - ⚠️ **Beachtung:** Supabase hat API Rate Limits (besonders im Free Tier)
   - ✅ **Lösung:** Pagination mit vernünftigen Limits implementieren (Standard: 100, Max: 1000)
   - ⚠️ **Beachtung:** Large Queries können timeout
   - ✅ **Lösung:** Streaming für große Datensätze implementieren

6. **Error Handling:**
   - ❌ **Fallstrick:** Generische Exception-Messages ohne Context
   - ✅ **Lösung:** Spezifische Error-Messages mit Supabase-Error-Details
   - ❌ **Fallstrick:** Nicht abgefangene Async-Exceptions
   - ✅ **Lösung:** Alle async Operationen in try/except wrappen

7. **Environment & Deployment:**
   - ❌ **Fallstrick:** .env Datei in Git committen
   - ✅ **Lösung:** .env immer in .gitignore eintragen
   - ❌ **Fallstrick:** Hardcoded Supabase URLs/Keys im Code
   - ✅ **Lösung:** Immer Environment Variables verwenden

8. **Projekt Setup & Dokumentation (KRITISCH):**
   - ✅ **Erforderlich:** `.env.example` Datei mit allen benötigten Environment Variables
   - ✅ **Erforderlich:** Detailliertes README.md mit Setup-Anweisungen
   - ✅ **Erforderlich:** Projekt-Struktur im README dokumentieren
   - ✅ **Erforderlich:** `python-dotenv` und `load_dotenv()` für Environment Variables verwenden (siehe GUIDELINES.md)
   - ❌ **Fallstrick:** Fehlende oder unvollständige Setup-Dokumentation
   - ❌ **Fallstrick:** Environment Variables nicht von Beginn an konfigurieren

**Erforderliche Dateien für Setup:**

**`.env.example` (Template für Environment Variables):**
```bash
# Supabase Configuration (Required)
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here

# Optional: For admin operations
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# Optional: Logging level
LOG_LEVEL=INFO

# Optional: MCP Server configuration
MCP_SERVER_NAME=supabase-mcp
MCP_MAX_QUERY_LIMIT=1000
```

**`README.md` Struktur (Mindestanforderungen):**
```markdown
# Supabase MCP Server

## 🚀 Quick Start
1. Clone repository
2. Copy `.env.example` to `.env`
3. Configure Supabase credentials
4. Install dependencies: `uv add "mcp[cli]" supabase python-dotenv pydantic`
5. Test server: `uv run mcp dev src/mcp_server.py`

## 📁 Project Structure
## ⚙️ Configuration
## 🔧 Development
## 🧪 Testing
## 📖 Available Tools
## 🔒 Security
## 🐛 Troubleshooting
```

**Implementierungsdetails:**
- **Environment Variables Implementation:** Siehe [GUIDELINES.md - Environment Variables Implementation](./GUIDELINES.md#environment-variables-implementation)
- **MCP Server Patterns:** Siehe [GUIDELINES.md - MCP Tools Implementation](./GUIDELINES.md#mcp-tools-implementation)
- **Security Implementation:** Siehe [GUIDELINES.md - Security Implementation](./GUIDELINES.md#security-implementation)
- **Code Style & Type Safety:** Siehe [GUIDELINES.md - Type Safety Rules](./GUIDELINES.md#type-safety-rules)

