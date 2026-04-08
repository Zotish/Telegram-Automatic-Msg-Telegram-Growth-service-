import asyncio
import pdfplumber
import docx
from bs4 import BeautifulSoup
import httpx
import io
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=2)

def _extract_pdf_sync(file_content: bytes) -> str:
    """Synchronous PDF extraction — runs in thread pool to avoid blocking event loop."""

    # Step 1: pdfplumber — text-based PDF
    try:
        text = ""
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for page in pdf.pages:
                content = page.extract_text()
                if content:
                    text += content + "\n"
        if text.strip():
            return text.strip()
    except Exception:
        pass

    # Step 2: pymupdf — better text extraction fallback
    try:
        import fitz
        text = ""
        doc = fitz.open(stream=file_content, filetype="pdf")
        for page in doc:
            text += page.get_text()
        if text.strip():
            return text.strip()
    except Exception:
        pass

    # Image-based PDF — return special marker
    return "IMAGE_PDF"

async def extract_text_from_pdf(file_content: bytes) -> str:
    """Run PDF extraction in thread pool — keeps async event loop free."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, _extract_pdf_sync, file_content)

def _extract_docx_sync(file_content: bytes) -> str:
    doc = docx.Document(io.BytesIO(file_content))
    return "\n".join([p.text for p in doc.paragraphs]).strip()

async def extract_text_from_docx(file_content: bytes) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, _extract_docx_sync, file_content)

async def extract_text_from_url(url: str, verify_ssl: bool = True) -> str:
    async with httpx.AsyncClient(verify=verify_ssl, timeout=30) as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()

    text = soup.get_text(separator="\n")
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    return "\n".join(chunk for chunk in chunks if chunk)
