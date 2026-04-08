
import asyncio
from context_processor import extract_text_from_pdf, extract_text_from_docx, extract_text_from_url
import os

async def test_extraction():
    # Test URL extraction (using a simple static site if possible, or just a known one)
    print("Testing URL extraction...")
    try:
        url_text = await extract_text_from_url("https://example.com", verify_ssl=False)
        print(f"URL Extract Length: {len(url_text)}")
        print(f"Preview: {url_text[:100]}...")
    except Exception as e:
        print(f"URL Extract Failed: {e}")

    # Test PDF extraction if a dummy file exists
    if os.path.exists("data.pdf"):
        print("\nTesting PDF extraction...")
        with open("data.pdf", "rb") as f:
            pdf_text = await extract_text_from_pdf(f.read())
            print(f"PDF Extract Length: {len(pdf_text)}")
            
    # Test TXT extraction manually is simple, so we skip it here.

if __name__ == "__main__":
    asyncio.run(test_extraction())
走
