from pathlib import Path
import shutil
from typing import Dict, List

from iiif_prezi3 import Manifest
import pyvips

# Import the helper to ensure the monkeypatch is applied
from . import create_canvas_from_local_iiif  # noqa: F401


class IIIFGenerator:
    VALID_VIEWING_DIRECTIONS = [
        "left-to-right",
        "right-to-left",
        "top-to-bottom",
        "bottom-to-top",
    ]

    def __init__(self, output_path: Path, base_url: str, tile_size: int = 256):
        """Initialize the IIIF Generator.

        Args:
            output_path: Directory where IIIF files will be generated
            base_url: Base URL where the IIIF resources will be served
            tile_size: Size of tiles in pixels (default: 256)
        """
        self.output_path = Path(output_path)
        self.base_url = base_url.rstrip("/")
        self.tile_size = tile_size
        self.image_identifiers = []

    def generate_tiles(
        self, image_path: Path, identifier: str, *, force: bool = False
    ) -> dict:
        """Generate IIIF tiles using libvips.

        Args:
            image_path: Path to source image
            identifier: IIIF identifier for the image
            force: Force regeneration of tiles even if they exist

        Returns:
            dict containing width and height of the original image
        """
        # Store identifier for manifest generation later
        self.image_identifiers.append(identifier)
        # Check and create output directory
        image_path = Path(image_path)
        output_dir = self.output_path / "images" / identifier
        if output_dir.is_dir() and not force:
            # Do not generate
            generate = False
        else:
            generate = True
            output_dir.mkdir(parents=True, exist_ok=True)

        # Load image
        image = pyvips.Image.new_from_file(str(image_path))

        if generate:
            # Generate IIIF tiles
            image.dzsave(
                str(output_dir),
                layout="iiif3",
                tile_size=self.tile_size,
                id=f"{self.base_url}/images",
            )
            # vips only creates tiles, but not the full image.
            # Copy the original file to the correct location
            # TODO: Handle formats other than JPG
            full_path = output_dir / "full" / "max" / "0" / "default.jpg"
            full_path.parent.mkdir(parents=True, exist_ok=True)
            if image_path.suffix.lower() in (".jpg", ".jpeg"):
                shutil.copy(image_path, full_path)

        return {
            "width": image.width,
            "height": image.height,
        }

    def generate_manifest(
        self,
        identifier: str,
        label: Dict[str, List[str]],
    ) -> str:
        """Generate IIIF Presentation 3.0 Manifest using iiif-prezi3.

        Args:
            identifier: IIIF identifier for the manifest
            label: Label as a language dict

        Returns:
            URL of the generated manifest
        """
        # Create manifest object
        manifest = Manifest(
            id=f"{self.base_url}/{identifier}",
            label=label,
        )
        # Add canvases for the individual images
        for image_identifier in self.image_identifiers:
            manifest.make_canvas_from_local_iiif(
                info_json_path=self.output_path
                / "images"
                / image_identifier
                / "info.json",
                image_id=f"images/{image_identifier}",
                base_url=self.base_url,
                anno_id=f"{self.base_url}/annotation/{image_identifier}",
                anno_page_id=f"{self.base_url}/page/{image_identifier}",
            )

        # Write manifest to file
        manifest_path = self.output_path / identifier / "manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w") as f:
            f.write(manifest.json(indent=2))

        return f"{self.base_url}/{identifier}/manifest.json"
