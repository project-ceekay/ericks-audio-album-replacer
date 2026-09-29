# Erick's Album Audio Replacer

NOTE FROM ERICK: Everything here is entirely Claude and Gemini. I had these series of programs made to make my life less manual, quicker, and easier overall.
I figured that there might be some other folk out there seeking a similar program that just works. I have only ever used AI for programming purposes, and I will
never use it in my creative work.

A small desktop tool for people who manage a personal music library in **Apple Music** (or iTunes). It **swaps the audio inside a tagged track for audio from a better source**, like a lossless FLAC, while keeping the track's existing tags, cover art, and filename.

<!-- Add a screenshot to docs/screenshot.png and uncomment the line below:
![Screenshot](docs/screenshot.png)
-->

## Why this exists

Apple Music and iTunes don't import FLAC, and they work best with `.m4a` (AAC) files. If you've spent time getting a track just right in your library (correct title, artist, album, track number, artwork), replacing its audio normally means re-tagging everything by hand.

This tool skips that. Point it at:

1. the **high-quality audio** you want to use (a FLAC from a lossless purchase or rip, for example), and
2. the **track already in your library**, which supplies the tags and cover art.

It encodes the new audio to AAC and writes a file that takes the library track's place, with the same name and the same metadata. Encoding settings match the iTunes Plus standard (256 kbps AAC, 44.1 kHz), so the result fits in with the rest of your library.

## Features

- Takes audio from **any format FFmpeg can read**: FLAC, WAV, AIFF, MP3, M4A, OGG, Opus, WMA, and more
- Copies **text tags** (title, artist, album, genre, track number, etc.) from your existing track
- Copies **embedded cover art** from any tagged format
- Keeps the **same filename and location** as your existing track, so it slots back into your library folder
- **Drag and drop** support, or use the file pickers
- Live **progress bar** with elapsed and total time
- Safe writes: the new file is encoded to a temporary file first and swapped in only on success, so a failed conversion never damages your original
- Modern interface that follows your system light or dark theme

## About this project

This project was **entirely vibe coded**: every line was written by an AI assistant through conversation, with no hand-written code and no formal testing or code review. It works for its intended purpose, but treat it accordingly:

