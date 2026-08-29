# A project by Brian Munger

from PIL import Image

RESET = "\033[0m"


def print_image(path, width=35):
    img = None
    try: 
        img = Image.open(path).convert("RGBA")
    except: 
        return

    print()

    # Crop fully transparent padding around the logo
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    # Maintain aspect ratio
    aspect_ratio = img.height / img.width
    height = max(2, int(width * aspect_ratio))

    # Need an even number of vertical pixels
    if height % 2:
        height += 1

    img = img.resize((width, height))

    for y in range(0, img.height, 2):
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

        print(RESET)

    print(RESET)