#!/usr/bin/env python3
import re

# Read the project file
with open('FalconEye.xcodeproj/project.pbxproj', 'r') as f:
    content = f.read()

# Remove Firebase SPM build file references
firebase_build_files = [
    r'4E1816E42E781031002B44A2 /\* FirebaseAI in Frameworks \*/ = \{isa = PBXBuildFile; productRef = 4E1816E32E781031002B44A2 /\* FirebaseAI \*/; \};',
    r'4E1816E62E781031002B44A2 /\* FirebaseAnalytics in Frameworks \*/ = \{isa = PBXBuildFile; productRef = 4E1816E52E781031002B44A2 /\* FirebaseAnalytics \*/; \};',
    r'4E1816E82E781031002B44A2 /\* FirebaseAnalyticsCore in Frameworks \*/ = \{isa = PBXBuildFile; productRef = 4E1816E72E781031002B44A2 /\* FirebaseAnalyticsCore \*/; \};',
    r'4E1816EA2E781031002B44A2 /\* FirebaseAnalyticsIdentitySupport in Frameworks \*/ = \{isa = PBXBuildFile; productRef = 4E1816E92E781031002B44A2 /\* FirebaseAnalyticsIdentitySupport \*/; \};',
    r'4E1816EC2E781031002B44A2 /\* FirebaseAppCheck in Frameworks \*/ = \{isa = PBXBuildFile; productRef = 4E1816EB2E781031002B44A2 /\* FirebaseAppCheck \*/; \};',
    r'4E1817242E7847F6002B44A2 /\* FirebaseAuth in Frameworks \*/ = \{isa = PBXBuildFile; productRef = 4E1817232E7847F6002B44A2 /\* FirebaseAuth \*/; \};',
    r'4E1817262E7847F6002B44A2 /\* FirebaseCore in Frameworks \*/ = \{isa = PBXBuildFile; productRef = 4E1817252E7847F6002B44A2 /\* FirebaseCore \*/; \};',
    r'4E1817282E7847F6002B44A2 /\* FirebaseMessaging in Frameworks \*/ = \{isa = PBXBuildFile; productRef = 4E1817272E7847F6002B44A2 /\* FirebaseMessaging \*/; \};',
]

for pattern in firebase_build_files:
    content = re.sub(pattern, '', content)

# Remove Firebase from frameworks list
frameworks_pattern = r'4E1817282E7847F6002B44A2 /\* FirebaseMessaging in Frameworks \*/,?\s*'
content = re.sub(frameworks_pattern, '', content)

frameworks_pattern = r'4E1816EA2E781031002B44A2 /\* FirebaseAnalyticsIdentitySupport in Frameworks \*/,?\s*'
content = re.sub(frameworks_pattern, '', content)

frameworks_pattern = r'4E1817242E7847F6002B44A2 /\* FirebaseAuth in Frameworks \*/,?\s*'
content = re.sub(frameworks_pattern, '', content)

frameworks_pattern = r'4E1816E62E781031002B44A2 /\* FirebaseAnalytics in Frameworks \*/,?\s*'
content = re.sub(frameworks_pattern, '', content)

frameworks_pattern = r'4E1816E82E781031002B44A2 /\* FirebaseAnalyticsCore in Frameworks \*/,?\s*'
content = re.sub(frameworks_pattern, '', content)

frameworks_pattern = r'4E1817262E7847F6002B44A2 /\* FirebaseCore in Frameworks \*/,?\s*'
content = re.sub(frameworks_pattern, '', content)

frameworks_pattern = r'4E1816EC2E781031002B44A2 /\* FirebaseAppCheck in Frameworks \*/,?\s*'
content = re.sub(frameworks_pattern, '', content)

frameworks_pattern = r'4E1816E42E781031002B44A2 /\* FirebaseAI in Frameworks \*/,?\s*'
content = re.sub(frameworks_pattern, '', content)

# Remove package product dependencies
package_deps_pattern = r'packageProductDependencies = \(\s*4E1816E32E781031002B44A2 /\* FirebaseAI \*/,?\s*4E1816E52E781031002B44A2 /\* FirebaseAnalytics \*/,?\s*4E1816E72E781031002B44A2 /\* FirebaseAnalyticsCore \*/,?\s*4E1816E92E781031002B44A2 /\* FirebaseAnalyticsIdentitySupport \*/,?\s*4E1816EB2E781031002B44A2 /\* FirebaseAppCheck \*/,?\s*4E1817232E7847F6002B44A2 /\* FirebaseAuth \*/,?\s*4E1817252E7847F6002B44A2 /\* FirebaseCore \*/,?\s*4E1817272E7847F6002B44A2 /\* FirebaseMessaging \*/,?\s*\);'
content = re.sub(package_deps_pattern, 'packageProductDependencies = ();', content)

# Write the cleaned content back
with open('FalconEye.xcodeproj/project.pbxproj', 'w') as f:
    f.write(content)

print("Removed Swift Package Manager Firebase dependencies")

