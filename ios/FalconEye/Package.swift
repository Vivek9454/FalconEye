// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "FalconEye",
    platforms: [
        .iOS(.v13)
    ],
    products: [
        .library(
            name: "FalconEye",
            targets: ["FalconEye"]
        ),
    ],
    dependencies: [
        // No external dependencies - using local notifications
    ],
    targets: [
        .target(
            name: "FalconEye",
            dependencies: [
                // No external dependencies
            ]
        ),
    ]
)