import SwiftUI
import PhotosUI
import UniformTypeIdentifiers
import WebKit
import Security

struct PartPlan: Decodable { let number: Int; let url: String }
struct UploadPlan: Decodable { let chunkSize: Int; let parts: [PartPlan] }
struct RemoteMatch: Decodable { let id: String; let title: String; let status: String }
struct MatchResponse: Decodable { let match: RemoteMatch; let chunkSize: Int? }
struct UploadJob: Codable, Identifiable {
    var id: String; var title: String; var filename: String; var total: Int64
    var partCount: Int; var completed: Set<Int> = []; var phase: String = "Preparing"
    var message: String = ""; var completedInBackground: Int = 0
    var fraction: Double { partCount == 0 ? 0 : Double(completed.count) / Double(partCount) }
}
struct PickedVideo: Transferable {
    let url: URL
    static var transferRepresentation: some TransferRepresentation {
        FileRepresentation(contentType: .movie) { value in SentTransferredFile(value.url) } importing: { received in
            let ext = received.file.pathExtension.isEmpty ? "mov" : received.file.pathExtension
            let url = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + "." + ext)
            try FileManager.default.copyItem(at: received.file, to: url)
            return PickedVideo(url: url)
        }
    }
}

@MainActor final class UploadManager: NSObject, ObservableObject, URLSessionTaskDelegate, URLSessionDelegate {
    static let shared = UploadManager()
    static let base = URL(string: "https://touchline-two-zeta.vercel.app")!
    @Published var jobs: [UploadJob] = []
    @Published var preparing = false
    @Published var notice = ""
    var backgroundCompletion: (() -> Void)?
    private var pendingCallbacks = 0
    private var eventsDrained = false
    private var scheduling = Set<String>()
    private let fm = FileManager.default
    var root: URL { fm.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("Transfers", isDirectory: true) }
    private lazy var session: URLSession = {
        let config = URLSessionConfiguration.background(withIdentifier: "com.carrabre.touchline.transfers.v1")
        config.isDiscretionary = false
        config.sessionSendsLaunchEvents = true
        config.waitsForConnectivity = true
        config.allowsCellularAccess = true
        config.allowsExpensiveNetworkAccess = true
        config.allowsConstrainedNetworkAccess = false
        config.httpMaximumConnectionsPerHost = 2
        config.timeoutIntervalForResource = 7 * 24 * 60 * 60
        let queue = OperationQueue(); queue.maxConcurrentOperationCount = 1
        return URLSession(configuration: config, delegate: self, delegateQueue: queue)
    }()
    override init() {
        super.init()
        try? fm.createDirectory(at: root, withIntermediateDirectories: true, attributes: [.protectionKey: FileProtectionType.completeUntilFirstUserAuthentication])
        var protectedRoot = root; var values = URLResourceValues(); values.isExcludedFromBackup = true
        try? protectedRoot.setResourceValues(values)
        if let data = try? Data(contentsOf: root.appendingPathComponent("jobs.json")), let saved = try? JSONDecoder().decode([UploadJob].self, from: data) { jobs = saved }
        _ = session
        NotificationCenter.default.addObserver(forName: UIApplication.didEnterBackgroundNotification, object: nil, queue: .main) { [weak self] _ in Task { @MainActor in self?.audit("app-entered-background") } }
        Task { await refresh() }
    }
    func audit(_ message: String) {
        let line = "\(Date().timeIntervalSince1970) \(message)\n"
        let file = root.appendingPathComponent("transfer-audit.txt")
        if !fm.fileExists(atPath: file.path) { try? Data().write(to: file) }
        if let handle = try? FileHandle(forWritingTo: file) { _ = try? handle.seekToEnd(); try? handle.write(contentsOf: Data(line.utf8)); try? handle.close() }
    }
    private func persist() { if let data = try? JSONEncoder().encode(jobs) { try? data.write(to: root.appendingPathComponent("jobs.json"), options: .atomic) } }
    private func update(_ id: String, _ change: (inout UploadJob) -> Void) { if let i = jobs.firstIndex(where: {$0.id == id}) { change(&jobs[i]); persist() } }

