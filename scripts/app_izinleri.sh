#!/bin/sh
# JARVIS.app'e konuşma tanıma izin açıklamasını ekler ve yeniden imzalar (Mac'in cihaz içi ses tanıması
# uygulama içinden çalışsın). İmza değiştiği için macOS mikrofon/erişilebilirlik iznini yeniden sorabilir.
APP="$(dirname "$0")/../JARVIS.app"
PL="$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Delete :NSSpeechRecognitionUsageDescription" "$PL" 2>/dev/null
/usr/libexec/PlistBuddy -c "Add :NSSpeechRecognitionUsageDescription string 'Jarvis sesli komutlarını cihazda yazıya döker.'" "$PL"
/usr/libexec/PlistBuddy -c "Set :NSMicrophoneUsageDescription 'Jarvis sesli komutları dinler.'" "$PL"
xattr -cr "$APP"                     # HDD/Finder ek öznitelikleri imzayı engeller
codesign --force --deep -s - "$APP" && echo "tamam: JARVIS.app imzalandı"
