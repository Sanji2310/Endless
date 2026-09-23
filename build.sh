#!/usr/bin/env bash
# Builds dist/EndlessRush.apk without Gradle, using the Debian/Ubuntu Android tool packages:
#   sudo apt-get install aapt apksigner zipalign dalvik-exchange android-sdk-platform-23 openjdk-17-jdk
set -euo pipefail
cd "$(dirname "$0")"

ANDROID_JAR="${ANDROID_JAR:-/usr/lib/android-sdk/platforms/android-23/android.jar}"
DX="$(command -v dalvik-exchange || command -v dx)"
OUT=build
rm -rf "$OUT"
mkdir -p "$OUT/classes" dist

echo "==> Compiling Java"
javac -nowarn -Xlint:-options --release 8 -encoding UTF-8 -cp "$ANDROID_JAR" -d "$OUT/classes" \
    $(find src -name '*.java')

echo "==> Dexing"
"$DX" --dex --min-sdk-version=21 --output="$OUT/classes.dex" "$OUT/classes"

echo "==> Packaging resources"
aapt package -f -M AndroidManifest.xml -S res -I "$ANDROID_JAR" -F "$OUT/unsigned.apk"
(cd "$OUT" && aapt add unsigned.apk classes.dex >/dev/null)

echo "==> Aligning & signing"
zipalign -f 4 "$OUT/unsigned.apk" "$OUT/aligned.apk"
KEYSTORE="${KEYSTORE:-keystore/debug.jks}"
if [ ! -f "$KEYSTORE" ]; then
    mkdir -p "$(dirname "$KEYSTORE")"
    keytool -genkeypair -keystore "$KEYSTORE" -storepass android -keypass android -alias endless \
        -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Endless Rush Debug" >/dev/null 2>&1
fi
apksigner sign --v4-signing-enabled false --ks "$KEYSTORE" --ks-pass pass:android --key-pass pass:android --out dist/EndlessRush.apk "$OUT/aligned.apk"
apksigner verify dist/EndlessRush.apk
ls -la dist/EndlessRush.apk
