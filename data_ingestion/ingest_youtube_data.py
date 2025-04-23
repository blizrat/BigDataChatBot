from globals import count, video_data
from youtube_transcript_api import YouTubeTranscriptApi , TranscriptsDisabled

class IngestYoutubeData:
    def __init__(self, db):
        self.collection = db['Youtube_data']

    def ingest_youtube_data(self):
        self.collection.delete_many({})

        for video in video_data:
            try:
                transcripts = YouTubeTranscriptApi.get_transcript(video['video_id'])
                text = ""
                for transcript in transcripts:
                    text = text + " " + transcript["text"]

                self.collection.insert_one({"count": count['value'], 'title': video['title'], 'text': text, 'link': video['url']})
                count['value']+= 1
                print(f"Inserted transcript for video ID: {video['video_id']}")
            except TranscriptsDisabled:
                print(f"Skipping {video['video_id']}: Transcripts are disabled.")

            except Exception as e:
                print(f"Failed to fetch transcript for {video['video_id']}: {e}")
