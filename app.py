from flask import Flask, render_template, request, jsonify
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import pymongo
import requests
import json
import base64
import re
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")
app = Flask(__name__)


class QueryProcessor:
    def __init__(self):
        self.client = pymongo.MongoClient("mongodb://localhost:27017/")
        self.db = self.client["ScrapedData"]
        self.collection = self.db["chunking"]
        self.index = faiss.read_index("faiss_index.bin")
        self.index_images = faiss.read_index("faiss_index_images.bin")
        self.id_counts = np.load("id_count.npy")
        self.chunk_ids = np.load("chunk_ids.npy")
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

    def extract_and_format_references(self, text_answer):
        """
        Extract references from the text answer, retrieve metadata, and format the response
        to replace raw references with human-readable metadata.

        Args:
            text_answer (str): The original answer text with references

        Returns:
            str: The modified answer with metadata instead of raw references
            list: The extracted metadata items
        """
        # Extract references using regex
        pattern = r"\[chunk_id=(\d+), count=(\d+)\]"
        matches = re.findall(pattern, text_answer)
        if not matches:
            return text_answer, []

        # Format references into list of dictionaries
        references = [{"chunk_id": int(chunk), "count": int(count)} for chunk, count in matches]

        # Extract counts from references
        counts = [ref["count"] for ref in references]

        # Retrieve metadata based on count values
        metadata_list = []
        for count in counts:
            if count <= 100:
                collection = self.db['Books']
                result = collection.find_one({"count": count}, {'_id': 0, 'text': 0})
                if result:
                    metadata_list.append(result)
            else:
                collection = self.db['Youtube_data']
                result = collection.find_one({"count": count}, {'_id': 0, 'text': 0})
                if result:
                    metadata_list.append(result)

        # Format metadata for display
        formatted_references = []
        for item in metadata_list:
            if 'book' in item and 'chapter' in item:
                formatted_references.append(f"{item['book']} - {item['chapter']}")
            elif 'title' in item and 'link' in item:
                formatted_references.append(f"{item['title']} (YouTube)")
            else:
                # Fallback for unexpected metadata format
                formatted_references.append(str(item))

        # Replace original references with formatted metadata
        modified_answer = text_answer
        if "References:" in modified_answer:
            # Replace everything after "References:" with our new formatted references
            parts = modified_answer.split("References:")
            modified_answer = parts[0] + "References: " + ", ".join(formatted_references)

        return modified_answer, metadata_list

    def process_query(self, user_query):
        # Encode the query
        embeddings = self.model.encode(user_query)

        # Process for text and images
        text_indices = self.processQueryText(embeddings)
        image_indices = self.processQueryImages(embeddings)

        # Get matching chunks
        chunks_text = self.matchingChunksText(text_indices, 'chunking')
        chunks_images = self.matchingChunksImages(image_indices, 'images')

        # Get answers
        text_answer = self.getTextAnswer(user_query, chunks_text)
        image_binary_answers = self.getImageAnswer(user_query, chunks_images)

        # Process image results
        image_results = self.process_image_results(image_binary_answers, chunks_images)

        # Process the text answer to replace references with metadata
        formatted_answer, metadata = self.extract_and_format_references(text_answer)

        return {
            "text_answer": formatted_answer,
            "metadata": metadata,
            "image_results": image_results
        }

    def processQueryText(self, embeddings):
        top_k = 5
        distances, indices = self.index.search(embeddings.reshape(1, -1), top_k)
        return indices

    def processQueryImages(self, embeddings):
        top_k = 5
        distances, indices = self.index_images.search(embeddings.reshape(1, -1), top_k)
        return indices

    def matchingChunksText(self, indices, collection_name):
        collection = self.db[collection_name]
        matching_chunks_text = []
        for idx in indices[0]:  # Iterate over retrieved indices
            chunk_id = int(self.chunk_ids[idx])  # Get corresponding chunk ID
            result = collection.find_one({"chunk_id": chunk_id}, {"_id": 0})

            if result:
                # Ensure all values are JSON serializable
                processed_result = {}
                for key, value in result.items():
                    if isinstance(value, (str, int, float, bool, list, dict)) or value is None:
                        processed_result[key] = value
                matching_chunks_text.append(processed_result)
        return matching_chunks_text

    def matchingChunksImages(self, indices, collection_name):
        collection = self.db[collection_name]
        matching_chunks_images = []
        for idx in indices[0]:  # Iterate over retrieved indices
            id_val = int(self.id_counts[int(idx)])  # Get corresponding chunk ID
            result = collection.find_one({"id_count": id_val}, {"_id": 0, "image": 0})

            if result:
                # Ensure all values are JSON serializable
                processed_result = {}
                for key, value in result.items():
                    if isinstance(value, (str, int, float, bool, list, dict)) or value is None:
                        processed_result[key] = value
                matching_chunks_images.append(processed_result)

        return matching_chunks_images

    def getTextAnswer(self, user_query, chunks_text):
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": "Bearer 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",
                "Content-Type": "application/json",
                "HTTP-Referer": "<YOUR_SITE_URL>",
                "X-Title": "<YOUR_SITE_NAME>",
            },
            data=json.dumps({
                "model": "meta-llama/llama-3.2-3b-instruct:free",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a precise knowledge retrieval assistant. Your task is to answer questions based only on the provided context chunks. "
                            "Follow these guidelines:\n\n"
                            "1. Use only information present in the given context chunks.\n"
                            "2. If the context doesn't contain the answer, state that clearly instead of speculating.\n"
                            "3. Provide concise, accurate answers with direct references to the sources.\n"
                            "4. Prioritize information from chunks that most directly address the query.\n"
                            "5. Keep your response focused and to the point.\n\n"
                            "At the end of your answer, include references to the specific chunks that supported your response, "
                            "formatted as: [chunk_id=X, count=Y], separated by commas."
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Context chunks:\n{json.dumps(chunks_text, indent=2)}\n\n"
                            f"User question: {user_query}\n\n"
                            "Answer based only on the provided context. Format your response as:\n"
                            "Answer: [Your clear, concise answer here]\n"
                            "References: [chunk_id=X, count=Y], [chunk_id=Z, count=W], etc."
                        )
                    }
                ]
            }))
        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        else:
            return "Sorry, I couldn't process your query at this time."

    def getImageAnswer(self, user_query, chunks_images):
        # If no images available, return early
        if not chunks_images:
            return "00000"

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": "Bearer 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",
                "Content-Type": "application/json",
                "HTTP-Referer": "<YOUR_SITE_URL>",
                "X-Title": "<YOUR_SITE_NAME>",
            },
            data=json.dumps({
                "model": "meta-llama/llama-3.2-3b-instruct:free",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a highly selective image retrieval assistant. Your task is to determine which images are STRONGLY relevant to a user query. "
                            "Follow these strict criteria:\n\n"
                            "1. An image is relevant ONLY if its title or description directly addresses the core topic of the query.\n"
                            "2. Peripheral or tangential relevance is NOT sufficient - images must be central to answering the query.\n"
                            "3. Return AT MOST 2-3 images, even if more seem relevant.\n"
                            "4. If no images are highly relevant, return all zeros.\n\n"
                            "Respond with a binary string where 1=highly relevant and 0=not relevant. Your response must contain ONLY the binary string."
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                                       f"User query: \"{user_query}\"\n\n"
                                       f"Available images (up to 5):\n"
                                   ) + "\n".join([
                            f"{i + 1}. Title: \"{img.get('title', 'Untitled')}\", Description: \"{img.get('description', 'No description')}\""
                            for i, img in enumerate(chunks_images[:5])]) + "\n\n"
                                                                           "Respond with ONLY a 5-digit binary string (e.g., '00100') where each position corresponds to an image, and 1 means highly relevant. "
                                                                           "Remember: be extremely selective and limit to 2-3 images maximum."
                    }
                ],
            })
        )

        if response.status_code == 200:
            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # Extract just the binary digits
            binary = re.search(r'[01]{1,5}', content)
            if binary:
                binary_str = binary.group(0)

                # Ensure we have exactly 5 digits
                binary_str = binary_str.ljust(5, '0')[:5]

                # Limit to maximum 3 relevant images
                if binary_str.count('1') > 3:
                    # Find positions of all '1's
                    one_positions = [i for i, bit in enumerate(binary_str) if bit == '1']
                    # Create a new binary string with only the first 3 '1's
                    new_binary = ['0'] * 5
                    for pos in one_positions[:3]:
                        new_binary[pos] = '1'
                    binary_str = ''.join(new_binary)

                return binary_str

        # Default or error case - return no matches
        return "00000"

    def process_image_results(self, binary_answer, chunks_images):
        # Clean the binary answer to ensure it only contains 0s and 1s
        clean_binary = re.sub(r'[^01]', '', binary_answer)

        # Ensure we have matching binary digits for each image
        results = []
        collection = self.db['images']

        for i, bit in enumerate(clean_binary[:len(chunks_images)]):
            if bit == '1':
                # For each matching image (marked with '1'), get the image data
                if i < len(chunks_images):
                    chunk = chunks_images[i]
                    id_count = chunk.get('id_count')
                    if id_count is not None:
                        image_doc = collection.find_one({"id_count": int(id_count)})
                        if image_doc and 'image' in image_doc:
                            # Convert binary image data to base64
                            try:
                                # Check if image is already a string (base64)
                                if isinstance(image_doc['image'], str):
                                    image_base64 = image_doc['image']
                                else:
                                    # Convert binary data to base64
                                    image_base64 = base64.b64encode(image_doc['image']).decode('utf-8')

                                # Return image data and metadata
                                results.append({
                                    "title": chunk.get('title', 'Untitled'),
                                    "image_data": image_base64,
                                    "id_count": id_count
                                })
                            except Exception as e:
                                print(f"Error processing image {id_count}: {e}")

        return results


# Initialize the query processor
query_processor = QueryProcessor()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/query', methods=['POST'])
def query():
    user_query = request.json.get('query', '')
    if not user_query:
        return jsonify({"error": "No query provided"}), 400

    try:
        results = query_processor.process_query(user_query)
        return jsonify(results)
    except Exception as e:
        print(f"Error processing query: {e}")
        return jsonify({"error": str(e), "text_answer": "Sorry, there was an error processing your request.",
                        "image_results": []}), 500


if __name__ == "__main__":
    app.run(debug=True)