# Architecture Diagrams

Natural language → SQL pipeline for RBI CIMS/RAQ return 2065 (Oracle backend).
Diagrams are Mermaid; they render on GitHub and in most Markdown viewers.

---

## 1. Component architecture

```mermaid
graph TB
    subgraph CLIENT["Client — React 18 + Vite 5 + Tailwind 3"]
        UI["Home page<br/><i>frontend/src/pages/Home</i>"]
        COMP["QueryInput · SqlDisplay<br/>ResultsTable · StatusBadge"]
        APIJS["api.js<br/><i>fetch wrapper</i>"]
        UI --> COMP --> APIJS
    end

    subgraph API["API — FastAPI + Uvicorn (CORS :5173)"]
        MAIN["main.py<br/><i>startup banner: asserts EMBEDDING_DIR</i>"]
        QROUTE["routes/query.py<br/><b>POST /query</b> — orchestrator"]
        HROUTE["routes/health.py<br/>GET /health"]
        SCHEMAS["schemas.py<br/><i>QueryRequest / QueryResult</i>"]
        MAIN --> QROUTE
        MAIN --> HROUTE
        QROUTE -.validates via.-> SCHEMAS
    end

    subgraph CORE["Pipeline core — src/"]
        RETR["retriever.py<br/><i>5-signal RRF fusion + precedence tiers</i>"]
        SEL["selector.py<br/><i>shortlist → 1 table</i>"]
        GEN["sql_generator.py<br/><i>prompt build · correction loop · validate</i>"]
        EXEC["executor.py<br/><i>oracledb pool · dry run · execute</i>"]
        VEC["vectorizer.py<br/><i>SentenceTransformer wrapper</i>"]
        CM["concept_map.py<br/><i>XBRL business layer</i>"]
        BS["business_semantics.py<br/><i>prompt block renderer</i>"]
        SEML["semantic_layer.py<br/><i>join allow-list</i>"]
        SECA["section_alias.py<br/><i>'Section 12' → table</i>"]
        DESC["description_fetcher.py<br/><i>row-label samples</i>"]
        CFG["config.py<br/><i>all env-driven settings</i>"]
    end

    subgraph MODELS["Models"]
        EMB["<b>bge-large-en</b> · 1024-d<br/>sentence-transformers 2.7<br/><i>LOCAL, in-process</i>"]
        SQLM["<b>sqlcoder-7b-2</b> Q5_K_M<br/><i>REMOTE via Ollama</i>"]
        SELM["<b>qwen2.5-coder:7b</b><br/><i>REMOTE via Ollama</i>"]
    end

    subgraph STORE["Stores"]
        FAISS["FAISS IndexFlatIP · faiss-cpu<br/>table · column · row_label<br/>qa · concept<br/><i>+ .pkl payload sidecars</i>"]
        ARTI["schema.json · concept_map.json<br/>semantic_layer.yaml<br/>qa_pairs.json · description_samples.json"]
        ORA[("Oracle XE<br/><i>41 CIMS_RAQ_Q_* tables</i>")]
    end

    subgraph PROXY["Ollama proxy — IIS / ASP.NET"]
        OP["/OllamaProxy/api/generate"]
    end

    APIJS ==>|"HTTP JSON"| QROUTE

    QROUTE ==> RETR
    QROUTE ==> SEL
    QROUTE ==> GEN
    QROUTE ==> EXEC

    RETR --> VEC
    RETR --> SECA
    RETR --> DESC
    SEL --> SEML
    GEN --> BS
    BS --> CM
    GEN --> SEML

    VEC ==> EMB
    SEL ==>|"HTTP"| OP
    GEN ==>|"HTTP"| OP
    OP ==> SELM
    OP ==> SQLM

    RETR --> FAISS
    CM --> ARTI
    GEN --> ARTI
    SEML --> ARTI
    EXEC ==>|"python-oracledb<br/>thin mode, pooled"| ORA

    CFG -.->|"read at call time"| RETR
    CFG -.-> SEL
    CFG -.-> GEN
    CFG -.-> EXEC

    classDef client fill:#e8f0f6,stroke:#1d5f8a,color:#12202b
    classDef api fill:#e4f1ec,stroke:#1f7a5c,color:#0f2b22
    classDef core fill:#f4f1e8,stroke:#8a6d1d,color:#2b2412
    classDef model fill:#f8e8e6,stroke:#a4342b,color:#2b1210
    classDef store fill:#eceef1,stroke:#5a6472,color:#1a1f26
    classDef proxy fill:#f6ecdd,stroke:#9c5c0c,color:#2b1f0c

    class UI,COMP,APIJS client
    class MAIN,QROUTE,HROUTE,SCHEMAS api
    class RETR,SEL,GEN,EXEC,VEC,CM,BS,SEML,SECA,DESC,CFG core
    class EMB,SQLM,SELM model
    class FAISS,ARTI,ORA store
    class OP proxy
```

