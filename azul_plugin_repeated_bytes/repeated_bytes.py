"""Search for repeating byte patterns within file content."""

import argparse

import pyprimesieve

# We'll search for the block of data with this size at the start of the file
# in the remainder of the file, to narrow down the list of widths we test.
SEARCH_BLOCK_SIZE = 32

# If we find ourselves trying more widths than this then it's likely the data
# we're searching has a quality which means we're effectively brute forcing the
# width. Even a 1MB file like this can take a minute to check, so once we hit
# a limit like this we'll just abort.
MAXIMUM_WIDTH_ATTEMPTS = 1024


def data_repeats_exactly_n_times(data, n):
    """Return whether the data is a pattern repeated n times (iterative).

    Naively checks that the given data is composed of <n> identical blocks by
    comparing them all against the first one.
    """
    # We can immediately return False if the length if not perfectly divisible
    # by <n>. (We probably won't ever call this function with such data though).
    if len(data) % n != 0:
        return False

    # Compute the size of the repeating chunk, then compare each subsequent
    # chunk of this size against the first one. We can fail as soon as we find
    # non-matching data.
    chunksize = int(len(data) / n)
    for i in range(1, n):
        if data[:chunksize] != data[chunksize * i : chunksize * (i + 1)]:
            return False

    # All chunks were found to be equal.
    return True


def data_repeats_exactly_n_times_recursive(data, n):
    """Return whether the data is a pattern repeated n times (recursive).

    Checks whether the data is composed of <n> identical blocks by recursively
    breaking it down. The motivation behind recursion is to improve performance
    by avoiding the large number of chunk comparisons which are required with
    the naive method when <n> is high. An example.

        data: "ABABABABABABABABABABABAB" n: 12
        Prime factors of 12: 2, 2, 3

        2: "ABABABABABAB" == "ABABABABABAB"   Compare 2 chunks, then recurse.
        2: "ABABAB" == "ABABAB"               Compare 2 chunks, then recurse.
        3: "AB" == "AB" == "AB"               Compare 3 chunks, then done.

        We confirmed 12 repeating chunks with 4 comparisons.
    """
    # A file which can be divided into <n> repeated chunks must also be able to
    # be divided into <p> repeated chunks for every prime factor <p> of <n>.
    # Generate the prime factors of <n>.
    prime_factors = []
    for p, c in pyprimesieve.factorize(n):
        prime_factors.extend([p] * c)

    # Recursively break the file down by these prime factors.
    for prime_factor in prime_factors:
        # If the file cannot be broken into <p> repeating chunks, then it can't
        # for <n> either, return False.
        if not data_repeats_exactly_n_times(data, prime_factor):
            return False

        # The file can be broken into <p> identical chunks. We'll reduce the
        # data we're examining to just one of these chunks and check whether it
        # can be broken down by the remaining prime factors.
        chunk_size = int(len(data) / prime_factor)
        data = data[:chunk_size]

    # We were able to recursively divide the file into repeating chunks for
    # every prime factor <p> of <n>, therefore the entire file can be broken
    # into <n> repeating chunks.
    return True


def data_repeats_with_width(data, width):
    """Return whether the data repeats at the specified width.

    Checks whether the given data simply repeats after the first <width> bytes.
    We handle fractional repeats, such as 1.5 instances of those <width> bytes.

        e.g. data_repeats_with_width("ABCDEFGHABCD", 8) == True
    """
    # We'll have some whole number of iterations of the <width> bytes,
    # potentially followed by some fractional remainder.
    num_full_repeats = int(len(data) / width)
    remainder = len(data) % width

    # If there's a "remainder" after our full repeats of <width> bytes then we
    # must compare it against the start of our data.
    if remainder != 0:
        # If it doesn't match we can immediately return False.
        if data[:remainder] != data[-remainder:]:
            return False

        # It did match, so we can carve off the remainder, reducing our problem
        # to one of checking whether some data repeats a known, whole number of
        # times.
        data = data[:-remainder]

    # Validate the number of full repeats on the main body of the data.
    return data_repeats_exactly_n_times_recursive(data, num_full_repeats)


def find_possible_repeat_widths(data):
    """Yield possible repeating data widths.

    Searches for SEARCH_BLOCK_SIZE bytes from the beginning of data
    to find other locations containing the content, yielding those offsets.

    We use this to generate a reduced candidate list of possible widths for
    repeating data.
    """
    # We're going to search for SEARCH_BLOCK_SIZE bytes from the start.
    pattern = data[:SEARCH_BLOCK_SIZE]
    offset = 0
    while True:
        # Search for the next occurrence of this pattern deeper into the data.
        offset = data.find(pattern, offset + 1)
        if offset == -1:
            break

        # Yield the offsets we locate.
        yield offset


def check_for_minimal_repeat_at_end(data):
    """Return fractional repeat at tail of data.

    If we've checked widths using find_possible_repeat_widths() then we will
    not have detected repeating data which:
        - repeats < 2 times
        - the fractional repeat is < SEARCH_BLOCK_SIZE bytes.

    This is a quick search to check whether we can find a small portion of data
    at the end of <data> which matches the data at the beginning.
    """
    # Our repeat can be as big as SEARCH_BLOCK_SIZE-1 bytes long, and as small
    # as 1 byte. We search through these possibilities backwards to make sure we
    # find the biggest repeat possible.
    for remainder_size in range(SEARCH_BLOCK_SIZE - 1, 0, -1):
        # Need to ignore sizes which will push past the boundaries of our
        # data, or just result in comparing the full data against itself.
        if remainder_size >= len(data):
            continue

        # If this remainder matches the start of our data then we've found a
        # repeat. Return the size of the actual data which is repeated.
        if data[-remainder_size:] == data[:remainder_size]:
            return len(data) - remainder_size

    # Failed to locate a repeat in the last SEARCH_BLOCK_SIZE bytes.
    return None


