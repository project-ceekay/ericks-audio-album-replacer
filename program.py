import customtkinter as ctk
from tkinter import filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
import os
import re
import sys
import shutil
import tempfile
import threading
import subprocess
from collections import deque
from datetime import timedelta

CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0
TIME_RE = re.compile(r'time=(\d+:\d{2}:\d{2}(?:\.\d+)?)')
AUDIO_EXTS = ('.flac', '.mp3', '.m4a', '.alac', '.aac', '.ogg', '.opus',
              '.wav', '.aiff', '.aif', '.wma', '.wv', '.ape')


def short_name(name, limit=36):
    return name if len(name) <= limit else name[:limit - 1] + "…"


class TkDnDctk(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)


class AlbumAudioReplacer(TkDnDctk):
    def __init__(self):
        super().__init__()
        self.title("Erick's Album Audio Replacer")
        self.geometry("550x700")

        if getattr(sys, 'frozen', False):
            self.current_dir = os.path.dirname(sys.executable)
        else:
            self.current_dir = os.path.dirname(os.path.abspath(__file__))

        self.audio_file = ""
        self.metadata_file = ""
        self.is_processing = False

        self._locate_ffmpeg()

        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.handle_drop)

        self._build_ui()

    # ------------------------------------------------------------------
    # FFmpeg / FFprobe location
    # ------------------------------------------------------------------
    def _locate_ffmpeg(self):
        exe = '.exe' if os.name == 'nt' else ''
        local_ffmpeg = os.path.join(self.current_dir, f'ffmpeg{exe}')
        local_ffprobe = os.path.join(self.current_dir, f'ffprobe{exe}')

        self.using_local_ffmpeg = os.path.exists(local_ffmpeg)
        self.ffmpeg_command = local_ffmpeg if self.using_local_ffmpeg else 'ffmpeg'
        self.ffprobe_command = (local_ffprobe
                                if self.using_local_ffmpeg and os.path.exists(local_ffprobe)
                                else 'ffprobe')

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _make_zone(self, header, hint, button_text, command):
        """A header + hint + button block that doubles as a drop zone."""
        zone = ctk.CTkFrame(self, fg_color="transparent")
        zone.pack(pady=(20, 0), fill="x")

        ctk.CTkLabel(zone, text=header, font=("Arial", 16, "bold")).pack(pady=(0, 2))
        ctk.CTkLabel(zone, text=hint, font=("Arial", 11), text_color="gray").pack()
        button = ctk.CTkButton(zone, text=button_text, width=360, command=command)
        button.pack(pady=10)
        return zone, button

    def _build_ui(self):
        self.audio_zone, self.btn_audio = self._make_zone(
            "1. Select or Drag Audio Source",
            "The file whose audio will be converted (any format)",
            "Choose Audio File", self.select_audio_file)

        self.meta_zone, self.btn_meta = self._make_zone(
            "2. Select or Drag Metadata Source",
            "Tags and cover art are copied from this file",
            "Choose Metadata File", self.select_metadata_file)

        # Output info card
        self.output_frame = ctk.CTkFrame(self)
        self.output_frame.pack(pady=20, padx=20, fill="x")

        ctk.CTkLabel(self.output_frame, text="Output",
                     font=("Arial", 14, "bold")).pack(pady=(10, 2))
        self.output_label = ctk.CTkLabel(
            self.output_frame,
            text="Choose a metadata source to see where the result will be saved.",
            font=("Arial", 12), text_color="gray", wraplength=440, justify="center")
        self.output_label.pack(padx=15, pady=(0, 12))

        # Progress + run
        self.progress_bar = ctk.CTkProgressBar(self, width=400)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(10, 0))

        self.btn_run = ctk.CTkButton(
            self, text="Convert & Apply Metadata", fg_color="#2ecc71",
            hover_color="#27ae60", height=40, command=self.start_conversion)
        self.btn_run.pack(pady=20)

        self.status_label = ctk.CTkLabel(self, text="Ready", text_color="gray")
        self.status_label.pack(pady=5)

        ffmpeg_note = ("Using local FFmpeg" if self.using_local_ffmpeg
                       else "Using FFmpeg from system PATH")
        ctk.CTkLabel(self, text=ffmpeg_note, font=("Arial", 10),
                     text_color="gray").pack(pady=(10, 0))
        ctk.CTkLabel(self, text="© 2025 Erick's Software - All Rights Reserved",
                     font=("Arial", 10, "italic"), text_color="gray").pack(pady=(2, 10))

    # ------------------------------------------------------------------
    # File selection (buttons + drag and drop)
    # ------------------------------------------------------------------
    def set_audio(self, path):
        self.audio_file = os.path.normpath(path)
        self.btn_audio.configure(text=f"Audio: {short_name(os.path.basename(path))}")

    def set_metadata(self, path):
        self.metadata_file = os.path.normpath(path)
        self.btn_meta.configure(text=f"Metadata: {short_name(os.path.basename(path))}")
        out = self._output_path_for(self.metadata_file)
        self.output_label.configure(
            text=f"Saves as  {os.path.basename(out)}\n"
                 f"in  {os.path.dirname(out)}\n"
                 f"(replaces the file if it already exists)",
            text_color=("gray10", "gray90"))

    def select_audio_file(self):
        path = filedialog.askopenfilename(
            initialdir=self.current_dir,
            filetypes=[("Audio Files", " ".join(f"*{e}" for e in AUDIO_EXTS)),
                       ("All files", "*.*")])
        if path:
            self.set_audio(path)

    def select_metadata_file(self):
        path = filedialog.askopenfilename(
            initialdir=self.current_dir,
            filetypes=[("Audio Files", " ".join(f"*{e}" for e in AUDIO_EXTS)),
                       ("All files", "*.*")])
        if path:
            self.set_metadata(path)

    @staticmethod
    def _over(widget, event):
        x0, y0 = widget.winfo_rootx(), widget.winfo_rooty()
        return (x0 <= event.x_root <= x0 + widget.winfo_width()
                and y0 <= event.y_root <= y0 + widget.winfo_height())

    def handle_drop(self, event):
        """Drop on a section to fill it. Drop anywhere else and files fill the first empty slot
        (Audio first, then Metadata); if both are already filled, Audio is replaced."""
        for path in self.tk.splitlist(event.data):
            if not os.path.isfile(path):
                continue

            if self._over(self.audio_zone, event):
                self.set_audio(path)
            elif self._over(self.meta_zone, event):
                self.set_metadata(path)
            elif not self.audio_file:
                self.set_audio(path)
            elif not self.metadata_file:
                self.set_metadata(path)
            else:
                self.set_audio(path)

    # ------------------------------------------------------------------
    # Thread-safe UI helpers
    # ------------------------------------------------------------------
    def _update_progress(self, fraction):
        self.after(0, lambda: self.progress_bar.set(fraction))

    def _update_status(self, message, color="gray"):
        self.after(0, lambda: self.status_label.configure(text=message, text_color=color))

    def _finish(self, success, message, folder=None):
        self.after(0, lambda: self._finish_ui(success, message, folder))

    def _finish_ui(self, success, message, folder):
        self.is_processing = False
        self.btn_run.configure(state="normal")

        if success:
            self.progress_bar.set(1)
            self.status_label.configure(text="Conversion Complete!", text_color="#2ecc71")
            if messagebox.askyesno("Success", f"{message}\n\nWould you like to open the folder?"):
                self._open_folder(folder)
        else:
            self.progress_bar.set(0)
            self.status_label.configure(text="Conversion failed", text_color="#e74c3c")
            messagebox.showerror("Operation Failed", message)

    @staticmethod
    def _open_folder(folder):
        if not folder:
            return
        folder = os.path.normpath(folder)
        if os.name == 'nt':
            os.startfile(folder)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', folder])
        else:
            subprocess.Popen(['xdg-open', folder])

    # ------------------------------------------------------------------
    # Start
    # ------------------------------------------------------------------
    @staticmethod
    def _output_path_for(metadata_file):
        target_dir = os.path.dirname(metadata_file)
        base_name = os.path.splitext(os.path.basename(metadata_file))[0]
        return os.path.join(target_dir, f"{base_name}.m4a")

    def start_conversion(self):
        if self.is_processing:
            return
        if not self.audio_file or not os.path.isfile(self.audio_file):
            messagebox.showwarning("Error", "Please select a valid Audio Source file.")
            return
        if not self.metadata_file or not os.path.isfile(self.metadata_file):
            messagebox.showwarning("Error", "Please select a valid Metadata Source file.")
            return

        output_file = self._output_path_for(self.metadata_file)
        if os.path.exists(output_file):
            if not messagebox.askyesno(
                    "Overwrite file?",
                    f"'{os.path.basename(output_file)}' already exists and will be replaced "
                    f"by the new version.\n\nContinue?"):
                return

        self.is_processing = True
        self.btn_run.configure(state="disabled")
        self.progress_bar.set(0)
        self._update_status("Starting conversion...")

        threading.Thread(
            target=self.run_conversion,
            args=(self.audio_file, self.metadata_file, output_file),
            daemon=True,
        ).start()

    # ------------------------------------------------------------------
    # FFmpeg helpers
    # ------------------------------------------------------------------
    def _check_ffmpeg_availability(self):
        try:
            subprocess.run([self.ffmpeg_command, '-version'], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=CREATE_NO_WINDOW)
            return True, ""
        except FileNotFoundError:
            return False, ("FFmpeg executable not found. Check system PATH or place "
                           "ffmpeg next to this program.")
        except Exception as e:
            return False, f"Error running FFmpeg check: {e}"

    def _get_duration(self, path):
        try:
            proc = subprocess.run(
                [self.ffprobe_command, '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'default=noprint_wrappers=1:nokey=1', path],
                capture_output=True, text=True, check=True,
                creationflags=CREATE_NO_WINDOW)
            return float(proc.stdout.strip())
        except Exception:
            return 0

    def _extract_cover_art(self, source_path, temp_dir):
        """Let FFmpeg pull embedded art from any container; always yields a JPEG."""
        self._update_status("Extracting cover art...")
        cover_file = os.path.join(temp_dir, "cover.jpg")
        try:
            proc = subprocess.run(
                [self.ffmpeg_command, '-hide_banner', '-nostdin', '-y',
                 '-i', source_path,
                 '-an', '-map', '0:v:0', '-frames:v', '1',
                 '-c:v', 'mjpeg', '-q:v', '2', cover_file],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW)
            if (proc.returncode == 0 and os.path.exists(cover_file)
                    and os.path.getsize(cover_file) > 0):
                return cover_file
        except Exception as e:
            print(f"WARNING: cover art extraction failed: {e}")
        return None

    # ------------------------------------------------------------------
    # Worker
    # ------------------------------------------------------------------
    def run_conversion(self, input_file, metadata_file, output_file):
        temp_dir = None
        target_dir = os.path.dirname(output_file)
        # Encode to a temp file beside the target, then swap it in. This protects the
        # original if encoding fails and avoids reading/writing the same file.
        temp_output = os.path.join(
            target_dir,
            f"{os.path.splitext(os.path.basename(output_file))[0]}.converting.m4a")

        try:
            available, check_message = self._check_ffmpeg_availability()
            if not available:
                self._finish(False, f"FFmpeg Check Failed: {check_message}")
                return

            temp_dir = tempfile.mkdtemp()
            cover_file = self._extract_cover_art(metadata_file, temp_dir)

            cmd = [self.ffmpeg_command, '-hide_banner', '-nostdin',
                   '-i', metadata_file,   # Input 0: tags
                   '-i', input_file]      # Input 1: audio
            if cover_file:
                cmd += ['-i', cover_file]  # Input 2: cover art

            cmd += ['-map_metadata', '0', '-map', '1:a:0']
            if cover_file:
                cmd += ['-map', '2:v:0', '-c:v', 'copy', '-disposition:v:0', 'attached_pic']

            cmd += ['-c:a', 'aac', '-ar', '44100', '-b:a', '256k', '-y', temp_output]

            duration_seconds = self._get_duration(input_file)
            if duration_seconds <= 0:
                self._update_status("Converting (progress unavailable)...")

            process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                text=True, encoding='utf-8', errors='replace',
                creationflags=CREATE_NO_WINDOW)

            recent_lines = deque(maxlen=20)
            for line in process.stderr:
                line = line.strip()
                if not line:
                    continue
                recent_lines.append(line)

                match = TIME_RE.search(line)
                if match and duration_seconds > 0:
                    h, m, s = map(float, match.group(1).split(':'))
                    current = h * 3600 + m * 60 + s
                    fraction = min(0.99, current / duration_seconds)
                    self._update_progress(fraction)
                    self._update_status(
                        f"Converting: {timedelta(seconds=int(current))} / "
                        f"{timedelta(seconds=int(duration_seconds))} ({int(fraction * 100)}%)")

            return_code = process.wait()
            if return_code != 0:
                tail = "\n".join(recent_lines)
                self._finish(False, f"FFmpeg failed with exit code {return_code}.\n\n{tail}")
                return

            try:
                os.replace(temp_output, output_file)
            except OSError as e:
                self._finish(
                    False,
                    f"Conversion finished, but the output file could not be replaced "
                    f"(is it open in another program?).\n\n{e}")
                return

            cover_note = "" if cover_file else "\n(No embedded cover art was found in the metadata source.)"
            self._finish(
                True,
                f"Output: '{os.path.basename(output_file)}'{cover_note}",
                folder=target_dir)

        except Exception as e:
            self._finish(False, f"An unexpected error occurred: {e}")
        finally:
            if os.path.exists(temp_output):
                try:
                    os.remove(temp_output)
                except OSError:
                    pass
            if temp_dir and os.path.isdir(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    app = AlbumAudioReplacer()
    app.mainloop()