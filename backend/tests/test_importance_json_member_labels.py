"""Dimension-member names come from structure.member_labels (6.0 table-linkbase
returns list members only as ids under structure.axes)."""
from backend.tools.importance_json import JsonImportance


def _payload(member_labels=None):
    p = {
        "return_metadata": {"regulatory_importance_status": {"available": True}},
        "concepts": [{
            "concept_id": "qcb:PE001504", "label": "Loans And Advances - Private Sector SMEs",
            "regulatory_importance": {"matched": True, "score": 50.0, "tier": "Medium"},
        }],
        "structure": {"axes": [{"axis_name": "qcb:DE000004", "members": ["qcb:DM000012"]}]},
    }
    if member_labels is not None:
        p["structure"]["member_labels"] = member_labels
    return p


def test_member_label_resolved_from_structure_member_labels():
    idx = JsonImportance("4079", "x.json", _payload({"qcb:DM000012": "Total"}))
    assert idx.label_for("DM000012") == "Total"
    assert idx.label_for("qcb:DM000012") == "Total"


def test_old_json_without_member_labels_still_loads():
    idx = JsonImportance("4079", "x.json", _payload())
    assert idx.label_for("DM000012") == ""
    assert idx.label_for("PE001504") == "Loans And Advances - Private Sector SMEs"


def test_concept_label_wins_over_member_label_and_marker_is_stripped():
    p = _payload({"qcb:PE001504": "SHOULD NOT WIN", "qcb:DM000010": "Inside Qatar [member]"})
    idx = JsonImportance("4079", "x.json", p)
    assert idx.label_for("PE001504") == "Loans And Advances - Private Sector SMEs"
    assert idx.label_for("DM000010") == "Inside Qatar"
