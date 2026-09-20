"""Módulo de captura de tela de alta velocidade e baixa largura de banda."""

import base64
import io
from typing import Optional
from PIL import Image, ImageGrab


def capture_screen_base64(max_width: int = 768, quality: int = 60) -> Optional[str]:
    """Captura a tela atual, redimensiona para otimizar velocidade/tokens e retorna em base64 JPEG."""
    img = None

    # Método 1: PIL ImageGrab com all_screens (pega jogos em tela cheia sem bordas e monitores múltiplos)
    try:
        img = ImageGrab.grab(all_screens=True)
    except Exception:
        pass

    # Método 2: PIL ImageGrab padrão
    if img is None:
        try:
            img = ImageGrab.grab()
        except Exception:
            pass

    # Método 3: mss (fallback de alta performance)
    if img is None:
        try:
            import mss
            with mss.MSS() as sct:
                # Captura monitor principal
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        except Exception:
            pass

    if img is None:
        return None

    try:
        # Redimensionar para reduzir latência e uso de memória
        width, height = img.size
        if width > max_width:
            new_height = int(height * (max_width / width))
            img = img.resize((max_width, new_height), Image.Resampling.BILINEAR)

        # Converter para JPEG comprimido em buffer de memória
        buffer = io.BytesIO()
        img.convert("RGB").save(buffer, format="JPEG", quality=quality, optimize=True)
        buffer.seek(0)

        b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{b64_str}"
    except Exception as e:
        print(f"[ScreenCapture Error]: {e}")
        return None
