from globals import chunk_id
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_experimental.text_splitter import SemanticChunker

class ChunkBookData:
    def __init__(self, db):
        self.db = db
        self.collection = db['Books_test']
        self.embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    def get_book_data(self):
        data = list(self.collection.find({}).sort('count', 1))
        return data

    def get_book_chunks(self):
        data = self.get_book_data()
        self.collection = self.db['chunking_test']
        self.collection.delete_many({})

        semantic_chunker = SemanticChunker(self.embedding_model)
        for docs in data:
            chunks = semantic_chunker.split_text(docs['text'])
            for chunk in chunks:
                self.collection.insert_one({
                    'chunk_id': chunk_id['value'],
                    'text': chunk,
                    'count': docs['count']
                }
                )
                chunk_id['value'] += 1