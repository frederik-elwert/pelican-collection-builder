import csv
import datetime
import mimetypes
from pathlib import Path

from pelican import signals
from pelican.contents import Article
from pelican.readers import BaseReader
from pelican.urlwrappers import URLWrapper

DEFAULT_COLLECTION_DATA_FILE = "collection.csv"
DEFAULT_COLLECTION_CATEGORY = "Collection"
COLLECTION_TEMPLATE = "collection_item"


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
        return {"image": f"{image.relative_to(content_path)}"}
    # Test folder of images
    item_path = raw_images_path / pid
    if item_path.is_dir():
        images = [f for f in item_path.iterdir() if _is_image(f)]
        return {"images": [f"{image.relative_to(content_path)}" for image in images]}


def read_collection_data(settings):
    """Read the CSV file and return a dictionary of collection items."""
    content_path = Path(settings["PATH"])
    data_file = settings.get("COLLECTION_DATA_FILE", DEFAULT_COLLECTION_DATA_FILE)
    csv_file_path = content_path / "data" / data_file

    collection_data = {}
    with csv_file_path.open(newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Add title based on label
            # `label` is used in the CSV file, a convention taken from wax.
            # `title` is pelican’s convention.
            row["title"] = row["label"]
            # Add image paths to the row data
            row.update(add_image(row, settings))
            # Add url to the row data so it is available in collection_data
            # Required so that jinja2content knows about item URLs
            class Article(URLWrapper):
                pass
            urlwrapper = Article(row["label"], settings)
            row["url"] = urlwrapper.url
            # Store in dictionary using pid as key
            collection_data[row["pid"]] = row

    return collection_data


def initialize_collection(pelican_obj):
    """Initialize the collection by reading CSV data and adding it to JINJA_GLOBALS."""
    collection_data = read_collection_data(pelican_obj.settings)

    # Initialize JINJA_GLOBALS if it doesn't exist
    if "JINJA_GLOBALS" not in pelican_obj.settings:
        pelican_obj.settings["JINJA_GLOBALS"] = {}

    # Add collection data to JINJA_GLOBALS
    pelican_obj.settings["JINJA_GLOBALS"]["collection_data"] = collection_data
    pelican_obj.settings["JINJA_GLOBALS"]["SITEURL"] = pelican_obj.settings.get(
        "SITEURL", ""
    )


def generate_collection_pages(generator):
    """Generate individual pages for collection items using the shared collection
    data."""
    collection_data = generator.settings["JINJA_GLOBALS"]["collection_data"]
    base_reader = BaseReader(generator.settings)
    category = generator.settings.get(
        "COLLECTION_CATEGORY", DEFAULT_COLLECTION_CATEGORY
    )

    for pid, item_data in collection_data.items():
        # Map basic metadata
        metadata = {
            "date": datetime.datetime.now(),
            "template": COLLECTION_TEMPLATE,
            "category": base_reader.process_metadata("category", category),
            **item_data,
        }

        # Generate and insert article
        content = ""
        article = Article(content, metadata, settings=generator.settings)
        generator.articles.append(article)


def register():
    """Register the plugin signals."""
    signals.initialized.connect(initialize_collection)
    signals.article_generator_pretaxonomy.connect(generate_collection_pages)
