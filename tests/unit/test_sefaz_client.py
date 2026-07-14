"""
Tests para o cliente real de Distribuição de DFe (src.sefaz.client)

Nenhum teste aqui bate na SEFAZ de verdade — usam certificados autoassinados
gerados na hora e um httpx.MockTransport para simular o web service.
"""

import base64
import datetime
import gzip

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from src.config.settings import settings
from src.sefaz.client import (
    DistDFeResult,
    SEFAZClient,
    SEFAZClientError,
    SEFAZDocument,
    _build_envelope,
    _load_client_certificate,
    _parse_response,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_pfx(path, password=None):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Cernova Test Cert")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    encryption = (
        serialization.BestAvailableEncryption(password) if password else serialization.NoEncryption()
    )
    pfx_bytes = pkcs12.serialize_key_and_certificates(
        name=b"cernova-test", key=key, cert=cert, cas=None, encryption_algorithm=encryption
    )
    path.write_bytes(pfx_bytes)
    return path


def _soap_response(cstat, xmotivo, ult_nsu="15", max_nsu="15", docs=()):
    entries = "".join(
        f'<docZip NSU="{nsu}" schema="{schema}">'
        f"{base64.b64encode(gzip.compress(xml.encode())).decode()}</docZip>"
        for nsu, schema, xml in docs
    )
    lote_xml = f"<loteDistDFeInt>{entries}</loteDistDFeInt>" if docs else ""
    body = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">'
        "<soap:Body>"
        '<nfeDistDFeInteresseResponse xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe">'
        "<nfeDistDFeInteresseResult>"
        '<retDistDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.35">'
        "<tpAmb>2</tpAmb><verAplic>TEST</verAplic>"
        f"<cStat>{cstat}</cStat><xMotivo>{xmotivo}</xMotivo>"
        "<dhResp>2026-07-14T10:00:00-03:00</dhResp>"
        f"<ultNSU>{ult_nsu.zfill(15)}</ultNSU><maxNSU>{max_nsu.zfill(15)}</maxNSU>"
        f"{lote_xml}"
        "</retDistDFeInt>"
        "</nfeDistDFeInteresseResult>"
        "</nfeDistDFeInteresseResponse>"
        "</soap:Body>"
        "</soap:Envelope>"
    ).encode("utf-8")
    return body


@pytest.fixture
def valid_sefaz_settings(monkeypatch):
    monkeypatch.setattr(settings, "SEFAZ_CNPJ", "12345678000199")
    monkeypatch.setattr(settings, "SEFAZ_UF_CODE", "35")
    monkeypatch.setattr(settings, "SEFAZ_ENVIRONMENT", "homologacao")
    monkeypatch.setattr(settings, "SEFAZ_RETRY_MAX", 3)
    monkeypatch.setattr(settings, "SEFAZ_RETRY_BACKOFF", 0.01)


def _mock_client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


# ---------------------------------------------------------------------------
# Certificate loading
# ---------------------------------------------------------------------------

def test_load_client_certificate_round_trips_pem(tmp_path):
    pfx_path = _make_pfx(tmp_path / "cert.pfx")

    cert_pem, key_pem = _load_client_certificate(str(pfx_path), None)

    assert cert_pem.startswith(b"-----BEGIN CERTIFICATE-----")
    assert key_pem.startswith(b"-----BEGIN RSA PRIVATE KEY-----") or key_pem.startswith(
        b"-----BEGIN PRIVATE KEY-----"
    )


def test_load_client_certificate_with_password(tmp_path):
    pfx_path = _make_pfx(tmp_path / "cert.pfx", password=b"s3nha")

    cert_pem, key_pem = _load_client_certificate(str(pfx_path), "s3nha")

    assert cert_pem.startswith(b"-----BEGIN CERTIFICATE-----")


def test_load_client_certificate_wrong_password_raises(tmp_path):
    pfx_path = _make_pfx(tmp_path / "cert.pfx", password=b"s3nha")

    with pytest.raises(SEFAZClientError):
        _load_client_certificate(str(pfx_path), "wrong")


def test_load_client_certificate_missing_file_raises(tmp_path):
    with pytest.raises(SEFAZClientError):
        _load_client_certificate(str(tmp_path / "does-not-exist.pfx"), None)


