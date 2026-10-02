# Operating cost estimates — unmeasured

No autonomous full-match detection passed verification, so these are scenario estimates, not observed bills. No services were purchased or paid plans upgraded. New dedicated storage/table resources use standard usage billing in the existing AWS account. Existing compute was inspected but no new instance was launched.

Using AWS's documented approximate **288 video input tokens per sampled frame** and the planned 1 fps scout / effective 2 fps deep review:

- 90 minutes, with 10-second overlap: about **1.65M Lite input tokens**.
- 120 minutes: about **2.20M Lite input tokens**.
- Deep review: every goal/possible-goal candidate plus up to 40 optional action candidates. At 40 reviews: 40 × 48 slowed seconds × 288 ≈ **0.553M Pro input tokens**. Each additional goal review adds roughly 13,824 input tokens; there is no 40-goal cap.
- Illustrative rate assumptions: Lite $0.06 / $0.24 per million input/output tokens; Pro $0.80 / $3.20. These are planning assumptions pending confirmation against the selected account/region's current price list. Actual usage is recorded on each match.
- Model subtotal for an illustrative 40-review run: about **$0.60–$0.75 per match**, allowing 30–45k Lite output tokens and 40–60k Pro output tokens. Fewer candidates cost less; extra goal candidates and retries increase cost. Shorter and larger prompt output lengths change these amounts.
- Storage assumption: $0.023/GB-month for S3 Standard. The actual 0.528 GB 90-minute asset plus a 0.1 GB reel is around **$0.015/month while retained**. A 10 GB source plus reel is around **$0.24/month**. Each regenerated reel also remains stored until deletion.
- Preview/download transfer, S3 requests and DynamoDB requests are additional. Illustrative outbound assumption $0.09/GB after any account-wide allowance: streaming a full 10 GB game once can cost around **$0.90**. Do not treat inference as the entire operating cost.
- Compute is shared with an already-running host. Marginal hourly host billing is unchanged if its running duration stays unchanged, but this is **not free compute**: the app consumes part of a paid instance's capacity. Processing time is not measured, so an allocated per-match compute cost cannot honestly be calculated yet. New dedicated compute would need a separate cost decision.
- Hosting uses the existing Sites environment. Its account allowances and metering were not measured here.

Pricing reference: https://aws.amazon.com/bedrock/pricing/ and https://aws.amazon.com/s3/pricing/
Token assumptions: https://docs.aws.amazon.com/nova/latest/userguide/modalities-video.html

After production tests, replace planning numbers with `metrics.modelUsage`, `analysisSeconds`, `renderSeconds`, output sizes and attributable AWS charges.
