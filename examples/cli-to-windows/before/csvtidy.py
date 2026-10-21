"""csvtidy (pre-port snapshot, trimmed for the example)."""
import os, subprocess, sys

CACHE = "/tmp/csvtidy-cache"
CONFIG = os.path.join(os.environ["HOME"], ".csvtidy")


def sort_file(path):
    # relies on GNU sort being on PATH
    return subprocess.run(["sort", "-u", path], capture_output=True, text=True).stdout


def read_rows(path):
    data = open(path, "r").read()
    return data.split("\n")


def write_rows(path, rows):
    with open(path, "w") as fh:
        fh.write("\n".join(rows))


if __name__ == "__main__":
    if sys.platform == "linux":
        os.makedirs(CACHE, exist_ok=True)
    print(sort_file(sys.argv[1]))
