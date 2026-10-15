"""
Download the LibreYOLO/circuit-elements dataset from HuggingFace.
CC BY 4.0 licensed - free for any use with attribution.
772 images across 45 electrical component classes.
"""
import os
from pathlib import Path
from huggingface_hub import snapshot_download

DATASET_DIR = Path(__file__).parent / "dataset"


def download():
    print("Downloading LibreYOLO/circuit-elements dataset from HuggingFace...")
    print("License: CC BY 4.0 (free to use)")
    print(f"Target: {DATASET_DIR}\n")

    snapshot_download(
        repo_id="LibreYOLO/circuit-elements",
        repo_type="dataset",
        local_dir=str(DATASET_DIR / "circuit-elements"),
    )

    print(f"\nDataset downloaded to: {DATASET_DIR / 'circuit-elements'}")

    train_imgs = DATASET_DIR / "circuit-elements" / "train" / "images"
    val_imgs = DATASET_DIR / "circuit-elements" / "valid" / "images"
    test_imgs = DATASET_DIR / "circuit-elements" / "test" / "images"

    for split_name, split_path in [("Train", train_imgs), ("Valid", val_imgs), ("Test", test_imgs)]:
        if split_path.exists():
            count = len(list(split_path.glob("*")))
            print(f"  {split_name}: {count} images")
        else:
            print(f"  {split_name}: directory not found at {split_path}")

    data_yaml = DATASET_DIR / "circuit-elements" / "data.yaml"
    if data_yaml.exists():
        print(f"\ndata.yaml found at: {data_yaml}")
        print(data_yaml.read_text())
    else:
        print("\nNo data.yaml found, checking README...")
        readme = DATASET_DIR / "circuit-elements" / "README.md"
        if readme.exists():
            print(readme.read_text()[:2000])


if __name__ == "__main__":
    download()
