MVT for Windows
===============

A Windows app for the Mobile Verification Toolkit (MVT) by Amnesty
International's Security Lab. It checks iPhones and Android phones for
traces of known spyware. https://github.com/2B-4G10/MVT-GUI

Start it
--------

1. Keep this folder somewhere you own: Documents, Desktop or a USB drive.
   (Not Program Files: the app saves its settings and indicators here.)
2. Double-click "MVT for Windows.exe".

Nothing is installed and nothing needs administrator rights. To remove the
app, delete this folder.

"MVT for Windows.exe" is Python's own signed launcher (pythonw.exe from
python.org), renamed. The folder also holds the Python runtime that runs
MVT, which is why you see python.exe, DLLs and Lib.

If Windows warns about the app
------------------------------

- Download only from https://github.com/2B-4G10/MVT-GUI/releases and check
  the zip against SHA256SUMS.txt.
- Before unzipping, you can right-click the zip, choose Properties, tick
  Unblock and press OK. Windows then treats the files like ones you made.
- If Smart App Control is on (Windows Security > App & browser control),
  it can block the small libraries that MVT uses, which aren't signed.
  There's no per-app exception; the app works when Smart App Control is off.
- Controlled folder access (Windows Security > Virus & threat protection >
  Ransomware protection) can stop MVT from writing results to Documents or
  Desktop. Choose another results folder, or allow python.exe from this
  folder.

Your data
---------

Settings and downloaded indicators are kept in the Data folder next to the
app. When the folder can't be written to, they're kept in
%LOCALAPPDATA%\MVT for Windows instead.

License
-------

MVT for Windows and MVT are released under the MVT License 1.1
(LICENSE.txt), which only allows checking a phone with the consent of its
owner or user. Credits are in NOTICE.txt. Python's license is in
Lib\PYTHON-LICENSE.txt; Qt and PySide6 (LGPLv3) include theirs in
Lib\site-packages.
