import logging
import os
import re
import shutil
from typing import Optional

logger = logging.getLogger(__name__)


class OCREngine:
    def __init__(self, library: str = "pytesseract", lang: str = "eng"):
        self.library = library
        self.lang = lang
        self._engine: Optional[str] = None
        self._easyocr_reader = None
        self._initialize()

    def _initialize(self):
        if self.library == "pytesseract":
            self._init_pytesseract()
        elif self.library == "easyocr":
            self._init_easyocr()
        else:
            raise ValueError(f"Unknown OCR library: {self.library}")

    def _init_pytesseract(self):
        try:
            import pytesseract

            pytesseract.pytesseract.tesseract_cmd = self._find_tesseract()
            self._engine = "pytesseract"
            logger.info("[OCR] pytesseract initialized successfully.")
        except ImportError:
            raise ImportError(
                "pytesseract not installed. Run: pip install pytesseract\n"
                "Also ensure Tesseract OCR is installed on your system:\n"
                "  Windows: choco install tesseract -y\n"
                "  macOS:   brew install tesseract\n"
                "  Linux:   sudo apt install tesseract-ocr"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize pytesseract: {e}")

    def _init_easyocr(self):
        try:
            import easyocr

            self._easyocr_reader = easyocr.Reader([self.lang], verbose=False)
            self._engine = "easyocr"
            logger.info("[OCR] EasyOCR initialized successfully.")
        except ImportError:
            raise ImportError("easyocr not installed. Run: pip install easyocr")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize EasyOCR: {e}")

    def _find_tesseract(self) -> str:
        tesseract = shutil.which("tesseract")
        if tesseract:
            return tesseract

        paths = []
        if os.name == "nt":
            pf = os.environ.get("ProgramFiles", "C:\\Program Files")
            pfx86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
            paths.extend(
                [
                    os.path.join(pf, "Tesseract-OCR", "tesseract.exe"),
                    os.path.join(pfx86, "Tesseract-OCR", "tesseract.exe"),
                ]
            )
        elif os.name == "darwin":
            paths.extend(["/usr/local/bin/tesseract", "/opt/homebrew/bin/tesseract"])

        for path in paths:
            if os.path.isfile(path):
                return path
        return "tesseract"

    def extract_text(self, image_path: str) -> Optional[str]:
        try:
            from PIL import Image

            img = Image.open(image_path)

            if self._engine == "pytesseract":
                import pytesseract

                text = pytesseract.image_to_string(img, lang=self.lang)
                text = self._clean_text(text)
                if text.strip():
                    logger.info(f"[OCR] Extracted {len(text)} chars.")
                    return text
                return None

            elif self._engine == "easyocr":
                results = self._easyocr_reader.readtext(image_path)
                if not results:
                    return None
                lines = []
                for bbox, text, confidence in results:
                    if confidence > 0.3 and text.strip():
                        lines.append(text.strip())
                full_text = " ".join(lines)
                if full_text.strip():
                    logger.info(f"[OCR] Extracted {len(full_text)} chars.")
                    return full_text
                return None

        except ImportError as e:
            logger.error(f"[OCR] Missing dependency: {e}")
        except Exception as e:
            logger.error(f"[OCR] Extraction failed: {e}")
        return None

    def _clean_text(self, text: str) -> str:
        lines = text.split("\n")
        cleaned = []
        for line in lines:
            line = line.strip()
            if line:
                line = re.sub(r"[ \t]+", " ", line)
                cleaned.append(line)
        return " ".join(cleaned)


class OCRProcessor:
    def __init__(self, config: dict):
        ocr_config = config.get("ocr", {})
        self.enabled: bool = ocr_config.get("enabled", False)
        self.library: str = ocr_config.get("library", "pytesseract")
        self.lang: str = ocr_config.get("lang", "eng+ind")
        self._engine: Optional[OCREngine] = None

        if self.enabled:
            try:
                self._engine = OCREngine(library=self.library, lang=self.lang)
                logger.info(f"[OCR] OCR Processor ready ({self.library}).")
            except Exception as e:
                logger.warning(f"[OCR] Failed to initialize: {e}")
                self.enabled = False

    def is_available(self) -> bool:
        return self.enabled and self._engine is not None

    def scan(self, image_path: str) -> Optional[str]:
        if not self.is_available():
            return None
        text = self._engine.extract_text(image_path) if self._engine else None
        if not text:
            logger.info("[OCR] No text extracted from this frame.")
        return text
