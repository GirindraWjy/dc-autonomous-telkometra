from PIL import Image, ImageDraw, ImageFont


def render_terminal(
    title,
    host,
    output,
    output_path,
    width=1365,
):
    try:
        font = ImageFont.truetype(
            "C:/Windows/Fonts/consola.ttf",
            16,
        )
    except OSError:
        font = ImageFont.load_default()

    try:
        small_font = ImageFont.truetype(
            "C:/Windows/Fonts/consola.ttf",
            13,
        )
    except OSError:
        small_font = font

    lines = output.splitlines()

    if not lines:
        lines = ["(no output)"]

    header_height = 48
    footer_height = 42
    padding_x = 24
    padding_top = 18
    line_height = 22

    content_height = (
        max(len(lines), 1) * line_height
    )

    height = (
        header_height
        + padding_top
        + 30
        + content_height
        + 20
        + footer_height
    )

    image = Image.new(
        "RGB",
        (width, height),
        "#0d1117",
    )

    draw = ImageDraw.Draw(image)

    # ========================================================
    # HEADER
    # ========================================================

    draw.rectangle(
        (0, 0, width, header_height),
        fill="#161b22",
    )

    # Traffic lights
    draw.ellipse(
        (18, 17, 30, 29),
        fill="#ff5f57",
    )

    draw.ellipse(
        (38, 17, 50, 29),
        fill="#febc2e",
    )

    draw.ellipse(
        (58, 17, 70, 29),
        fill="#28c840",
    )

    draw.text(
        (90, 14),
        f"{title}  |  {host}",
        fill="#e6edf3",
        font=font,
    )

    # ========================================================
    # OUTPUT
    # ========================================================

    y = header_height + padding_top

    for line in lines:

        draw.text(
            (padding_x, y),
            line,
            fill="#e6edf3",
            font=small_font,
        )

        y += line_height

    # ========================================================
    # FOOTER
    # ========================================================

    footer_y = height - footer_height

    draw.rectangle(
        (0, footer_y, width, height),
        fill="#161b22",
    )

    draw.text(
        (20, footer_y + 13),
        "SERVER STATUS",
        fill="#22c55e",
        font=font,
    )

    draw.text(
        (180, footer_y + 14),
        "SSH command execution completed",
        fill="#d1d5db",
        font=small_font,
    )

    # ========================================================
    # SAVE
    # ========================================================

    image.save(
        output_path
    )