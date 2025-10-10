import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import threading
import subprocess
import re
from datetime import timedelta
import tempfile 
import shutil 

# IMPORTS for metadata handling
from mutagen import File as MutagenFile # Keep Mutagen only for reading source file metadata and artwork data

class FlacToM4AConverterGUI:
    def __init__(self, master):
        self.master = master
        
        # --- TITLE CHANGE START ---
        master.title("Erick's Album Audio Replacer")
        # --- TITLE CHANGE END ---
        
        # Variables
        self.audio_source_path = tk.StringVar()    # File 1: FLAC file (source audio data)
        self.metadata_source_path = tk.StringVar() # File 2: Any file with tags (source metadata)
        self.output_dir_path = tk.StringVar()
        self.is_processing = False
        self.temp_dir = None # To store the path of the temporary directory for cleanup
        
        # --- FFmpeg Path Logic: Prioritize local folder ---
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            base_dir = os.getcwd()
            
        self.local_ffmpeg = os.path.join(base_dir, 'ffmpeg.exe')
        self.ffmpeg_command = self.local_ffmpeg if os.path.exists(self.local_ffmpeg) else 'ffmpeg'
        self.use_shell = (self.ffmpeg_command == 'ffmpeg' and os.name == 'nt') 
        # --- END FFmpeg Path Logic ---
        
        self.create_widgets()

    def create_widgets(self):
        s = ttk.Style()
        s.theme_use('vista') 
        s.configure('TFrame', background='#f0f0f0')
        s.configure('G.TButton', font=('Inter', 12, 'bold'), foreground='#FFFFFF', background='#28a745', padding=10)
        s.map('G.TButton', background=[('active', '#1e7e34')])

        self.master.config(padx=20, pady=20, background='#f0f0f0')

        # --- File 1: Audio Source (FLAC) ---
        input_frame = ttk.LabelFrame(self.master, text="1. Audio Source File (FLAC to be Converted)", padding="10")
        input_frame.pack(padx=10, pady=10, fill="x")
        
        ttk.Entry(input_frame, textvariable=self.audio_source_path, width=50, font=('Inter', 10)).pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x")
        ttk.Button(input_frame, text="Select FLAC", command=self.select_audio_file).pack(side=tk.LEFT, padx=5, pady=5)
        
        # --- File 2: Metadata Source (Any Tagged File) ---
        metadata_frame = ttk.LabelFrame(self.master, text="2. Metadata Source File (File to Copy Tags From)", padding="10")
        metadata_frame.pack(padx=10, pady=10, fill="x")
        
        ttk.Entry(metadata_frame, textvariable=self.metadata_source_path, width=50, font=('Inter', 10)).pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x")
        ttk.Button(metadata_frame, text="Select Metadata Source", command=self.select_metadata_file).pack(side=tk.LEFT, padx=5, pady=5)
        
        # --- Output Directory Frame ---
        # NOTE: This GUI input is mostly ignored now, as output path is forced to Metadata Source directory.
        output_frame = ttk.LabelFrame(self.master, text="3. Select Output Directory (Output path is now fixed to Metadata Source folder)", padding="10")
        output_frame.pack(padx=10, pady=10, fill="x")

        ttk.Entry(output_frame, textvariable=self.output_dir_path, width=50, font=('Inter', 10)).pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x")
        ttk.Button(output_frame, text="Select Folder", command=self.select_output_dir).pack(side=tk.LEFT, padx=5, pady=5)

        # --- Process Button ---
        self.process_btn = ttk.Button(self.master, text="CONVERT & APPLY METADATA", command=self._start_conversion_thread, style='G.TButton')
        self.process_btn.pack(pady=20, fill="x", padx=10)
        
        # --- Progress Bar and Status ---
        self.status_label = ttk.Label(self.master, text="", background='#f0f0f0', font=('Inter', 10, 'italic'), foreground='#333')
        self.status_label.pack(pady=(5, 0), padx=10, fill="x")

        self.progress_bar = ttk.Progressbar(self.master, orient='horizontal', length=100, mode='determinate')
        self.progress_bar.pack(pady=10, fill="x", padx=10)
        
        # --- FFmpeg instruction label ---
        ffmpeg_status = "Local ffmpeg.exe found and will be used." if self.ffmpeg_command != 'ffmpeg' else "FFmpeg command will rely on system PATH."
        ttk.Label(self.master, text=f"FFmpeg command check:\n({ffmpeg_status})", 
                  foreground="#888", background='#f0f0f0').pack(pady=5)
                  
        # --- COPYRIGHT ADDITION START ---
        ttk.Label(self.master, 
                  text="© 2025 Erick's Software - All Rights Reserved", 
                  font=('Inter', 8, 'italic'), 
                  foreground="#aaa", 
                  background='#f0f0f0').pack(pady=(5, 0))
        # --- COPYRIGHT ADDITION END ---

    def select_audio_file(self):
        """Opens a file dialog for selecting a FLAC file (Audio Source)."""
        filepath = filedialog.askopenfilename(
            defaultextension=".flac",
            filetypes=[("FLAC Files", "*.flac")]
        )
        if filepath:
            self.audio_source_path.set(filepath)
            # Suggest output path in the same directory initially
            self.output_dir_path.set(os.path.dirname(filepath))
            
    def select_metadata_file(self):
        """Opens a file dialog for selecting any audio file (Metadata Source)."""
        filepath = filedialog.askopenfilename(
            defaultextension=".*",
            filetypes=[("Audio Files", ["*.mp3", "*.flac", "*.m4a", "*.alac", "*.ogg", "*.wav"]),
                       ("All files", "*.*")]
        )
        if filepath:
            self.metadata_source_path.set(filepath)

    def select_output_dir(self):
        """Opens a file dialog for selecting the output directory."""
        dirpath = filedialog.askdirectory()
        if dirpath:
            self.output_dir_path.set(dirpath)
            
    def _start_conversion_thread(self):
        """Starts the conversion in a new thread."""
        if self.is_processing:
            return
        
        audio_file = self.audio_source_path.get()
        metadata_file = self.metadata_source_path.get()
        output_dir = self.output_dir_path.get()
        
        if not audio_file or not os.path.exists(audio_file):
            messagebox.showerror("Error", "Please select a valid Audio Source (FLAC) file.")
            return
        if not metadata_file or not os.path.exists(metadata_file):
            messagebox.showerror("Error", "Please select a valid Metadata Source file.")
            return
        if not output_dir or not os.path.isdir(output_dir):
            messagebox.showerror("Error", "Please select a valid output directory.")
            return

        self.is_processing = True
        self.process_btn.config(state=tk.DISABLED)
        self.progress_bar['value'] = 0
        self._update_status("Starting conversion...")
        
        thread = threading.Thread(target=self.run_conversion)
        thread.start()

    def _update_progress(self, percentage):
        """Updates the progress bar safely from a background thread."""
        self.master.after(0, lambda: self.progress_bar.config(value=percentage))

    def _update_status(self, message):
        """Updates the status message label safely from a background thread."""
        self.master.after(0, lambda: self.status_label.config(text=message))

    def _finish_process(self, success, message):
        """Finalizes the process and re-enables the button."""
        self.is_processing = False
        self.process_btn.config(state=tk.NORMAL)
        self.progress_bar['value'] = 100 if success else 0
        
        if success:
            messagebox.showinfo("Success! 🎉", message)
        else:
            messagebox.showerror("Operation Failed", message)

        self._update_status("")

    def _check_ffmpeg_availability(self):
        """Checks if the configured FFmpeg command executes successfully."""
        try:
            subprocess.run([self.ffmpeg_command, '-version'], 
                           check=True, 
                           stdout=subprocess.PIPE, 
                           stderr=subprocess.PIPE,
                           shell=self.use_shell,
                           creationflags=0x08000000 if os.name == 'nt' else 0)
            return True, ""
        except FileNotFoundError:
            return False, f"FFmpeg executable not found. Check system PATH or place ffmpeg.exe next to this script."
        except Exception as e:
            return False, f"Error running FFmpeg check: {e}"
            
    def _extract_cover_art_to_temp_file(self, source_path):
        """
        Reads cover art from the source file using Mutagen and saves it to a 
        temporary file for FFmpeg to use.
        """
        self._update_status("Extracting cover art...")
        
        # Create a temporary directory if it doesn't exist
        if not self.temp_dir:
            self.temp_dir = tempfile.mkdtemp()
        
        try:
            source_audio = MutagenFile(source_path)
            
            # Note: 'pictures' attribute is common in FLAC, but Mutagen handles various formats
            if hasattr(source_audio, 'pictures') and source_audio.pictures:
                pic = source_audio.pictures[0] # Take the first picture
                mime_type = pic.mime.lower()
                
                ext = ".jpg" if "jpeg" in mime_type or "jpg" in mime_type else ".png"
                cover_file = os.path.join(self.temp_dir, f"cover{ext}")

                with open(cover_file, 'wb') as f:
                    f.write(pic.data)
                
                return cover_file
                
            return None # No cover found
            
        except Exception as e:
            print(f"ERROR during cover art extraction: {e}")
            return None

    def _cleanup_temp_files(self):
        """Removes the temporary directory and its contents."""
        if self.temp_dir and os.path.isdir(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                self.temp_dir = None
                print(f"DEBUG: Cleaned up temporary directory: {self.temp_dir}")
            except Exception as e:
                print(f"WARNING: Failed to clean up temporary directory {self.temp_dir}: {e}")


    def run_conversion(self):
        """
        Executes the FLAC to M4A conversion, applying metadata in a single FFmpeg pass.
        """
        
        available, check_message = self._check_ffmpeg_availability()
        if not available:
            self._cleanup_temp_files()
            self._finish_process(False, f"FFmpeg Check Failed: {check_message}")
            return
            
        # Get paths
        input_file = self.audio_source_path.get()
        metadata_file = self.metadata_source_path.get()
        
        # --- Output File Path: Set to the location and name of the Metadata Source file (.m4a) ---
        # 1. Determine the target directory (where the metadata source file is located)
        target_dir = os.path.dirname(metadata_file)
        # 2. Use the metadata file name (minus extension) for the output M4A file
        base_name = os.path.splitext(os.path.basename(metadata_file))[0]
        output_file = os.path.join(target_dir, f"{base_name}.m4a")
        # Overwriting is handled by the '-y' flag in the FFmpeg command.
        # --- END CHANGE ---

        # --- Step 1: Extract Cover Art to Temp File ---
        # The metadata file is used here as the source for the album art
        temp_cover_file = self._extract_cover_art_to_temp_file(metadata_file)

        # --- Step 2: FFmpeg Conversion & Tagging ---
        
        cmd = [
            self.ffmpeg_command, 
            '-i', metadata_file,    # Input 0: Metadata Source (Used for -map_metadata 0)
            '-i', input_file,       # Input 1: Audio Source (Used for -map 1:a:0)
        ]

        if temp_cover_file:
            # Add the cover art file as Input 2
            cmd.extend(['-i', temp_cover_file]) 
        
        # --- Mapping Streams and Metadata ---
        
        # 1. Text Tags: Copy all text metadata from Input 0 (metadata_file)
        cmd.extend([
            '-map_metadata', '0', 
        ])
        
        # 2. Audio Stream: Map the audio stream from Input 1 (the FLAC file)
        cmd.extend([
            '-map', '1:a:0',        
        ])
        
        # 3. Cover Art (Video Stream): Map the image stream from the temporary file (Input 2) if present
        if temp_cover_file:
            # Map the image stream from Input 2 (the first video stream of input 2)
            cmd.extend([
                '-map', '2:v:0',
                # CRUCIAL: Set codec and disposition for M4A cover art visibility in file properties
                '-c:v:0', 'mjpeg', 
                '-disposition:v:0', 'attached_pic',
            ])
        
        # --- Encoding Parameters ---
        cmd.extend([
            '-c:a', 'aac',          # Use AAC for M4A container (required for M4A)
            '-ar', '44100',         # Set sample rate to 44100 Hz
            '-b:a', '256k',          # Set bitrate to 256 kbps
            '-y',                   # Overwrite output file without asking
            output_file 
        ])

        # --- Step 3: Run FFmpeg Process (Progress Tracking remains the same) ---
        duration_seconds = 0
        try:
            ffprobe_cmd = self.ffmpeg_command.replace('ffmpeg', 'ffprobe')
            duration_proc = subprocess.run([ffprobe_cmd, '-v', 'error', '-show_entries', 'format=duration', 
                                             '-of', 'default=noprint_wrappers=1:nokey=1', input_file], 
                                            capture_output=True, text=True, check=True, shell=self.use_shell,
                                            creationflags=0x08000000 if os.name == 'nt' else 0)
            duration_seconds = float(duration_proc.stdout.strip())
        except Exception:
            self._update_status("Warning: Could not determine file duration for progress tracking.")
            duration_seconds = 0 
            
        time_re = re.compile(r'time=(\d{2}:\d{2}:\d{2}\.\d{2})')
        
        popen_kwargs = {
            'stdout': subprocess.PIPE, 
            'stderr': subprocess.PIPE, 
            'universal_newlines': True,
            'shell': self.use_shell
        }
        if os.name == 'nt': 
            CREATE_NO_WINDOW = 0x08000000
            popen_kwargs['creationflags'] = CREATE_NO_WINDOW
        
        conversion_success = False

        try:
            process = subprocess.Popen(cmd, **popen_kwargs)
            
            # Read stderr for progress
            while True:
                line = process.stderr.readline()
                if not line:
                    break
                
                match = time_re.search(line)
                if match and duration_seconds > 0:
                    time_str = match.group(1)
                    h, m, s = map(float, time_str.split(':'))
                    current_time = h * 3600 + m * 60 + s

                    if duration_seconds > 0:
                        percentage = (current_time / duration_seconds) * 100
                        percentage = min(99, int(percentage)) 
                        
                        self._update_progress(percentage)
                        self._update_status(f"Converting: {timedelta(seconds=int(current_time))} / {timedelta(seconds=int(duration_seconds))} ({percentage}%)")

            return_code = process.wait()

            if return_code != 0:
                # Read the remaining error output for better diagnostics
                error_output = process.stderr.read()
                self._finish_process(False, f"FFmpeg conversion failed with exit code {return_code}.\nOutput: {error_output}")
                return
            
            # If we reach here, conversion was successful
            conversion_success = True
            
        except Exception as e:
            self._finish_process(False, f"An unexpected error occurred during conversion: {e}")
            return
        finally:
            # --- Step 4: Cleanup ---
            self._cleanup_temp_files()
        
        # --- Step 5: Finalize ---
        if conversion_success:
            self._update_progress(100)
            self._finish_process(True, f"Conversion Complete! File properties should now be correct.\nOutput: '{os.path.basename(output_file)}'")
            


if __name__ == "__main__":
    root = tk.Tk()
    app = FlacToM4AConverterGUI(root)
    root.mainloop()