    // The upload identity belongs to this app and never contains AWS credentials.
    func cookie() -> String? {
        let query: [String: Any] = [kSecClass as String:kSecClassGenericPassword, kSecAttrService as String:"touchline-session", kSecReturnData as String:true, kSecMatchLimit as String:kSecMatchLimitOne]
        var result: CFTypeRef?; guard SecItemCopyMatching(query as CFDictionary, &result) == errSecSuccess, let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }
    private func saveCookie(_ value: String) {
        let query: [String: Any] = [kSecClass as String:kSecClassGenericPassword, kSecAttrService as String:"touchline-session"]
        SecItemDelete(query as CFDictionary)
        var add = query; add[kSecValueData as String] = Data(value.utf8); add[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        SecItemAdd(add as CFDictionary, nil)
    }
    private func request(_ path: String, body: [String: Any]? = nil) async throws -> Data {
        var req = URLRequest(url: Self.base.appendingPathComponent("api/" + path)); req.timeoutInterval = 90
        if let cookie = cookie() { req.setValue(cookie, forHTTPHeaderField: "Cookie") }
        if let body = body { req.httpMethod = "POST"; req.httpBody = try JSONSerialization.data(withJSONObject: body); req.setValue("application/json", forHTTPHeaderField: "Content-Type") }
        let (data, response) = try await URLSession.shared.data(for: req)
        guard let response = response as? HTTPURLResponse else { throw URLError(.badServerResponse) }
        if let raw = response.value(forHTTPHeaderField: "Set-Cookie"), raw.hasPrefix("touchline_session=") { saveCookie(String(raw.split(separator: ";")[0])) }
        guard (200..<300).contains(response.statusCode) else {
            let message = (try? JSONSerialization.jsonObject(with: data) as? [String: Any])?["error"] as? String ?? "The upload service is unavailable. Try again."
            throw NSError(domain: "Touchline", code: response.statusCode, userInfo: [NSLocalizedDescriptionKey:message])
        }
        return data
    }
    func ensureSession() async throws { if cookie() == nil { _ = try await request("matches") } }
    func importVideo(_ input: URL, title: String) async {
        guard !preparing else { return }
        preparing = true; notice = "Preparing the video. Keep Touchline open until the background upload is ready."
        defer { preparing = false }
        var preparationID = ""
        do {
            try await ensureSession()
            let originalName = input.lastPathComponent
            let bytes = (try fm.attributesOfItem(atPath: input.path)[.size] as? NSNumber)?.int64Value ?? 0
            guard bytes > 0 && bytes <= 16 * 1024 * 1024 * 1024 else { throw NSError(domain:"Touchline",code:1,userInfo:[NSLocalizedDescriptionKey:"Choose a video between 1 byte and 16 GB."]) }
            let free = try root.resourceValues(forKeys: [.volumeAvailableCapacityForImportantUsageKey]).volumeAvailableCapacityForImportantUsage ?? 0
            guard free > bytes * 3 + 128 * 1024 * 1024 else { throw NSError(domain:"Touchline",code:2,userInfo:[NSLocalizedDescriptionKey:"Free more storage to prepare this background upload. iOS needs temporary space for file transfers."]) }
            let ext = input.pathExtension.lowercased(); let mime = ext == "mov" ? "video/quicktime" : ext == "webm" ? "video/webm" : "video/mp4"
            let data = try await request("matches", body:["title":String((title.isEmpty ? originalName : title).prefix(100)),"filename":originalName,"mime":mime,"size":bytes,"fingerprint":UUID().uuidString,"backgroundUpload":true])
            let created = try JSONDecoder().decode(MatchResponse.self, from:data)
            let chunk = created.chunkSize ?? 16 * 1024 * 1024; let count = Int((bytes + Int64(chunk) - 1) / Int64(chunk)); preparationID = created.match.id
            jobs.insert(UploadJob(id:created.match.id,title:created.match.title,filename:originalName,total:bytes,partCount:count),at:0); persist()
            let directory = root.appendingPathComponent(created.match.id)
            try fm.createDirectory(at: directory, withIntermediateDirectories:true, attributes:[.protectionKey:FileProtectionType.completeUntilFirstUserAuthentication])
            try await Task.detached(priority:.userInitiated) {
                let reader = try FileHandle(forReadingFrom:input); defer {try? reader.close()}
                for number in 1...count {
                    guard let part = try reader.read(upToCount:chunk), !part.isEmpty else {throw URLError(.cannotOpenFile)}
                    let file = directory.appendingPathComponent("part-\(number)")
                    try part.write(to:file, options:[.atomic, .completeFileProtectionUntilFirstUserAuthentication])
                }
            }.value
            await schedule(created.match.id)
        } catch {
            notice = error.localizedDescription
            if !preparationID.isEmpty {update(preparationID){$0.phase="Needs attention";$0.message="Preparation was interrupted. Remove the incomplete upload from your games and choose the video again."}}
        }
    }
    func schedule(_ id: String) async {
        guard !scheduling.contains(id) else {return}; scheduling.insert(id); defer{scheduling.remove(id)}
        do {
            let data = try await request("matches/\(id)/background-plan",body:[:]);let plan = try JSONDecoder().decode(UploadPlan.self,from:data)
            let current = await session.allTasks
            let active = Set(current.compactMap(\.taskDescription))
            for part in plan.parts {
                let tag="\(id):\(part.number)"; if active.contains(tag){continue}
                let file=root.appendingPathComponent(id).appendingPathComponent("part-\(part.number)")
                guard fm.fileExists(atPath:file.path), let url=URL(string:part.url) else {throw URLError(.fileDoesNotExist)}
                var req=URLRequest(url:url);req.httpMethod="PUT"
                let task=session.uploadTask(with:req,fromFile:file);task.taskDescription=tag
                #if DEBUG
                if ProcessInfo.processInfo.arguments.contains("--verify-background") {task.earliestBeginDate=Date().addingTimeInterval(25)}
                #endif
                task.resume()
            }
            let count=jobs.first{$0.id==id}?.partCount ?? 1
            let completed=Set(1...max(1,count)).subtracting(plan.parts.map(\.number))
            update(id){$0.phase=plan.parts.isEmpty ? "Processing" : "Uploading";$0.completed.formUnion(completed);$0.message="iOS is managing this upload. You can switch apps or lock the phone. Do not force-quit Touchline."}
            notice="Background upload is ready. You can leave Touchline now."
            audit("background-ready \(id) parts=\(plan.parts.count)")
        } catch {update(id){$0.phase="Needs attention";$0.message=error.localizedDescription};notice=error.localizedDescription}
    }
    func refresh() async {
        for job in jobs {
            do {
                let data=try await request("matches/\(job.id)");let remote=try JSONDecoder().decode(MatchResponse.self,from:data).match
                if remote.status != "uploading" {update(job.id){$0.phase=remote.status == "ready" ? "Ready" : remote.status == "failed" ? "Needs attention" : "Processing";$0.completed=Set(1...max(1,$0.partCount));$0.message="The recording is on AWS. You can leave the app."};try? fm.removeItem(at:root.appendingPathComponent(job.id))}
            } catch {
                if (error as NSError).domain=="Touchline" && (error as NSError).code==404 {
                    update(job.id){$0.phase="Removed";$0.message="This game was removed from the library."}
                    for task in await session.allTasks where task.taskDescription?.hasPrefix(job.id+":")==true {task.cancel()}
                    try? fm.removeItem(at:root.appendingPathComponent(job.id))
                }
            }
        }
    }
    nonisolated func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        let tag=task.taskDescription ?? "";let status=(task.response as? HTTPURLResponse)?.statusCode ?? 0
        DispatchQueue.main.async {
            let pair=tag.split(separator:":");guard pair.count==2,let number=Int(pair[1]) else{return};let id=String(pair[0]);if self.jobs.first(where:{$0.id==id})?.phase=="Removed"{return}
            let inactive=UIApplication.shared.applicationState != .active
            if error == nil && (200..<300).contains(status) {
                self.update(id){$0.completed.insert(number);if inactive{$0.completedInBackground+=1};if $0.completed.count == $0.partCount{$0.phase="Processing";$0.message="Uploaded. AWS will finalize and process the video without the app."}}
                try? self.fm.removeItem(at:self.root.appendingPathComponent(id).appendingPathComponent("part-\(number)"))
                self.audit("part-complete \(id) \(number) inactive=\(inactive)")
            } else {self.notice="Upload needs attention. Saved parts can be retried.";self.update(id){$0.phase="Needs attention";$0.message="Transfer interrupted. Tap Resume to retry saved parts."};self.audit("part-error \(id) \(number) status=\(status) domain=\((error as NSError?)?.domain ?? "none") code=\((error as NSError?)?.code ?? 0) message=\(error?.localizedDescription ?? "none")")}
        }
    }
    nonisolated func urlSessionDidFinishEvents(forBackgroundURLSession session: URLSession) {
        DispatchQueue.main.async {self.eventsDrained=true;self.finishBackgroundEvents()}
    }
    func finishBackgroundEvents(){if eventsDrained && pendingCallbacks==0 {eventsDrained=false;let handler=backgroundCompletion;backgroundCompletion=nil;handler?()}}
}

