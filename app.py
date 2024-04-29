from flask import Flask, request, jsonify, send_from_directory
import pytesseract
from pdf2image import convert_from_path
from PIL import Image, ImageDraw, ImageFont
import json
import os
from io import BytesIO
import base64
import openai
from dotenv import load_dotenv
import platform

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
# Initialize Flask app
app = Flask(__name__)
client = openai.OpenAI(api_key=api_key)

# System prompt for the OpenAI API call
system_prompt = """
             You are looking at an images of a troubleshooting guide and corresponging images with approximate paragraph coordinates. 
             This guide is organized in a table with the headings 'Problem', 'Cause', and 'Solution' or in a similar manner. 
             Your task is to extract the text from each cell of the table and structure it in a clear and organized manner into a JSON format.

             For each 'Problem' listed in the guide, create an object that contains the problem description, an array of possible causes, and an array of solutions. 
             For problems with multiple causes or solutions, each cause and solution should be a separate string in their respective arrays.
             For each problem provide approximate bounding box location and page.

            Here is an example of how you should format the information:

            {
              "TroubleShooting": [
                {
                  "Problem": "Example Problem 1",
                  "ProblemBoundingBox": [x1,y1, width1, height1]
                  "ProblemPage": int
                  "Causes": [
                    "Example Cause 1a",
                    "Example Cause 1b"
                  ],
                  "Solutions": [
                    "Example Solution 1a",
                    "Example Solution 1b"
                  ]
                },
                {
                  "Problem": "Example Problem 2",
                  "ProblemBoundingBox": [x2,y2, width2, height2]
                  "ProblemPage": int
                  "Causes": [
                    "Example Cause 2a"
                  ],
                  "Solutions": [
                    "Example Solution 2a"
                  ]
                }
                // ... Add additional problems with their causes and solutions here
              ]
            }
            Please ensure that you transcribe the text exactly as it appears, including any specific instructions or details. 
            If a cell contains a list, represent each item as a separate string within the appropriate array. 
            If any part of the text is not legible, please mark it as '[illegible]'."
            """



# Configure Tesseract executable path based on operating system
if platform.system() == 'Linux':
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
elif platform.system() == 'Darwin': 
     pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'
else:
    raise EnvironmentError("Unsupported platform. Tesseract configuration needs to be set for either Linux or macOS.")

def encode_image_to_base64(image):
    """Converts an image to a base64 string."""
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def process_and_annotate_image(image):
    """Annotate image with OCR text and bounding boxes."""
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    draw = ImageDraw.Draw(image)
    font_path = "./files/Arial.ttf"
    font = ImageFont.truetype(font_path, 24)  # Ensure the font is available
    colors = ['red', 'green', 'blue', 'yellow', 'purple', 'orange', 'white']
    
    for i in range(len(data['text'])):
        if data['level'][i] == 4:  # Level 4 corresponds to 'block'
            x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
            color = colors[i % len(colors)]
            draw.rectangle([x, y, x + w, y + h], outline=color, width=2)
            coords_text = f"{x}, {y}, {w}, {h}"
            text_x = x + 5 if x + w + 5 < image.width else x - 5
            text_y = y + 5 if y + h + 5 < image.height else y - 5
            draw.text((text_x, text_y), coords_text, fill=color, font=font)
    return image

@app.route('/process-pdf', methods=['POST'])
def process_pdf():
    file = request.files['file']
    pages_request = request.form.get('pages', default=None)
    if not pages_request:
        return jsonify({"error": "No pages specified"}), 400

    pages = []
    if pages_request:
        ranges = pages_request.split(',')
        for range_ in ranges:
            if '-' in range_:
                start, end = map(int, range_.split('-'))
                pages.extend(range(start, end + 1))
            else:
                pages.append(int(range_))

    temp_path = "temp_file.pdf"
    file.save(temp_path)

    # Convert specified pages to images, defaulting to all pages if none are specified
    if pages:
        images = convert_from_path(temp_path, dpi=300, first_page=min(pages), last_page=max(pages))
    else:
        images = convert_from_path(temp_path, dpi=300)

    vision_list = []
    for page_number, image in enumerate(images):
        base64_image = encode_image_to_base64(image)
        vision_list.append( {
                "type": "image_url",
                "image_url": {
                    "url":f"data:image/jpeg;base64,{base64_image}"}})
        
        image_annotated = process_and_annotate_image(image.copy())
        base64_image_annotated = encode_image_to_base64(image_annotated)
        vision_list.append( {
                "type": "image_url",
                "image_url": {
                    "url":f"data:image/jpeg;base64,{base64_image_annotated}"}} )
    messages = [{"role": "system", "content": system_prompt},
            {"role": "user",  "content":vision_list }]

    response = client.chat.completions.create(
        model="gpt-4-turbo-2024-04-09",
        response_format={"type": "json_object"},
        messages=messages,
        max_tokens=2000  # Increase max_tokens if necessary
    )

    # Send request to OpenAI
    response_json = json.loads(response.choices[0].message.content)
    return response_json

if __name__ == '__main__':
    app.run(debug=True)
