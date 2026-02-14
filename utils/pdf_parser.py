def extract_text_from_pdf(path: str, max_pages: int = 30) -> str:
    text = ""
    pdf = fitz.open(path)
    for i, page in enumerate(pdf):
        if i >= max_pages:
            break
        text += page.get_text("text") + "\n"
    pdf.close()
    return text