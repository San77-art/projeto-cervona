"""
Cliente real do web service de Distribuição de DF-e (DistDFe) da SEFAZ

Consulta o Ambiente Nacional (AN) por documentos fiscais disponibilizados a um
CNPJ, paginando por NSU (Número Sequencial Único). Autenticação é só TLS mútuo
com certificado A1 (ICP-Brasil) — não existe usuário/senha para este serviço.

IMPORTANTE — verifique antes de usar em produção:
As URLs de endpoint, o namespace WSDL e a versão do schema `distDFeInt` abaixo
refletem o "Manual de Integração do Contribuinte — Distribuição de DFe"
(SEFAZ/ENCAT) vigente no momento em que este cliente foi escrito. São valores
mantidos pelo governo e podem mudar entre revisões do manual. `SEFAZ_DISTDFE_URL`
em settings.py permite sobrescrever a URL sem alterar código caso o endpoint
abaixo esteja desatualizado. Este módulo não foi testado contra o ambiente real
da SEFAZ (exige certificado A1 válido) — só contra respostas SOAP sintéticas
(ver tests/unit/test_sefaz_client.py). Valide em homologação antes de produção.
"""

import base64
import gzip
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import httpx
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    pkcs12,
)
from lxml import etree
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.config.settings import settings

logger = logging.getLogger(__name__)

_SOAP_NS = "http://www.w3.org/2003/05/soap-envelope"
_WSDL_NS = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe"
_DFE_NS = "http://www.portalfiscal.inf.br/nfe"
_DIST_DFE_INT_VERSAO = "1.35"
_SOAP_ACTION = f"{_WSDL_NS}/nfeDistDFeInteresse"

# A Distribuição de DFe é centralizada no Ambiente Nacional — diferente dos
# demais web services de NFe (autorização, etc.), que são por UF/SVAN.
_DEFAULT_URLS = {
    "producao": "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx",
    "homologacao": "https://hom.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx",
}

_TP_AMB = {"producao": "1", "homologacao": "2"}

# cStat que indicam consulta bem-sucedida (137 = nenhum documento novo, 138 = há documentos)
_SUCCESS_STATUS_CODES = {"137", "138"}


class SEFAZClientError(Exception):
    """Erro ao consultar o web service de Distribuição de DFe da SEFAZ"""


class _RetryableHTTPError(Exception):
    """Interno: sinaliza falha 5xx do lado da SEFAZ, elegível para retry"""


@dataclass
class SEFAZDocument:
    """Um documento da Distribuição de DFe, já descompactado (gzip+base64 decodificados)"""

    nsu: str
    schema: str
    xml: str

    @property
    def is_full_document(self) -> bool:
        """
        True para procNFe/procNFCe/procEventoNFe — XML completo, pronto para
        src.sefaz.parser.parse_nfe_items (que já lida com o wrapper <nfeProc>).
        False para resNFe/resEvento: são resumos/notificações, sem itens, e não
        devem ser tratados como uma NFe processável.
        """
        return self.schema.startswith("proc")


@dataclass
class DistDFeResult:
    """Resultado de uma consulta de distribuição por NSU"""

    documents: List[SEFAZDocument]
    ult_nsu: str
    max_nsu: str
    status_code: str
    status_reason: str

    @property
    def caught_up(self) -> bool:
        """True quando não há mais documentos a paginar (ultNSU alcançou maxNSU)"""
        return int(self.ult_nsu) >= int(self.max_nsu)


def _environment() -> str:
    env = (settings.SEFAZ_ENVIRONMENT or "homologacao").lower()
    if env not in _TP_AMB:
        raise SEFAZClientError(
            f"SEFAZ_ENVIRONMENT inválido: {env!r} (use 'producao' ou 'homologacao')"
        )
    return env


def _load_client_certificate(pfx_path: str, pfx_password: Optional[str]) -> Tuple[bytes, bytes]:
    """
    Carrega um certificado A1 (.pfx/.p12) e devolve (cert_pem, key_pem) para uso
    como certificado de cliente TLS mútuo.
    """
    try:
        pfx_data = Path(pfx_path).read_bytes()
    except OSError as e:
        raise SEFAZClientError(f"Não foi possível ler o certificado em {pfx_path}: {e}") from e

    password = pfx_password.encode("utf-8") if pfx_password else None
    try:
        private_key, certificate, _ = pkcs12.load_key_and_certificates(pfx_data, password)
    except ValueError as e:
        raise SEFAZClientError(f"Certificado ou senha inválidos em {pfx_path}: {e}") from e

    if private_key is None or certificate is None:
        raise SEFAZClientError(f"{pfx_path} não contém um par certificado+chave privada válido")

    key_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
    cert_pem = certificate.public_bytes(Encoding.PEM)
    return cert_pem, key_pem


