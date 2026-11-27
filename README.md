<p align="center">
  <img src="images/icon.png" width="112" height="112" alt="MVT GUI icon">
</p>

<h1 align="center">MVT GUI</h1>

<p align="center">
  <b>Check iPhones and Android phones for traces of known spyware.</b><br>
  A friendly Mac and Windows app for Amnesty International's
  <a href="https://docs.mvt.re/">Mobile Verification Toolkit</a>. No Terminal needed.
</p>

<p align="center">
  <a href="https://github.com/Dream1Works/MVT-GUI/releases/latest"><img src="https://img.shields.io/github/v/release/Dream1Works/MVT-GUI?style=for-the-badge&label=download&logo=github&color=2ea44f" alt="Latest release"></a>
  <a href="https://github.com/Dream1Works/MVT-GUI/releases"><img src="https://img.shields.io/github/downloads/Dream1Works/MVT-GUI/total?style=for-the-badge&label=downloads&color=0969da" alt="Total downloads"></a>
  <a href="EULA.md"><img src="https://img.shields.io/badge/license-EULA-orange?style=for-the-badge" alt="License: MVT GUI EULA"></a>
</p>

<p align="center">
  <img src="images/setup.png" width="80%" alt="MVT GUI's Setup screen">
</p>

## ⬇️ Download

<table align="center">
  <tr>
    <th width="50%"><img src="https://cdn.simpleicons.org/apple/000000/ffffff" width="18" height="18" alt=""> Mac</th>
    <th width="50%"><img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/windows11/windows11-original.svg" width="18" height="18" alt=""> Windows</th>
  </tr>
  <tr>
    <td>macOS 13 Ventura or newer, Apple silicon</td>
    <td>Windows 10 or 11, 64-bit</td>
  </tr>
  <tr>
    <td>
      <b>Coming to the Mac App Store.</b><br>
      MVT comes built in, and the App Store keeps it up to date.
      There is no Mac download here.
    </td>
    <td>
      1. Download <code>MVT-for-Windows-….zip</code> from
      <a href="https://github.com/Dream1Works/MVT-GUI/releases/latest">the latest release</a>.<br>
      2. Unzip it anywhere: Documents, the Desktop or a USB drive.<br>
      3. Double-click <b>MVT for Windows.exe</b>. Nothing is installed.
    </td>
  </tr>
</table>

Check a download against `SHA256SUMS.txt` in its release if you want to be
sure it is the real one.

## 🚀 Get started

1. Nothing to install: MVT is built into both apps.
2. **Indicators** → **Download All**. Indicators are lists of known spyware
   traces from [mvt-indicators](https://github.com/mvt-project/mvt-indicators),
   [Amnesty International](https://github.com/AmnestyTech/investigations) and
   [Echap](https://github.com/AssoEchap/stalkerware-indicators).
3. Back up the phone and run a check, as below.

<details>
<summary><b>📱 Check an iPhone</b></summary>

1. Connect the iPhone with a cable, unlock it, and tap **Trust** if it asks.
2. Make an encrypted backup:
   - **Mac:** select the iPhone in Finder, tick **Encrypt local backup**,
     set a password and press **Back Up Now**.
   - **Windows:** open **Back Up iPhone**, choose a folder, keep
     **Encrypt the backup** on, set a password and press **Back Up**. It needs
     Apple's **Apple Devices** app (or iTunes) installed.
3. Open **Decrypt Backup**, choose the backup and press **Decrypt**, then
   **Check Decrypted Backup**.
4. Choose a **Results folder** and press **Run Check**.

If the iPhone's backups were already encrypted, use the password you set
back then.

<p align="center"><img src="images/check-backup.png" width="80%" alt="Checking an iPhone backup"></p>
</details>

<details>
<summary><b>🤖 Check an Android phone</b></summary>

On the phone, turn on **Developer options**: tap **Build number** seven
times in **Settings → About phone**.

**Mac**, no cable needed:

1. In **Developer options**, tap **Take bug report**, then **Full report**.
2. When the phone says it's ready, tap the notification and send the .zip
   to your Mac (AirDrop, Quick Share, a cable or a message to yourself).
3. Open **Get a Bug Report**, press **Check the Newest in Downloads**, then
   **Run Check**.

**Windows**, with a cable:

1. In **Developer options**, turn on **USB debugging**, connect the phone
   and allow USB debugging for this computer.
2. Open **Collect with AndroidQF**, choose a folder and press
   **Open AndroidQF**. It opens in a window and asks a few questions.
3. When it's done, press **Check the Newest Acquisition**, then **Run Check**.

<p align="center"><img src="images/check-androidqf.png" width="80%" alt="Checking an AndroidQF acquisition"></p>
</details>

<details>
<summary><b>🔎 Read the results</b></summary>

- Alerts are sorted by severity, from **Critical** to **Info**. Click one to
  see what triggered it.
- **Timeline** shows every dated event, with the ones at the time of an
  alert highlighted.
- **Export Report** saves a PDF or web page to keep, or to send to someone
  who helps you.

<p align="center"><img src="images/results.png" width="80%" alt="The Results screen"></p>
</details>

> [!IMPORTANT]
> **No alerts doesn't mean a phone is clean.** Public indicators miss new
> and targeted attacks. If you're worried, get expert help from
> [Amnesty International's Security Lab](https://securitylab.amnesty.org/get-help/?c=mvt_docs)
> or [Access Now's Digital Security Helpline](https://www.accessnow.org/help/).
> Only check a phone with the consent of its owner.

## ✨ What's inside

| | |
|---|---|
| 📲 **Get the data easily** | Check an Android phone from a bug report it makes itself (Mac), or back up an iPhone and collect from Android in the app (Windows). |
| 🧭 **Guided checks** | Every MVT check as a simple form, with live, color-coded output. |
| 🛡️ **Fresh indicators** | Warns when indicators are a week old, and can update them before each check. |
| 📊 **Clear results** | Alerts by severity, a timeline, and a report to share. |
| 🔔 **Stays out of the way** | A notification when a long check ends. |
| 🌗 **Light and dark** | Follows your system, or pick one. |

<details>
<summary><b>🪟 More about the Windows app</b></summary>

- It starts through Python's own signed launcher, so Windows Security and
  SmartScreen don't block it.
- MVT is included. When a newer MVT is out, **Setup** offers **Update MVT**.
- Settings and indicators live in the app folder's `Data` folder. To remove
  the app, delete the folder.
- `README.txt` in the folder covers Smart App Control and controlled folder
  access.
</details>

## ❤️ Support

If MVT GUI helps you, you can support it on
[Patreon](https://patreon.com/Dossary) or [Ko-fi](https://ko-fi.com/2b4g10/10).
Found a security problem? See [SECURITY.md](.github/SECURITY.md).

## 📄 License

MVT GUI is Copyright © 2026 2B-4G10, licensed under the
[MVT GUI End User License Agreement](EULA.md). Earlier versions keep the
license they were released under.

MVT, the engine inside, is Copyright © 2021-2026 The MVT Authors under the
[MVT License 1.1](LICENSE-MVT); its source is at
[mvt-project/mvt](https://github.com/mvt-project/mvt). Credits for artwork
and trademarks are in [NOTICE](NOTICE), and the Windows download lists every
bundled component's license in `THIRD-PARTY-NOTICES.txt`.

<p align="center"><sub>Made by <a href="https://github.com/2B-4G10">2B-4G10</a></sub></p>
