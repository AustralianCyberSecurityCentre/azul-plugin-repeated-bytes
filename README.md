# Azul Plugin Repeated Bytes

![azul | plugin](https://img.shields.io/static/v1.svg?label=azul&message=plugin&color=163a66)
![state | prod](https://img.shields.io/static/v1.svg?label=state&message=prod&color=163a66)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Security: bandit](https://img.shields.io/badge/security-bandit-green.svg)](https://github.com/PyCQA/bandit)

Find smaller portion of data which repeats after its first occurrence.

It features information about the sizes of the unique / repeated portions and
will either feature a string representation of the unique portion if it is
small enough, or insert it as a 'deduplicated' child.

## Development Installation

To install azul-plugin-repeated-bytes for development run the command
(from the root directory of this project):

```bash
pip install -e .
```

## Usage

Usage on local files:

```bash
azul-plugin-repeated-bytes malware.file
```

Example usage on a sample file from VirusShare:

```bash
    $ azul-plugin-repeated-bytes VirusShare_d8ef9e41807d0bd0d73be688d073ebc1

    Output features:
        tag: repeated_bytes
        rep_byte_ratio: 1.7371335209222112
        rep_byte_excess_size: 24363
        rep_byte_data_size: 33051
```

Results show that roughly 74% of the PE file is repeated, this saves time,
and allows the analyst to ignore the 'second' PE in the file as it's a duplicate.
The plugin will also 'deduplicate' the file, carving off the repeating
data, and reinserting the result as a child.
In many cases this would be the 'clean' version of the file.

Automated usage in system:

```bash
azul-plugin-repeated-bytes --server http://azul-dispatcher.localnet/
```

## Usage repeated-bytes

Installing as a pip package creates the command line utility "repeated-bytes".

Check whether a file has a repeating property:

```bash
repeated-bytes file.bin
# Require that the repeating data is at least 1024 bytes:
repeated-bytes --min-repeated 1024 file.bin
# Require that the data is repeated at least twice:
repeated-bytes --min-ratio 2.0 file.bin
# Don't abort a search if it is slow:
repeated-bytes --force file.bin
# Write deduplicated data to disk:
repeated-bytes --outpath deduped.bin
```

## Example Output

Below are some examples from a collection of 5GB of malware from VirusShare.
The "1 byte repeating" case is probably just by chance.
This can be avoided by using the minimum size or ratio arguments.
It also detects interesting cases of full or partial repetition, which might have been difficult to detect
otherwise:

    /mnt/malware/5gb_pe/VirusShare_c39fece0274201d03a6ef98b487c9390
        File consists of 4582561 bytes which repeat.
        Number of repeated bytes: 1
        Repeat ratio: 1.000000

    /mnt/malware/5gb_pe/VirusShare_a8aa773f0cc16a89d734290ecd5f913f
        File consists of 11584 bytes which repeat.
        Number of repeated bytes: 11584
        Repeat ratio: 2.000000

    /mnt/malware/5gb_pe/VirusShare_f6d69630b3325f24ccda11fde3f130ed
        File consists of 690391 bytes which repeat.
        Number of repeated bytes: 1
        Repeat ratio: 1.000001

    /mnt/malware/5gb_pe/VirusShare_71cce47a1d00d6f0e72fdfb1b8dc932f
        File consists of 74957 bytes which repeat.
        Number of repeated bytes: 1
        Repeat ratio: 1.000013

    /mnt/malware/5gb_pe/VirusShare_d8ef9e41807d0bd0d73be688d073ebc1
        File consists of 33051 bytes which repeat.
        Number of repeated bytes: 24363
        Repeat ratio: 1.737134

    /mnt/malware/5gb_pe/VirusShare_23da7f3d2efe2d0dba802c786e03b0f5
        File consists of 12572 bytes which repeat.
        Number of repeated bytes: 2920
        Repeat ratio: 1.232262

    /mnt/malware/5gb_pe/VirusShare_48f66315af1645d5b5cb1fc0c0f41032
        File consists of 4878064 bytes which repeat.
        Number of repeated bytes: 9652
        Repeat ratio: 1.001979

## Performance

In most cases this analysis is pretty fast, but there are some instances where
performance will degrade to effectively a brute force search for the size of
the repeating data.

The code searches for data from the start of the file (configured to 32 bytes) throughout the remainder of the file,
and uses these as candidates for the width of the repeating data.
In cases where the data at the beginning is extremely common throughout the remainder of the file,
very little time is saved by using this search technique.
If the code detects that it has reached a configured maximum guesses for the width,
it aborts the search and returns no results.

This can be overridden with the --force flag, but the processing may take a long time - in the worst cases,
up to a minute per MB. On some data generated to exercise this worst case it took up to a minute per MB.

Since raising the size of the data searched for from 8 to 32 bytes I have not
(in fairly limited testing) encountered a real file for which the search was

The worst case scenario for a slow to process file  is one that is very sparse with mostly zeros.
A file to exercise this worst can be made with something like: - 1 MB of zero bytes - A single "A"

This is not necessarily limited to zero bytes, an almost as bad file would be: - "ACBDEFGH" for a few MB - A single "1"

## Python Package management

This python package is managed using a `setup.py` and `pyproject.toml` file.

Standardisation of installing and testing the python package is handled through tox.
Tox commands include:

```bash
# Run all standard tox actions
tox
# Run linting only
tox -e style
# Run tests only
tox -e test
```

## Dependency management

Dependencies are managed in the requirements.txt, requirements_test.txt and debian.txt file.

The requirements files are the python package dependencies for normal use and specific ones for tests
(e.g pytest, black, flake8 are test only dependencies).

The debian.txt file manages the debian dependencies that need to be installed on development systems and docker images.

Sometimes the debian.txt file is insufficient and in this case the Dockerfile may need to be modified directly to
install complex dependencies.
