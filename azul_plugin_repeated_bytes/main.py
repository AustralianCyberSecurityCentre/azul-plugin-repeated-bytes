"""Find smaller portion of data which repeats after its first occurrence.

The original logic has been expanded to search for arbitrary widths.
"""

from azul_runner import BinaryPlugin, Feature, Job, cmdline_run

from azul_plugin_repeated_bytes.repeated_bytes import data_repeats

# To prevent featuring meaningless repetitions (such as a PE file that ends
# with the character 'M') we must meet one of these two thresholds.
MIN_BYTES_REPEATED = 64
MIN_RATIO = 1.25

# This will decide whether we feature a string representation of the core data,
# or instead insert it as "deduplicated" child.
MAX_STRING_FEATURE_SIZE = 32


class AzulPluginRepeatedBytes(BinaryPlugin):
    """Find smaller portion of data which repeats after its first occurrence."""

    VERSION = "2024.04.29"
    FEATURES = [
        Feature("rep_byte_data", "Representation of the core data which is repeated.", str),
        Feature("rep_byte_data_size", "Size of the core data which is repeated.", int),
        Feature("rep_byte_excess_size", "Size of the excess, repeated data.", int),
        Feature("rep_byte_ratio", "Ratio of the total size to the size of the core data.", float),
        Feature("tag", "Tags to set on this entity", str),
    ]

    def execute(self, job: Job):
        """Run across data searching for repeated patterns."""
        # Read in the sample data, and use the repeated_bytes package to detect
        # repetition.
        data = job.get_data()
        sample_data = data.read()
        width = data_repeats(sample_data)

        # If no repetition was discovered, return no features.
        if not width:
            return

        # If the search was aborted due to poor performance, return no features.
        if width == -1:
            return

        # The number of repeated bytes following the unique portion.
        num_repeated_bytes = len(sample_data) - width

        # The ratio of the entire size to the size of the unique portion.
        repeat_ratio = len(sample_data) / width

        # If the repetition didn't meet EITHER of our configured thresholds,
        # return no features. These help to ensure that we only feature
        # meaningful repetition and not for example a PE file whose final byte
        # is an 'M' etc.
        if repeat_ratio < MIN_RATIO or num_repeated_bytes < MIN_BYTES_REPEATED:
            return {}

        features = {
            "rep_byte_data_size": width,
            "rep_byte_excess_size": num_repeated_bytes,
            "rep_byte_ratio": repeat_ratio,
            "tag": "repeated_bytes",
        }

        # Carve out the unique portion, removing any repetition.
        deduplicated = sample_data[:width]

        # If the size is small enough we'll feature a hex representation of the
        # data, otherwise we'll add the data as a child.
        if len(deduplicated) <= MAX_STRING_FEATURE_SIZE:
            # Use repr() to get a reasonable representation that will include
            # readable ascii if any should be present. The string slicing is to
            # remove the byte indicator and quotes from the resulting string.
            # e.g. "b'\x00\x01'" -> "\x00\x01"
            features["rep_byte_data"] = repr(deduplicated)[2:-1]

        else:
            self.add_child_with_data({"label": "deduplicated"}, deduplicated)

        # Return our features.
        self.add_many_feature_values(features)


def main():
    """Run plugin via command-line."""
    cmdline_run(plugin=AzulPluginRepeatedBytes)


if __name__ == "__main__":
    main()
