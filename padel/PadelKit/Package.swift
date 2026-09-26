// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "PadelKit",
    platforms: [.iOS(.v17), .watchOS(.v10), .macOS(.v14)],
    products: [
        .library(name: "PadelKit", targets: ["PadelKit"])
    ],
    targets: [
        .target(name: "PadelKit"),
        .testTarget(name: "PadelKitTests", dependencies: ["PadelKit"])
    ]
)
