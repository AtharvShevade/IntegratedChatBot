"""L-14: XML parsing of untrusted/externally-supplied XML (user-submitted
XBRL instance documents, validator-generated error files) now goes through
defusedxml.ElementTree instead of the stdlib xml.etree.ElementTree, which
would silently resolve XXE/entity-expansion constructs.

Covers:
  - backend/tools/xml_loader.py (shared loader, used widely)
  - backend/tools/instance_context.py (parses the actual XBRL instance doc)
  - backend/tools/report_lookup.py's _extract_error_summary_from_xml /
    count_errors_by_category's XML branch
  - backend/tools/xbrl_comparator.py's XML-fallback instance loader

Confirms normal/malformed XML still works exactly as before, and that a
classic XXE/billion-laughs payload is rejected rather than resolved.
"""
from __future__ import annotations

from backend.tools import xml_loader

_NORMAL_XML = '<?xml version="1.0"?><Root><Row Id="1" Name="Alpha"/></Root>'
_MALFORMED_XML = "<Root><Row Id=1></Root"
_XXE_ENTITY_XML = """<?xml version="1.0"?>
<!DOCTYPE root [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<Root>&xxe;</Root>"""
_BILLION_LAUGHS_XML = """<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
]>
<Root>&lol2;</Root>"""


class TestXmlLoaderNormalBehaviorUnchanged:
    def test_valid_xml_parses_normally(self, tmp_path):
        p = tmp_path / "good.xml"
        p.write_text(_NORMAL_XML, encoding="utf-8")
        root = xml_loader.load_xml_tree(str(p), label="good.xml")
        assert root is not None
        assert root.find("Row").get("Name") == "Alpha"

    def test_malformed_xml_returns_none_not_raise(self, tmp_path):
        p = tmp_path / "bad.xml"
        p.write_text(_MALFORMED_XML, encoding="utf-8")
        root = xml_loader.load_xml_tree(str(p), label="bad.xml")
        assert root is None

    def test_missing_file_returns_none(self, tmp_path):
        root = xml_loader.load_xml_tree(str(tmp_path / "missing.xml"))
        assert root is None

    def test_empty_path_returns_none(self):
        assert xml_loader.load_xml_tree("") is None


class TestXmlLoaderRejectsUnsafeConstructs:
    def test_xxe_external_entity_is_rejected_not_resolved(self, tmp_path):
        p = tmp_path / "xxe.xml"
        p.write_text(_XXE_ENTITY_XML, encoding="utf-8")
        root = xml_loader.load_xml_tree(str(p), label="xxe.xml")
        # Must fail safe (None), never return a tree with /etc/passwd's
        # contents resolved into it.
        assert root is None

    def test_billion_laughs_is_rejected(self, tmp_path):
        p = tmp_path / "lolz.xml"
        p.write_text(_BILLION_LAUGHS_XML, encoding="utf-8")
        root = xml_loader.load_xml_tree(str(p), label="lolz.xml")
        assert root is None


class TestInstanceContextUsesDefusedXml:
    def test_module_imports_defusedxml_not_stdlib(self):
        from backend.tools import instance_context
        assert instance_context.ET.__name__.startswith("defusedxml")

    def test_normal_instance_document_still_parses(self, tmp_path, monkeypatch):
        from backend.tools import instance_context
        instance_context._CACHE.clear()
        p = tmp_path / "instance.xml"
        p.write_text(
            '<?xml version="1.0"?>'
            '<xbrl xmlns="http://www.xbrl.org/2003/instance">'
            '<context id="c1"></context>'
            "</xbrl>",
            encoding="utf-8",
        )
        result = instance_context._load(str(p))
        assert result is not None

    def test_xxe_instance_document_fails_safe(self, tmp_path):
        from backend.tools import instance_context
        instance_context._CACHE.clear()
        p = tmp_path / "xxe_instance.xml"
        p.write_text(_XXE_ENTITY_XML, encoding="utf-8")
        result = instance_context._load(str(p))
        assert result is None


class TestXbrlComparatorXmlFallbackUsesDefusedXml:
    def test_malformed_instance_raises_not_silently_resolves(self, tmp_path):
        from backend.tools import xbrl_comparator
        p = tmp_path / "bad_instance.xml"
        p.write_text(_MALFORMED_XML, encoding="utf-8")
        import defusedxml.ElementTree as DET
        raised = False
        try:
            xbrl_comparator._load_via_xml(str(p))
        except DET.ParseError:
            raised = True
        assert raised

    def test_xxe_instance_is_rejected(self, tmp_path):
        from backend.tools import xbrl_comparator
        from defusedxml.common import DefusedXmlException
        p = tmp_path / "xxe_instance.xml"
        p.write_text(_XXE_ENTITY_XML, encoding="utf-8")
        raised = False
        try:
            xbrl_comparator._load_via_xml(str(p))
        except DefusedXmlException:
            raised = True
        assert raised


class TestReportLookupErrorXmlUsesDefusedXml:
    def test_normal_error_xml_still_extracts_messages(self, tmp_path):
        from backend.tools import report_lookup
        p = tmp_path / "errors.xml"
        p.write_text(
            '<?xml version="1.0"?><Errors>'
            "<ErrorMessage>Something went wrong</ErrorMessage>"
            "</Errors>",
            encoding="utf-8",
        )
        result = report_lookup._extract_error_summary_from_xml(str(p))
        assert "Something went wrong" in result["messages"]

    def test_xxe_error_xml_falls_back_gracefully(self, tmp_path):
        from backend.tools import report_lookup
        p = tmp_path / "xxe_errors.xml"
        p.write_text(_XXE_ENTITY_XML, encoding="utf-8")
        result = report_lookup._extract_error_summary_from_xml(str(p))
        # Must fail safe to the fallback message, never raise out to the caller.
        assert result == {"messages": ["Detailed error information could not be extracted."]}
