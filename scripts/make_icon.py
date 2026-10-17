"""assets/jarvis.png: arayüzdeki küreyle aynı yumuşak renkli simge (numpy ile, ek paket yok)."""
import struct
import sys
import zlib

import numpy as np

N = 1024
y, x = np.mgrid[0:N, 0:N] / N
img = np.zeros((N, N, 4))
# yuvarlatılmış kare zemin (macOS simge biçimi)
m, r = 0.1, 0.18
qx, qy = np.clip(np.abs(x - .5) - (.5 - m - r), 0, None), np.clip(np.abs(y - .5) - (.5 - m - r), 0, None)
inside = np.clip((r - np.hypot(qx, qy)) * N / 2, 0, 1)
bg = np.array([0.11, 0.11, 0.12])
img[..., :3] = bg * (1 - 0.35 * y[..., None])
for cx, cy, s, col in [(.42, .42, .17, (.39, .82, 1)), (.58, .46, .17, (.37, .36, .9)),
                       (.48, .6, .16, (.75, .35, .95)), (.58, .58, .12, (1, .22, .37))]:
    g = np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * s * s))[..., None] * 0.9
    img[..., :3] = img[..., :3] * (1 - g) + np.array(col) * g
core = np.exp(-((x - .46) ** 2 + (y - .45) ** 2) / (2 * .06 ** 2))[..., None] * .55
img[..., :3] = img[..., :3] * (1 - core) + core
img[..., 3] = inside
px = (np.clip(img, 0, 1) * 255).astype(np.uint8)
raw = b"".join(b"\0" + row.tobytes() for row in px)
chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)  # noqa: E731
png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", N, N, 8, 6, 0, 0, 0)) + \
      chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
open(sys.argv[1], "wb").write(png)
