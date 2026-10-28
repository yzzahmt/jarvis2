# 019 — Küçültünce alttaki Jarvis çubuğu (dock) + daha premium arayüz
Kullanıcı: "Google'da gezinirken altta çıkan Jarvis dock'u normal konuşurken küçülttüğümüzde de çıksın; arayüz daha
kullanışlı ve premium olsun".
- Sarı düğme / ⌘M / Esc (mini) → ana pencere gizlenir, altta Jarvis çubuğu kalır (`App.dock`, `LocalBar.docked`).
  Dock'ta: durumla değişen küre, dinlerken/konuşurken ses dalgası, kenarda dönen ışık; söylediğin ve son cevap;
  düğmeler: durdur (görevde), mikrofon, büyüt, gizle (×). Görev adımları da orada; görev bitince 6 sn sonra dock
  görünümüne döner (dock değilse eskisi gibi gizlenir). Dock açıkken "hey jarvis" büyük pencereyi açmaz.
  Çubuğun düğmeleri `BarApi` (overlay penceresine js_api). Kısayol ('<'+'z') mini pencereyi açarsa dock kapanır.
- Ana pencere: ışıklı ince kenar ve üst parlama (dinlerken/konuşurken belirginleşir), degrade JARVIS yazısı,
  durum yanında ses dalgası, Jarvis mesajları küre avatarlı kart + üzerine gelince Kopyala, yazı alanında odak
  parlaması, saate göre selamlama.
- Denendi: ekran görüntüsüyle küçült → dock → büyüt akışı çalışıyor. Testler: 58.
