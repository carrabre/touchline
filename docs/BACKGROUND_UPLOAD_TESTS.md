# Background upload verification

Production API and AWS worker are deployed. Native uploader source is in `ios/`.

- Signed iOS simulator app scheduled six file-backed background PUT transfers for an 85,750,201-byte video. After transfer handoff, the uploader process was suspended with SIGSTOP. S3 initially had zero completed parts. All six parts arrived while the process remained stopped. AWS completed the multipart object and advanced the job to analysis without an app `/finish` request. Source multipart ETag integrity matched all six original file chunks.
- A separate production API client uploaded part 1, verified incomplete uploads stayed pending and retry plans skipped that part, uploaded parts 2–6, then exited without calling `/finish`. AWS finalized, analyzed and rendered that video. The stored source SHA256 matched the local input.
- 28 web tests and 18 media/completion tests passed; one optional media test skipped. Signed native simulator build, development-signed physical-device build and production web build passed. The unavailable iPhone is registered in the development profile. The locally packaged IPA is a development build, not a public distribution release.
- Initial unsigned simulator build could not connect to the background-transfer daemon. Ad-hoc signing resolved this; the subsequent production transfer passed. The final workflow uses signed simulator builds.

**Limits:** This verifies out-of-process simulator transfers against production and autonomous AWS completion. Simulator UI control timed out, so switching apps through the UI was not verified. The physical iPhone was unavailable; lock-screen transfers, real-device relaunch and installation are not certified. The website itself still requires staying open during iPhone file transfer. A native app must be installed for this background capability. No claim of completed physical-device testing or App Store/TestFlight publication is made.

Structured results: [BACKGROUND_UPLOAD_RESULTS.json](BACKGROUND_UPLOAD_RESULTS.json). Native build, install and operating instructions: [ios/README.md](../ios/README.md).
