// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "FalconEyeKit",
    platforms: [
        .iOS(.v14)
    ],
    products: [
        .library(
            name: "FalconEyeKit",
            targets: ["FalconEyeKit"]
        ),
    ],
    targets: [
        .target(
            name: "FalconEyeKit",
            path: "Sources"
        ),
        .testTarget(
            name: "FalconEyeKitTests",
            dependencies: ["FalconEyeKit"],
            path: "Tests"
        )
    ]
)
