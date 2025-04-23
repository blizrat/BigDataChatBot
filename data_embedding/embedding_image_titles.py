from sentence_transformers import SentenceTransformer

class EmbeddingImageTitles:
    def __init__(self, db):
        self.db = db
        self.collection = db['images']
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.text = []
        self.id_count = []

    def get_images_data(self):
        data = self.collection.find({})
        return data

    def get_image_embedding(self):
        data = self.get_images_data()
        for chunk in data:
            self.text.append(chunk['caption'])
            self.id_count.append(chunk['id_count'])

        embeddings = self.model.encode(self.text,
                                      convert_to_numpy=True,
                                      normalize_embeddings= True)
        return embeddings, self.id_count
