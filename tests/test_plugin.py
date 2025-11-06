import unittest

from azul_runner import (
    FV,
    Event,
    EventData,
    EventParent,
    JobResult,
    State,
    test_template,
)

from azul_plugin_repeated_bytes.main import AzulPluginRepeatedBytes


class TestRepeatedBytes(test_template.TestPlugin):
    PLUGIN_TO_TEST = AzulPluginRepeatedBytes

    def test_not_repeated(self):
        # Basic test, run our plugin on some data which does not repeat and
        # ensure no features are produced.

        result = self.do_execution(data_in=[("content", b"Not repeating.")])
        self.assertJobResult(result, JobResult(state=State(State.Label.COMPLETED_EMPTY)))

        result = self.do_execution(data_in=[("content", b"Amost repeats...Almost reheats...")])
        self.assertJobResult(result, JobResult(state=State(State.Label.COMPLETED_EMPTY)))

        result = self.do_execution(data_in=[("content", b"ABCDEDFGH" * 100 + b"Z")])
        self.assertJobResult(result, JobResult(state=State(State.Label.COMPLETED_EMPTY)))

    def test_single_byte(self):
        result = self.do_execution(data_in=[("content", b"A" * 119)])
        self.assertJobResult(
            result,
            JobResult(
                state=State(State.Label.COMPLETED),
                events=[
                    Event(
                        entity_type="binary",
                        entity_id="17d2f0f7197a6612e311d141781f2b9539c4aef7affd729246c401890e000dde",
                        features={
                            "rep_byte_data": [FV("A")],
                            "rep_byte_data_size": [FV(1)],
                            "rep_byte_excess_size": [FV(118)],
                            "rep_byte_ratio": [FV(119.0)],
                            "tag": [FV("repeated_bytes")],
                        },
                    )
                ],
            ),
        )

    def test_multi_byte(self):
        result = self.do_execution(data_in=[("content", b"A\xaeB" * 41)])
        self.assertJobResult(
            result,
            JobResult(
                state=State(State.Label.COMPLETED),
                events=[
                    Event(
                        entity_type="binary",
                        entity_id="b6bdab3f569b588a55c2db89a67fdb47e2ba2e9f7e05ff2d361b7bdde4849df1",
                        features={
                            "rep_byte_data": [FV("A\\xaeB")],
                            "rep_byte_data_size": [FV(3)],
                            "rep_byte_excess_size": [FV(120)],
                            "rep_byte_ratio": [FV(41.0)],
                            "tag": [FV("repeated_bytes")],
                        },
                    )
                ],
            ),
        )

    def test_nulls(self):
        result = self.do_execution(data_in=[("content", b"\x00" * 115)])
        self.assertJobResult(
            result,
            JobResult(
                state=State(State.Label.COMPLETED),
                events=[
                    Event(
                        entity_type="binary",
                        entity_id="23cd67852af04fd6885d2763266f2765b5e03c6ae3a5c1c6c95f7e03e10ec10d",
                        features={
                            "rep_byte_data": [FV("\\x00")],
                            "rep_byte_data_size": [FV(1)],
                            "rep_byte_excess_size": [FV(114)],
                            "rep_byte_ratio": [FV(115.0)],
                            "tag": [FV("repeated_bytes")],
                        },
                    )
                ],
            ),
        )

    def test_insignificant_repeats(self):
        # Test on some fake data that we ignore "insignificant" repeats as
        # defined by minimum repeat ratios and minimum repeated byte counts
        # in our plugin.

        # Exceeds the minimum ratio, but not minimum number of repeated bytes.
        data = bytes([x for x in range(100)]) + bytes([x for x in range(60)])
        result = self.do_execution(data_in=[("content", data)])
        self.assertJobResult(result, JobResult(state=State(State.Label.COMPLETED_EMPTY)))

        # Exceeds the minimum repeated bytes, but not the required ratio.
        data = bytes([x & 0xFF for x in range(1000)])
        data += bytes([x & 0xFF for x in range(100)])
        result = self.do_execution(data_in=[("content", data)])
        self.assertJobResult(result, JobResult(state=State(State.Label.COMPLETED_EMPTY)))

    def test_insignificant_repeating_exe(self):
        # Test on a sample PE which just happens to end with the byte 'M'.
        # Ensure we generate no features for this trivial repetition.
        sample_data = self.load_test_file_bytes(
            "307fbb2f7752019ed8e1f9649c170463f994c7712df1c9e875141fb215ca4a11",
            "Malicious Windows 32EXE, Ends on an M byte.",
        )
        result = self.do_execution(data_in=[("content", sample_data)])
        self.assertJobResult(result, JobResult(state=State(State.Label.COMPLETED_EMPTY)))

    def test_partially_repeating_exe(self):
        # This sample from VirusShare is a PE file which repeats partially after
        # The first occurrence (about 74%).
        partial_repeat = self.load_test_file_bytes(
            "dca477353494231daacb83a0e8d8696bc8409ba2e8940a47d6518285d1fb4dc7",
            "Malicious Windows 32EXE, with lots of repeating sections.",
        )
        result = self.do_execution(data_in=[("content", partial_repeat)])
        self.assertJobResult(
            result,
            JobResult(
                state=State(State.Label.COMPLETED),
                events=[
                    Event(
                        entity_type="binary",
                        entity_id="dca477353494231daacb83a0e8d8696bc8409ba2e8940a47d6518285d1fb4dc7",
                        features={
                            "rep_byte_data_size": [FV(33051)],
                            "rep_byte_excess_size": [FV(24363)],
                            "rep_byte_ratio": [FV(1.7371335209222112)],
                            "tag": [FV("repeated_bytes")],
                        },
                    ),
                    Event(
                        parent=EventParent(
                            entity_type="binary",
                            entity_id="dca477353494231daacb83a0e8d8696bc8409ba2e8940a47d6518285d1fb4dc7",
                        ),
                        entity_type="binary",
                        entity_id="d49a38e4c2b9103a7f53c6caab8d939c112063184dfd99c80a15095824022a2b",
                        relationship={"label": "deduplicated"},
                        data=[
                            EventData(
                                hash="d49a38e4c2b9103a7f53c6caab8d939c112063184dfd99c80a15095824022a2b",
                                label="content",
                            )
                        ],
                    ),
                ],
                data={"d49a38e4c2b9103a7f53c6caab8d939c112063184dfd99c80a15095824022a2b": b""},
            ),
        )

    def test_fully_repeating_exe(self):
        # This sample from VirusShare is a PE file which repeats fully after
        # The first occurrence i.e. a 'doubled' file.
        full_repeat = self.load_test_file_bytes(
            "e547815b6547e0652b57b596b42078914f158579f21b6682b54fd0630b08f62d",
            "Malicious Windows 32EXE, repeats fully after it's first occurrence i.e. a 'doubled' file",
        )
        result = self.do_execution(data_in=[("content", full_repeat)])
        self.assertJobResult(
            result,
            JobResult(
                state=State(State.Label.COMPLETED),
                events=[
                    Event(
                        entity_type="binary",
                        entity_id="e547815b6547e0652b57b596b42078914f158579f21b6682b54fd0630b08f62d",
                        features={
                            "rep_byte_data_size": [FV(11584)],
                            "rep_byte_excess_size": [FV(11584)],
                            "rep_byte_ratio": [FV(2.0)],
                            "tag": [FV("repeated_bytes")],
                        },
                    ),
                    Event(
                        parent=EventParent(
                            entity_type="binary",
                            entity_id="e547815b6547e0652b57b596b42078914f158579f21b6682b54fd0630b08f62d",
                        ),
                        entity_type="binary",
                        entity_id="65ae9cdf1eb7ec0214e984698469fd7b0006491288e690cff9f6c719f1a74ffd",
                        relationship={"label": "deduplicated"},
                        data=[
                            EventData(
                                hash="65ae9cdf1eb7ec0214e984698469fd7b0006491288e690cff9f6c719f1a74ffd",
                                label="content",
                            )
                        ],
                    ),
                ],
                data={"65ae9cdf1eb7ec0214e984698469fd7b0006491288e690cff9f6c719f1a74ffd": b""},
            ),
        )

    def test_poor_performance_case(self):
        # Run our plugin on data which will cause the repeated-bytes package
        # to terminate due to poor performance. This will cause it return a
        # width of -1, and we need to ensure azul-repeated-bytes handles this
        # correctly and doesn't generate any features.
        data = b"\x00" * 2048 + b"A"
        result = self.do_execution(data_in=[("content", data)])
        self.assertJobResult(result, JobResult(state=State(State.Label.COMPLETED_EMPTY)))


if __name__ == "__main__":
    unittest.main()
