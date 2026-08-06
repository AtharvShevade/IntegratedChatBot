"""
The Context layer: everything between retrieval and the SQL prompt.

Retrieval answers "what might be relevant" (recall). This package answers "what
goes in the prompt" (precision), and it is the only thing the renderer is
allowed to read from. If a column, row label, rule or example is not in the
PromptContext this package emits, no prompt style can leak it — which is the
structural fix for the prompt builder reaching back into schema.json at render
time and re-inflating whole tables.

Stage layout (see also the module docstrings):

    normalize   query expansion + one embedding          (still in src.retriever)
    intent.py   what KIND of question is this
    domain.py   which return/section may answer it       -> DomainGate
    metrics.py  which (table, column) does it name       -> ColumnBinding
    slicer.py   the minimum slice of one table           -> TableSlice
    resolver.py assemble + budget                        -> PromptContext
    budget.py   per-axis caps and the drop report

types.py holds the data structures all of the above exchange. They are frozen
dataclasses of tuples: a PromptContext is fully serializable, which is what
makes context quality measurable offline (scripts/eval_context.py) without an
LLM or a database.
"""
