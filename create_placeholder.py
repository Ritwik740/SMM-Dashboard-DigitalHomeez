from PIL import Image, ImageDraw, ImageFont
import os

def create_placeholder():
    # Create a 300x300 image with a light gray background
    width = 300
    height = 300
    image = Image.new('RGB', (width, height), '#f0f0f0')
    draw = ImageDraw.Draw(image)
    
    # Draw a border
    draw.rectangle([(0, 0), (width-1, height-1)], outline='#cccccc', width=2)
    
    # Add text
    text = "Loading..."
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    # Center the text
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    # Draw the text
    draw.text((x, y), text, fill='#666666', font=font)
    
    # Create the images directory if it doesn't exist
    os.makedirs('static/images', exist_ok=True)
    
    # Save the image
    image.save('static/images/placeholder.png')

if __name__ == '__main__':
    create_placeholder() 