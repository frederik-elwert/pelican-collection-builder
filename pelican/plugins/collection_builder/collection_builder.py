import csv
import datetime
import mimetypes
from pathlib import Path

from pelican import signals
from pelican.contents import Article
from pelican.readers import BaseReader


def _is_image(path):
    mtype, enc = mimetypes.guess_type(path)
    if mtype is None:
        return False
    if mtype.split("/")[0] == "image":
        return True
    return False


def add_image(row, settings):
    content_path = Path(settings["PATH"])
    raw_images_path = content_path / "images"
    pid = row["pid"]
    # Test single image
    matches = list(raw_images_path.glob(f"{pid}.*"))
    if len(matches) == 1 and _is_image(matches[0]):
        image = matches[0]
        return {"image": f"/{image.relative_to(content_path)}"}
    # Test folder of images
    item_path = raw_images_path / pid
    if item_path.is_dir():
        images = [f for f in item_path.iterdir() if _is_image(f)]
        return {
            "images": [
                f"/{image.relative_to(content_path)}" for image in images
            ]
        }


def add_csv_items(generator):
    content_path = Path(generator.settings["PATH"])
    csv_file_path = content_path / "data" / "collection.csv"

    base_reader = BaseReader(generator.settings)
    with csv_file_path.open(newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Map basic metadata
            metadata = {
                "title": row["label"],
                "date": datetime.datetime.now(),
                "template": "collection_item",
                "category": base_reader.process_metadata("category", "Collection"),
                **row,
            }
            # Add image paths
            metadata.update(add_image(row, generator.settings))
            # Add content
            content = ""
            # Generate and insert article
            article = Article(content, metadata, settings=generator.settings)
            generator.articles.append(article)


def register():
    signals.article_generator_pretaxonomy.connect(add_csv_items)
