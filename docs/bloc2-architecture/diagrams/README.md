# Diagrams — NOUREDDINE Data Platform (Bloc 2)

All diagrams are written in **Mermaid** (`.mmd` source files). They can be rendered as PNG/SVG for slides.

## Diagram index

| File | Type | Description |
|------|------|-------------|
| `business-process.mmd` | flowchart | End-to-end customer and data journey |
| `erd.mmd` | erDiagram | OLTP entity-relationship diagram (all 10 tables) |
| `star-schema.mmd` | erDiagram | Gold star schema (5 dims + fact_sales) |
| `logical-architecture.mmd` | flowchart | Sources → medallion layers → consumption |
| `technical-architecture.mmd` | flowchart | Docker services, ports, volumes, network |

## How to render / export

### Option 1 — mermaid.live (online, easiest for slides)

1. Go to https://mermaid.live
2. Paste the `.mmd` file contents into the editor.
3. Click **Export → PNG** or **Export → SVG**.

### Option 2 — mermaid-cli (local, scriptable)

```bash
# Install
npm install -g @mermaid-js/mermaid-cli

# Render a single diagram
mmdc -i docs/bloc2-architecture/diagrams/erd.mmd \
     -o docs/bloc2-architecture/diagrams/erd.png \
     -t default -b white

# Render all
for f in docs/bloc2-architecture/diagrams/*.mmd; do
    mmdc -i "$f" -o "${f%.mmd}.png" -t default -b white
done
```

### Option 3 — VS Code extension

Install **Mermaid Preview** (`bierner.markdown-mermaid`) and open any `.mmd` file to see a live preview.