---

## 2. Model touchpoints

Both remote models share one URL and differ only by the `model` field in the
payload — which is why an unpulled selector model surfaces as a 404 while SQL
generation keeps working.

```mermaid
graph LR
    Q["User question"]

    subgraph LOCAL["Runs in the API process"]
        E["<b>bge-large-en</b><br/>SentenceTransformer<br/>1024-d, L2-normalised<br/>~100ms CPU"]
    end

    subgraph REMOTE["Remote — one URL, two models"]
        direction TB
        S["<b>qwen2.5-coder:7b</b> · 4.7GB<br/><i>instruct</i> — picks the table<br/>temp 0 · num_predict 160"]
        G["<b>sqlcoder-7b-2:Q5_K_M</b> · 4.8GB<br/><i>completion</i> — writes SQL only<br/>temp 0 · num_predict 512 · ctx 8192"]
    end

    Q -->|"_expand_query()<br/>npa → non performing assets"| E
    E -->|"ONE vector,<br/>reused 6×"| F["5 FAISS searches<br/>+ RRF fusion"]
    F -->|"8 candidates"| S
    S -->|"1 table"| G
    G -->|"SQL"| V["validate + Oracle dry run"]
    V -->|"invalid, ≤3 rounds"| G

    S -.->|"404: model not pulled<br/><b>fallback = retrieval top-1</b>"| FB["degraded:<br/>top1 0.711 vs hit@k 0.911"]

    classDef local fill:#e4f1ec,stroke:#1f7a5c,color:#0f2b22
    classDef remote fill:#f8e8e6,stroke:#a4342b,color:#2b1210
    classDef flow fill:#eceef1,stroke:#5a6472,color:#1a1f26
    classDef bad fill:#f8e8e6,stroke:#a4342b,color:#2b1210,stroke-dasharray: 4 3

    class E local
    class S,G remote
    class Q,F,V flow
    class FB bad
```

---

## 3. How a question becomes an answer

Non-technical overview. Every question passes three safeguards before any data is
read, and questions we have answered before skip the AI entirely.

```mermaid
flowchart TD
    Q(["Analyst asks a question<br/>in plain English"])

    Q --> CLEAR{"Enough detail<br/>to answer?"}
    CLEAR -->|"too vague"| ASK(["Ask for the metric<br/>and the period"])

    CLEAR -->|yes| KNOWN{"Asked before?"}
    KNOWN -->|"yes — recognised"| REUSE(["<b>Reuse the approved answer</b><br/>Written and checked by hand.<br/>No AI involved, instant."])

    KNOWN -->|"no — new question"| FIND["<b>Find the right part of the return</b><br/>Searches the regulatory vocabulary,<br/>not just column names"]

    FIND --> PICK["<b>Narrow to one section</b><br/>A second check confirms the single<br/>correct table before anything is written"]

    PICK --> DRAFT["<b>Draft the query</b><br/>Given only that one section's structure,<br/>its real row labels, and the reporting unit"]

    DRAFT --> SAFE{"<b>Safety checks</b><br/>Read-only · real columns only<br/>test-run against the database"}
    SAFE -->|"problem found"| RETRY["Correct and re-check<br/><i>up to 3 attempts</i>"]
    RETRY --> DRAFT

    SAFE -->|passes| RUN["<b>Run the query</b><br/>Read-only, capped at 100 rows"]
    RUN --> OUT(["<b>Answer</b><br/>figures · the query used<br/>· any caveats"])

    SAFE -->|"still failing"| FLAG(["Return the problem,<br/>not a guess"])

    classDef ask fill:#e4f1ec,stroke:#1f7a5c,stroke-width:2px,color:#0f2b22
    classDef work fill:#e8f0f6,stroke:#1d5f8a,color:#12202b
    classDef check fill:#f6ecdd,stroke:#9c5c0c,color:#2b1f0c
    classDef done fill:#e4f1ec,stroke:#1f7a5c,stroke-width:2px,color:#0f2b22

    class Q,ASK,FLAG ask
    class FIND,PICK,DRAFT,RUN,RETRY work
    class CLEAR,KNOWN,SAFE check
    class REUSE,OUT done
```

