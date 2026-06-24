#!/bin/bash
# Builds the Mumble desktop app for macOS using PyInstaller.
# Run this AFTER updating MUMBLE_URL in mumble_app_release.py.

set -e

echo "Installing PyInstaller..."
pip install pyinstaller pywebview

ICON="Mumble.app/Contents/Resources/MumbleIcon.icns"

echo "Building Mumble.app..."
pyinstaller \
  --onefile \
  --windowed \
  --name "Mumble" \
  --icon "$ICON" \
  --add-data "$ICON:." \
  mumble_app_release.py

echo ""
echo "Done! Your app is at: dist/Mumble"
echo "To make a .dmg for easy sharing, run:"
echo "  hdiutil create -volname Mumble -srcfolder dist/Mumble.app -ov -format UDZO Mumble.dmg"