# ---------------------------------------------------------------------------
# Envelope building
# ---------------------------------------------------------------------------

def test_build_envelope_contains_expected_fields():
    envelope = _build_envelope(cnpj="12345678000199", uf_code="35", tp_amb="2", ult_nsu="42")

    assert "<CNPJ>12345678000199</CNPJ>" in envelope
    assert "<cUFAutor>35</cUFAutor>" in envelope
    assert "<tpAmb>2</tpAmb>" in envelope
    assert "<ultNSU>000000000000042</ultNSU>" in envelope


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def test_parse_response_no_new_documents():
    body = _soap_response("137", "Nenhum documento localizado", ult_nsu="15", max_nsu="15")

    result = _parse_response(body)

    assert result.status_code == "137"
    assert result.documents == []
    assert result.caught_up is True


def test_parse_response_decodes_docs():
    body = _soap_response(
        "138",
        "Documento(s) localizado(s)",
        ult_nsu="17",
        max_nsu="20",
        docs=[
            ("16", "resNFe_v1.01.xsd", "<resNFe><chNFe>123</chNFe></resNFe>"),
            ("17", "procNFe_v1.01.xsd", "<nfeProc><NFe><infNFe/></NFe></nfeProc>"),
        ],
    )

    result = _parse_response(body)

    assert result.status_code == "138"
    assert result.ult_nsu == "000000000000017"
    assert result.max_nsu == "000000000000020"
    assert result.caught_up is False
    assert len(result.documents) == 2

    res_doc, proc_doc = result.documents
    assert res_doc.nsu == "16"
    assert res_doc.is_full_document is False
    assert "<chNFe>123</chNFe>" in res_doc.xml

    assert proc_doc.nsu == "17"
    assert proc_doc.is_full_document is True
    assert "<infNFe/>" in proc_doc.xml


def test_parse_response_raises_on_error_status():
    body = _soap_response("656", "Rejeicao: Consumo Indevido")

    with pytest.raises(SEFAZClientError, match="656"):
        _parse_response(body)


def test_parse_response_raises_on_malformed_xml():
    with pytest.raises(SEFAZClientError):
        _parse_response(b"<not-xml")


def test_parse_response_raises_when_ret_dist_dfe_int_missing():
    body = b'<?xml version="1.0"?><soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"><soap:Body><soap:Fault><faultstring>boom</faultstring></soap:Fault></soap:Body></soap:Envelope>'

    with pytest.raises(SEFAZClientError):
        _parse_response(body)


# ---------------------------------------------------------------------------
# SEFAZClient construction / validation
# ---------------------------------------------------------------------------

def test_client_requires_cnpj(monkeypatch):
    monkeypatch.setattr(settings, "SEFAZ_CNPJ", None)
    with pytest.raises(SEFAZClientError, match="SEFAZ_CNPJ"):
        SEFAZClient(http_client=_mock_client(lambda r: httpx.Response(200)))


def test_client_rejects_invalid_cnpj(monkeypatch):
    monkeypatch.setattr(settings, "SEFAZ_CNPJ", "123")
    monkeypatch.setattr(settings, "SEFAZ_UF_CODE", "35")
    with pytest.raises(SEFAZClientError, match="14 dígitos"):
        SEFAZClient(http_client=_mock_client(lambda r: httpx.Response(200)))


def test_client_requires_uf_code(monkeypatch):
    monkeypatch.setattr(settings, "SEFAZ_CNPJ", "12345678000199")
    monkeypatch.setattr(settings, "SEFAZ_UF_CODE", None)
    with pytest.raises(SEFAZClientError, match="SEFAZ_UF_CODE"):
        SEFAZClient(http_client=_mock_client(lambda r: httpx.Response(200)))


def test_client_rejects_invalid_environment(monkeypatch, valid_sefaz_settings):
    monkeypatch.setattr(settings, "SEFAZ_ENVIRONMENT", "producao-mas-errado")
    with pytest.raises(SEFAZClientError, match="SEFAZ_ENVIRONMENT"):
        SEFAZClient(http_client=_mock_client(lambda r: httpx.Response(200)))


