#!/bin/sh
# JARVIS.app'e konuşma tanıma izin açıklamasını ekler ve yeniden imzalar (Mac'in cihaz içi ses tanıması
# uygulama içinden çalışsın). İmza değiştiği için macOS mikrofon/erişilebilirlik iznini yeniden sorabilir.
APP="$(dirname "$0")/../JARVIS.app"
PL="$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Delete :NSSpeechRecognitionUsageDescription" "$PL" 2>/dev/null
/usr/libexec/PlistBuddy -c "Add :NSSpeechRecognitionUsageDescription string 'Jarvis sesli komutlarını cihazda yazıya döker.'" "$PL"
/usr/libexec/PlistBuddy -c "Set :NSMicrophoneUsageDescription 'Jarvis sesli komutları dinler.'" "$PL"
# Simge paketin içinde (Finder'ın özel simgesi xattr'dır, imza için temizlenince kayboluyordu)
SET="$(mktemp -d)/jarvis.iconset"; mkdir -p "$SET"
for n in 16 32 128 256 512; do
  sips -z $n $n "$(dirname "$0")/../assets/jarvis.png" --out "$SET/icon_${n}x${n}.png" >/dev/null
  sips -z $((n*2)) $((n*2)) "$(dirname "$0")/../assets/jarvis.png" --out "$SET/icon_${n}x${n}@2x.png" >/dev/null
done
iconutil -c icns "$SET" -o "$APP/Contents/Resources/applet.icns" && rm -rf "$(dirname "$SET")"
/usr/libexec/PlistBuddy -c "Delete :CFBundleIconName" "$PL" 2>/dev/null   # Assets.car'daki genel simge yerine applet.icns
xattr -cr "$APP"                     # HDD/Finder ek öznitelikleri imzayı engeller
codesign --force --deep -s - "$APP" && echo "tamam: JARVIS.app imzalandı"