def data_repeats(data):
    """Check whether <data> consists of some smaller portion of data repeated.

    This is the core function we want to implement. All other code is to enable
    this function to achieve this goal with reasonable performance in standard
    cases.

    If we find a width after which the data repeats, we return it.
    If we find there is no width after which the data repeats, we return None.
    If we recognize we are in a poor performance case we abort the search and
    return -1.
    """
    # Need at least two bytes to have repetition.
    if len(data) < 2:
        return None

    # If the data is not larger than SEARCH_BLOCK_SIZE then we just brute
    # force the width, as find_possible_repeat_widths() will not be able to
    # give us any offsets.
    if len(data) <= SEARCH_BLOCK_SIZE:
        # Try every possible width and if any work, return them.
        for offset in range(1, len(data)):
            if data_repeats_with_width(data, offset):
                return offset

        # The data has no repeating property.
        return None

    # Our data is big enough that we'll try and speed things up by searching
    # for the initial block of data later in the file, and only considering
    # these offsets as possible widths.
    attempts = 0
    for offset in find_possible_repeat_widths(data):
        # The presence of the starting block at this offset means the data
        # could possibly be repeating again. If it is, return this width.
        if data_repeats_with_width(data, offset):
            return offset

        # There are some worst-case scenarios where the preformance of trying
        # widths returned by find_possible_repeat_widths() will be similar to
        # that of a brute force search, which is not feasible. If we find we've
        # hit our MAXIMUM_WIDTH_ATTEMPTS then we'll abort the search.
        attempts += 1
        if attempts == MAXIMUM_WIDTH_ATTEMPTS:
            return -1

    # When searching widths returned by find_possible_repeat_widths() we may
    # have missed repeats where the repeated data had size less than
    # SEARCH_BLOCK_SIZE. We can detected this specific scenario with a quick
    # check of the data at the end of the file.
    width = check_for_minimal_repeat_at_end(data)
    if width:
        return width

    # Reaching here means the data does not repeat after some number of bytes.
    return None


def main():
    """Command-line scanner for finding repeated byte patterns."""
    # Use argparse to provide a user interface and collect arguments.
    description = """
Determine whether a file consists of some smaller portion of data which is
repeated some number (possibly fractional) of times.
"""
    examples = """
usage examples:

    Check whether a file has a repeating property:
        repeated-bytes file.bin

    Require that the repeating data is at least 1024 bytes:
        repeated-bytes --min-repeated 1024 file.bin

    Require that the data is repeated at least twice:
        repeated-bytes --min-ratio 2.0 file.bin

    Don't abort a search if it is slow:
        repeated-bytes --force file.bin

    Write deduplicated data to disk:
        repeated-bytes --outpath deduped.bin
"""
    parser = argparse.ArgumentParser(
        description=description, epilog=examples, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("filepath", help="File to analyse.")

    help_text = "Minimum number of repeated bytes required to be displayed."
    parser.add_argument("--min-repeated", help=help_text, default=0)

    help_text = "Minimum repeat ratio required to be displayed."
    parser.add_argument("--min-ratio", help=help_text, default=1.0)

    help_text = "Don't abort poorly performing searches."
    parser.add_argument("--force", help=help_text, action="store_true")

    help_text = "Filepath where deduplicated data should be written."
    parser.add_argument("--outpath", help=help_text)

    args = parser.parse_args()

    # Don't abort a poorly performing search if the --force flag was provided.
    global MAXIMUM_WIDTH_ATTEMPTS
    if args.force:
        MAXIMUM_WIDTH_ATTEMPTS = None

    # Load in the given file.
    with open(args.filepath, "rb") as f:
        data = f.read()

    # Run our analysis.
    width = data_repeats(data)

    # No width was found.
    if width is None:
        return

    # Search was aborted due to poor performance. Report and hint that this
    # can be overridden with --force.
    if width == -1:
        print(args.filepath)
        print("\tSearch aborted due to poor performance. Try --force.")
        return

    # Successfully found a width.
    num_repeated_bytes = len(data) - width

    # If this repeat is less than a provided minimum number of bytes, do not
    # display it.
    if num_repeated_bytes < int(args.min_repeated):
        return

    # If the ratio of this repeated data is less then a provided minimum, do
    # not display it.
    repeat_ratio = len(data) / width
    if repeat_ratio < float(args.min_ratio):
        return

    # Display information about the repeat.
    print(args.filepath)
    print("\tFiles consists of %d bytes which repeat." % width)
    print("\tNumber of repeated bytes: %d" % num_repeated_bytes)
    print("\tRepeat ratio: %f" % repeat_ratio)

    # If an output path is provided, deduplicate the data and write to disk.
    if args.outpath:
        with open(args.outpath, "wb") as f:
            f.write(data[:width])
        print("\n\tDeduplicated data written to %s." % args.outpath)


if __name__ == "__main__":
    main()
