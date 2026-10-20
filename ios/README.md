# Touchline iPhone uploader

Native SwiftUI companion for videos in Photos or Files. Uses a background URLSession with durable, file-backed multipart uploads. Wait for **Background upload is ready**, then switch apps or lock the device. iOS controls scheduling, connectivity and battery policy; it does not promise immediate transfer. Force-quitting cancels transfers until the app is reopened. A website or home-screen shortcut does not provide this native capability.

## Build / install

Requires Xcode 16.2+, iOS 17+, and XcodeGen. Run `xcodegen generate --spec ios/project.yml`, open `ios/TouchlineUploader.xcodeproj`, select your Apple development team and connected iPhone, and run the TouchlineUploader scheme. Device installation needs a valid signing profile, a trusted/unlocked device and Developer Mode. This is source/build delivery, not an App Store or TestFlight release.

## Transfer design

- The app creates its own signed Touchline session and stores it in the device Keychain. Its embedded game view uses the same identity so edits/deletion work. Existing Safari uploads retain their separate browser identity.
- Original file is read into 16 MB disk parts. Staging needs temporary free storage; keep the app foreground until all transfers have been handed to iOS. Parts use protection that remains accessible after the first device unlock. Transfer files are excluded from backups.
- Owner-only `/background-plan` returns PUT URLs for missing parts, scoped to one upload and valid for up to seven days. Resume refreshes URLs and skips parts already in S3. Local task descriptions and jobs survive process relaunch. Failed preparation requires selecting the source again.
- AWS worker verifies part numbers, exact sizes, source length and revision/stage before completing and queueing a native upload. No phone `/finish` request is required. Existing website uploads and browser recording are unchanged.
- Keep API/worker contracts backward compatible. Worker deployment must include `background_uploads.py`; web `main` alone does not deploy it. No AWS credentials are bundled in the app.

## Verification

`xcodebuild -project ios/TouchlineUploader.xcodeproj -scheme TouchlineUploader -sdk iphonesimulator -configuration Debug CODE_SIGNING_ALLOWED=NO build` validates the simulator build. Backend tests cover ownership, missing parts, interrupted completion and deletion races.

The debug-only `--verify-background` launch argument reads only `Documents/Verification/input.mp4`, stages a test upload, and delays the earliest transfer start by 25 seconds so the app can be backgrounded first. Transfer audit records are local and contain no credentials. Confirm the source object and processing state in production, compare byte hashes, and record native background events. Simulator results do not establish locked-device behavior on a physical iPhone. A physical-device test must leave the app and lock the phone until AWS confirms completion.
