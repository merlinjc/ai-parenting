// swift-tools-version: 5.9

import PackageDescription

let package = Package(
    name: "AIParenting",
    platforms: [
        .iOS(.v17),
        .macOS(.v14)
    ],
    products: [
        .library(
            name: "AIParenting",
            targets: ["AIParenting"]
        )
    ],
    targets: [
        .target(
            name: "AIParenting",
            path: "Sources/AIParenting"
        ),
        .testTarget(
            name: "AIParentingTests",
            dependencies: ["AIParenting"],
            path: "Tests/AIParentingTests"
        )
    ]
)