**What this buys us**

| | |
|---|---|
| **Repeat questions are free** | A recognised question replays an answer a human already verified — no AI, no cost, no risk of a different answer next time. |
| **The AI is never given a free hand** | It sees one section of the return, that section's real row labels, and nothing else. It cannot reach data it was not given. |
| **Nothing is written, ever** | Read-only by design, enforced before execution, not by convention. |
| **Wrong beats invented** | If the query cannot be made valid in three attempts, the system reports the problem instead of returning a plausible number. |
| **Every answer is auditable** | The query used is returned alongside the figures, so any number can be traced back to the exact rows it came from. |

---

## 3b. Same flow, engineering detail

```mermaid
flowchart TD
    START(["POST /query"]) --> G0{"len ≥ 20 chars?"}
    G0 -->|no| X0(["return needs_more_info"])
    G0 -->|yes| G1{"time expression<br/>present?"}
    G1 -->|no| HINT["attach accuracy_hint"]
    G1 -->|yes| EMB1
    HINT --> EMB1

    EMB1["<b>1 · Embed once</b><br/>_expand_query → bge-large-en<br/>one 1024-d vector, reused everywhere"]

    EMB1 --> QA{"<b>2 ·</b> literal similarity<br/>to a stored question<br/>≥ 0.99?"}
    QA -->|yes| X1(["replay verified SQL<br/>validate → execute<br/>source=direct_match"])

    QA -->|no| RET["<b>3 · Retrieval — widen (k=8)</b><br/>qa 2.5 · table 2.0 · concept 2.0<br/>column 1.5 · row_label 1.0 · member 0<br/>fused by RRF"]

    RET --> TIER["precedence tiers, in order:<br/>relative-floor prune (15%)<br/>→ 95% QA match forced to front<br/>→ explicit section pinned"]

    TIER --> EMPTY{"any table?"}
    EMPTY -->|no| X2(["no matching tables"])

    EMPTY -->|yes| SELQ{"<b>4 ·</b> selection needed?<br/>>1 candidate, no strong match,<br/>top ≤ 2× runner-up"}
    SELQ -->|no| PRUNE
    SELQ -->|yes| SELM["selector model<br/>qwen2.5-coder:7b<br/>8 → 1 table"]
    SELM -->|"404 / error"| FB["fall back to top-1<br/><i>silent — no warning surfaced</i>"]
    SELM --> PRUNE
    FB --> PRUNE

    PRUNE["<b>5 · Prune</b><br/>drop columns + row labels<br/>of rejected tables"]

    PRUNE --> GEN["<b>6 · Generate</b> — sqlcoder-7b-2<br/>Task → DDL → business semantics<br/>→ time → example → rules → Answer"]

    GEN --> CHK{"validate_sql<br/>AND Oracle dry run"}
    CHK -->|"invalid,<br/>< 3 rounds"| FIX["deterministic autocorrect,<br/>else re-prompt with the error"]
    FIX --> GEN

    CHK -->|valid| VAL["<b>7 · Validate</b><br/>SELECT only · no DML/DDL<br/>TO_DATE-wrapped literals<br/>declared joins only<br/>+ stock/flow warning"]

    VAL --> EX["<b>8 · Execute</b><br/>oracledb pool · max 100 rows"]
    EX --> RESP(["<b>9 · Respond</b><br/>sql · rows · warnings<br/>source · timings_ms"])

    CHK -->|"invalid after 3"| RESP

    classDef exit fill:#e4f1ec,stroke:#1f7a5c,color:#0f2b22
    classDef stage fill:#e8f0f6,stroke:#1d5f8a,color:#12202b
    classDef model fill:#f8e8e6,stroke:#a4342b,color:#2b1210
    classDef bad fill:#f6ecdd,stroke:#9c5c0c,color:#2b1f0c
    classDef gate fill:#eceef1,stroke:#5a6472,color:#1a1f26

    class X0,X1,X2,RESP exit
    class EMB1,RET,TIER,PRUNE,VAL,EX,HINT stage
    class SELM,GEN model
    class FB,FIX bad
    class G0,G1,QA,EMPTY,SELQ,CHK gate
```