def _build_envelope(cnpj: str, uf_code: str, tp_amb: str, ult_nsu: str) -> str:
    """Monta o envelope SOAP 1.2 do pedido distDFeInt, modo distNSU (paginação por cursor)"""
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        f'<soap12:Envelope xmlns:soap12="{_SOAP_NS}">'
        "<soap12:Body>"
        f'<nfeDistDFeInteresse xmlns="{_WSDL_NS}">'
        "<nfeDadosMsg>"
        f'<distDFeInt xmlns="{_DFE_NS}" versao="{_DIST_DFE_INT_VERSAO}">'
        f"<tpAmb>{tp_amb}</tpAmb>"
        f"<cUFAutor>{uf_code}</cUFAutor>"
        f"<CNPJ>{cnpj}</CNPJ>"
        f"<distNSU><ultNSU>{ult_nsu.zfill(15)}</ultNSU></distNSU>"
        "</distDFeInt>"
        "</nfeDadosMsg>"
        "</nfeDistDFeInteresse>"
        "</soap12:Body>"
        "</soap12:Envelope>"
    )


def _local_tag(element) -> str:
    tag = element.tag
    return tag.split("}", 1)[1] if "}" in tag else tag


def _find_first(element, name: str):
    if element is None:
        return None
    for child in element.iter():
        if _local_tag(child) == name:
            return child
    return None


def _text(element) -> str:
    if element is None or element.text is None:
        return ""
    return element.text.strip()


def _parse_response(soap_xml: bytes) -> DistDFeResult:
    """Interpreta a resposta SOAP de nfeDistDFeInteresse, descompactando docZip"""
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    try:
        root = etree.fromstring(soap_xml, parser=parser)
    except etree.XMLSyntaxError as e:
        raise SEFAZClientError(f"Resposta SOAP inválida: {e}") from e

    ret = _find_first(root, "retDistDFeInt")
    if ret is None:
        raise SEFAZClientError(
            "Resposta não contém retDistDFeInt — verifique um possível SOAP Fault"
        )

    status_code = _text(_find_first(ret, "cStat"))
    status_reason = _text(_find_first(ret, "xMotivo"))

    if status_code not in _SUCCESS_STATUS_CODES:
        raise SEFAZClientError(f"SEFAZ retornou cStat={status_code}: {status_reason}")

    ult_nsu = _text(_find_first(ret, "ultNSU")) or "0"
    max_nsu = _text(_find_first(ret, "maxNSU")) or ult_nsu

    documents: List[SEFAZDocument] = []
    lote = _find_first(ret, "loteDistDFeInt")
    if lote is not None:
        for doc_zip in lote:
            if _local_tag(doc_zip) != "docZip":
                continue
            nsu = doc_zip.get("NSU", "")
            schema = doc_zip.get("schema", "")
            try:
                xml_bytes = gzip.decompress(base64.b64decode(doc_zip.text or ""))
            except (OSError, ValueError, gzip.BadGzipFile) as e:
                raise SEFAZClientError(f"Falha ao descompactar docZip NSU={nsu}: {e}") from e
            documents.append(SEFAZDocument(nsu=nsu, schema=schema, xml=xml_bytes.decode("utf-8")))

    return DistDFeResult(
        documents=documents,
        ult_nsu=ult_nsu,
        max_nsu=max_nsu,
        status_code=status_code,
        status_reason=status_reason,
    )


