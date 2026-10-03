"""
generate_icons.py — Generate PWA icons
Run: python generate_icons.py
"""
import os

os.makedirs("static/icons", exist_ok=True)

try:
    from PIL import Image, ImageDraw, ImageFont
    
    def make_icon(size):
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Background circle — dark
        draw.ellipse([0, 0, size, size], fill=(13, 13, 26, 255))
        
        # Glow ring
        ring = int(size * 0.04)
        draw.ellipse([ring, ring, size-ring, size-ring], 
                     outline=(0, 255, 170, 200), width=int(size*0.03))
        
        # Inner circle
        pad = int(size * 0.12)
        draw.ellipse([pad, pad, size-pad, size-pad], 
                     fill=(0, 20, 40, 255))
        
        # Emoji/text — robot face
        emoji_size = int(size * 0.45)
        try:
            # Try to use a font
            font = ImageFont.truetype("arial.ttf", emoji_size)
        except:
            font = ImageFont.load_default()
        
        text = "🤖"
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            draw.text(((size - tw) // 2, (size - th) // 2 - int(size*0.03)), 
                     text, font=font, fill=(0, 255, 170, 255))
        except:
            # Fallback — draw "DVT" text
            font2 = ImageFont.load_default()
            draw.text((size//2 - 20, size//2 - 10), "DVT", 
                     fill=(0, 255, 170, 255), font=font2)
        
        return img
    
    # Generate 192x192
    img192 = make_icon(192)
    img192.save("static/icons/icon-192.png", "PNG")
    print("✅ icon-192.png created")
    
    # Generate 512x512
    img512 = make_icon(512)
    img512.save("static/icons/icon-512.png", "PNG")
    print("✅ icon-512.png created")

except ImportError:
    # PIL not available — create minimal valid PNG
    import struct, zlib, base64
    
    # Minimal 1x1 green PNG as placeholder
    PNG_1x1_GREEN = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
        "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )
    
    with open("static/icons/icon-192.png", "wb") as f:
        f.write(PNG_1x1_GREEN)
    with open("static/icons/icon-512.png", "wb") as f:
        f.write(PNG_1x1_GREEN)
    print("⚠️  Placeholder icons created (install Pillow for better icons)")
    print("   pip install Pillow")

print("\n✅ Icons ready in static/icons/")
