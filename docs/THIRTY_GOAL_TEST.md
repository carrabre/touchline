# 30-goal reel capacity

The local test renders 30 separate one-second goal clips from generated footage, with event labels and Titan instrumental music. It verifies all 30 clips reach the H.264/AAC output and validates the final duration. This tests rendering capacity, not automatic goal detection.

Selection regression tests also verify 30 detected goals and 30 manually added moments survive each 90 / 180 / 240-second target (1,050 seconds of selected footage), while excluded goals stay excluded.

Validation: 19 web/session/access tests passed; 13 media tests passed, with one optional real-recording test skipped because no source was specified. The generated 30-clip render is included in the passing tests.

Deletion regression tests cover all upload/processing/finished states, uploader ownership, worker revision invalidation, concurrency conflicts and multipart cleanup failure. Cleanup is scoped to the deleted game's own media prefix.
