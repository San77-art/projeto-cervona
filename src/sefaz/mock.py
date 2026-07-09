"""
Mock SEFAZ client para testes locais
"""

from typing import List, Dict
import random
from datetime import datetime, timedelta

class MockSEFAZClient:
    """Simula respostas da API SEFAZ para testes"""
    
    @staticmethod
    def mock_nfe() -> Dict:
        """Retorna XML de NFe mock"""
        return {
            "xml": """<?xml version="1.0"?>
<NFe>
    <infNFe Id="NFe12345678901234567890123456789012345678901234">
        <ide>
            <dEmi>2026-07-09</dEmi>
            <hEmi>14:30:00</hEmi>
        </ide>
        <emit>
            <CNPJ>12345678901234</CNPJ>
        </emit>
        <det>
            <prod>
                <NCM>12345678</NCM>
                <CFOP>5102</CFOP>
                <qCom>10.0000</qCom>
                <vUnCom>100.00</vUnCom>
            </prod>
            <imposto>
                <ICMS>
                    <ICMS00>
                        <CST>00</CST>
                    </ICMS00>
                </ICMS>
            </imposto>
        </det>
    </infNFe>
</NFe>""",
            "status": "success",
            "nsu": "12345",
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    @staticmethod
    async def query_xml(cnpj: str) -> List[Dict]:
        """Simula busca de XMLs da SEFAZ"""
        # Retorna lista mock de XMLs
        return [
            MockSEFAZClient.mock_nfe(),
            MockSEFAZClient.mock_nfe(),
        ]
    
    @staticmethod
    async def manifest(nsu: str) -> Dict:
        """Simula ciência da manifestação"""
        return {
            "status": "success",
            "nsu": nsu,
            "timestamp": datetime.utcnow().isoformat(),
        }
