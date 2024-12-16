import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sqlite3
import os
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
import re
import time

class VoiceMemosExporter:
    def __init__(self, root):
        self.root = root
        self.root.title("Voice Memos Exporter")
        self.root.geometry("600x400")
        
        # Create and set up the main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Output directory selection
        self.output_path = tk.StringVar(value=str(Path.home() / "Desktop" / "Exported Voice Memos"))
        ttk.Label(self.main_frame, text="Export Location:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(self.main_frame, textvariable=self.output_path, width=50).grid(row=0, column=1, sticky=tk.W+tk.E, padx=5)
        ttk.Button(self.main_frame, text="Browse", command=self.browse_output).grid(row=0, column=2, sticky=tk.W)

        # Status text
        self.status_text = tk.Text(self.main_frame, height=15, width=60, wrap=tk.WORD)
        self.status_text.grid(row=1, column=0, columnspan=3, pady=10)
        
        # Progress bar
        self.progress = ttk.Progressbar(self.main_frame, mode='determinate')
        self.progress.grid(row=2, column=0, columnspan=3, sticky=tk.W+tk.E, pady=5)
        
        # Export button
        ttk.Button(self.main_frame, text="Export Voice Memos", command=self.start_export).grid(row=3, column=0, columnspan=3, pady=10)
        
        # Configure grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)

    def browse_output(self):
        directory = filedialog.askdirectory(initialdir=self.output_path.get())
        if directory:
            self.output_path.set(directory)

    def log_message(self, message):
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)
        self.root.update()

    def get_voice_memos_path(self):
        home = Path.home()
        return home / "Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings"

    def format_date(self, mac_timestamp):
        mac_epoch = datetime(2001, 1, 1, tzinfo=timezone.utc)
        return mac_epoch + timedelta(seconds=mac_timestamp)

    def sanitize_filename(self, filename):
        if not filename:
            return "Untitled Recording"
        filename = re.sub(r'[<>:"/\\|?*]', '-', filename)
        filename = filename.strip('. ')
        return filename

    def check_database_access(self, db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            conn.close()
            return True
        except sqlite3.Error:
            return False

    def start_export(self):
        try:
            # Reset progress bar
            self.progress['value'] = 0
            self.status_text.delete(1.0, tk.END)
            
            # Get paths
            voice_memos_dir = self.get_voice_memos_path()
            db_path = voice_memos_dir / "CloudRecordings.db"
            export_path = Path(self.output_path.get())
            
            self.log_message(f"Looking for database at: {db_path}")
            
            if not db_path.exists():
                raise FileNotFoundError("Could not find Voice Memos database")
            
            if not self.check_database_access(db_path):
                messagebox.showwarning(
                    "Permission Required",
                    "This app needs Full Disk Access to read Voice Memos.\n\n"
                    "1. Open System Settings > Privacy & Security\n"
                    "2. Scroll to Full Disk Access\n"
                    "3. Click '+' and add Terminal or your Python IDE\n"
                    "4. Make sure it's checked to enable access"
                )
                return
            
            # Create export directory
            export_path.mkdir(parents=True, exist_ok=True)
            
            # Connect to database
            self.log_message("Connecting to database...")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get recordings
            cursor.execute("""
                SELECT ZPATH, ZENCRYPTEDTITLE, ZDATE, ZDURATION
                FROM ZCLOUDRECORDING
                WHERE ZPATH IS NOT NULL
            """)
            recordings = cursor.fetchall()
            
            self.log_message(f"\nFound {len(recordings)} voice memos")
            self.progress['maximum'] = len(recordings)
            
            # Export each recording
            for i, (path, title, date_timestamp, duration) in enumerate(recordings, 1):
                try:
                    source_file = voice_memos_dir / path
                    
                    if not source_file.exists():
                        self.log_message(f"Warning: Source file not found: {source_file}")
                        continue
                    
                    # Format the date
                    recording_date = self.format_date(date_timestamp)
                    date_str = recording_date.strftime("%Y-%m-%d")
                    
                    # Use title if available, otherwise use original filename
                    display_title = title if title else Path(path).stem
                    display_title = self.sanitize_filename(display_title)
                    
                    # Create new filename
                    new_filename = f"{date_str} - {display_title}.m4a"
                    dest_file = export_path / new_filename
                    
                    # Handle duplicates
                    counter = 1
                    while dest_file.exists():
                        new_filename = f"{date_str} - {display_title} ({counter}).m4a"
                        dest_file = export_path / new_filename
                        counter += 1
                    
                    # Copy the file
                    shutil.copy2(source_file, dest_file)
                    self.log_message(f"Exported: {new_filename}")
                    
                    # Update progress
                    self.progress['value'] = i
                    self.root.update()
                    
                except Exception as e:
                    self.log_message(f"Error exporting {path}: {e}")
            
            conn.close()
            messagebox.showinfo("Success", f"Export completed!\nFiles saved to:\n{export_path}")
            
        except Exception as e:
            messagebox.showerror("Error", str(e))

def main():
    root = tk.Tk()
    app = VoiceMemosExporter(root)
    root.mainloop()

if __name__ == '__main__':
    main()