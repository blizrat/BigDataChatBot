from config import config
from config import index
from data_ingestion.ingest_book_data import IngestBookData
from data_ingestion.ingest_youtube_data import IngestYoutubeData
from data_ingestion.ingest_book_images import  IngestBookImages
from data_chunking.chunk_book_data import ChunkBookData
from data_chunking.chunk_youtube_data import ChunkYoutubeData
from data_embedding.embedding_text_chunks import EmbeddingTextChunks
from data_embedding.embedding_image_titles import EmbeddingImageTitles
from data_indexing.indexing_text_embeddings import IndexTextEmbeddings
from data_indexing.indexing_image_embeddings import IndexImageEmbeddings



class Main:

    def add_books(self):
        obj1 = config.GetBookConfig('Big Data for Dummies', index.bigData_chapters, 22, 'bigDataBook.pdf')
        obj1.add_book()
        obj2 = config.GetBookConfig('Kafka the Definitive Guide', index.kafka_chapters, 0, 'KafkaBook.pdf')
        obj2.add_book()
        obj3 = config.GetBookConfig('Spark the Definitive Guide', index.spark_chapters, 0, 'SparkBook.pdf')
        obj3.add_book()
        obj4 = config.GetBookConfig('Stream Processing with Apache Flink', index.flink_chapters, 0, 'FlinkBook.pdf')
        obj4.add_book()
        obj5 = config.GetBookConfig('Haddop the Definitive Guide', index.hadoop_chapters, 28, 'HadoopBook.pdf')
        obj5.add_book()

    def add_video_data(self):
        obj1 = config.GetVideoDataConfig()
        obj1.get_video_data()

if __name__ == '__main__':
    obj = Main()
    obj.add_books()
    obj.add_video_data()

    config_obj = config.Config()
    db = config_obj.get_connection()

    ingest_book_data_obj = IngestBookData(db = db)
    ingest_book_data_obj.ingest_books()

    ingest_youtube_data_obj = IngestYoutubeData(db = db)
    ingest_youtube_data_obj.ingest_youtube_data()

    ingest_book_images_obj = IngestBookImages(db = db)
    ingest_book_images_obj.get_figures_from_books()

    chunk_book_data_obj = ChunkBookData(db = db)
    chunk_book_data_obj.get_book_chunks()

    chunk_youtube_data_obj = ChunkYoutubeData(db = db)
    chunk_youtube_data_obj.get_youtube_chunks()

    embed_text_chunks_obj = EmbeddingTextChunks(db)
    embeddings, chunk_ids = embed_text_chunks_obj.get_text_embedding()

    index_text_embeddings_obj = IndexTextEmbeddings(embeddings, chunk_ids)
    index_text_embeddings_obj.get_indexed_embeddings()

    embed_image_titles_obj = EmbeddingImageTitles(db = db)
    embeddings, id_count = embed_image_titles_obj.get_image_embedding()

    index_image_embedding_obj = IndexImageEmbeddings(embeddings, id_count)
    index_image_embedding_obj.get_indexed_embeddings()