class SEFAZClient:
    """
    Cliente do web service de Distribuição de DF-e (Ambiente Nacional).

    Uso normal (carrega o certificado configurado em settings):

        async with SEFAZClient() as client:
            result = await client.consultar_nsu(ult_nsu="0")
            for doc in result.documents:
                if doc.is_full_document:
                    items = parse_nfe_items(doc.xml)

    Para testes, injete um httpx.AsyncClient próprio (ex.: com MockTransport) via
    `http_client=` — nesse caso o certificado configurado em settings não é lido.
    """

    def __init__(self, http_client: Optional[httpx.AsyncClient] = None):
        if not settings.SEFAZ_CNPJ:
            raise SEFAZClientError("SEFAZ_CNPJ não configurado")
        cnpj = "".join(filter(str.isdigit, settings.SEFAZ_CNPJ))
        if len(cnpj) != 14:
            raise SEFAZClientError(f"SEFAZ_CNPJ deve ter 14 dígitos: {settings.SEFAZ_CNPJ!r}")
        self._cnpj = cnpj

        if not settings.SEFAZ_UF_CODE or not settings.SEFAZ_UF_CODE.isdigit() or len(settings.SEFAZ_UF_CODE) != 2:
            raise SEFAZClientError(
                f"SEFAZ_UF_CODE deve ser o código IBGE de 2 dígitos da UF (ex.: '35' para SP), "
                f"recebido: {settings.SEFAZ_UF_CODE!r}"
            )
        self._uf_code = settings.SEFAZ_UF_CODE

        self._environment = _environment()
        self._tp_amb = _TP_AMB[self._environment]
        self._base_url = settings.SEFAZ_DISTDFE_URL or _DEFAULT_URLS[self._environment]
        self._max_attempts = max(1, settings.SEFAZ_RETRY_MAX)
        self._backoff = max(0.1, float(settings.SEFAZ_RETRY_BACKOFF))

        self._cert_file = None
        self._key_file = None

        if http_client is not None:
            self._http = http_client
            self._owns_http_client = False
        else:
            if not settings.SEFAZ_CERTIFICATE_PATH:
                raise SEFAZClientError("SEFAZ_CERTIFICATE_PATH não configurado")
            cert_pem, key_pem = _load_client_certificate(
                settings.SEFAZ_CERTIFICATE_PATH, settings.SEFAZ_CERTIFICATE_PASSWORD
            )
            self._cert_file = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
            self._key_file = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
            self._cert_file.write(cert_pem)
            self._key_file.write(key_pem)
            self._cert_file.flush()
            self._key_file.flush()
            self._http = httpx.AsyncClient(
                cert=(self._cert_file.name, self._key_file.name),
                timeout=settings.SEFAZ_TIMEOUT,
            )
            self._owns_http_client = True

    async def __aenter__(self) -> "SEFAZClient":
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self.close()

    async def close(self) -> None:
        if self._owns_http_client:
            await self._http.aclose()
        for f in (self._cert_file, self._key_file):
            if f is not None:
                f.close()
                Path(f.name).unlink(missing_ok=True)

    async def consultar_nsu(self, ult_nsu: str = "0") -> DistDFeResult:
        """
        Consulta documentos disponíveis a partir de um NSU (cursor de paginação).
        Chame novamente com `result.ult_nsu` até `result.caught_up` ser True.
        """
        digits_nsu = "".join(filter(str.isdigit, ult_nsu)) or "0"
        envelope = _build_envelope(self._cnpj, self._uf_code, self._tp_amb, digits_nsu)
        response_body = await self._post_with_retry(envelope)
        return _parse_response(response_body)

    async def _post_with_retry(self, envelope: str) -> bytes:
        headers = {
            "Content-Type": f'application/soap+xml; charset=utf-8; action="{_SOAP_ACTION}"',
        }
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self._max_attempts),
                wait=wait_exponential(multiplier=self._backoff),
                retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException, _RetryableHTTPError)),
                reraise=True,
            ):
                with attempt:
                    logger.info(
                        f"Consultando DistDFe ({self._environment}) para CNPJ {self._cnpj[:8]}********"
                    )
                    response = await self._http.post(
                        self._base_url, content=envelope.encode("utf-8"), headers=headers
                    )
                    if response.status_code >= 500:
                        raise _RetryableHTTPError(f"HTTP {response.status_code}")
                    if response.status_code >= 400:
                        raise SEFAZClientError(
                            f"HTTP {response.status_code} do web service SEFAZ: {response.text[:500]}"
                        )
                    return response.content
        except _RetryableHTTPError as e:
            raise SEFAZClientError(
                f"SEFAZ indisponível após {self._max_attempts} tentativa(s): {e}"
            ) from e
        except (httpx.TransportError, httpx.TimeoutException) as e:
            raise SEFAZClientError(
                f"Falha de rede ao consultar SEFAZ após {self._max_attempts} tentativa(s): {e}"
            ) from e

        raise SEFAZClientError("Falha ao consultar SEFAZ: nenhuma tentativa executada")  # pragma: no cover
