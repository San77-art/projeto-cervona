"""
Tests para o parser de NFe
"""

import pytest

from src.sefaz.mock import MockSEFAZClient
from src.sefaz.parser import parse_nfe_items

NAMESPACED_MULTI_ITEM_XML = """<?xml version="1.0"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
  <NFe>
    <infNFe Id="NFe1">
      <det nItem="1">
        <prod><NCM>84713012</NCM><CFOP>5405</CFOP></prod>
        <imposto><ICMS><ICMSSN101><CSOSN>101</CSOSN></ICMSSN101></ICMS></imposto>
      </det>
      <det nItem="2">
        <prod><NCM>22030000</NCM><CFOP>6102</CFOP></prod>
        <imposto><ICMS><ICMS60><CST>60</CST></ICMS60></ICMS></imposto>
      </det>
    </infNFe>
  </NFe>
</nfeProc>"""


def test_parse_nfe_items_from_mock_xml():
    xml = MockSEFAZClient.mock_nfe()["xml"]

    items = parse_nfe_items(xml)

    assert items == [{"ncm": "12345678", "cfop": "5102", "cst": "00"}]


def test_parse_nfe_items_handles_namespace_and_csosn():
    items = parse_nfe_items(NAMESPACED_MULTI_ITEM_XML)

    assert items == [
        {"ncm": "84713012", "cfop": "5405", "cst": "101"},
        {"ncm": "22030000", "cfop": "6102", "cst": "60"},
    ]


def test_parse_nfe_items_returns_empty_list_when_no_det():
    xml = '<NFe xmlns="http://www.portalfiscal.inf.br/nfe"><infNFe Id="NFe1"></infNFe></NFe>'

    assert parse_nfe_items(xml) == []


def test_parse_nfe_items_raises_on_malformed_xml():
    with pytest.raises(ValueError):
        parse_nfe_items("<not-xml")
