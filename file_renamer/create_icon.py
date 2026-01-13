"""
Create a custom icon for File Renamer Pro
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    """Create a professional icon for the File Renamer app"""

    # Icon sizes to include (Windows standard)
    sizes = [16, 32, 48, 64, 128, 256]

    images = []

    for size in sizes:
        # Create image with transparent background
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Calculate dimensions
        padding = max(1, size // 16)

        # Background - rounded rectangle (blue gradient feel)
        # Main color: Professional blue
        bg_color = (41, 98, 168)  # #2962A8
        highlight = (66, 133, 244)  # #4285F4

        # Draw rounded rectangle background
        radius = size // 6
        draw.rounded_rectangle(
            [padding, padding, size - padding - 1, size - padding - 1],
            radius=radius,
            fill=bg_color
        )

        # Draw a subtle highlight on top portion
        highlight_height = size // 3
        draw.rounded_rectangle(
            [padding, padding, size - padding - 1, padding + highlight_height],
            radius=radius,
            fill=highlight
        )
        # Cover the bottom corners of highlight
        draw.rectangle(
            [padding, padding + radius, size - padding - 1, padding + highlight_height],
            fill=highlight
        )

        # Draw document icon (white)
        doc_color = (255, 255, 255)
        doc_left = size // 4
        doc_top = size // 5
        doc_right = size * 3 // 5
        doc_bottom = size * 4 // 5
        fold_size = size // 8

        # Document body
        doc_points = [
            (doc_left, doc_top + fold_size),  # Top left (after fold)
            (doc_right - fold_size, doc_top + fold_size),  # Before fold
            (doc_right - fold_size, doc_top),  # Fold corner top
            (doc_right, doc_top + fold_size),  # Fold corner right
            (doc_right, doc_bottom),  # Bottom right
            (doc_left, doc_bottom),  # Bottom left
        ]
        draw.polygon(doc_points, fill=doc_color)

        # Document fold (slightly darker)
        fold_color = (220, 220, 220)
        fold_points = [
            (doc_right - fold_size, doc_top + fold_size),
            (doc_right, doc_top + fold_size),
            (doc_right - fold_size, doc_top),
        ]
        draw.polygon(fold_points, fill=fold_color)

        # Draw arrow (green, pointing right) - represents renaming/moving
        arrow_color = (52, 168, 83)  # Google green
        arrow_y = size // 2 + size // 10
        arrow_left = size // 2
        arrow_right = size - padding - size // 10
        arrow_height = size // 6

        # Arrow shaft
        shaft_top = arrow_y - arrow_height // 4
        shaft_bottom = arrow_y + arrow_height // 4
        shaft_right = arrow_right - arrow_height // 2

        draw.rectangle(
            [arrow_left, shaft_top, shaft_right, shaft_bottom],
            fill=arrow_color
        )

        # Arrow head
        head_points = [
            (shaft_right, arrow_y - arrow_height // 2),  # Top
            (arrow_right, arrow_y),  # Point
            (shaft_right, arrow_y + arrow_height // 2),  # Bottom
        ]
        draw.polygon(head_points, fill=arrow_color)

        # Add subtle lines on document to represent text
        if size >= 32:
            line_color = (200, 200, 200)
            line_y_start = doc_top + fold_size + size // 10
            line_spacing = max(2, size // 16)
            line_left = doc_left + size // 16
            line_right = doc_right - size // 8

            for i in range(3):
                y = line_y_start + i * line_spacing * 2
                if y < arrow_y - arrow_height:
                    # Vary line lengths slightly
                    right = line_right - (i % 2) * size // 12
                    draw.line([(line_left, y), (right, y)], fill=line_color, width=max(1, size // 32))

        images.append(img)

    # Save as ICO file with all sizes
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(script_dir, "app_icon.ico")

    # Save with multiple sizes
    images[0].save(
        icon_path,
        format='ICO',
        sizes=[(s, s) for s in sizes],
        append_images=images[1:]
    )

    print(f"Icon created: {icon_path}")
    return icon_path


if __name__ == "__main__":
    create_icon()
