#!/bin/bash

# Create iconset directory
mkdir -p icon.iconset

# Convert SVG to PNG in various sizes
for size in 16 32 128 256 512; do
  # Normal resolution
  sips -z $size $size app_icon.png --out icon.iconset/icon_${size}x${size}.png
  
  # Retina resolution (@2x)
  if [ $size -lt 512 ]; then
    sips -z $((size*2)) $((size*2)) app_icon.png --out icon.iconset/icon_${size}x${size}@2x.png
  fi
done

# Create icns file
iconutil -c icns icon.iconset

# Cleanup
rm -rf icon.iconset

echo "Icon created successfully!"