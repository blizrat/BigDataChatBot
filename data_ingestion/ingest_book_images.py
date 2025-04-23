from globals import id_count
import fitz  # PyMuPDF
import re
from bson import Binary

class IngestBookImages:
    def __init__(self, db):
        self.db = db
        self.collection = db['images_test']

    def extract_figures_to_mongodb(self, pdf_path):
        doc = fitz.open(pdf_path)
        figure_count = 0

        for page_num, page in enumerate(doc):
            image_list = page.get_images(full=True)
            blocks = page.get_text("dict")["blocks"]

            print(f"\n📄 Page {page_num + 1} - Found {len(image_list)} images.")

            for img_index, img_info in enumerate(image_list):
                xref = img_info[0]

                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    ext = base_image["ext"]
                except Exception as e:
                    print(f"⚠️ Could not extract image xref {xref}: {e}")
                    continue

                # Locate image block (first image block on the page for now)
                image_block = None
                for block in blocks:
                    if block.get("type") == 1:
                        image_block = fitz.Rect(block["bbox"])
                        break

                if image_block is None:
                    print("❌ No matching image block found for xref", xref)
                    continue

                # Define wider caption area below the image block (full width)
                caption_area = fitz.Rect(
                    0,  # from left edge of the page
                    image_block.y1,
                    page.rect.width,  # to right edge of the page
                    image_block.y1 + 80  # search vertically down
                )

                caption_text = ""
                for block in blocks:
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line["spans"]:
                                span_rect = fitz.Rect(span["bbox"])
                                if caption_area.contains(span_rect):
                                    # Match variants like "Figure 2-1." or "Fig. 2-1."
                                    match = re.match(r"(Figure|Fig\.?)\s+\d+-\d+\.", span["text"].strip())
                                    if match:
                                        caption_text = re.sub(r"^(Figure|Fig\.?)\s+\d+-\d+\.\s*", "",
                                                              span["text"].strip())
                                        break
                            if caption_text:
                                break
                    if caption_text:
                        break

                if caption_text:
                    # Save to MongoDB
                    self.collection.insert_one({
                        "id_count": id_count['value'],
                        "page": page_num + 1,
                        "caption": caption_text,
                        "image": Binary(image_bytes)
                    })
                    print(f"✅ Inserted image from page {page_num + 1}, figure {img_index + 1}")
                    print(f"   ➤ Caption: {caption_text}")
                    id_count['value'] += 1
                    figure_count += 1
                else:
                    print(f"🟡 No caption found for image on page {page_num + 1}")

        print(f"\n✅ Done. Inserted {figure_count} figure(s) into MongoDB.")


    def get_figures_from_books(self):
        books_path = ['SparkBook.pdf', 'HadoopBook.pdf', 'FlinkBook.pdf', 'KafkaBook.pdf']
        for book_path in books_path:
            self.extract_figures_to_mongodb(book_path)

