# MVT GUI
# Copyright (c) 2026 2B-4G10. All rights reserved.
# Proprietary: use of this file is governed by the MVT GUI End User
# License Agreement in the EULA.md file at the root of this repository.
#
# Written by packaging/update_packages.py for each release.

cask "mvt-gui" do
  version "4.0.2-beta"
  sha256 "f1059a64ea7d034df9cd49145334f5c27f57ecbd1af88b9f49ba2ab7990ad2a6"

  url "https://github.com/2B-4G10/MVT-GUI/releases/download/gui-v#{version}/MVT-GUI-#{version}-macOS.zip"
  name "MVT GUI"
  desc "Desktop app for the Mobile Verification Toolkit"
  homepage "https://github.com/2B-4G10/MVT-GUI"

  depends_on macos: ">= :ventura"

  app "MVT-GUI-#{version}/MVTGUI.app"

  zap trash: [
    "~/Library/Application Support/MVT GUI",
    "~/Library/Preferences/io.github.mvtgui.MVTGUI.plist",
  ]

  caveats <<~EOS
    If macOS says the app can't be checked for malicious software, open it
    once with right-click > Open, or allow it in System Settings > Privacy &
    Security. Then press Install MVT on its Setup screen.
  EOS
end
