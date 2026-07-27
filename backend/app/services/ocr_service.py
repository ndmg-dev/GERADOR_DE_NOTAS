import logging
import shutil

from app.core.config import settings

logger = logging.getLogger(__name__)


class OcrService:
    """Fallback de extração de texto via OCR (pytesseract + pdf2image)."""

    LANGS = "por+eng"
    DPI = 300

    def __init__(self, tesseract_cmd: str | None = None) -> None:
        self.tesseract_cmd = tesseract_cmd or settings.tesseract_cmd

    def is_available(self) -> bool:
        try:
            import pytesseract  # noqa: F401
            from pdf2image import convert_from_path  # noqa: F401
        except ImportError:
            return False
        return bool(shutil.which(self.tesseract_cmd) or shutil.which("tesseract"))

    def extract_text(self, pdf_path: str) -> str:
        """Rasteriza o PDF e aplica OCR página a página."""
        import pytesseract
        from pdf2image import convert_from_path

        if shutil.which(self.tesseract_cmd):
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

        logger.info("Executando OCR em %s (dpi=%d)", pdf_path, self.DPI)
        paginas = convert_from_path(pdf_path, dpi=self.DPI)

        partes: list[str] = []
        for numero, imagem in enumerate(paginas, start=1):
            texto = pytesseract.image_to_string(imagem, lang=self.LANGS)
            partes.append(texto)
            logger.debug("OCR página %d: %d caracteres", numero, len(texto))

        return "\n".join(partes)
