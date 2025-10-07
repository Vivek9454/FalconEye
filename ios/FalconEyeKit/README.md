# FalconEyeKit

Bonjour discovery and client helpers for the FalconEye iOS app.

## Integrate

1. In Xcode: File > Add Packages… > Add local package at `ios/FalconEyeKit`.
2. Link `FalconEyeKit` to the app target.
3. Add the following to Info.plist:

```
<key>NSBonjourServices</key>
<array>
  <string>_falconeye._tcp</string>
  <string>_http._tcp</string>
  <string>_https._tcp</string>
  <string>_airplay._tcp</string>
  <string>_raop._tcp</string>
  <string>_companion-link._tcp</string>
  <string>_hap._tcp</string>
  <string>_mediaremotetv._tcp</string>
  <string>_sleep-proxy._udp</string>
</array>
<key>NSLocalNetworkUsageDescription</key>
<string>Discover and connect to FalconEye on your local network</string>
```

## Usage

```
import FalconEyeKit

let discovery = FalconEyeDiscovery()
discovery.start { services in
  let base = EndpointSelector.chooseBaseURL(local: services, tunnelURL: URL(string: "https://cam.falconeye.website"))
  if let base = base {
    let client = FalconEyeClient(baseURL: base)
    client.discover { result in
      // use endpoints
    }
  }
}
```
