"""Step 0 — fetch and verify the datasets.

LIAR and McIntire are downloaded automatically if missing. ISOT needs a Kaggle
account, so it is downloaded by hand (instructions are printed if it is missing).
Every file is then checked against the SHA-256 checksum of the copy the results
were produced from, so a reproducer knows they have exactly the same data.
"""

import hashlib
import io
import sys
import urllib.request
import zipfile

from common import DATA_DIR

ISOT_URL = "https://www.kaggle.com/datasets/clmentbisaillon/fake-and-real-news-dataset"

# zip URL -> {member name inside the zip: destination path}
DOWNLOADS = {
    "https://sites.cs.ucsb.edu/~william/data/liar_dataset.zip": {
        "train.tsv": DATA_DIR / "liar" / "train.tsv",
        "valid.tsv": DATA_DIR / "liar" / "valid.tsv",
        "test.tsv": DATA_DIR / "liar" / "test.tsv",
    },
    "https://raw.githubusercontent.com/joolsa/fake_real_news_dataset/master/fake_or_real_news.csv.zip": {
        "fake_or_real_news.csv": DATA_DIR / "mcintire" / "fake_or_real_news.csv",
    },
}

SHA256 = {
    DATA_DIR / "True.csv": "ba0844414a65dc6ae7402b8eee5306da24b6b56488d6767135af466c7dcb2775",
    DATA_DIR / "Fake.csv": "bebf8bcfe95678bf2c732bf413a2ce5f621af0102c82bf08083b2e5d3c693d0c",
    DATA_DIR / "liar" / "train.tsv": "23ef8cb7ff57b25c941100d0744039cebc595d65a67ea190f72b330a658d8c36",
    DATA_DIR / "liar" / "valid.tsv": "8dd3d7ed1a11e78ed7df090c9eddb0f91147f895850c78d49dd7b4e88fd09a16",
    DATA_DIR / "liar" / "test.tsv": "ee41e2c741e0019216952625145af8c4aa8c8d3057ec68284b134267bb845e6f",
    DATA_DIR / "mcintire" / "fake_or_real_news.csv":
        "bb7fa746dd7148b63b0a10e47b329f4b4825afc85b206d3fea18ecfce28ee731",
}


def download(url, members):
    """Fetch a zip and write only the named members to their destinations."""
    print(f"downloading {url}")
    with urllib.request.urlopen(url, timeout=120) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))
    for member, dest in members.items():
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(archive.read(member))
        print(f"  wrote {dest.relative_to(DATA_DIR.parent)}")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    for url, members in DOWNLOADS.items():
        if not all(dest.exists() for dest in members.values()):
            download(url, members)

    problems = 0
    for path, expected in SHA256.items():
        name = path.relative_to(DATA_DIR.parent)
        if not path.exists():
            print(f"MISSING   {name}")
            problems += 1
        elif sha256(path) != expected:
            print(f"DIFFERENT {name}  (not the file the results were produced from)")
            problems += 1
        else:
            print(f"ok        {name}")

    if not (DATA_DIR / "True.csv").exists() or not (DATA_DIR / "Fake.csv").exists():
        print(f"\nISOT must be downloaded by hand (free Kaggle account needed):\n  {ISOT_URL}\n"
              f"Unzip it and put True.csv and Fake.csv in {DATA_DIR}")
    if problems:
        sys.exit(f"\n{problems} data file(s) missing or different; fix before running the experiments.")
    print("\nall datasets present and verified")


if __name__ == "__main__":
    main()
