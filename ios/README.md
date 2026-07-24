# iOS

SwiftUI iOS client for the Seasonly API. Open `Seasonly.xcodeproj` in Xcode to build the app and its
unit/UI test targets.

Debug builds default to the local API at `http://127.0.0.1:8001/api/v1`. Set the
`SEASONLY_API_BASE_URL` scheme environment variable for another development endpoint. Release
builds require an HTTPS `SEASONLY_API_BASE_URL` user-defined build setting; it is copied into the
generated Info.plist, and the app fails closed if it is absent or not HTTPS.
