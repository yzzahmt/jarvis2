# 004 — Genel ajan (YARIM, izin bekliyor)
Hedef: sabit komutlar yerine her işi yapabilen yerel ajan (qwen3:8b + araçlar), beceri belleği, makrolar.
**Yazılan:** `jarvis/agent/tools.py` (shell, dosya, Spotlight, open_app, AppleScript, ses, ekran görüntüsü+görsel model,
klavye/fare, web arama, sayfa okuma, tarayıcı, hafıza, ask_user; riskli işlemler onay ister, tehlikeli komutlar reddedilir). Henüz commit yok.
**Engellenen:** ajan döngüsü / tarayıcı oturumu / beceri belleği dosyalarını yazmak Claude Code güvenlik denetimi tarafından
"Create Unsafe Agents" gerekçesiyle durduruldu. Kullanıcı kararı bekleniyor.
**İndiriliyor:** qwen3:8b (data/ollama).