---

## 4. Offline build vs runtime read

Nothing in the request path writes. Every artifact is built ahead of time; the
API only reads.

```mermaid
graph TB
    subgraph SRC["Sources of truth"]
        XSD["XBRL taxonomy<br/><i>data/2065 1.json</i> · 3.27 MB"]
        XLS["RAQBaseFile.xlsx<br/><i>34-sheet return form</i>"]
        DDL["data/schema.sql<br/><i>Oracle DDL dump</i>"]
        DESCX["data/.json-formatted<br/><i>column descriptions</i>"]
        LIVE[("Oracle<br/><i>live row labels</i>")]
    end

    subgraph BUILD["Build — embedding_building/cims_raq_quarterly/"]
        BSCH["build_schema.py"]
        BCM["build_concept_map.py"]
        BEMB["build_embeddings.py"]
        BCE["build_concept_embeddings.py"]
        BQA["build_qa_index.py"]
    end

    subgraph ART["Artifacts read at runtime"]
        SJ["schema.json<br/><i>26 of 41 tables</i>"]
        CMJ["concept_map.json<br/><i>245 metrics · 0.48 MB</i>"]
        IDX["table · column · row_label<br/>concept · qa indexes"]
        DS["description_samples.json"]
        SL["semantic_layer.yaml"]
    end

    subgraph VER["Verification"]
        ER["scripts/eval_retrieval.py<br/><i>no LLM · ~17s · 3 datasets</i>"]
        TG["scripts/test_accuracy_guards.py<br/><i>71 offline checks</i>"]
        P0["scripts/phase0_xbrl_reconcile.py<br/><i>coverage + live validation</i>"]
        VU["scripts/verify_unit_conversion.py<br/><i>needs Ollama</i>"]
        RE["eval/run_eval.py<br/><i>full pipeline · hours</i>"]
    end

    DDL --> BSCH
    DESCX --> BSCH
    LIVE --> BSCH
    BSCH --> SJ

    XSD --> BCM
    BCM --> CMJ

    SJ --> BEMB
    LIVE --> BEMB
    BEMB --> IDX
    BEMB --> DS

    CMJ --> BCE
    SJ --> BCE
    BCE --> IDX

    BQA --> IDX

    XLS -->|"hand-written<br/>from form wording"| RQ["eval/raq_user_queries.json<br/><i>55 queries · leak-free</i>"]
    RQ --> ER

    SJ --> ER
    IDX --> ER
    CMJ --> TG
    XSD --> P0
    LIVE --> P0

    classDef src fill:#eceef1,stroke:#5a6472,color:#1a1f26
    classDef build fill:#f4f1e8,stroke:#8a6d1d,color:#2b2412
    classDef art fill:#e8f0f6,stroke:#1d5f8a,color:#12202b
    classDef ver fill:#e4f1ec,stroke:#1f7a5c,color:#0f2b22

    class XSD,XLS,DDL,DESCX,LIVE src
    class BSCH,BCM,BEMB,BCE,BQA build
    class SJ,CMJ,IDX,DS,SL,RQ art
    class ER,TG,P0,VU,RE ver
```

Rebuild order — each step reads the previous one's output:

```
build_schema.py → build_concept_map.py → build_embeddings.py → build_concept_embeddings.py
                                                                ↳ then restart the API
```

The API caches indexes and artifacts for the life of the process, and uvicorn's
reloader watches `api/` and `src/` but **not** `embedding_building/` — a rebuild
alone will not be picked up.
