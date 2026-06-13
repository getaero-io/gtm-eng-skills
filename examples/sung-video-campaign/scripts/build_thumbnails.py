#!/usr/bin/env python3
from pathlib import Path
import os
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
VIDEOS = ROOT / "videos"
OUT = ROOT / "thumbnails"

DEEPLINE_API_ROOT = Path(
    os.environ.get("DEEPLINE_API_ROOT", "/Users/jaitoor/dev/deepline-api")
)
FONT_DIR = DEEPLINE_API_ROOT / "src/app/fonts"
BRAND_DIR = DEEPLINE_API_ROOT / "public/brand"

FONT_DISPLAY = FONT_DIR / "geist-800.ttf"
FONT_TEXT = FONT_DIR / "geist-500.ttf"
FONT_MONO = FONT_DIR / "geist-mono-500.ttf"
LOGO_DARK = BRAND_DIR / "logo_full_dark.png"
DITHER_VERTICAL = BRAND_DIR / "dither_vertical.png"

PALETTE = {
    "paper": (250, 250, 248),
    "paper_2": (242, 238, 228),
    "bg_0": (252, 252, 253),
    "plum": (28, 17, 42),
    "plum_2": (42, 27, 61),
    "indigo": (25, 25, 255),
    "indigo_soft": (165, 180, 252),
    "cyan_soft": (103, 232, 249),
    "border": (215, 215, 226),
    "muted": (86, 81, 93),
}

SPECS = [
    {
        "video": "waterfall-complexity-polished.mp4",
        "out": "waterfall-complexity.png",
        "time": "00:01:10",
        "eyebrow": "waterfall enrichment",
        "headline": ["Apollo is not", "the workflow"],
        "terminal": "$ deepline enrich waterfall --providers apollo,prospeo,leadmagic",
    },
    {
        "video": "provider-sprawl-polished.mp4",
        "out": "provider-sprawl.png",
        "time": "00:02:30",
        "eyebrow": "provider sprawl",
        "headline": ["Stop being", "the CSV sherpa"],
        "terminal": "$ deepline build tam --inspect-provider-coverage",
    },
    {
        "video": "speedrun-time-to-integration-polished.mp4",
        "out": "speedrun-time-to-integration.png",
        "time": "00:00:55",
        "eyebrow": "time to integration",
        "headline": ["MCP is access,", "not guardrails"],
        "terminal": "$ deepline connect snowflake crm campaign --preview",
    },
    {
        "video": "pipeline-as-code-screenstudio.mp4",
        "out": "pipeline-as-code.png",
        "time": "00:01:22",
        "eyebrow": "account mapping",
        "headline": ["Pipeline as code", "for GTM"],
        "terminal": "$ deepline run account-mapping.play.ts",
    },
]


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    if path.exists():
        return ImageFont.truetype(str(path), size)
    fallback = "/System/Library/Fonts/Supplemental/Arial.ttf"
    return ImageFont.truetype(fallback, size)


def run_ffmpeg(video: Path, at: str, frame: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            at,
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-vf",
            "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720",
            str(frame),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def text_size(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.FreeTypeFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=face)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def fit_font(lines: list[str], max_width: int, starting_size: int) -> ImageFont.FreeTypeFont:
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    size = starting_size
    while size > 34:
        face = font(FONT_DISPLAY, size)
        if all(text_size(probe, line, face)[0] <= max_width for line in lines):
            return face
        size -= 2
    return font(FONT_DISPLAY, size)


def fit_single_line(text: str, font_path: Path, max_width: int, starting_size: int) -> ImageFont.FreeTypeFont:
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    size = starting_size
    while size > 14:
        face = font(font_path, size)
        if text_size(probe, text, face)[0] <= max_width:
            return face
        size -= 1
    return font(font_path, size)


def paste_rounded(base: Image.Image, image: Image.Image, xy: tuple[int, int], radius: int) -> None:
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, image.width, image.height), radius=radius, fill=255)
    base.paste(image, xy, mask)


def add_grid(canvas: Image.Image) -> None:
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    grid = (*PALETTE["plum"], 13)
    for x in range(0, 1280, 32):
        draw.line((x, 0, x, 720), fill=grid, width=1)
    for y in range(0, 720, 32):
        draw.line((0, y, 1280, y), fill=grid, width=1)
    canvas.alpha_composite(overlay)


