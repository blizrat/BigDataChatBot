import numpy as np
import faiss

class IndexTextEmbeddings:

    def __init__(self, embeddings, chunk_ids):
        self.embeddings = embeddings
        self.chunk_ids = chunk_ids

    def get_indexed_embeddings(self):
        index = faiss.IndexFlatL2(self.embeddings.shape[1])
        index.add(self.embeddings)
        faiss.write_index(index, "faiss_index.bin")
        np.save("chunk_ids.npy", np.array(self.chunk_ids))

