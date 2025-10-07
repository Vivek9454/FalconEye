#!/usr/bin/env python3
import re

# Read the project file
with open('FalconEye.xcodeproj/project.pbxproj', 'r') as f:
    content = f.read()

# Remove all CocoaPods build phases and references
patterns_to_remove = [
    # Remove CocoaPods build phases
    r'/\* Begin PBXShellScriptBuildPhase section \*/\n.*?/\* \[CP\] Embed Pods Frameworks \*/\n.*?/\* End PBXShellScriptBuildPhase section \*/',
    r'/\* Begin PBXShellScriptBuildPhase section \*/\n.*?/\* \[CP\] Check Pods Manifest\.lock \*/\n.*?/\* End PBXShellScriptBuildPhase section \*/',
    r'/\* Begin PBXShellScriptBuildPhase section \*/\n.*?/\* \[CP\] Copy Pods Resources \*/\n.*?/\* End PBXShellScriptBuildPhase section \*/',
    
    # Remove CocoaPods file references
    r'F1CB5DAF8A9FB1CACE703F69 /\* Pods_FalconEye\.framework in Frameworks \*/ = \{isa = PBXBuildFile; fileRef = 10608B6450EE03BA48BF0720 /\* Pods_FalconEye\.framework \*/; \};',
    r'10608B6450EE03BA48BF0720 /\* Pods_FalconEye\.framework \*/ = \{isa = PBXFileReference; explicitFileType = wrapper\.framework; includeInIndex = 0; path = Pods_FalconEye\.framework; sourceTree = BUILT_PRODUCTS_DIR; \};',
    r'260D8D7BB477C7A1BAC8DE91 /\* Pods-FalconEye\.debug\.xcconfig \*/ = \{isa = PBXFileReference; includeInIndex = 1; lastKnownFileType = text\.xcconfig; name = "Pods-FalconEye\.debug\.xcconfig"; path = "Target Support Files/Pods-FalconEye/Pods-FalconEye\.debug\.xcconfig"; sourceTree = "<group>"; \};',
    r'42F894DC501504AFB3D05250 /\* Pods-FalconEye\.release\.xcconfig \*/ = \{isa = PBXFileReference; includeInIndex = 1; lastKnownFileType = text\.xcconfig; name = "Pods-FalconEye\.release\.xcconfig"; path = "Target Support Files/Pods-FalconEye/Pods-FalconEye\.release\.xcconfig"; sourceTree = "<group>"; \};',
    
    # Remove from buildPhases
    r'F1CB5DAF8A9FB1CACE703F69 /\* Pods_FalconEye\.framework in Frameworks \*/,',
    r'10608B6450EE03BA48BF0720 /\* Pods_FalconEye\.framework \*/,',
    r'260D8D7BB477C7A1BAC8DE91 /\* Pods-FalconEye\.debug\.xcconfig \*/,',
    r'42F894DC501504AFB3D05250 /\* Pods-FalconEye\.release\.xcconfig \*/,',
    
    # Remove Pods group
    r'C612E9E0569E40B276D38312 /\* Pods \*/ = \{[^}]*\};',
    r'C612E9E0569E40B276D38312 /\* Pods \*/,',
    
    # Remove CocoaPods build settings
    r'baseConfigurationReference = 260D8D7BB477C7A1BAC8DE91 /\* Pods-FalconEye\.debug\.xcconfig \*/;',
    r'baseConfigurationReference = 42F894DC501504AFB3D05250 /\* Pods-FalconEye\.release\.xcconfig \*/;',
]

# Apply removals
for pattern in patterns_to_remove:
    content = re.sub(pattern, '', content, flags=re.MULTILINE | re.DOTALL)

# Remove empty lines and clean up
content = re.sub(r'\n\s*\n', '\n', content)

# Write back
with open('FalconEye.xcodeproj/project.pbxproj', 'w') as f:
    f.write(content)

print("Completely cleaned up CocoaPods references from project file")

