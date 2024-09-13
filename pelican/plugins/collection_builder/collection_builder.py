import datetime
import csv
from pathlib import Path

from pelican import signals
from pelican.contents import Article
from pelican.readers import BaseReader


def add_csv_items(generator):
    content_path = Path(generator.settings["PATH"])
    csv_file_path = content_path / "data" / "collection.csv"

    base_reader = BaseReader(generator.settings)
    with csv_file_path.open(newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            metadata = {
                "title": row["label"],
                "date": datetime.datetime.now(),
                "template": "collection_item",
                "category": base_reader.process_metadata("category", "Collection"),
                **row,
            }
            content = ""
            article = Article(content, metadata, settings=generator.settings)
            generator.articles.append(article)


def register():
    signals.article_generator_pretaxonomy.connect(add_csv_items)
