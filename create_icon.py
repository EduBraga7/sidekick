"""Cria um ícone .ico para o executável do Sidekick."""

import sys
from PIL import Image, ImageDraw
import os

# Configura encoding UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def create_icon_file(size=256, output_path="src/ui/gamepad_icon.ico"):
    """Cria arquivo .ico com o ícone do gamepad."""
    
    # Cria a imagem do ícone
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Cores
    outline_color = (0, 230, 200, 255)
    neon_color = (0, 230, 200, 255)
    fill_color = (35, 38, 48, 255)
    
    # Corpo do controle gamer
    margin_x = int(size * 0.12)
    margin_y = int(size * 0.22)
    bottom_y = int(size * 0.78)
    
    # Base do controle
    draw.rounded_rectangle(
        [margin_x, margin_y, size - margin_x, bottom_y],
        radius=int(size * 0.05),
        fill=fill_color,
        outline=outline_color,
        width=int(size * 0.02)
    )
    
    # D-Pad na esquerda
    dpad_cx = int(size * 0.32)
    dpad_cy = int(size * 0.50)
    dpad_w = int(size * 0.02)
    dpad_l = int(size * 0.08)
    draw.rectangle([dpad_cx - dpad_w, dpad_cy - dpad_l, dpad_cx + dpad_w, dpad_cy + dpad_l], fill=neon_color)
    draw.rectangle([dpad_cx - dpad_l, dpad_cy - dpad_w, dpad_cx + dpad_l, dpad_cy + dpad_w], fill=neon_color)
    
    # Botões de Ação na direita
    btn_cx = int(size * 0.68)
    btn_cy = int(size * 0.50)
    btn_r = int(size * 0.02)
    btn_offset = int(size * 0.05)
    
    # Topo (Y)
    draw.ellipse([btn_cx - btn_r, btn_cy - btn_offset - btn_r, btn_cx + btn_r, btn_cy - btn_offset + btn_r], fill=(255, 204, 0, 255))
    # Direita (B)
    draw.ellipse([btn_cx + btn_offset - btn_r, btn_cy - btn_r, btn_cx + btn_offset + btn_r, btn_cy + btn_r], fill=(255, 68, 68, 255))
    # Baixo (A)
    draw.ellipse([btn_cx - btn_r, btn_cy + btn_offset - btn_r, btn_cx + btn_r, btn_cy + btn_offset + btn_r], fill=(51, 204, 51, 255))
    # Esquerda (X)
    draw.ellipse([btn_cx - btn_offset - btn_r, btn_cy - btn_r, btn_cx - btn_offset + btn_r, btn_cy + btn_r], fill=(51, 153, 255, 255))
    
    # Cria o diretório se não existir
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Salva como .ico
    image.save(output_path, format='ICO', sizes=[(size, size)])
    print(f"Icone criado: {output_path}")


if __name__ == "__main__":
    create_icon_file()
