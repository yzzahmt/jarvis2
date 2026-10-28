# 021 — JARVIS.app'e konuşma tanıma izni (Mac ikinci kulağı uygulama içinde)
Kullanıcı onayıyla: JARVIS.app Info.plist'ine NSSpeechRecognitionUsageDescription eklendi, mikrofon açıklaması
Türkçeleştirildi, ek öznitelikler temizlenip (xattr -cr; HDD/Finder "detritus" imzayı engelliyordu) ad-hoc yeniden
imzalandı. Betik: scripts/app_izinleri.sh (uygulama yeniden oluşturulursa tekrar çalıştır).
- Yeniden imzadan sonra mikrofon çalışıyor ("hey jarvis" ile uyandı, 00:07:50).
- İlk konuşmada macOS "Konuşma Tanıma" izni sorar → İzin Ver. Sonra Mac tanıması ikinci kulak olarak çalışır
  (apple_ok olunca uydurma metni veto eder). Günlükte "Mac tanıması çalışmadı" görülürse izin verilmemiştir.
