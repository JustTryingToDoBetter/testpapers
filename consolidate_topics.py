import os
import cv2
import numpy as np
import pytesseract
import re
from PIL import Image
from pdf2image import convert_from_path

# --- CONFIGURATION ---
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Point this to your folder full of question papers
INPUT_DIR = r'C:\Users\umorrja\projects\testpapers\Question Papers' 
OUTPUT_DIR = r'C:\Users\umorrja\projects\testpapers\categorized_output'

TOPIC_KEYWORDS = {
    "Finance": ["interest", "loan", "vat", "tax", "budget", "salary", "tariff"],
    "Measurement": ["area", "volume", "perimeter", "distance", "cm", "litres", "capacity"],
    "Maps_and_Plans": ["scale", "map", "elevation", "layout", "floor plan", "compass"],
    "Data_Handling": ["mean", "median", "mode", "graph", "chart", "probability", "statistics"]
}

def deskew(image_cv):
    """Deskews an OpenCV image."""
    gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    coords = np.column_stack(np.where(gray > 0))
    angle = cv2.minAreaRect(coords)[-1]
    
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    (h, w) = image_cv.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image_cv, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated

def extract_topic(text):
    """Determines the topic of the page based on keyword frequency."""
    text = text.lower()
    topic_scores = {topic: 0 for topic in TOPIC_KEYWORDS}
    
    for topic, keywords in TOPIC_KEYWORDS.items():
        for keyword in keywords:
            topic_scores[topic] += len(re.findall(rf'\b{keyword}\b', text))
            
    best_topic = max(topic_scores, key=topic_scores.get)
    
    if topic_scores[best_topic] == 0:
        return "General_or_Unknown"
    
    return best_topic

def setup_directories():
    """Creates the necessary output folders for temporary images."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    topics = list(TOPIC_KEYWORDS.keys()) + ["General_or_Unknown"]
    for topic in topics:
        topic_path = os.path.join(OUTPUT_DIR, topic)
        if not os.path.exists(topic_path):
            os.makedirs(topic_path)
    return topics

def compile_pdfs(topics):
    """Combines the saved images in each topic folder into a single PDF."""
    print("\n--- Compiling Final PDFs ---")
    for topic in topics:
        topic_dir = os.path.join(OUTPUT_DIR, topic)
        image_files = [f for f in os.listdir(topic_dir) if f.endswith('.png')]
        
        if not image_files:
            continue # Skip if no images were found for this topic
            
        print(f"Compiling {len(image_files)} pages for {topic}...")
        
        # Load all images for this topic
        images = []
        for img_file in image_files:
            img_path = os.path.join(topic_dir, img_file)
            images.append(Image.open(img_path).convert('RGB'))
            
        # Save as a single PDF
        output_pdf_path = os.path.join(OUTPUT_DIR, f"COMPILED_{topic}_Questions.pdf")
        images[0].save(output_pdf_path, save_all=True, append_images=images[1:])
        print(f"Saved -> {output_pdf_path}")

def main():
    topics = setup_directories()
    
    # Get all PDF files in the input directory
    pdf_files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.pdf')]
    print(f"Found {len(pdf_files)} PDF files to process.\n")

    for pdf_filename in pdf_files:
        pdf_path = os.path.join(INPUT_DIR, pdf_filename)
        print(f"--- Processing: {pdf_filename} ---")
        
        try:
            pages = convert_from_path(pdf_path)
        except Exception as e:
            print(f"Error reading {pdf_filename}: {e}. Skipping.")
            continue
            
        for i, page in enumerate(pages):
            # 1. Convert to OpenCV
            open_cv_image = np.array(page) 
            open_cv_image = open_cv_image[:, :, ::-1].copy()
            
            # 2. Deskew
            processed_cv_image = deskew(open_cv_image)
            processed_pil_image = Image.fromarray(cv2.cvtColor(processed_cv_image, cv2.COLOR_BGR2RGB))
            
            # 3. Extract Text & Topic
            page_text = pytesseract.image_to_string(processed_pil_image)
            topic = extract_topic(page_text)
            
            # 4. Save to temporary topic folder immediately to save RAM
            # Using the original filename + page number to keep things organized
            clean_name = pdf_filename.replace('.pdf', '')
            save_name = f"{clean_name}_Page_{i+1}.png"
            save_path = os.path.join(OUTPUT_DIR, topic, save_name)
            
            processed_pil_image.save(save_path)
            print(f"  Page {i + 1} -> {topic}")

    # 5. Compile the saved images into final PDFs
    compile_pdfs(topics)
    print("\nBatch Processing Complete!")

if __name__ == "__main__":
    main()