import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sqlite3
import os
import shutil
from datetime import datetime, timedelta
import re
import subprocess

class VoiceMemosExporter:
    def __init__(self, root):
        self.root = root
        self.root.title("Voice Memos Exporter")
        
        # Configure root window
        self.root.geometry("1000x600")
        self.root.minsize(800, 400)
        
        # Variables
        self.selected_items = set()
        self.db_path = os.path.expanduser("~/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings/CloudRecordings.db")
        self.recordings_path = os.path.dirname(self.db_path)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.filter_recordings)
        
        # Create GUI elements
        self.create_widgets()
        
        # Load recordings
        self.load_recordings()

    def open_security_preferences(self):
        """Open System Preferences at Security & Privacy > Privacy > Full Disk Access"""
        try:
            subprocess.run(['open', 'x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles'])
        except Exception as e:
            print(f"Error opening System Preferences: {e}")

    def show_permissions_dialog(self):
        """Show a custom dialog with instructions for granting Full Disk Access"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Full Disk Access Required")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()

        warning_label = ttk.Label(dialog, text="⚠️", font=('TkDefaultFont', 48))
        warning_label.pack(pady=10)

        ttk.Label(dialog, text="Full Disk Access Required", font=('TkDefaultFont', 14, 'bold')).pack(pady=5)
        
        instructions = ttk.Frame(dialog)
        instructions.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        steps = [
            "1. Click 'Open Security Settings' below",
            "2. Click the lock 🔒 icon to make changes",
            "3. Click + to add an application",
            "4. Navigate to Terminal.app or your Python application",
            "   (usually in /Applications/Utilities/Terminal.app)",
            "5. Select the application and click Open",
            "6. Ensure the checkbox next to the application is selected",
            "7. Restart this application"
        ]
        
        for step in steps:
            ttk.Label(instructions, text=step, wraplength=400).pack(anchor='w', pady=2)

        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=20, pady=20)
        
        ttk.Button(button_frame, text="Open Security Settings", 
                  command=lambda: [self.open_security_preferences(), dialog.destroy()]).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", 
                  command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Search frame
        search_frame = ttk.Frame(main_frame)
        search_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Create treeview with title column
        self.tree = ttk.Treeview(main_frame, columns=('title', 'date', 'duration', 'checked'), show='headings')
        self.tree.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure treeview columns
        self.tree.heading('title', text='Title')
        self.tree.heading('date', text='Date')
        self.tree.heading('duration', text='Duration')
        self.tree.heading('checked', text='Select ☐')
        
        self.tree.column('title', width=300)
        self.tree.column('date', width=200)
        self.tree.column('duration', width=100)
        self.tree.column('checked', width=80, anchor='center')
        
        # Style configuration for better visibility
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=1, column=2, sticky=(tk.N, tk.S))
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Button frame with descriptions
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Left side buttons with descriptions
        left_frame = ttk.Frame(button_frame)
        left_frame.pack(side=tk.LEFT)
        
        ttk.Button(left_frame, text="Select All", command=self.select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_frame, text="Deselect All", command=self.deselect_all).pack(side=tk.LEFT, padx=5)
        ttk.Label(left_frame, text="Click checkbox column to select individual items").pack(side=tk.LEFT, padx=10)
        
        # Right side export button
        ttk.Button(button_frame, text="Export Selected", command=self.export_selected).pack(side=tk.RIGHT, padx=5)
        
        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Bind click event
        self.tree.bind('<Button-1>', self.on_click)

    def filter_recordings(self, *args):
        """Filter recordings based on search term"""
        search_term = self.search_var.get().lower()
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            if any(search_term in str(value).lower() for value in values):
                self.tree.reattach(item, '', 'end')
            else:
                self.tree.detach(item)

    def load_recordings(self):
        try:
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Query recordings with title
            cursor.execute("""
                SELECT ZPATH, ZENCRYPTEDTITLE, ZDATE, ZDURATION 
                FROM ZCLOUDRECORDING 
                ORDER BY ZDATE DESC
            """)
            
            # Clear existing items
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Insert recordings into treeview
            for path, title, date, duration in cursor.fetchall():
                if path:  # Only process if path exists
                    # Use title if available, otherwise use filename
                    display_title = title if title else os.path.splitext(os.path.basename(path))[0]
                    
                    # Convert date from Apple timestamp (seconds since 2001) to Python datetime
                    date_obj = datetime(2001, 1, 1) + timedelta(seconds=date)
                    date_str = date_obj.strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Format duration
                    duration_str = f"{int(duration // 60)}:{int(duration % 60):02d}"
                    
                    # Insert into treeview
                    self.tree.insert('', 'end', values=(display_title, date_str, duration_str, '☐'), tags=('unchecked',))
            
            conn.close()
            
        except sqlite3.Error as e:
            self.show_permissions_dialog()
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def on_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            if column == "#4":  # Check if clicking the 'checked' column
                item = self.tree.identify_row(event.y)
                self.toggle_item(item)

    def toggle_item(self, item):
        if item in self.selected_items:
            self.selected_items.remove(item)
            self.tree.set(item, 'checked', '☐')
        else:
            self.selected_items.add(item)
            self.tree.set(item, 'checked', '☑')

    def select_all(self):
        for item in self.tree.get_children():
            if item not in self.selected_items:
                self.selected_items.add(item)
                self.tree.set(item, 'checked', '☑')

    def deselect_all(self):
        for item in self.selected_items:
            self.tree.set(item, 'checked', '☐')
        self.selected_items.clear()

    def export_selected(self):
        if not self.selected_items:
            messagebox.showwarning("No Selection", "Please select at least one recording to export.")
            return
        
        # Ask for export directory
        export_dir = filedialog.askdirectory(title="Select Export Directory")
        if not export_dir:
            return
            
        try:
            # Create progress bar
            progress_window = tk.Toplevel(self.root)
            progress_window.title("Exporting...")
            progress_window.geometry("300x150")
            progress_window.transient(self.root)
            
            progress_label = ttk.Label(progress_window, text="Exporting recordings...")
            progress_label.pack(pady=10)
            
            progress_var = tk.DoubleVar()
            progress_bar = ttk.Progressbar(progress_window, variable=progress_var, maximum=len(self.selected_items))
            progress_bar.pack(pady=10, padx=20, fill=tk.X)
            
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            exported_count = 0
            for item in self.selected_items:
                values = self.tree.item(item)['values']
                title = values[0]
                date_str = values[1]
                
                # Query the actual file path
                cursor.execute("""
                    SELECT ZPATH 
                    FROM ZCLOUDRECORDING 
                    WHERE datetime(ZDATE + 978307200, 'unixepoch') = ? 
                    AND (ZENCRYPTEDTITLE = ? OR ZPATH LIKE ?)
                """, (date_str, title, f"%{os.path.basename(title)}%"))
                result = cursor.fetchone()
                
                if result and result[0]:
                    source_path = os.path.join(self.recordings_path, result[0])
                    if os.path.exists(source_path):
                        # Create destination path with original filename
                        dest_path = os.path.join(export_dir, os.path.basename(source_path))
                        
                        # Handle duplicate filenames
                        base, ext = os.path.splitext(dest_path)
                        counter = 1
                        while os.path.exists(dest_path):
                            dest_path = f"{base}_{counter}{ext}"
                            counter += 1
                        
                        # Copy file
                        shutil.copy2(source_path, dest_path)
                        exported_count += 1
                        
                        # Update progress
                        progress_var.set(exported_count)
                        progress_window.update()
            
            conn.close()
            progress_window.destroy()
            
            messagebox.showinfo("Export Complete", f"Successfully exported {exported_count} recordings to {export_dir}")
            
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error accessing database: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during export: {str(e)}")

def main():
    root = tk.Tk()
    app = VoiceMemosExporter(root)
    root.mainloop()

if __name__ == "__main__":
    main()
