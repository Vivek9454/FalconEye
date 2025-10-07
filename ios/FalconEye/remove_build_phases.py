#!/usr/bin/env python3
import re

# Read the project file
with open('FalconEye.xcodeproj/project.pbxproj', 'r') as f:
    content = f.read()

# Remove specific build phases
phases_to_remove = [
    '7545759FA8AC8DC9C06EC06A /* [CP] Check Pods Manifest.lock */',
    'B45F052B3715F8CA32E8A2A4 /* [CP] Embed Pods Frameworks */'
]

# Remove from buildPhases array
for phase in phases_to_remove:
    content = re.sub(f'{re.escape(phase)},\\s*', '', content)
    content = re.sub(f'{re.escape(phase)}\\s*', '', content)

# Remove the build phase definitions
for phase in phases_to_remove:
    # Remove the entire build phase definition
    pattern = f'{re.escape(phase)} = \\{{[^}}]*\\}};'
    content = re.sub(pattern, '', content, flags=re.MULTILINE | re.DOTALL)

# Clean up empty lines
content = re.sub(r'\n\s*\n', '\n', content)

# Write back
with open('FalconEye.xcodeproj/project.pbxproj', 'w') as f:
    f.write(content)

print("Removed CocoaPods build phases from project file")

