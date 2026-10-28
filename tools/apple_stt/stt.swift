// Mac'in cihaz içi Türkçe konuşma tanıması (ücretsiz, internetsiz, kotasız).
// Kullanım: apple_stt [ad1,ad2,...]  → stdin'den satır satır wav yolu okur, her biri için tek satır metin yazar.
// Kalıcı çalışır (her komutta açılış beklemesi olmasın). Hata satırı "!" ile başlar.
import Foundation
import Speech

setvbuf(stdout, nil, _IOLBF, 0)
let names = CommandLine.arguments.count > 1 ? CommandLine.arguments[1].split(separator: ",").map { String($0).trimmingCharacters(in: .whitespaces) } : []

let auth = DispatchSemaphore(value: 0)
var status = SFSpeechRecognizerAuthorizationStatus.notDetermined
SFSpeechRecognizer.requestAuthorization { s in status = s; auth.signal() }
auth.wait()
guard status == .authorized else { print("!izin yok: Sistem Ayarları > Gizlilik > Konuşma Tanıma"); exit(2) }
guard let rec = SFSpeechRecognizer(locale: Locale(identifier: "tr-TR")), rec.supportsOnDeviceRecognition else {
    print("!tr-TR cihazda yok"); exit(3)
}
rec.queue = OperationQueue()
print("hazır")

while let path = readLine() {
    let req = SFSpeechURLRecognitionRequest(url: URL(fileURLWithPath: path))
    req.requiresOnDeviceRecognition = true
    req.shouldReportPartialResults = false
    req.addsPunctuation = true
    req.contextualStrings = names
    let done = DispatchSemaphore(value: 0)
    var out = ""
    let task = rec.recognitionTask(with: req) { res, err in
        if let r = res, r.isFinal { out = r.bestTranscription.formattedString; done.signal() }
        else if let e = err as NSError? {
            // 1110 = konuşma yok (gerçek "boş"); başka hata = tanıma çalışmadı → "!" ile bildir (Python veto etmez)
            out = (e.code == 1110) ? "" : "!\(e.domain) \(e.code) \(e.localizedDescription)"
            done.signal()
        }
    }
    if done.wait(timeout: .now() + 15) == .timedOut { task.cancel(); out = "!zaman aşımı" }
    print(out.replacingOccurrences(of: "\n", with: " "))
}