def test_client_without_injected_http_requires_certificate_path(monkeypatch, valid_sefaz_settings):
    monkeypatch.setattr(settings, "SEFAZ_CERTIFICATE_PATH", None)
    with pytest.raises(SEFAZClientError, match="SEFAZ_CERTIFICATE_PATH"):
        SEFAZClient()


def test_client_loads_real_certificate_when_no_http_client_injected(monkeypatch, valid_sefaz_settings, tmp_path):
    pfx_path = _make_pfx(tmp_path / "cert.pfx")
    monkeypatch.setattr(settings, "SEFAZ_CERTIFICATE_PATH", str(pfx_path))

    client = SEFAZClient()
    try:
        assert client._cert_file is not None
        assert client._owns_http_client is True
    finally:
        import asyncio
        asyncio.run(client.close())


# ---------------------------------------------------------------------------
# consultar_nsu over a mocked transport
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_consultar_nsu_success(valid_sefaz_settings):
    captured = {}

    def handler(request):
        captured["body"] = request.content.decode("utf-8")
        captured["headers"] = request.headers
        return httpx.Response(
            200,
            content=_soap_response("138", "OK", ult_nsu="5", max_nsu="5", docs=[("5", "procNFe_v1.01.xsd", "<nfeProc/>")]),
        )

    client = SEFAZClient(http_client=_mock_client(handler))
    result = await client.consultar_nsu("0")

    assert isinstance(result, DistDFeResult)
    assert result.caught_up is True
    assert len(result.documents) == 1
    assert isinstance(result.documents[0], SEFAZDocument)

    assert "<CNPJ>12345678000199</CNPJ>" in captured["body"]
    assert "<tpAmb>2</tpAmb>" in captured["body"]  # homologacao
    assert "action=" in captured["headers"]["content-type"]


@pytest.mark.asyncio
async def test_consultar_nsu_zero_pads_and_strips_nsu(valid_sefaz_settings):
    captured = {}

    def handler(request):
        captured["body"] = request.content.decode("utf-8")
        return httpx.Response(200, content=_soap_response("137", "OK"))

    client = SEFAZClient(http_client=_mock_client(handler))
    await client.consultar_nsu("nsu=000000123 ")

    assert "<ultNSU>000000000000123</ultNSU>" in captured["body"]


@pytest.mark.asyncio
async def test_consultar_nsu_retries_on_5xx_then_succeeds(valid_sefaz_settings):
    calls = {"count": 0}

    def handler(request):
        calls["count"] += 1
        if calls["count"] < 3:
            return httpx.Response(500, content=b"server error")
        return httpx.Response(200, content=_soap_response("137", "OK"))

    client = SEFAZClient(http_client=_mock_client(handler))
    result = await client.consultar_nsu("0")

    assert calls["count"] == 3
    assert result.status_code == "137"


@pytest.mark.asyncio
async def test_consultar_nsu_exhausts_retries_and_raises(valid_sefaz_settings):
    calls = {"count": 0}

    def handler(request):
        calls["count"] += 1
        return httpx.Response(500, content=b"server error")

    client = SEFAZClient(http_client=_mock_client(handler))

    with pytest.raises(SEFAZClientError, match="indisponível"):
        await client.consultar_nsu("0")

    assert calls["count"] == settings.SEFAZ_RETRY_MAX


@pytest.mark.asyncio
async def test_consultar_nsu_does_not_retry_on_4xx(valid_sefaz_settings):
    calls = {"count": 0}

    def handler(request):
        calls["count"] += 1
        return httpx.Response(400, content=b"bad request")

    client = SEFAZClient(http_client=_mock_client(handler))

    with pytest.raises(SEFAZClientError, match="400"):
        await client.consultar_nsu("0")

    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_consultar_nsu_retries_on_network_timeout(valid_sefaz_settings):
    calls = {"count": 0}

    def handler(request):
        calls["count"] += 1
        raise httpx.ConnectTimeout("timed out", request=request)

    client = SEFAZClient(http_client=_mock_client(handler))

    with pytest.raises(SEFAZClientError, match="rede"):
        await client.consultar_nsu("0")

    assert calls["count"] == settings.SEFAZ_RETRY_MAX
