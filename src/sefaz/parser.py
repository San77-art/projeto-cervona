"""
Deterministic NFe XML parser
"""

import logging
from typing import Dict, List, Optional

from lxml import etree

logger = logging.getLogger(__name__)


def _local_tag(element) -> str:
    """Strip the XML namespace off an element's tag"""
    tag = element.tag
    return tag.split("}", 1)[1] if "}" in tag else tag


def _find_child(element, name: str):
    """Find a descendant by local tag name, namespace-agnostic"""
    for child in element.iter():
        if _local_tag(child) == name:
            return child
    return None


def _extract_cst(imposto_element) -> Optional[str]:
    """
    ICMS CST/CSOSN lives under whichever regime tag is present (ICMS00, ICMS10,
    ICMS60, ICMSSN101, ...), so scan for a CST or CSOSN tag instead of a fixed path.
    """
    icms = _find_child(imposto_element, "ICMS")
    if icms is None:
        return None
    for child in icms.iter():
        tag = _local_tag(child)
        if tag in ("CST", "CSOSN"):
            return child.text.strip() if child.text else None
    return None


def parse_nfe_items(xml_content: str) -> List[Dict[str, Optional[str]]]:
    """
    Parse an NFe XML document and return NCM, CFOP and CST for each line item (<det>)
    """
    try:
        root = etree.fromstring(xml_content.encode("utf-8"))
    except etree.XMLSyntaxError as e:
        logger.error(f"Failed to parse NFe XML: {e}")
        raise ValueError(f"Invalid NFe XML: {e}") from e

    items = []
    for det in root.iter():
        if _local_tag(det) != "det":
            continue

        prod = _find_child(det, "prod")
        imposto = _find_child(det, "imposto")

        ncm_el = _find_child(prod, "NCM") if prod is not None else None
        cfop_el = _find_child(prod, "CFOP") if prod is not None else None
        cst = _extract_cst(imposto) if imposto is not None else None

        items.append({
            "ncm": ncm_el.text.strip() if ncm_el is not None and ncm_el.text else None,
            "cfop": cfop_el.text.strip() if cfop_el is not None and cfop_el.text else None,
            "cst": cst,
        })

    if not items:
        logger.warning("No <det> line items found in NFe XML")

    return items
