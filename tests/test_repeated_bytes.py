import unittest

from azul_plugin_repeated_bytes.repeated_bytes import (
    SEARCH_BLOCK_SIZE,
    check_for_minimal_repeat_at_end,
    data_repeats,
    data_repeats_exactly_n_times,
    data_repeats_exactly_n_times_recursive,
    data_repeats_with_width,
    find_possible_repeat_widths,
)


class TestRepeat(unittest.TestCase):
    def test_data_repeats_exactly_n_times(self):
        """
        Ensure that this core function correctly validates when some data
        repeats the given number of times.
        """
        alphabet = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        examples = []
        for i in range(1, len(alphabet) + 1):
            examples.append((alphabet[:i] * 1024, 1024, i))

        for data, repeats, size in examples:
            # Ensure we correctly validate the expected number of repeats.
            self.assertTrue(data_repeats_exactly_n_times(data, repeats))

            # Add a byte which breaks the repetition and ensure we report False.
            self.assertFalse(data_repeats_exactly_n_times(data + b"1", repeats))

            # Ensure we report False if we ask for the wrong repeat size.
            self.assertFalse(data_repeats_exactly_n_times(data, repeats + 1))

    def test_data_repeats_exactly_n_times_coarse(self):
        """
        Ensure that we can us data_repeats_exactly_n_times() with values of
        <n> which are multiples of the true repeating width.
        """
        # True repeating width is 2, but we should also report true for
        # "coarser" comparisons.
        data = "ABABABABABABABABABABABABABABABAB"
        self.assertTrue(data_repeats_exactly_n_times(data, 2))
        self.assertTrue(data_repeats_exactly_n_times(data, 4))
        self.assertTrue(data_repeats_exactly_n_times(data, 8))
        self.assertTrue(data_repeats_exactly_n_times(data, 16))

        # Ensure that we aren't just returning True for everything...
        for i in [3, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15]:
            self.assertFalse(data_repeats_exactly_n_times(data, i))

    def test_data_repeats_exactly_n_times_recursive(self):
        """
        Check that our recursive approach (which will just call our core
        function in smarter ways) still correctly validates the correct widths.
        """
        alphabet = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        examples = []
        for i in range(1, len(alphabet) + 1):
            examples.append((alphabet[:i] * 1024, 1024, i))
        for data, repeats, size in examples:
            # Ensure we correctly validate the expected number of repeats.
            self.assertTrue(data_repeats_exactly_n_times_recursive(data, repeats))

        data = b"\x00" * 2 * 3 * 5 * 7 * 11 * 13
        self.assertTrue(data_repeats_exactly_n_times_recursive(data, 2 * 3 * 5 * 7 * 11 * 13))

        # Try a big prime. This should just result in one call to our base
        # function.
        data = b"\x00" * 65537
        self.assertTrue(data_repeats_exactly_n_times_recursive(data, 65537))

    def test_data_repeats_with_width(self):
        """
        Ensure that we correctly detect when data is repeating with a given
        width.
        """
        # Check a wide range of small widths.
        for width in range(1, 100):
            # Do 10 repeats, then slice bytes off the end to ensure that
            # fractional repeats don't throw us off.
            data = bytes(range(width)) * 10
            for i in range(width):
                data = data[:-1]
                self.assertTrue(data_repeats_with_width(data, width))

        # Check a larger width. Roughly a megabyte of data, then it starts to
        # repeat again.
        start = "Starts like this."
        end = "The end!"
        data = start + "\x00" * 1024 * 1024 + end
        core_length = len(data)

        # Throw the starting data onto the end.
        data += start

        # Check we correctly detect the data repeats after the core data.
        self.assertTrue(data_repeats_with_width(data, core_length))

    def test_find_possible_repeat_widths(self):
        """
        Ensure that find_possible_repeat_widths() doesn't suggest widths
        which are inconsistent with the data from the start of the file.
        """
        # Make a 100KB of zeroes, with some interesting data at the start.
        start_block = bytes(range(SEARCH_BLOCK_SIZE))
        data = bytearray(100 * 1024)
        data[:SEARCH_BLOCK_SIZE] = start_block

        # Insert the same interesting data at a few other offsets.
        offsets = [42, 420, 666, 1337, 2020, 31337]
        for offset in offsets:
            data[offset : offset + SEARCH_BLOCK_SIZE] = start_block

        # Ensure that find_possible_repeat_widths() is going to only suggest
        # widths consistent with the appearance of our starting data.
        results = list(find_possible_repeat_widths(data))
        self.assertEqual(results, offsets)

    def test_check_for_minimal_repeat_at_end(self):
        """
        check_for_minimal_repeat_at_end() exists to detect very specific
        scenarios.
            - The data repeats < 2 times (a fraction is repeated).
            - The size of that fraction is < SEARCH_BLOCK_SIZE bytes.
        """
        # Actual data from 2 bytes up to SEARCH_BLOCK_SIZE
        for core_size in range(2, SEARCH_BLOCK_SIZE + 1):
            # We'll repeat part of it, with every size from a single byte to
            # one byte short of the full data.
            for repeat_size in range(1, core_size):
                # Build the test data.
                core_data = bytes(range(core_size))
                repeat_data = core_data[:repeat_size]
                full_data = core_data + repeat_data

                # Check that we correctly determine the width of the core data.
                width = check_for_minimal_repeat_at_end(full_data)
                self.assertEqual(width, len(core_data))

    def test_data_repeats(self):
        """
        This is the main function our package implements, so we'll throw a
        comprehensive number of examples at it to ensure its behaviour is as
        we expect.
        """
        # Going to try every possible size of data from 1 -> 3 * SEARCH_BLOCK_SIZE.
        for core_size in range(1, SEARCH_BLOCK_SIZE * 3):
            for full_size in range(core_size, core_size * 3):
                data = bytes(range(core_size))
                full_data = bytes(data[i % len(data)] for i in range(full_size))

                # Ensure that the width data_repeats() finds matched that which
                # we built.
                found_width = data_repeats(full_data)

                # When full_size == core_size our data has no repeats, so we
                # should expect to get None back
                if full_size == core_size:
                    self.assertEqual(found_width, None)
                # Otherwise, we want expect to get core_size back.
                else:
                    self.assertEqual(found_width, core_size)


if __name__ == "__main__":
    unittest.main()