def add_dither(canvas: Image.Image) -> None:
    if not DITHER_VERTICAL.exists():
        return
    dither = Image.open(DITHER_VERTICAL).convert("RGBA")
    dither = dither.resize((542, 720))
    dither.putalpha(34)
    canvas.alpha_composite(dither, (738, 0))


def add_logo(canvas: Image.Image) -> None:
    if LOGO_DARK.exists():
        logo = Image.open(LOGO_DARK).convert("RGBA")
        width = 186
        height = round(logo.height * (width / logo.width))
        logo = logo.resize((width, height), Image.Resampling.LANCZOS)
        canvas.alpha_composite(logo, (72, 56))
        return

    draw = ImageDraw.Draw(canvas)
    draw.text((72, 56), "Deepline", font=font(FONT_DISPLAY, 34), fill=PALETTE["plum"])


def add_terminal(draw: ImageDraw.ImageDraw, spec: dict) -> None:
    x, y, w, h = 72, 548, 594, 92
    draw.rounded_rectangle((x, y, x + w, y + h), radius=14, fill=PALETTE["plum"])
    draw.rectangle((x, y, x + w, y + 28), fill=PALETTE["plum_2"])
    for i, color in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        draw.ellipse((x + 18 + i * 18, y + 10, x + 27 + i * 18, y + 19), fill=color)
    draw.text(
        (x + 22, y + 48),
        spec["terminal"],
        font=fit_single_line(spec["terminal"], FONT_MONO, 536, 23),
        fill=(252, 252, 253),
    )


def add_frame(canvas: Image.Image, source_frame: Path) -> None:
    frame = Image.open(source_frame).convert("RGB")
    frame = frame.resize((576, 324), Image.Resampling.LANCZOS)

    card_x, card_y = 684, 126
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        (card_x - 18, card_y - 18, card_x + 594, card_y + 342),
        radius=28,
        fill=PALETTE["bg_0"],
        outline=PALETTE["border"],
        width=2,
    )
    paste_rounded(canvas, frame.convert("RGBA"), (card_x, card_y), 18)
    draw.rounded_rectangle(
        (card_x, card_y, card_x + 576, card_y + 324),
        radius=18,
        outline=(*PALETTE["plum"], 70),
        width=2,
    )


def build(spec: dict) -> None:
    video = VIDEOS / spec["video"]
    output = OUT / spec["out"]
    OUT.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        frame = Path(tmp) / "frame.png"
        run_ffmpeg(video, spec["time"], frame)

        canvas = Image.new("RGBA", (1280, 720), PALETTE["paper"])
        draw = ImageDraw.Draw(canvas)
        add_grid(canvas)
        add_dither(canvas)

        draw.rectangle((0, 0, 14, 720), fill=PALETTE["indigo"])
        draw.rounded_rectangle((56, 36, 1218, 666), radius=30, outline=PALETTE["border"], width=2)

        add_logo(canvas)
        add_frame(canvas, frame)

        eyebrow_font = font(FONT_MONO, 24)
        headline_font = fit_font(spec["headline"], 578, 78)
        body_font = font(FONT_TEXT, 28)

        draw.line((72, 154, 104, 154), fill=PALETTE["indigo"], width=2)
        draw.text((118, 139), spec["eyebrow"], font=eyebrow_font, fill=PALETTE["indigo"])

        y = 206
        for line in spec["headline"]:
            draw.text((72, y), line, font=headline_font, fill=PALETTE["plum"])
            _, line_height = text_size(draw, line, headline_font)
            y += line_height + 16

        draw.text(
            (72, 472),
            "Inspectable GTM systems. Rerunnable workflows.",
            font=body_font,
            fill=PALETTE["muted"],
        )
        add_terminal(draw, spec)

        draw.text((1020, 610), "deepline.com", font=font(FONT_MONO, 24), fill=PALETTE["plum"])

        canvas.convert("RGB").save(output, "PNG", optimize=True)
        print(output)


def main() -> None:
    for spec in SPECS:
        build(spec)


if __name__ == "__main__":
    main()
