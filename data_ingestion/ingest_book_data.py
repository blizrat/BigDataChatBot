from globals import titles, index_map, upgradation_vals, locations, count
from PyPDF2 import PdfReader

class IngestBookData:
    def __init__(self, db):
        self.collection = db['Books']

    def ingest_books(self):
        self.collection.delete_many({})
        for i in range(0, len(titles)):
            title = titles[i]
            index = index_map[i]
            upgradation_val = upgradation_vals[i]
            location = locations[i]
            instance = PdfReader(location)
            for j, val in index.items():
                text = ""
                for k in range(j, val[1]):
                    text = text + " " + instance.pages[k + upgradation_val].extract_text()
                self.collection.insert_one({"count": count['value'], "book": title, "chapter": val[0], "text": text})
                count['value'] += 1