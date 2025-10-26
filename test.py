import sys
import threading
import time
import re
import subprocess
import json
import math
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QFrame, QMenu, 
                            QListWidget, QListWidgetItem, QMessageBox, QScrollArea,
                            QFileDialog, QDialog, QFormLayout, QLineEdit, QProgressBar)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QPoint, QRect, QSize, QStandardPaths
from PyQt6.QtGui import QFont, QPalette, QColor, QPainter, QPixmap, QAction, QLinearGradient, QBrush

class LogMonitorThread(QThread):
    """Thread for monitoring log file"""
    class_detected = pyqtSignal(str, str)  # class_name, player_name
    combat_started = pyqtSignal()
    combat_ended = pyqtSignal()
    
    def __init__(self, log_file_path):
        super().__init__()
        self.log_file = Path(log_file_path)
        self.monitoring = True
        self.last_position = 0
        self.detected_classes = {}  # Store detected classes and players
        self.in_combat = False
        
        # Initialize position to end of file to ignore existing content
        self.initialize_position_to_end()
    
    def initialize_position_to_end(self):
        """Set the file position to the end to ignore existing content"""
        try:
            if self.log_file.exists():
                with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(0, 2)  # Seek to end of file
                    self.last_position = f.tell()
                print(f"DEBUG: Log monitor initialized at position {self.last_position} (end of file)")
            else:
                print("DEBUG: Log file doesn't exist yet, will start from beginning when created")
        except Exception as e:
            print(f"DEBUG: Error initializing log position: {e}")
            self.last_position = 0
        
    def run(self):
        """Monitor log file for changes"""
        consecutive_errors = 0
        max_errors = 5
        
        while self.monitoring:
            try:
                if self.log_file.exists():
                    with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(self.last_position)
                        new_lines = f.readlines()
                        self.last_position = f.tell()
                        
                        if new_lines:
                            for line in new_lines:
                                line = line.strip()
                                if line:
                                    self.process_line(line)
                            
                            consecutive_errors = 0
                        else:
                            time.sleep(0.1)
                else:
                    time.sleep(1)
                    consecutive_errors = 0
                
            except Exception as e:
                consecutive_errors += 1
                print(f"Error monitoring log file: {e}")
                
                if consecutive_errors >= max_errors:
                    print(f"Too many consecutive errors, stopping monitoring")
                    break
                
                sleep_time = min(1 * (2 ** consecutive_errors), 10)
                time.sleep(sleep_time)
    
    def process_line(self, line):
        """Process a log line for class detection"""
        # Check for combat start
        if "[Information (combat)]" in line and "lance le sort" in line:
            if not self.in_combat:
                self.in_combat = True
                self.combat_started.emit()
                print(f"DEBUG: Combat started")
        
        # Check for combat end
        if "Combat terminé, cliquez ici pour rouvrir l'écran de fin de combat." in line:
            if self.in_combat:
                self.in_combat = False
                self.combat_ended.emit()
                print(f"DEBUG: Combat ended")
                return
        
        # Only process combat lines for class detection
        if "[Information (combat)]" not in line or "lance le sort" not in line:
            return
        
        # Extract player and spell info
        spell_match = re.search(r'\[Information \(combat\)\] ([^:]+)[:\s]+lance le sort ([^(]+)', line)
        if not spell_match:
            return
        
        player_name = spell_match.group(1).strip()
        spell_name = spell_match.group(2).strip()
        
        # Detect class based on spells
        detected_class = self.detect_class(spell_name)
        if detected_class and detected_class not in self.detected_classes:
            self.detected_classes[detected_class] = player_name
            print(f"DEBUG: {detected_class} detected: {player_name}")
            self.class_detected.emit(detected_class, player_name)
    
    def detect_class(self, spell_name):
        """Detect class based on spell name"""
        # Iop spells
        iop_spells = [
            "Épée céleste", "Fulgur", "Super Iop Punch", "Jugement", "Colère de Iop", 
            "Ébranler", "Roknocerok", "Fendoir", "Ravage", "Jabs", "Rafale", 
            "Torgnole", "Tannée", "Épée de Iop", "Bond", "Focus", "Éventrail", "Uppercut"
        ]
        
        # Cra spells
        cra_spells = [
            "Flèche criblante", "Flèche fulminante", "Flèche d'immolation", 
            "Flèche enflammée", "Flèche Ardente", "Flèche explosive", 
            "Flèche cinglante", "Flèche perçante", "Flèche destructrice", 
            "Flèche chercheuse", "Flèche de recul", "Flèche tempête", 
            "Flèche harcelante", "Flèche statique", "Balise de destruction", 
            "Balise d'alignement", "Balise de contact", "Tir précis", "Débalisage", "Eclaireur",
            "Flèche lumineuse", "Pluie de flèches", "Roulade"
        ]
        
        if spell_name.lower() in (s.lower() for s in iop_spells):
            return "Iop"
        elif spell_name.lower() in (s.lower() for s in cra_spells):
            return "Cra"
        
        return None
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False

if __name__ == "__main__":

    line = "Bob : lance le sort Fulgur"


        

    