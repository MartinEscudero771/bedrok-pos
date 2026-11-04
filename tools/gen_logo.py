"""Genera favicon.ico desde la composicion del logo (Pillow)."""
import math

from PIL import Image, ImageDraw


def gradient_square(size=256):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    grad = Image.new("RGBA", (size, size))
    px = grad.load()
    c1 = (122, 107, 255)
    c2 = (90, 79, 224)
    c3 = (31, 182, 201)
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * (size - 1))
            if t < 0.55:
                k = t / 0.55
                col = tuple(int(c1[i] + (c2[i] - c1[i]) * k) for i in range(3))
            else:
                k = (t - 0.55) / 0.45
                col = tuple(int(c2[i] + (c3[i] - c2[i]) * k) for i in range(3))
            px[x, y] = col + (255,)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([8, 8, size - 8, size - 8], radius=int(size * 0.22), fill=255)
    img.paste(grad, (0, 0), mask)
    return img


def draw_receipt(img):
    size = img.size[0]
    d = ImageDraw.Draw(img)
    s = size / 256
    x0, x1, y0 = int(76 * s), int(180 * s), int(56 * s)
    tip = y0 + int(136 * s)
    zig = int(7 * s)
    pts = []
    steps = 4
    for i in range(steps + 1):
        yy = tip + (i % 2) * 0
        pts.append((x0 + int((x1 - x0) * i / steps), tip))
        pts.append((x0 + int((x1 - x0) * (i + 0.5) / steps), tip - zig if False else tip))
    # rect sencillo con dientes abajo
    d.polygon(
        [(x0, y0), (x1, y0), (x1, tip), (x1 - int(13 * s), tip - zig), (x1 - int(26 * s), tip),
         (x1 - int(39 * s), tip - zig), (x1 - int(52 * s), tip), (x1 - int(65 * s), tip - zig),
         (x1 - int(78 * s), tip), (x1 - int(91 * s), tip - zig), (x1 - int(104 * s), tip), (x0, tip)],
        fill=(255, 255, 255, 255),
    )
    # lineas internas
    d.rounded_rectangle([24 * int(s * 24) / 24 + int(88 * s), y0 + int(26 * s),
                         x0 + int(52 * s), y0 + int(26 * s) + int(12 * s)],
                        radius=int(6 * s), fill=(90, 79, 224, 255))
    d.rounded_rectangle([x0 + int(10 * s), y0 + int(52 * s), x0 + int(66 * s), y0 + int(64 * s)],
                        radius=int(6 * s), fill=(201, 197, 255, 255))
    # mini QR
    q = int(14 * s)
    for (qx, qy, a) in [(0, 0, 255), (1, 0, 255), (0, 1, 90), (1, 1, 255)]:
        d.rounded_rectangle(
            [x0 + int(12 * s) + qx * (q + int(4 * s)), y0 + int(84 * s) + qy * (q + int(4 * s)),
             x0 + int(12 * s) + qx * (q + int(4 * s)) + q, y0 + int(84 * s) + qy * (q + int(4 * s)) + q],
            radius=int(3 * s), fill=(31, 182, 201, a))
    # check blanco-verde abajo derecha
    cx, cy, r = int(180 * s), int(180 * s), int(34 * s)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 255))
    d.line([(cx - int(14 * s), cy), (cx - int(3 * s), cy + int(11 * s))], fill=(15, 122, 85, 255), width=int(10 * s))
    d.line([(cx - int(3 * s), cy + int(11 * s)), (cx + int(16 * s), cy - int(10 * s))], fill=(15, 122, 85, 255), width=int(10 * s))
    return img


def main():
    base = gradient_square(256)
    logo = draw_receipt(base)
    # PNG de apoyo
    logo.save(r"static\img\logo-512.png")
    favicon = logo.copy()
    favicon.save("static/img/favicon.ico",
                 sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("favicon.ico + logo-512.png generados")


if __name__ == "__main__":
    main()
