# xml_loader.py — Reusable, safe XML file loader for repository-sourced files.
# All callers that need to parse Returns.xml or XML_InstanceLog should use
# load_xml_tree() so error handling is consistent across the codebase.

from __future__ import annotations

# L-14: defusedxml.ElementTree is a drop-in replacement for
# xml.etree.ElementTree (same parse()/fromstring()/ParseError surface) that
# additionally rejects XXE/billion-laughs/external-entity constructs instead
# of silently resolving them -- this loader is the single most-reused XML
# entry point in the codebase (Returns.xml, XML_InstanceLog, and other
# repository-sourced files read through load_xml_tree()).
import logging
import os

import defusedxml.ElementTree as ET
from defusedxml.common import DefusedXmlException

logger = logging.getLogger(__name__)


def load_xml_tree(path: str, label: str = "") -> ET.Element | None:
    """Parse an XML file and return its root element.

    Parameters
    ----------
    path:  Absolute path to the XML file (from config.py).
    label: Human-readable name used in log/error messages (e.g. "Returns.xml").

    Returns
    -------
    The root ``ET.Element`` on success, or ``None`` if the file is missing,
    unreadable, or contains invalid XML.  Callers must treat ``None`` as
    "no data available" and return gracefully.
    """
    display = label or os.path.basename(path)

    if not path:
        logger.error("[xml_loader] %s: path is empty — check config.py", display)
        return None

    if not os.path.isfile(path):
        logger.error(
            "[xml_loader] %s not found at path: %s  "
            "(set the correct path in config.py or via the environment variable)",
            display, path,
        )
        return None

    try:
        tree = ET.parse(path)
        root = tree.getroot()
        logger.debug("[xml_loader] Loaded %s (%d top-level children)", display, len(root))
        return root
    except ET.ParseError as exc:
        logger.error("[xml_loader] XML parse error in %s: %s", display, exc)
        return None
    except DefusedXmlException as exc:
        logger.error("[xml_loader] Rejected unsafe XML construct in %s: %s", display, exc)
        return None
    except OSError as exc:
        logger.error("[xml_loader] Cannot read %s: %s", display, exc)
        return None
