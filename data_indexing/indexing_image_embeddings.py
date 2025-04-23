import numpy as np
import faiss

class IndexImageEmbeddings:

    def __init__(self, embeddings, id_count):
        self.embeddings = embeddings
        self.id_count =id_count

    def get_indexed_embeddings(self):
        index = faiss.IndexFlatL2(self.embeddings.shape[1])
        index.add(self.embeddings)
        faiss.write_index(index, "faiss_index_images.bin")
        np.save("id_count.npy", np.array(self.id_count))