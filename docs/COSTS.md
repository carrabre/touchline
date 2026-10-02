# Operating cost estimates — unmeasured

No autonomous full-match detection passed verification, so these are scenario estimates, not observed bills. No services were purchased or paid plans upgraded. New dedicated storage/table resources use standard usage billing in the existing AWS account. Existing compute was inspected but no new instance was launched.

The current detector uses Amazon Nova 2 Lite for the full-match goal scan and separate candidate reviews. Both passes use the same model with different prompts. It samples video at 1 fps; half-speed review provides an effective 2 fps on original footage. The tested match's actual usage is recorded in the validation report; token usage is measured, the billed charge is not. Earlier Lite/Pro price assumptions do not apply to this detector. See AWS's current regional pricing before estimating future charges.

- 90-minute scan with overlap: approximately 1.4–1.7M input tokens depending on preprocessing and prompts.
- Every candidate is reviewed over up to 128 slowed seconds. Candidate counts and retry counts determine additional usage; no goal-candidate cap applies.
- Storage assumption: $0.023/GB-month for S3 Standard. The actual 0.528 GB 90-minute asset plus a 0.1 GB reel is around **$0.015/month while retained**. A 10 GB source plus reel is around **$0.24/month**. Each regenerated reel also remains stored until deletion.
- Preview/download transfer, S3 requests and DynamoDB requests are additional. Illustrative outbound assumption $0.09/GB after any account-wide allowance: streaming a full 10 GB game once can cost around **$0.90**. Do not treat inference as the entire operating cost.
- Compute is shared with an already-running host. Marginal hourly host billing is unchanged if its running duration stays unchanged, but this is **not free compute**: the app consumes part of a paid instance's capacity. Processing time is not measured, so an allocated per-match compute cost cannot honestly be calculated yet. New dedicated compute would need a separate cost decision.
- Hosting uses the existing Sites environment. Its account allowances and metering were not measured here.

Pricing reference: https://aws.amazon.com/bedrock/pricing/ and https://aws.amazon.com/s3/pricing/
Token assumptions: https://docs.aws.amazon.com/nova/latest/nova2-userguide/using-multimodal-models.html

After production tests, replace planning numbers with `metrics.modelUsage`, `analysisSeconds`, `renderSeconds`, output sizes and attributable AWS charges.
