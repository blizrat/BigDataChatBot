from sentence_transformers import SentenceTransformer

class EmbeddingTextChunks:
    def __init__(self, db):
        self.db = db
        self.collection = db['chunking_test']
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.text = []
        self.chunk_ids = []

    def get_chunk_data(self):
        data = self.collection.find({})
        return data

    def get_text_embedding(self):
        data = self.get_chunk_data()
        for chunk in data:
            self.text.append(chunk['text'])
            self.chunk_ids.append(chunk['chunk_id'])

        embeddings = self.model.encode(self.text,
                                      convert_to_numpy=True,
                                      normalize_embeddings= True)
        return embeddings, self.chunk_ids




