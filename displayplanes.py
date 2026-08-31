# A project by Brian Munger

from PIL import Image

RESET = "\033[0m"
WHITE_TEXT = "\033[37m"


def print_image(path, text="", height=45, width=None):
    img = None
    print()
    try: 
        img = Image.open(path).convert("RGBA")
    except: 
        img = Image.open("logos/default.png").convert("RGBA")

    # Crop fully transparent padding around the logo
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    # Keep logos the same height while preserving each logo's aspect ratio.
    height = max(2, int(height))

    # Need an even number of vertical pixels
    if height % 2:
        height += 1

    if width is None:
        aspect_ratio = img.width / img.height
        width = max(1, round(height * aspect_ratio))

    # Reset image sizing
    img = img.resize((width, height))

    # Calculate rows number
    rows = range(0, img.height, 2)
    text_lines = text.splitlines()
    text_start_row = max(0, (len(rows) - len(text_lines)) // 2)
    
    for row_number, y in enumerate(rows):
        for x in range(img.width):
            top = img.getpixel((x, y))
            bottom = img.getpixel((x, y + 1))

            top_visible = top[3] > 128
            bottom_visible = bottom[3] > 128

            # Both transparent: print nothing
            if not top_visible and not bottom_visible:
                print(RESET + " ", end="")

            # Both visible: use foreground + background
            elif top_visible and bottom_visible:
                print(
                    f"\033[38;2;{top[0]};{top[1]};{top[2]}m"
                    f"\033[48;2;{bottom[0]};{bottom[1]};{bottom[2]}m"
                    "▀",
                    end=""
                )

            # Only top visible
            elif top_visible:
                print(
                    RESET +
                    f"\033[38;2;{top[0]};{top[1]};{top[2]}m"
                    "▀",
                    end=""
                )

            # Only bottom visible
            else:
                print(
                    RESET +
                    f"\033[38;2;{bottom[0]};{bottom[1]};{bottom[2]}m"
                    "▄",
                    end=""
                )

        if text_start_row <= row_number < text_start_row + len(text_lines):
            print(
                f"{RESET}{WHITE_TEXT}  {text_lines[row_number - text_start_row]}{RESET}",
                end=""
            )

        print(RESET)

    print(RESET)
