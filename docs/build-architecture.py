"""Render docs/architecture.png — a simple block diagram of the system.

Uses only Pillow (already a reportlab dep). Run:

    python docs/build-architecture.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT_PNG = ROOT / "architecture.png"

W, H = 1400, 900
BG = (250, 250, 252)
TXT = (30, 30, 35)
ACCENT = (31, 58, 104)
ACCENT2 = (58, 95, 168)
GREY = (160, 160, 170)
WHITE = (255, 255, 255)


def _font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "DejaVuSans.ttf",
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _box(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    label: str,
    sub: str = "",
    fill=(255, 255, 255),
    border=ACCENT,
    font_size: int = 18,
    sub_size: int = 12,
) -> tuple[int, int]:
    draw.rounded_rectangle((x, y, x + w, y + h), radius=12, fill=fill, outline=border, width=2)
    f = _font(font_size)
    bbox = draw.textbbox((0, 0), label, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((x + (w - tw) // 2, y + 14), label, fill=ACCENT, font=f)
    if sub:
        sf = _font(sub_size)
        bbox2 = draw.textbbox((0, 0), sub, font=sf)
        sw = bbox2[2] - bbox2[0]
        draw.text((x + (w - sw) // 2, y + 14 + th + 6), sub, fill=TXT, font=sf)
    return x + w // 2, y + h // 2


def _arrow(draw: ImageDraw.ImageDraw, p1, p2, label: str = "", color=GREY) -> None:
    x1, y1 = p1
    x2, y2 = p2
    draw.line((x1, y1, x2, y2), fill=color, width=2)

    import math

    angle = math.atan2(y2 - y1, x2 - x1)
    size = 9
    a1 = (x2 - size * math.cos(angle - math.pi / 7), y2 - size * math.sin(angle - math.pi / 7))
    a2 = (x2 - size * math.cos(angle + math.pi / 7), y2 - size * math.sin(angle + math.pi / 7))
    draw.polygon([(x2, y2), a1, a2], fill=color)

    if label:
        f = _font(11)
        mx, my = (x1 + x2) // 2, (y1 + y2) // 2
        bb = draw.textbbox((0, 0), label, font=f)
        tw = bb[2] - bb[0]
        draw.rectangle(
            (mx - tw // 2 - 4, my - 9, mx + tw // 2 + 4, my + 9), fill=WHITE, outline=None
        )
        draw.text((mx - tw // 2, my - 7), label, fill=TXT, font=f)


def render() -> Path:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # Title
    title_font = _font(28)
    d.text((40, 30), "PDF Merger API — Architecture", fill=ACCENT, font=title_font)
    sub_font = _font(14)
    d.text(
        (40, 70),
        "FastAPI · PostgreSQL · LocalStack S3 · Kubernetes · Prometheus/Grafana · OpenTelemetry",
        fill=GREY,
        font=sub_font,
    )

    # Client
    c_x, c_y = _box(
        d, 60, 160, 220, 90, "Client", "Postman / curl / Playwright", fill=(245, 246, 250)
    )

    # Kubernetes cluster box (dashed border)
    d.rounded_rectangle((340, 130, 1340, 800), radius=14, outline=ACCENT2, width=2)
    d.text((360, 142), "Kubernetes cluster (Minikube)", fill=ACCENT2, font=_font(14))

    # FastAPI service (deployment)
    api_cx, api_cy = _box(
        d,
        380,
        200,
        280,
        120,
        "FastAPI service",
        "Deployment · 2 replicas\nuvicorn, /api/v1/*",
        fill=WHITE,
    )

    # Routers expanded
    rb_y = 360
    _box(
        d,
        380,
        rb_y,
        130,
        60,
        "/files",
        "upload + list",
        fill=(240, 244, 252),
        font_size=13,
        sub_size=10,
    )
    _box(
        d,
        530,
        rb_y,
        130,
        60,
        "/merge",
        "job + status",
        fill=(240, 244, 252),
        font_size=13,
        sub_size=10,
    )
    _box(
        d,
        380,
        rb_y + 80,
        130,
        60,
        "/health",
        "DB + S3 probe",
        fill=(240, 244, 252),
        font_size=13,
        sub_size=10,
    )
    _box(
        d,
        530,
        rb_y + 80,
        130,
        60,
        "/metrics",
        "Prometheus",
        fill=(240, 244, 252),
        font_size=13,
        sub_size=10,
    )

    # PostgreSQL
    pg_cx, pg_cy = _box(
        d, 720, 200, 240, 120, "PostgreSQL", "pdf_files\nmerge_jobs", fill=(245, 240, 232)
    )

    # LocalStack S3
    s3_cx, s3_cy = _box(
        d,
        1020,
        200,
        280,
        120,
        "LocalStack S3",
        "bucket: pdf-merger\nuploads/* · merged/*",
        fill=(232, 245, 240),
    )

    # Prometheus
    pm_cx, pm_cy = _box(
        d, 720, 380, 240, 90, "Prometheus", "scrapes /metrics every 10s", fill=(248, 240, 245)
    )

    # Grafana
    gf_cx, gf_cy = _box(
        d,
        1020,
        380,
        280,
        90,
        "Grafana",
        "5 panels · auto-provisioned dashboard",
        fill=(248, 240, 245),
    )

    # Jaeger
    jg_cx, jg_cy = _box(
        d,
        720,
        510,
        580,
        80,
        "Jaeger (OTel)",
        "Distributed tracing: HTTP → DB → S3 spans",
        fill=(240, 245, 250),
    )

    # KEDA
    keda_cx, keda_cy = _box(
        d,
        720,
        620,
        580,
        80,
        "KEDA ScaledObject",
        "Scales FastAPI pods 1→5 based on Prometheus rate",
        fill=(252, 248, 230),
    )

    # Arrows: client → API
    _arrow(d, (c_x + 110, c_y), (380, api_cy), "HTTPS")

    # API → Postgres
    _arrow(d, (660, 240), (720, 240), "SQL")
    # API → S3
    _arrow(d, (660, 280), (1020, 260), "boto3 + presigned")
    # Prometheus ← API /metrics
    _arrow(d, (api_cx, 320), (pm_cx, 380), "scrape")
    # Grafana ← Prometheus
    _arrow(d, (960, pm_cy), (1020, pm_cy), "query")
    # OTel → Jaeger
    _arrow(d, (api_cx, 320), (jg_cx - 200, 510), "OTLP gRPC")
    # KEDA reads Prometheus
    _arrow(d, (pm_cx, 470), (keda_cx - 200, 620), "metric query")
    # KEDA scales API
    _arrow(d, (keda_cx - 250, 620), (api_cx, 320), "scale ↕")

    # Footer / legend
    f_small = _font(11)
    d.text(
        (40, 830),
        "Source: docs/build-architecture.py · See docs/final-report.pdf for details",
        fill=GREY,
        font=f_small,
    )

    img.save(OUT_PNG, format="PNG", optimize=True)
    return OUT_PNG


if __name__ == "__main__":
    out = render()
    print(f"Wrote {out} ({out.stat().st_size} bytes)")