final class AppDelegate: NSObject, UIApplicationDelegate {
    func application(_ application: UIApplication, handleEventsForBackgroundURLSession identifier: String, completionHandler: @escaping () -> Void) {
        UploadManager.shared.backgroundCompletion=completionHandler
    }
}
struct GameView: UIViewRepresentable {
    let cookie:String?; let id:String?
    func makeUIView(context:Context)->WKWebView{
        let view=WKWebView();var address=UploadManager.base
        if let id=id {var c=URLComponents(url:address,resolvingAgainstBaseURL:false)!;c.queryItems=[URLQueryItem(name:"match",value:id)];address=c.url!}
        let request=URLRequest(url:address)
        if let raw=cookie,let value=raw.split(separator:"=",maxSplits:1).last,let c=HTTPCookie(properties:[.name:"touchline_session",.value:String(value),.domain:address.host!,.path:"/",.secure:"TRUE",.expires:Date().addingTimeInterval(365*24*60*60)]) {
            view.configuration.websiteDataStore.httpCookieStore.setCookie(c){view.load(request)}
        }else{view.load(request)}
        return view
    }
    func updateUIView(_ uiView:WKWebView,context:Context){}
}
struct LibraryTarget:Identifiable{let id:String}
struct ContentView: View {
    @StateObject private var uploads=UploadManager.shared
    @Environment(\.scenePhase) private var scenePhase
    @State private var photo:PhotosPickerItem?
    @State private var files=false
    @State private var title=""
    @State private var game:LibraryTarget?
    let lime=Color(red:0.86,green:1,blue:0.47)
    var body:some View {
        NavigationStack {
            ScrollView {
                VStack(alignment:.leading,spacing:24) {
                    Text("Every game.\nEvery goal.").font(.system(size:40,weight:.semibold)).foregroundStyle(.white)
                    TextField("Match title",text:$title).textFieldStyle(.roundedBorder).accessibilityLabel("Match title")
                    PhotosPicker(selection:$photo,matching:.videos){Label("Choose from Photos",systemImage:"photo.on.rectangle")}.buttonStyle(.borderedProminent).tint(lime).foregroundStyle(.black).disabled(uploads.preparing)
                    Button {files=true} label:{Label("Choose video file",systemImage:"folder")}.buttonStyle(.bordered).disabled(uploads.preparing)
                    if !uploads.notice.isEmpty{Text(uploads.notice).font(.callout).foregroundStyle(lime).accessibilityIdentifier("upload-notice")}
                    Text("Wait for ‘Background upload is ready’, then switch apps or lock your phone. iOS controls timing. Force-quitting the app stops its transfers.").font(.footnote).foregroundStyle(.secondary)
                    ForEach(uploads.jobs){job in
                        VStack(alignment:.leading,spacing:12){
                            Text(job.title).font(.headline)
                            Text(job.phase).foregroundStyle(lime)
                            ProgressView(value:job.fraction).tint(lime)
                            Text("\(job.completed.count) of \(job.partCount) parts saved").font(.caption).monospacedDigit()
                            Text(job.message).font(.caption).foregroundStyle(.secondary)
                            if job.phase=="Needs attention"{Button("Resume upload"){Task{await uploads.schedule(job.id)}}}
                            Button("View game"){game=LibraryTarget(id:job.id)}
                        }.padding(20).frame(maxWidth:.infinity,alignment:.leading).background(.white.opacity(0.05),in:RoundedRectangle(cornerRadius:18))
                    }
                }.padding(24).frame(maxWidth:700)
            }.background(Color(red:0.047,green:0.055,blue:0.055)).navigationTitle("⚽ Touchline").navigationBarTitleDisplayMode(.inline)
            .toolbar{Button("All games"){game=LibraryTarget(id:"")}}
            .fileImporter(isPresented:$files,allowedContentTypes:[.movie,.video]){result in
                if case let .success(url)=result{let access=url.startAccessingSecurityScopedResource();Task{await uploads.importVideo(url,title:title);if access{url.stopAccessingSecurityScopedResource()}}}
            }
            .onChange(of:scenePhase){_,phase in if phase == .active {Task{await uploads.refresh()}}}
            .onChange(of:photo){_,item in Task{do{if let video=try await item?.loadTransferable(type:PickedVideo.self){await uploads.importVideo(video.url,title:title);try? FileManager.default.removeItem(at:video.url)}}catch{uploads.notice=error.localizedDescription}}}
            .sheet(item:$game){target in GameView(cookie:uploads.cookie(),id:target.id.isEmpty ? nil:target.id).ignoresSafeArea(edges:.bottom)}
            .task{
                #if DEBUG
                if ProcessInfo.processInfo.arguments.contains("--verify-background") && !uploads.jobs.isEmpty {await uploads.schedule(uploads.jobs[0].id)}
                if ProcessInfo.processInfo.arguments.contains("--verify-background") && uploads.jobs.isEmpty {
                    let file=FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0].appendingPathComponent("Verification/input.mp4")
                    if FileManager.default.fileExists(atPath:file.path){await uploads.importVideo(file,title:"Background transfer verification")}
                }
                #endif
            }
        }.preferredColorScheme(.dark)
    }
}
@main struct TouchlineApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var delegate
    var body:some Scene{WindowGroup{ContentView()}}
}
