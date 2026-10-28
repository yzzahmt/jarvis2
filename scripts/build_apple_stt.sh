#!/bin/sh
# Mac'in cihaz içi Türkçe ses tanıma yardımcısını derler → data/bin/apple_stt (ilk çalışmada izin ister).
cd "$(dirname "$0")/../tools/apple_stt" || exit 1
mkdir -p ../../data/bin
swiftc -O stt.swift -o ../../data/bin/apple_stt \
  -Xlinker -sectcreate -Xlinker __TEXT -Xlinker __info_plist -Xlinker Info.plist && echo "tamam: data/bin/apple_stt"