- Expect rough edges and untested corners.
- **Back up your files** before using it on anything you can't replace.
- Bug reports, fixes, and improvements are welcome. See [Contributing](#contributing).

## How it works

You choose two files:

| Slot | Purpose |
|------|---------|
| **1. Audio Source** | The file whose **sound** you want to use. |
| **2. Metadata Source** | The file whose **tags, cover art, and filename** you want to keep, usually the track that's already in your library. |

The result is saved as `<metadata file name>.m4a` **in the same folder as the metadata file**.

> ⚠️ **If your library track is already an `.m4a`, it will be replaced** by the new version. You'll be asked to confirm first, but there is no undo, so keep a backup of anything you can't replace.

## Requirements

- **Python 3.9 or newer**
- **FFmpeg** and **FFprobe**
- Python packages: `customtkinter`, `tkinterdnd2`

Developed and tested on **Windows**. It uses cross-platform libraries and may work on macOS and Linux, but that hasn't been tested.

## Installation

1. **Install Python 3** from [python.org](https://www.python.org/downloads/). On Windows, tick *"Add Python to PATH"* during setup.
2. **Get the code**:
   ```
   git clone https://github.com/<your-username>/ericks-audio-album-replacer.git
   cd ericks-audio-album-replacer
   ```
   (or download the repository as a ZIP and extract it)
3. **Install the dependencies**:
   ```
   python -m pip install -r requirements.txt
   ```
   On Windows you can also use `py -m pip install -r requirements.txt`.
4. **Install FFmpeg** (see below).
5. **Run it**:
   ```
   python program.py
   ```

### Installing FFmpeg

The program looks for FFmpeg in two places, in this order:

1. **Next to the program**: place `ffmpeg.exe` and `ffprobe.exe` in the same folder as `program.py`. Nothing else to configure.
2. **On your system PATH**: if you install FFmpeg system-wide, the program finds it automatically.

Easiest ways to get it:

- **Windows (winget):** `winget install Gyan.FFmpeg`, then restart your terminal
- **Windows (manual):** download a build from [ffmpeg.org/download.html](https://ffmpeg.org/download.html), extract it, and copy `ffmpeg.exe` and `ffprobe.exe` from the `bin` folder next to the program
- **macOS (Homebrew):** `brew install ffmpeg`
- **Linux (apt):** `sudo apt install ffmpeg`

The bottom of the app tells you whether it's using a local FFmpeg or the one on your PATH.

## Usage: upgrading a track in your Apple Music library

1. **Back up first.** Copy the track (or your whole media folder) somewhere safe. Try the process on a single track before doing a whole album.
2. **Close Apple Music / iTunes.** This avoids the file being locked while it's replaced.
3. **Find the track's file.** In Apple Music, right-click the track and choose the option to show it in File Explorer (Finder on Mac).
4. **Add the audio source.** Drag your FLAC (or other high-quality file) onto the window, or click **Choose Audio File**.
5. **Add the metadata source.** Drag the library track in, or click **Choose Metadata File**. The **Output** card shows exactly where the result will be saved.
6. Click **Convert & Apply Metadata**. When it finishes, you'll be offered a shortcut to open the output folder.
7. **Reopen Apple Music.** The track keeps its filename and location, so the library entry should carry on pointing to it.

### Drag and drop tips

- Drop a file **directly on a section** to put it in that slot.
- Drop a file **anywhere else** and it fills the first empty slot (Audio, then Metadata).
- You can drop **two files at once**. They fill Audio then Metadata in the order your system hands them over, so check the labels afterwards. If they landed the wrong way round, drop one onto the correct section.

### Example

Your library has `01 - Song Title.m4a` with perfect tags and artwork, but you've since bought the lossless version as `Song Title.flac`.

- Audio Source → `Song Title.flac`
- Metadata Source → `01 - Song Title.m4a` (from your library folder)

Afterwards, `01 - Song Title.m4a` contains the FLAC's audio with the original tags and cover.

## Things to know

- **DRM-free files only.** Tracks downloaded from an Apple Music *subscription* are protected and can't be read by FFmpeg. Purchased, ripped, or imported tracks work.
- **What carries over.** Standard text tags and cover art are copied. Data that Apple Music keeps in its own library database rather than in the file (such as play counts, ratings, and playlist membership) isn't stored in the track, so it isn't touched, and it should stay attached as long as the filename and location don't change. Some Apple-specific tag fields inside the file may not carry over, so spot-check a track after converting.
- **Stale details.** Apple Music may keep showing the old file's details (length, bitrate) until it re-reads the file. Restarting the app usually refreshes it.
- **Lossless in, lossy out.** The output is AAC, which is lossy. Converting from a lossless source (FLAC, WAV, AIFF) gives the best result. If your source is already lossy (MP3 or another AAC file), it gets compressed a second time, so expect a small quality loss.

## Output settings

Encoding is currently fixed at:

| Setting | Value |
|---------|-------|
| Container | M4A |
| Codec | AAC |
| Bitrate | 256 kbps |
| Sample rate | 44.1 kHz |

To change them, edit the `-c:a`, `-ar`, and `-b:a` arguments in `run_conversion()` inside `program.py`.

## Troubleshooting

**"FFmpeg executable not found"**
Put `ffmpeg.exe` and `ffprobe.exe` next to the program, or install FFmpeg and make sure `ffmpeg -version` works in a fresh terminal.

**"The output file could not be replaced"**
The file is open in another program. Close Apple Music / iTunes (and any media player) and try again.

**FFmpeg reports an error**
The last lines of FFmpeg's output are shown in the error dialog. Common causes are an audio source with no audio stream, or a metadata file that is copy-protected.

**The progress bar doesn't move**
The program couldn't read the audio file's length (FFprobe missing or unable to read the file). The conversion still runs, just without a progress readout.

**The output has no cover art**
The metadata file has no embedded picture. The success message tells you when this happens.

**Drag and drop doesn't work**
Make sure `tkinterdnd2` is installed. If the app is run as Administrator, Windows blocks drag and drop from a normal Explorer window, so run it normally. You can always use the file pickers instead.

## Project structure

```
.
├── program.py         # The application
├── requirements.txt   # Python dependencies
├── LICENSE            # MIT License
└── README.md
```

## Built with

- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter): modern-looking Tkinter widgets
- [tkinterdnd2](https://github.com/Eliav2/tkinterdnd2): drag-and-drop support
- [FFmpeg](https://ffmpeg.org/): all audio conversion and tag handling

## Contributing

This is a community-friendly, open source project. Fork it, change it, and share your improvements. Issues and pull requests are welcome. Because the code is vibe coded, clear bug reports (what you did, what you expected, what happened) are especially useful.

## Disclaimer

This project is not affiliated with or endorsed by Apple Inc. Apple Music and iTunes are trademarks of Apple Inc. Always keep backups of your music library.

## License

Released under the [MIT License](LICENSE). You are free to use, copy, modify, merge, publish, distribute, sublicense, and sell copies of this software, provided the copyright and license notice are included. The software is provided "as is", without warranty of any kind.