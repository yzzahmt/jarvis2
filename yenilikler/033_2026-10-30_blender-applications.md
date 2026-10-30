# 033 — Blender yalnız HDD'den (30.10.2026)

Kullanıcı Blender'ı kendi kullanımı için /Applications'a kurdu; o kalır, Jarvis ona dokunmaz.
Jarvis yalnız data/apps/Blender.app'i kullanır (önceki /Applications yedeği geri alındı) ve Blender'ı
BLENDER_USER_RESOURCES=data/blender-user ile çalıştırır: ayar/önbellek Mac diskine (~/Library) yazılmaz.
Kural: Jarvis'e ait hiçbir şey Mac diskinde yer kaplamaz. 71 test geçiyor.
