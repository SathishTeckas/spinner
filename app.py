from flask import Flask, request, jsonify
from PIL import Image, ImageDraw
import io
from math import cos, radians, sin
import os
import json
import random
import base64

# Load emojis from JSON file
with open("emojis.json", encoding="utf-8") as f:
    emojis = json.load(f)["emojis"]

# Directory where emoji PNGs are stored
emoji_dir = "emoji_pngs"

app = Flask(__name__)

def preprocess_image(image):
    size = max(image.size)
    new_image = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    new_image.paste(image, ((size - image.width) // 2, (size - image.height) // 2))
    new_image = new_image.resize((256, 256), Image.LANCZOS)

    random_emoji = random.choice(list(emojis.keys()))
    emoji = emojis[random_emoji]["emoji"]
    emoji_path = os.path.join(emoji_dir, f"{random_emoji}.png")
    if os.path.exists(emoji_path):
        emoji_image = Image.open(emoji_path).convert("RGBA")
        emoji_image = emoji_image.resize((256, 256), Image.LANCZOS)
        new_image.paste(emoji_image, (0, 0), emoji_image)

    return new_image, random_emoji, emoji

def create_gif(image1, image2, transition_type):
    frames = []
    duration = 100
    total_frames = 18

    try:
        img1 = image1.convert('RGBA')
        img2 = image2.convert('RGBA')

        img1, random_emoji1, emoji1 = preprocess_image(img1)
        img2, random_emoji2, emoji2 = preprocess_image(img2)

        size = (256, 256)
        img1 = img1.resize(size, Image.LANCZOS)
        img2 = img2.resize(size, Image.LANCZOS)

        if transition_type == "slide":
            full_width = size[0]
            step = full_width // (total_frames // 2)

            for i in range(0, full_width, step):
                frame = Image.new('RGBA', size)
                frame.paste(img1, (0, 0))
                frame.paste(img2.crop((i, 0, full_width, size[1])), (i, 0), mask=img2.crop((i, 0, full_width, size[1])))
                draw = ImageDraw.Draw(frame)
                draw.line((i, 0, i, size[1]), fill=(0, 255, 0), width=2)
                frame = frame.convert('P', palette=Image.ADAPTIVE)
                frames.append(frame)

            for i in range(full_width, step, -step):
                frame = Image.new('RGBA', size)
                frame.paste(img1, (0, 0))
                frame.paste(img2.crop((i, 0, full_width, size[1])), (i, 0), mask=img2.crop((i, 0, full_width, size[1])))
                draw = ImageDraw.Draw(frame)
                draw.line((i, 0, i, size[1]), fill=(0, 255, 0), width=2)
                frame = frame.convert('P', palette=Image.ADAPTIVE)
                frames.append(frame)
        else:
            mask_size = (size[0] * 2, size[1] * 2)
            mask = Image.new('L', mask_size, 0)
            draw = ImageDraw.Draw(mask)
            draw.rectangle([size[0], 0, mask_size[0], mask_size[1]], fill=255)

            center_x, center_y = size[0] // 2, size[1] // 2

            for angle in range(0, 360, 360 // total_frames):
                rotated_mask = mask.rotate(angle, center=(mask_size[0] // 2, mask_size[1] // 2), expand=False)
                cropped_mask = rotated_mask.crop(
                    (size[0] // 2, size[1] // 2, size[0] // 2 + size[0], size[1] // 2 + size[1]))
                frame = Image.composite(img1, img2, cropped_mask)
                draw = ImageDraw.Draw(frame)
                reverse_angle = -angle + 90
                end_x1 = center_x + int(size[0] * 1.5 * cos(radians(reverse_angle)))
                end_y1 = center_y + int(size[1] * 1.5 * sin(radians(reverse_angle)))
                end_x2 = center_x - int(size[0] * 1.5 * cos(radians(reverse_angle)))
                end_y2 = center_y - int(size[1] * 1.5 * sin(radians(reverse_angle)))
                draw.line([center_x, center_y, end_x1, end_y1], fill=(0, 255, 0), width=3)
                draw.line([center_x, center_y, end_x2, end_y2], fill=(0, 255, 0), width=3)
                frame = frame.convert('P', palette=Image.ADAPTIVE)
                frames.append(frame)

        output = io.BytesIO()
        frames[0].save(output, format='GIF', save_all=True, append_images=frames[1:], duration=duration, loop=0, optimize=True)
        output.seek(0)

        return output, emoji1, emoji2

    except Exception as e:
        return None

@app.route("/api/generate_gif", methods=["POST"])
def generate_gif():
    data = request.get_json()
    if 'image1' not in data or 'image2' not in data:
        return jsonify({"error": "Please provide both image1 and image2 in base64 format"}), 400

    try:
        image1_data = base64.b64decode(data['image1'])
        image2_data = base64.b64decode(data['image2'])

        image1 = Image.open(io.BytesIO(image1_data))
        image2 = Image.open(io.BytesIO(image2_data))

        transition_type = data.get("transition_type", "slide")

        output, emoji1, emoji2 = create_gif(image1, image2, transition_type)

        if output:
            base64_gif = base64.b64encode(output.getvalue()).decode('utf-8')
            return jsonify({"gif": base64_gif, "emoji1": emoji1, "emoji2": emoji2})

        return jsonify({"error": "Failed to create GIF"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route("/", methods=["GET"])
def hello_world():
    return "Hello, World!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
