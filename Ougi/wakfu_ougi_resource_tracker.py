#!/usr/bin/env python3
"""
Wakfu Ougi Class Resource Tracker - Full Screen Overlay System
Full-screen transparent overlay with draggable icons anywhere on screen
Tracks rage and tracker resources in real-time from chat logs
"""

import sys
import threading
import time
import re
import math
import json
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QProgressBar, QFrame, QMenu)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QPoint, QRect
from PyQt6.QtGui import QFont, QPalette, QColor, QPainter, QLinearGradient, QBrush, QPixmap, QPen, QAction
from PyQt6.QtWidgets import QGraphicsOpacityEffect

class LogMonitorThread(QThread):
    """Thread for monitoring log file"""
    log_updated = pyqtSignal(str)
    
    def __init__(self, log_file_path):
        super().__init__()
        self.log_file = Path(log_file_path)
        self.monitoring = True
        self.last_position = 0
        
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
                                    # Debug: Log when we emit a line
                                    if "lance le sort" in line:
                                        timestamp = time.strftime("%H:%M:%S")
                                        print(f"DEBUG [{timestamp}]: LogMonitor emitting spell line: {line[:80]}...")
                                    self.log_updated.emit(line)
                            
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
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False

class OutlinedLabel(QLabel):
    """QLabel with outlined text (white text with black border)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.text_to_draw = ""
    
    def setText(self, text):
        """Override setText to store text and trigger repaint"""
        self.text_to_draw = text
        super().setText(text)
        self.update()
    
    def get_resource_color(self, text):
        """Get color based on resource type"""
        if "PA" in text:
            return QColor(0, 150, 255)  # Bright blue for PA
        elif "PM" in text:
            return QColor(0, 128, 0)   # Green for PM
        elif "PW" in text:
            return QColor(0, 206, 209) # Turquoise for PW
        else:
            return QColor(255, 255, 255)  # Default white
    
    def paintEvent(self, event):
        """Custom paint event to draw outlined text with colored resource types"""
        if not self.text_to_draw:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Parse text to separate number from resource type
        text = self.text_to_draw
        number_part = ""
        resource_part = ""
        
        # Extract number and resource type (e.g., "1PA" -> "1" and "PA")
        for i, char in enumerate(text):
            if char.isdigit():
                number_part += char
            else:
                resource_part = text[i:]
                break
        
        # Font sizes - make them closer in size for better alignment
        font_size_large = 9  # Larger font for numbers
        font_size_small = 8  # Smaller font for resource types (increased from 7)
        font_large = QFont('Segoe UI', font_size_large, QFont.Weight.Bold)
        font_small = QFont('Segoe UI', font_size_small, QFont.Weight.Bold)
        
        # Calculate metrics for both fonts
        painter.setFont(font_large)
        metrics_large = painter.fontMetrics()
        painter.setFont(font_small)
        metrics_small = painter.fontMetrics()
        
        # Calculate total width of the entire text
        number_width = metrics_large.boundingRect(number_part).width() if number_part else 0
        resource_width = metrics_small.boundingRect(resource_part).width() if resource_part else 0
        total_width = number_width + resource_width
        
        # Center the entire text block
        start_x = (self.width() - total_width) // 2
        y = (self.height() + metrics_large.height()) // 2
        
        # Draw number part (larger font)
        if number_part:
            painter.setFont(font_large)
            current_x = start_x
            
            # Draw black outline for number
            painter.setPen(QPen(QColor(0, 0, 0, 255), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx != 0 or dy != 0:
                        painter.drawText(current_x + dx, y + dy, number_part)
            
            # Draw number in white
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawText(current_x, y, number_part)
        
        # Draw resource part (smaller font) - positioned right after the number with small gap
        if resource_part:
            painter.setFont(font_small)
            # Position resource part right after the number with a small gap for clarity
            resource_x = start_x + number_width + 1  # Add 1 pixel gap
            
            # Draw black outline for resource
            painter.setPen(QPen(QColor(0, 0, 0, 255), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx != 0 or dy != 0:
                        painter.drawText(resource_x + dx, y + dy, resource_part)
            
            # Draw resource part in appropriate color
            resource_color = self.get_resource_color(resource_part)
            painter.setPen(QPen(resource_color, 1))
            painter.drawText(resource_x, y, resource_part)

class preyIcon(QLabel):
    """Custom tracker icon with fade animation support"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.fade_alpha = 0.0
        self._pixmap = None
    
    def setFadeAlpha(self, alpha):
        """Set the fade alpha value (0.0 to 1.0)"""
        self.fade_alpha = max(0.0, min(1.0, alpha))
        self.update()  # Trigger repaint
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set opacity based on fade alpha
        painter.setOpacity(self.fade_alpha)
        
        # Draw the icon itself
        if self._pixmap:
            painter.drawPixmap(3, 3, self._pixmap)
        
        painter.end()
    
    def setPixmap(self, pixmap):
        """Override to store pixmap for custom drawing"""
        self._pixmap = pixmap
        super().setPixmap(pixmap)

class rageIcon(QLabel):
    """Custom rage icon with fade animation support"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.fade_alpha = 0.0
        self._pixmap = None
    
    def setFadeAlpha(self, alpha):
        """Set the fade alpha value (0.0 to 1.0)"""
        self.fade_alpha = max(0.0, min(1.0, alpha))
        self.update()  # Trigger repaint
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set opacity based on fade alpha
        painter.setOpacity(self.fade_alpha)
        
        # Draw the icon itself
        if self._pixmap:
            painter.drawPixmap(3, 3, self._pixmap)
        
        painter.end()
    
    def setPixmap(self, pixmap):
        """Override to store pixmap for custom drawing"""
        self._pixmap = pixmap
        super().setPixmap(pixmap)

class rageProgressBar(QProgressBar):
    """Custom progress bar for rage with modern animated gradient"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.decimal_value = 0
        self.target_value = 0
        self.smooth_value = 0
        self.smooth_transitions = True
        self.animation_frame = 0
        self.showing_red = False
        self.red_animation_frames = 0
        
        # Smooth transition variables
        self.transition_speed = 0.12  # How fast the bar moves toward target (smooth for high FPS)
        self.is_transitioning = False
        
        # Separate high-frequency timer for progress bar only
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.update_animation)
        self.progress_timer.start(16)  # ~60 FPS for smooth progress bar only
        
        # Animation variables for gradient progression
        self.gradient_animation_speed = 0.02
        self.gradient_offset = 0
        self.gradient_phase = 0
        
        self.setFixedHeight(24)
        self.setFixedWidth(250)
        self.setRange(0, 100)
        self.setValue(0)
        
        # Hide default text
        self.setTextVisible(False)
        
        # Ultra minimal styling (like Crâ)
        self.setStyleSheet(self.get_minimal_style())
        
    def setValue(self, value):
        """Override setValue to handle decimal values and red animation"""
        self.target_value = float(value)
        self.is_transitioning = True
        
        # Check if we're reaching 100 (should trigger red animation)
        if self.target_value >= 100 and not self.showing_red:
            self.showing_red = True
            self.red_animation_frames = 30  # Show red for 30 frames
        
        super().setValue(int(self.target_value))
    
    def update_animation(self):
        """Update gradient animation and smooth value transitions"""
        # Update gradient animation (back to original speed)
        self.gradient_phase += self.gradient_animation_speed
        self.gradient_offset = math.sin(self.gradient_phase) * 0.3 + 0.7  # Oscillate between 0.4 and 1.0
        
        # Handle smooth value transitions
        if self.is_transitioning:
            # Calculate the difference between current and target
            difference = self.target_value - self.decimal_value
            
            # If we're close enough to the target, snap to it
            if abs(difference) < 0.1:
                self.decimal_value = self.target_value
                self.is_transitioning = False
            else:
                # Move toward target at the specified speed
                self.decimal_value += difference * self.transition_speed
        
        self.update()
    
    
    def paintEvent(self, event):
        """Custom paint event with modern animated gradient and text"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate progress percentage
        progress = self.decimal_value / 100.0
        bar_width = int(self.width() * progress)
        
        # Create animated gradient based on progress
        gradient = QLinearGradient(0, 0, self.width(), 0)
        
        if progress < 0.3:
            # Low rage: Cool blue tones
            gradient.setColorAt(0, QColor(64, 181, 246, int(200 * self.gradient_offset)))      # Light blue
            gradient.setColorAt(1, QColor(33, 150, 243, int(255 * self.gradient_offset)))     # Blue
        elif progress < 0.7:
            # Medium rage: Blue to cyan transition
            gradient.setColorAt(0, QColor(33, 150, 243, int(220 * self.gradient_offset)))     # Blue
            gradient.setColorAt(0.5, QColor(0, 188, 212, int(240 * self.gradient_offset)))    # Cyan
            gradient.setColorAt(1, QColor(0, 172, 193, int(255 * self.gradient_offset)))     # Dark cyan
        else:
            # High rage: Cyan to electric blue
            gradient.setColorAt(0, QColor(0, 172, 193, int(240 * self.gradient_offset)))     # Dark cyan
            gradient.setColorAt(0.5, QColor(3, 169, 244, int(255 * self.gradient_offset)))   # Electric blue
            gradient.setColorAt(1, QColor(0, 123, 255, int(255 * self.gradient_offset)))     # Bright blue
        
        # Draw background
        painter.fillRect(0, 0, self.width(), self.height(), QColor(0, 0, 0, 77))  # Semi-transparent black
        
        # Draw animated progress bar
        if bar_width > 0:
            painter.fillRect(0, 0, bar_width, self.height(), QBrush(gradient))
        
        # Draw border
        painter.setPen(QPen(QColor(51, 51, 51, 255), 2))
        painter.drawRect(0, 0, self.width()-1, self.height()-1)
        
        # Set font
        font = QFont('Segoe UI', 16, QFont.Weight.Bold)
        painter.setFont(font)
        
        # Get text - use decimal_value for accurate display
        text = f"{round(self.decimal_value)}/100"
        
        # Get text metrics
        metrics = painter.fontMetrics()
        text_rect = metrics.boundingRect(text)
        
        # Center the text
        x = (self.width() - text_rect.width()) // 2
        y = (self.height() + text_rect.height()) // 2 - metrics.descent()
        
        # Draw black outline (border)
        painter.setPen(QPen(QColor(0, 0, 0), 3))
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                if dx != 0 or dy != 0:
                    painter.drawText(x + dx, y + dy, text)
        
        # Draw white text
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawText(x, y, text)
        
        painter.end()
        
    def get_minimal_style(self):
        """Get transparent style since we're using custom painting"""
        return """
            QProgressBar {
                border: none;
                background-color: transparent;
                text-align: center;
            }
        """

class DraggableIcon(QLabel):
    """Draggable icon widget"""
    
    def __init__(self, icon_path, icon_size=64, parent=None):
        super().__init__(parent)
        self.icon_path = icon_path
        self.icon_size = icon_size
        self.is_locked = False
        self.drag_start_position = QPoint()
        
        self.setFixedSize(icon_size, icon_size)
        self.setScaledContents(True)
        
        # Load and set icon
        if Path(icon_path).exists():
            pixmap = QPixmap(icon_path)
            self.setPixmap(pixmap.scaled(icon_size, icon_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            print(f"Warning: Icon not found at {icon_path}")
            # Create a placeholder
            self.setStyleSheet("background-color: rgba(100, 100, 100, 100); border: 2px solid white;")
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Initially hidden
        self.hide()
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging"""
        if event.button() == Qt.MouseButton.LeftButton and not self.is_locked:
            self.drag_start_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging"""
        if event.buttons() == Qt.MouseButton.LeftButton and not self.is_locked:
            self.move(event.globalPosition().toPoint() - self.drag_start_position)
    
    def show_icon(self):
        """Show the icon"""
        self.show()
    
    def hide_icon(self):
        """Hide the icon"""
        self.hide()

class WakfuOugiResourceTracker(QMainWindow):
    """Main window for Ougi resource tracker"""

    def __init__(self, hidden_mode=False):
        super().__init__()
        
        # Store hidden mode
        self.hidden_mode = hidden_mode
        
        # Resource tracking variables
        self.rage = 0
        self.tracker = 0
        self.tracker = 0
        self.prey = False
        self.rage = 0
        self.current_rage = 0
        self.current_tracker = 0
        self.current_tracker = 0
        self.current_prey = False
        self.current_rage = 0
        
        # Préparation Damage Confirmation System
        self.pending_rage_loss = False  # True when waiting for damage confirmation
        self.rage_loss_caster = None  # Player who cast spell that should remove rage
        self.rage_loss_spell = None  # Spell that should remove rage
        self.in_combat = False
        
        # Player tracking
        self.tracked_player_name = None  # Track the player we're monitoring
        
        # Combat detection
        self.is_sac_patate_combat = False  # Track if we're fighting Sac à patate
        
        # Turn-based visibility system
        self.is_ougi_turn = False  # Track if it's currently the Iop's turn
        self.overlay_visible = False  # Track if overlay should be visible
        self.iop_spells = ["Épée céleste", "Fulgur", "Super Iop Punch", "Jugement", "Colère de Iop", 
                          "Ébranler", "Roknocerok", "Fendoir", "Ravage", "Jabs", "Rafale", 
                          "Torgnole", "Tannée", "Épée de Iop", "Bond", "Focus", "Éventrail", "Uppercut",
                          "Amplification", "Duel", "Étendard de bravoure", "Vertu", "Charge"]
        
        # Duplicate prevention system
        self.processed_lines = set()  # Track processed log lines to prevent duplicates
        
        # Turn tracking
        self.last_spell_caster = None  # Track the last player who cast a spell
        self.last_etendard_cast = False  # Track if Étendard de bravoure was just cast
        self.last_bond_cast = False  # Track if Bond was just cast
        self.last_charge_cast = False  # Track if Charge was just cast
        
        # Animation variables
        self.animation_frame = 0
        self.smooth_transitions = False  # Disable smooth transitions for more responsive updates
        
        # tracker icon animation - realistic bouncing physics
        self.tracker_bounce_offset = 0
        self.tracker_bounce_velocity = 0  # Current velocity (pixels per frame)
        self.tracker_bounce_gravity = 1.2  # Gravity acceleration (faster)
        self.tracker_bounce_damping = 0.7  # Energy loss on bounce (0.7 = loses 30% energy each bounce)
        self.tracker_bounce_min_velocity = 0.3  # Stop bouncing when velocity is very small
        self.tracker_ground_level = 0  # Ground level (normal position)
        
        # Égaré icon animation variables
        self.prey_fade_alpha = 0.0  # Current opacity (0.0 to 1.0)
        self.prey_target_alpha = 0.0  # Target opacity
        # Use separate speeds for fade-in and fade-out for better feel
        self.prey_fade_in_speed = 0.08   # per frame when fading in
        self.prey_fade_out_speed = 0.14  # per frame when fading out (faster)
        self.prey_visible = False  # Track on-screen visibility for debug
        self.prey_slide_offset = 0  # Slide-in offset (pixels)
        self.prey_slide_speed = 2  # Pixels per frame during fade-in (faster)
        self.prey_slide_max = 14  # Start this many pixels above and slide down

        # Préparation icon animation variables
        self.rage_fade_alpha = 0.0  # Current opacity (0.0 to 1.0)
        self.rage_target_alpha = 0.0  # Target opacity
        self.rage_fade_in_speed = 0.08   # per frame when fading in
        self.rage_fade_out_speed = 0.14  # per frame when fading out (faster)
        self.rage_visible = False  # Track on-screen visibility for debug
        self.rage_slide_offset = 0  # Slide-in offset (pixels)
        self.rage_slide_speed = 2  # Pixels per frame during fade-in (faster)
        self.rage_slide_max = 14  # Start this many pixels above and slide down

        # Préparation bounce animation variables
        self.rage_bounce_offset = 0
        self.rage_bounce_velocity = 0  # Current velocity (pixels per frame)
        self.rage_bounce_gravity = 2.0  # Gravity acceleration (faster)
        self.rage_bounce_damping = 0.6  # Energy loss on bounce (0.6 = loses 40% energy each bounce, faster decay)
        self.rage_bounce_min_velocity = 0.5  # Stop bouncing when velocity is very small (higher threshold)
        self.rage_bounce_ground_level = 0  # Ground level (normal position)
        self.rage_bounce_delay = 0  # Delay before bouncing starts (frames)
        self.rage_bounce_delay_max = 15  # Wait 15 frames (0.25 seconds at 60fps) before bouncing (faster)
        self.rage_bounce_loop_delay = 0  # Delay between bounce loops (frames)
        self.rage_bounce_loop_delay_max = 30  # Wait 30 frames (0.5 seconds) between bounce loops (faster)
        self.rage_bounce_loop_active = False  # Whether continuous bouncing is active

        # Debug state tracking to prevent spam
        self.last_tracker_bars_state = 0  # Track last tracker bars count
        self.last_tracker_state = 0  # Track last tracker state
        self.last_rage_state = 0  # Track last rage state
        self.last_tracker_hidden_debug = False  # Track if tracker hidden debug was printed
        self.last_tracker_hidden_debug = False  # Track if tracker hidden debug was printed
        self.last_rage_hidden_debug = False  # Track if rage hidden debug was printed

        # Cast timeline (last 5 casts by tracked player)
        self.timeline_max_slots = 5
        self.timeline_entries = []  # list[{ 'spell': str, 'icon': QPixmap, 'cost': str }]
        self.timeline_icon_labels = []
        self.timeline_cost_labels = []
        self.spell_icon_stem_map = {
            "Épée céleste": "epeeceleste",
            "Fulgur": "fulgur",
            "Super Iop Punch": "superioppunch",
            "Jugement": "jugement",
            "Colère de Iop": "colere",
            "Ébranler": "ebranler",
            "Roknocerok": "roknocerok",
            "Fendoir": "fendoir",
            "Ravage": "ravage",
            "Jabs": "jabs",
            "Rafale": "rafale",
            "Torgnole": "torgnole",
            "Tannée": "tannee",
            "Épée de Iop": "epeeduiop",
            "Bond": "bond",
            "Focus": "Focus",
            "Éventrail": "eventrail",
            "Uppercut": "uppercut",
            "Amplification": "Amplification",
            "Duel": "Duel",
            "Étendard de bravoure": "Etandard",
            "Vertu": "Vertu",
            "Charge": "charge",
        } #TODO : change name of spells
        
        # Paths
        # Get the directory where the script is located (works for both script and executable)
        if getattr(sys, 'frozen', False):
            # Running as executable - look in the bundled Iop folder
            self.base_path = Path(sys._MEIPASS) / "Iop"
        else:
            # Running as script
            self.base_path = Path(__file__).parent
        self.rage_icon_path = self.base_path / "img" / "rage.png"
        self.tracker_icon_path = self.base_path / "img" / "Couroux.png"
        self.prey_icon_path = self.base_path / "img" / "tracker.png"
        self.rage_icon_path = self.base_path / "img" / "rage.png"
        
        # Log file path
        # Log file path - use default Wakfu logs location
        user_profile = Path.home()
        self.log_file_path = user_profile / "AppData" / "Roaming" / "zaap" / "gamesLogs" / "wakfu" / "logs" / "wakfu_chat.log"
        
        # Position saving
        self.positions_locked = False
        self.config_file = self.base_path / "positions_config.json"
        self.auto_save_timer = None
        self.drag_start_position = QPoint()
        self.dragging_rage = False
        self.dragging_rage = False
        self.rage_offset_x = 0  # Offset for rage icon from rage bar
        self.rage_offset_y = 0
        
        self.setup_ui()
        self.setup_log_monitoring()
        self.setup_animations()
        self.setup_shortcuts()
        
        # Load saved positions
        QTimer.singleShot(100, self.load_positions)
        
    
    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("Wakfu Ougi Resource Tracker")
        
        # Set window flags based on hidden mode
        if self.hidden_mode:
            # In hidden mode, use flags that hide from taskbar
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint | 
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.Tool |
                Qt.WindowType.X11BypassWindowManagerHint
            )
        else:
            # Normal mode
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint | 
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.Tool
            )
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Make window full screen
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        self.setGeometry(screen_geometry)
        
        # Main widget (full screen)
        main_widget = QWidget()
        main_widget.setLayout(QVBoxLayout())
        main_widget.layout().setContentsMargins(0, 0, 0, 0)
        
        # rage icon (positioned absolutely)
        self.rage_icon = QLabel()
        self.rage_icon.setFixedSize(28, 28)
        self.rage_icon.setScaledContents(True)
        self.rage_icon.setParent(main_widget)
        
        if self.rage_icon_path.exists():
            pixmap = QPixmap(str(self.rage_icon_path))
            self.rage_icon.setPixmap(pixmap.scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.rage_icon.setStyleSheet("background-color: transparent;")
        else:
            self.rage_icon.setText("🐶")
            self.rage_icon.setStyleSheet("""
                QLabel {
                    color: #64b5f6;
                    font-size: 20px;
                    font-weight: bold;
                    background-color: transparent;
                }
            """)
        
        # rage progress bar
        self.rage_bar = rageProgressBar()
        self.rage_bar.setParent(main_widget)
        
        # tracker icon (positioned absolutely, initially hidden)
        self.tracker_icon = QLabel()
        self.tracker_icon.setFixedSize(28, 28)
        self.tracker_icon.setScaledContents(True)
        self.tracker_icon.setParent(main_widget)
        self.tracker_icon.hide()
        
        if self.tracker_icon_path.exists():
            pixmap = QPixmap(str(self.tracker_icon_path))
            self.tracker_icon.setPixmap(pixmap.scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.tracker_icon.setStyleSheet("background-color: transparent;")
        else:
            self.tracker_icon.setText("⚡")
            self.tracker_icon.setStyleSheet("""
                QLabel {
                    color: #ff6b35;
                    font-size: 20px;
                    font-weight: bold;
                    background-color: transparent;
                }
            """)
        
        # tracker counter (positioned absolutely, initially hidden)
        self.tracker_counter = OutlinedLabel()
        self.tracker_counter.setFixedSize(28, 28)
        self.tracker_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tracker_counter.setParent(main_widget)
        self.tracker_counter.hide()
        
        # Préparation icon (positioned absolutely, initially hidden)
        self.rage_icon = QLabel()
        self.rage_icon.setFixedSize(40, 40)
        self.rage_icon.setScaledContents(True)
        self.rage_icon.setParent(main_widget)
        self.rage_icon.hide()
        
        if self.rage_icon_path.exists():
            pixmap = QPixmap(str(self.rage_icon_path))
            self.rage_icon.setPixmap(pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.rage_icon.setStyleSheet("background-color: transparent;")
        else:
            self.rage_icon.setText("📋")
            self.rage_icon.setStyleSheet("""
                QLabel {
                    color: #ff9800;
                    font-size: 28px;
                    font-weight: bold;
                    background-color: transparent;
                }
            """)
        
        # Préparation counter (positioned absolutely, initially hidden)
        self.rage_counter = OutlinedLabel()
        self.rage_counter.setFixedSize(40, 40)
        self.rage_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rage_counter.setParent(main_widget)
        self.rage_counter.hide()
        
        # tracker bars (2 small bars, initially hidden)
        self.tracker_bars = []
        for i in range(2):
            bar = QFrame()
            bar.setFixedSize(30, 6)  # Small horizontal bars
            bar.setParent(main_widget)
            bar.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 255, 255, 30);
                    border: 1px solid rgba(255, 255, 255, 50);
                    border-radius: 3px;
                }
            """)
            bar.hide()
            self.tracker_bars.append(bar)
        
        # prey icon (positioned above first Tracker bar, initially hidden)
        self.prey_icon = preyIcon()
        self.prey_icon.setFixedSize(24, 24)
        self.prey_icon.setScaledContents(True)
        self.prey_icon.setParent(main_widget)
        self.prey_icon.hide()
        
        if self.prey_icon_path.exists():
            pixmap = QPixmap(str(self.prey_icon_path))
            scaled_pixmap = pixmap.scaled(18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.prey_icon.setPixmap(scaled_pixmap)
        else:
            # Fallback to emoji if image not found
            self.prey_icon.setText("🎯")
            self.prey_icon.setStyleSheet("""
                QLabel {
                    color: #ff6b35;
                    font-size: 16px;
                    font-weight: bold;
                    background-color: transparent;
                }
            """)

        # Create timeline UI elements (icons and cost overlays)
        for _ in range(self.timeline_max_slots):
            # Icon label
            icon_label = QLabel()
            icon_label.setParent(main_widget)
            icon_label.setFixedSize(32, 32)
            icon_label.setScaledContents(True)
            icon_label.setStyleSheet("background-color: transparent;")
            icon_label.hide()
            self.timeline_icon_labels.append(icon_label)

            # Cost label below the icon using outlined white text
            cost_label = OutlinedLabel()
            cost_label.setParent(main_widget)
            cost_label.setFixedSize(32, 16)  # Give it a proper size
            cost_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cost_label.setStyleSheet("background-color: transparent;")
            cost_label.hide()
            self.timeline_cost_labels.append(cost_label)
        
        # Position elements (will be updated when visible)
        self.position_elements()
        
        # Initially hide all elements since we start out of combat
        self.rage_icon.hide()
        self.rage_bar.hide()
        
        self.setCentralWidget(main_widget)

    def position_elements(self):
        """Position all elements on screen"""
        # Get rage bar position
        base_x = self.rage_bar.x()
        base_y = self.rage_bar.y()
        
        # Position rage icon (left of bar)
        self.rage_icon.move(base_x - 35, base_y - 2)
        
        # Position tracker icon (right of bar)
        self.tracker_icon.move(base_x + 255, base_y - 2)
        
        # Position tracker counter (on top of tracker icon)
        self.tracker_counter.move(base_x + 255, base_y - 2)
        
        # Position rage icon (right of tracker + offset)
        self.rage_icon.move(base_x + 290 + self.rage_offset_x, base_y - 2 + self.rage_offset_y)
        
        # Position rage counter (on top of rage icon)
        self.rage_counter.move(base_x + 290 + self.rage_offset_x, base_y - 2 + self.rage_offset_y)
        
        # Position tracker bars (on top of rage bar)
        for i, bar in enumerate(self.tracker_bars):
            bar_x = base_x + (i * 35)  # 35px spacing between bars
            bar_y = base_y - 15  # 15px above the rage bar
            bar.move(bar_x, bar_y)

        # Position tracker icon (well above the first tracker bar - 10/50)
        tracker_x = base_x  # Same X position as first tracker bar
        # Apply slide-in offset during fade-in (start slightly above and slide down)
        slide_offset = getattr(self, 'tracker_slide_offset', 0)
        tracker_y = base_y - 50 - slide_offset
        self.tracker_icon.move(tracker_x, tracker_y)

        # Position timeline slots relative to rage bar
        timeline_icon_y = base_y + 30  # icons row
        slot_spacing = 32  # no gap between icons (same as icon width)
        icon_w, icon_h = 32, 32
        for i in range(self.timeline_max_slots):
            icon_x = base_x + (i * slot_spacing)
            # Icon position
            self.timeline_icon_labels[i].move(icon_x, timeline_icon_y)
            # Cost label below icon, centered horizontally
            cost_x = icon_x + (icon_w - 32) // 2  # Center the 32px wide cost label under the 32px icon
            cost_y = timeline_icon_y + icon_h - 2
            self.timeline_cost_labels[i].move(cost_x, cost_y)
    
    def setup_log_monitoring(self):
        """Setup log file monitoring"""
        self.log_monitor = LogMonitorThread(self.log_file_path)
        self.log_monitor.log_updated.connect(self.parse_log_line)
        self.log_monitor.start()
    
    def setup_animations(self):
        """Setup animation timers"""
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animations)
        self.animation_timer.start(50)  # 20 FPS (back to original)
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Close application
        close_action = QAction("Close", self)
        close_action.setShortcut("Ctrl+Q")
        close_action.triggered.connect(self.close)
        self.addAction(close_action)
        
        # Force close
        force_close_action = QAction("Force Close", self)
        force_close_action.setShortcut("Ctrl+Shift+Q")
        force_close_action.triggered.connect(lambda: sys.exit(0))
        self.addAction(force_close_action)
    
    def parse_log_line(self, line):
        """Parse log line for Ougir resources"""
        try:
            # Prevent duplicate processing of the same spell cast within a short time window
            # Extract the core content without timestamp for spell lines
            if "lance le sort" in line:
                # Extract player and spell info for duplicate detection
                spell_match = re.search(r'\[Information \(combat\)\] ([^:]+)[:\s]+lance le sort ([^(]+)', line)
                if spell_match:
                    player_name = spell_match.group(1).strip()
                    spell_name = spell_match.group(2).strip()
                    
                    # Use line hash for duplicate detection (same log line = duplicate)
                    line_hash = hash(line.strip())
                    if line_hash in self.processed_lines:
                        print(f"DEBUG: Skipping duplicate log line: {line.strip()[:50]}...")
                        return
                    
                    # Record this log line as processed
                    self.processed_lines.add(line_hash)
                    print(f"DEBUG: Processing new spell cast: {player_name}:{spell_name}")
                else:
                    # Fallback to line hash for non-spell lines
                    line_hash = hash(line.strip())
                    if line_hash in self.processed_lines:
                        print(f"DEBUG: Skipping duplicate line: {line.strip()[:50]}...")
                        return
                    self.processed_lines.add(line_hash)
            else:
                # For non-spell lines, use line hash
                line_hash = hash(line.strip())
                if line_hash in self.processed_lines:
                    print(f"DEBUG: Skipping duplicate line: {line.strip()[:50]}...")
                    return
                self.processed_lines.add(line_hash)
            
            # Keep only the last 1000 processed lines to prevent memory issues
            if len(self.processed_lines) > 1000:
                # Remove oldest entries (this is a simple approach)
                self.processed_lines = set(list(self.processed_lines)[-500:])
            # Check for Sac à patate combat start (check this FIRST - works on any line type)
            if "Sac à patate" in line and ("Quand tu auras fini de me frapper" in line or "abandonner" in line or "Abandonne le combat" in line):
                self.is_sac_patate_combat = True
            
            # Check for combat start and Iop turn detection - CONSOLIDATED SPELL PROCESSING
            if "lance le sort" in line:
                # Extract player name for spell cast lines; supports both "Name: lance le sort" and "Name lance le sort"
                player_spell_match = re.search(r'\[Information \(combat\)\]\s+([^:]+):\s+lance le sort', line)
                if not player_spell_match:
                    player_spell_match = re.search(r'\[Information \(combat\)\]\s+([^:]+)\s+lance le sort', line)

                # Extract spell name for debug purposes
                spell_name_match = re.search(r'lance le sort ([^\(\n]+)', line)
                spell_name = spell_name_match.group(1).strip() if spell_name_match else "?"

                # Extract caster name
                caster_name = None
                if player_spell_match:
                    caster_name = player_spell_match.group(1).strip()
                    # Track the last player who cast a spell (for turn end detection)
                    self.last_spell_caster = caster_name

                # Check if this is an Ougi spell (regardless of who casts it)
                is_ougi_spell = spell_name in self.ougi_spells

                # Turn-based visibility logic - handle first Ougi spell
                if is_ougi_spell:
                    # If no tracked player yet, set it to this caster (first Ougi spell)
                    if not self.tracked_player_name:
                        self.tracked_player_name = caster_name
                        print(f"DEBUG: Tracked player set to {self.tracked_player_name} on Ougi spell '{spell_name}'")
                
                # Determine if this cast is by the tracked player (after potentially setting tracked_player_name)
                is_tracked_caster = False
                if caster_name and self.tracked_player_name:
                    is_tracked_caster = (caster_name.strip() == self.tracked_player_name.strip())
                
                timestamp = time.strftime("%H:%M:%S")
                print(f"DEBUG [{timestamp}]: Spell cast detected - caster='{caster_name}', spell='{spell_name}', tracked='{self.tracked_player_name}', is_tracked={is_tracked_caster}, is_ougi_spell={is_ougi_spell}")

                # Initialize tracker only once per combat, when transitioning into combat due to the tracked player's first cast
                if not self.in_combat and is_tracked_caster:
                    self.in_combat = True
                    self.tracker = 0
                    self.current_tracker = 0
                    print("DEBUG: Combat started by tracked player; tracker initialized to 0")
                else:
                    # Still mark combat as active, but do not reinitialize tracker
                    self.in_combat = True
                
                # Show overlay immediately when Ougi spell is cast by tracked player
                if is_ougi_spell and is_tracked_caster:
                    self.is_ougi_turn = True
                    self.overlay_visible = True
                    print(f"DEBUG: Ougi turn started - overlay shown for '{spell_name}'")

                # Handle specific spell effects for tracked player
                if is_tracked_caster and spell_name:
                    # Track Étendard de bravoure for cost adjustment
                    if spell_name == "Étendard de bravoure":
                        self.last_etendard_cast = True
                        print(f"DEBUG: Étendard de bravoure detected - waiting for next line to determine cost")
                    else:
                        self.last_etendard_cast = False
                    
                    # Add spell to timeline
                    self.add_spell_to_timeline(spell_name)
                    print(f"DEBUG: Spell '{spell_name}' added to timeline for tracked player")
                
                # Return to prevent further processing of this line
                return
            
            # Normal combat end: "Combat terminé, cliquez ici pour rouvrir l'écran de fin de combat."
            if "Combat terminé" in line or "Combat terminé, cliquez ici pour rouvrir l'écran de fin de combat." in line:
                combat_ended = True
            
            # Exception: KO/hors-combat only triggers end for Sac à patate combat
            elif (re.search(r'est hors-combat', line) or re.search(r'est KO !', line)) and self.is_sac_patate_combat:
                combat_ended = True
            
            if combat_ended:
                self.in_combat = False
                self.is_sac_patate_combat = False  # Reset Sac à patate flag
                self.is_ougi_turn = False  # Reset turn state
                self.overlay_visible = False  # Hide overlay
                # Reset all resources when combat ends
                self.rage = 0
                self.tracker = 0
                self.prey = False
                self.current_rage = 0
                self.current_tracker = 0
                self.current_prey = False
                self.current_rage = 0
                # Stop rage bouncing loop
                self.rage_bounce_loop_active = False
                self.rage_bounce_velocity = 0
                self.rage_bounce_offset = 0
                # Reset damage confirmation system
                self.pending_rage_loss = False
                self.rage_loss_caster = None
                self.rage_loss_spell = None
                # Clear timeline when combat ends
                self.timeline_entries.clear()
                self.current_turn_spells.clear()
                # Hide all timeline elements immediately
                for i in range(self.timeline_max_slots):
                    self.timeline_icon_labels[i].hide()
                    self.timeline_cost_labels[i].hide()
                print("DEBUG: Combat ended - overlay hidden and timeline cleared")
                return
            
            # Only process combat lines
            if "[Information (combat)]" not in line:
                return
            #TODO: ougi styles
            # Parse rage - actual format: "rage (+65 Niv.)"
            rage_match = re.search(r'rage \(\+(\d+) Niv\.\)', line)
            if rage_match:
                # Extract player name from rage log
                player_rage_match = re.search(r'\[Information \(combat\)\] ([^:]+): rage', line)
                if player_rage_match:
                    self.tracked_player_name = player_rage_match.group(1)
                
                rage_value = int(rage_match.group(1))
                
                # Check if rage reaches 100+ (triggers overflow and tracker loss)
                if rage_value >= 100:
                    # Wrap around using modulo - e.g., 140 becomes 40
                    self.rage = rage_value % 100
                    # Lose tracker buff when rage overflows
                    if self.prey:
                        self.prey = False
                        self.current_prey = self.prey
                        # Start fade out (animated)
                        self.prey_target_alpha = 0.0
                        if self.prey_visible:
                            print("DEBUG: Égaré removed due to rage overflow")
                            self.prey_visible = False
                else:
                    # Normal rage tracking
                    self.rage = rage_value
                return
            
            # Parse Égaré loss - turn passing ("seconde reportée pour le tour suivant" or "secondes reportées pour le tour suivant")
            # This MUST be checked BEFORE tracker loss to avoid early return
            if ("reportée pour le tour suivant" in line) or ("reportées pour le tour suivant" in line):
                print(f"DEBUG: Turn end detected in log: {line.strip()[:80]}...")
                
                # Determine which player's turn is ending
                # Use the last player who cast a spell as the turn owner
                turn_owner = self.last_spell_caster
                print(f"DEBUG: Turn end detected - last spell caster was: '{turn_owner}' (tracked: '{self.tracked_player_name}')")
                
                if turn_owner and self.tracked_player_name and turn_owner == self.tracked_player_name:
                    # The tracked Iop is passing turn - hide overlay
                    self.is_ougi_turn = False
                    self.overlay_visible = False
                    
                    # If we were waiting for damage confirmation, cancel it
                    if self.pending_rage_loss:
                        self.pending_rage_loss = False
                        self.rage_loss_caster = None
                        self.rage_loss_spell = None
                        print(f"DEBUG: Préparation damage confirmation cancelled - turn passed without damage")
                    
                    print(f"DEBUG: Iop turn ended - overlay hidden (turn passed by {turn_owner})")
                elif turn_owner:
                    # Different player is passing turn - overlay remains as is
                    print(f"DEBUG: Turn passed by different player '{turn_owner}' - overlay remains {'visible' if self.overlay_visible else 'hidden'}")
                else:
                    # No recent spell caster - assume it's the tracked player's turn ending
                    print(f"DEBUG: No recent spell caster - assuming tracked player's turn ending")
                    if self.tracked_player_name:
                        self.is_ougi_turn = False
                        self.overlay_visible = False
                        
                        # If we were waiting for damage confirmation, cancel it
                        if self.pending_rage_loss:
                            self.pending_rage_loss = False
                            self.rage_loss_caster = None
                            self.rage_loss_spell = None
                            print(f"DEBUG: Préparation damage confirmation cancelled - assumed turn end without damage")
                        
                        print(f"DEBUG: Iop turn ended - overlay hidden (assumed turn end)")
                    else:
                        print(f"DEBUG: No tracked player set - cannot determine turn owner")
                
                if self.prey:
                    self.prey = False
                    self.current_prey = self.prey
                    # Start fade out (animated)
                    self.prey_target_alpha = 0.0
                    if self.prey_visible:
                        print("DEBUG: Égaré removed due to turn carryover")
                        self.prey_visible = False
                
                # Clear timeline when turn passes
                timeline_count = len(self.timeline_entries)
                if timeline_count > 0:
                    print(f"DEBUG: Clearing {timeline_count} timeline entries due to turn end")
                    self.timeline_entries.clear()
                    # Hide all timeline elements immediately
                    for i in range(self.timeline_max_slots):
                        self.timeline_icon_labels[i].hide()
                        self.timeline_cost_labels[i].hide()
                else:
                    print("DEBUG: Timeline already empty - no clearing needed")
                
                return
            
            # Parse tracker - actual format: "tracker (+50 Niv.)"
            tracker_match = re.search(r'tracker \(\+(\d+) Niv\.\)', line)
            if tracker_match:
                tracker_value = int(tracker_match.group(1))
                self.tracker = min(tracker_value, 50)  # Cap at 50
                # Force immediate display update
                self.current_tracker = self.tracker
                return
            
            # Parse tracker loss - "n'est plus sous l'emprise de 'tracker' (Iop isolé)"
            if "n'est plus sous l'emprise de 'tracker' (Iop isolé)" in line:
                # Extract player name and only apply to tracked player
                player_tracker_loss_match = re.search(r'\[Information \(combat\)\] ([^:]+): n\'est plus sous l\'emprise de \'tracker\'', line)
                if player_tracker_loss_match and self.tracked_player_name:
                    player_name = player_tracker_loss_match.group(1)
                    if player_name == self.tracked_player_name:
                        self.tracker = max(0, self.tracker - 10)  # Lose 10 tracker, minimum 0
                        # Force immediate display update
                        self.current_tracker = self.tracker
                return
            
            # Parse tracker gains - "tracker (+30 Niv.) (Compulsion)" OR "tracker (+1 Niv.) (rage)"
            # Note: The number in (+X Niv.) is the TOTAL current amount, not the amount gained
            tracker_gain_match = re.search(r'tracker \(\+(\d+) Niv\.\) \((Compulsion|rage)\)', line)
            if tracker_gain_match:
                tracker_total = int(tracker_gain_match.group(1))
                old_tracker = self.tracker
                self.tracker = min(tracker_total, 4)  # Set to the total amount shown in log, max 4 stacks
                # Force immediate display update
                self.current_tracker = self.tracker
                # Trigger bounce animation when gaining tracker (only if it increased)
                if self.tracker > old_tracker:
                    self.trigger_tracker_bounce()
                return
            
            # Parse tracker loss - "n'est plus sous l'emprise de 'tracker' (Compulsion)"
            if "n'est plus sous l'emprise de 'tracker' (Compulsion)" in line:
                # Extract player name and only apply to tracked player
                player_tracker_loss_match = re.search(r'\[Information \(combat\)\] ([^:]+): n\'est plus sous l\'emprise de \'tracker\'', line)
                if player_tracker_loss_match and self.tracked_player_name:
                    player_name = player_tracker_loss_match.group(1)
                    if player_name == self.tracked_player_name:
                        self.tracker = 0  # Lose ALL stacks
                        # Force immediate display update
                        self.current_tracker = self.tracker
                return
            
            # Note: Spell processing is now consolidated above to prevent duplicate timeline entries
            
            # Parse tracker loss - damage dealt with (tracker) tag
            # Pattern: "[Information (combat)] monster: -xx PV (element) (tracker)"
            if "(tracker)" in line and "PV" in line:
                tracker_damage_match = re.search(r'\[Information \(combat\)\] .*: -(\d+) PV \([^)]+\) \(tracker\)', line)
                if tracker_damage_match:
                    self.tracker = 0  # Lose ALL stacks when damage is dealt with tracker
                    # Force immediate display update
                    self.current_tracker = self.tracker
                    return
            
            # Parse Préparation gains - "Belluya: Préparation (+20 Niv.)"
            rage_gain_match = re.search(r'Préparation \(\+(\d+) Niv\.\)', line)
            if rage_gain_match:
                rage_total = int(rage_gain_match.group(1))
                old_rage = self.rage
                self.rage = rage_total  # Set to the total amount shown in log
                # Force immediate display update
                self.current_rage = self.rage
                # Trigger slide animation when gaining rage (only if it increased)
                if self.rage > old_rage:
                    self.trigger_rage_slide()
                print(f"DEBUG: Préparation gained: {rage_total} stacks")
                return
            
            # Parse damage lines - "Sac à patates: -64 PV  (Feu)" or "Sac à patates: -133 PV (Feu) (tracker)"
            damage_match = re.search(r'\[Information \(combat\)\] ([^:]+):\s*-(\d+)\s*PV', line)
            if damage_match and self.pending_rage_loss:
                damage_target = damage_match.group(1).strip()
                damage_amount = int(damage_match.group(2))
                
                print(f"DEBUG: Damage detected: {damage_amount} PV to {damage_target} (waiting for: {self.rage_loss_caster})")
                
                # Check if this damage is from the tracked player's spell
                if self.rage_loss_caster == self.tracked_player_name:
                    # Damage confirmed - remove Préparation
                    self.rage = 0
                    self.current_rage = self.rage
                    # Stop continuous bouncing loop
                    self.rage_bounce_loop_active = False
                    self.rage_bounce_velocity = 0
                    self.rage_bounce_offset = 0
                    # Reset damage confirmation system
                    self.pending_rage_loss = False
                    self.rage_loss_caster = None
                    self.rage_loss_spell = None
                    print(f"DEBUG: Préparation lost due to confirmed damage: {damage_amount} PV to {damage_target}")
                    return
                else:
                    print(f"DEBUG: Damage detected but not from tracked player - caster: {self.rage_loss_caster}, tracked: {self.tracked_player_name}")
                
        except Exception as e:
            pass  # Silently handle parsing errors
    
    def update_animations(self):
        """Update animations and visual effects"""
        self.animation_frame += 1
        
        # Show/hide overlay based on turn-based visibility (only during ougi's turn)
        if self.overlay_visible and self.in_combat:
            self.rage_icon.show()
            self.rage_bar.show()
            self.position_elements()  # Ensure elements are positioned
            # Show timeline slots that have entries
            self.update_timeline_display()

        else:
            self.rage_icon.hide()
            self.rage_bar.hide()
            self.tracker_icon.hide()
            self.tracker_counter.hide()
            # Hide all tracker bars when not Iop's turn
            for bar in self.tracker_bars:
                bar.hide()
            # Target fade out for tracker icon, but keep processing fade animation below (no early return)
            self.prey_target_alpha = 0.0
            # Hide timeline when not Iop's turn
            for i in range(self.timeline_max_slots):
                self.timeline_icon_labels[i].hide()
                self.timeline_cost_labels[i].hide()
        
        # Direct value updates for responsive display
        self.current_rage = self.rage
        self.current_tracker = self.tracker
        self.current_tracker = self.tracker
        self.current_prey = self.prey
        
        # Update rage bar with smooth transitions
        if self.rage != self.rage_bar.target_value:
            self.rage_bar.setValue(self.current_rage)
        
        # Progress bar has its own high-frequency timer, no need to update here
        
        # Update tracker bars (show bars based on tracker level) - only when overlay is visible
        if self.overlay_visible and self.in_combat:
            bars_to_show = min(5, self.current_tracker // 10)  # Each bar represents 10 tracker
            if bars_to_show > 0:
                # Only print debug message when state changes
                if bars_to_show != self.last_tracker_bars_state:
                    print(f"DEBUG: tracker bars showing - tracker: {self.current_tracker}, bars: {bars_to_show}, overlay_visible: {self.overlay_visible}, in_combat: {self.in_combat}")
                    self.last_tracker_bars_state = bars_to_show
                # Reset hidden debug flag when bars become visible
                self.last_tracker_hidden_debug = False
            for i, bar in enumerate(self.tracker_bars):
                if i < bars_to_show:
                    bar.show()
                    # Light up the bar with a bright color
                    bar.setStyleSheet("""
                        QFrame {
                            background-color: rgba(100, 200, 255, 200);
                            border: 1px solid rgba(150, 220, 255, 255);
                            border-radius: 3px;
                        }
                    """)
                else:
                    bar.hide()
        else:
            # Hide all tracker bars when overlay is not visible
            if self.current_tracker > 0 and not self.last_tracker_hidden_debug:
                print(f"DEBUG: tracker bars hidden despite having tracker - overlay_visible: {self.overlay_visible}, in_combat: {self.in_combat}")
                self.last_tracker_hidden_debug = True
            for bar in self.tracker_bars:
                bar.hide()
            # Reset state tracking when hidden
            self.last_tracker_bars_state = 0
        
        # Update tracker display - only show if we have stacks AND overlay is visible
        if self.current_tracker > 0 and self.overlay_visible and self.in_combat:
            self.tracker_icon.show()
            self.tracker_counter.setText(str(int(self.current_tracker)))
            self.tracker_counter.show()
            # Only print debug message when state changes
            if self.current_tracker != self.last_tracker_state:
                print(f"DEBUG: tracker showing - stacks: {self.current_tracker}, overlay_visible: {self.overlay_visible}, in_combat: {self.in_combat}")
                self.last_tracker_state = self.current_tracker
            # Reset hidden debug flag when tracker becomes visible
            self.last_tracker_hidden_debug = False
            
            # Realistic bouncing physics for tracker icon
            # Apply gravity to velocity
            self.tracker_bounce_velocity += self.tracker_bounce_gravity
            
            # Update position based on velocity
            self.tracker_bounce_offset += self.tracker_bounce_velocity
            
            # Check for ground collision (bounce)
            if self.tracker_bounce_offset >= self.tracker_ground_level:
                # Hit the ground - reverse velocity and apply damping
                self.tracker_bounce_offset = self.tracker_ground_level
                self.tracker_bounce_velocity = -self.tracker_bounce_velocity * self.tracker_bounce_damping
                
                # Stop bouncing if velocity is too small
                if abs(self.tracker_bounce_velocity) < self.tracker_bounce_min_velocity:
                    self.tracker_bounce_velocity = 0
                    self.tracker_bounce_offset = self.tracker_ground_level
            
            # Apply bounce offset to tracker icon position
            base_x, base_y = self.rage_bar.pos().x(), self.rage_bar.pos().y()
            tracker_x = int(base_x + 255)
            tracker_y = int(base_y - 2 + self.tracker_bounce_offset)  # Positive offset = UP from ground level
            
            # Move both icon and counter together
            self.tracker_icon.move(tracker_x, tracker_y)
            self.tracker_counter.move(tracker_x, tracker_y)  # Counter follows the icon
        else:
            self.tracker_icon.hide()
            self.tracker_counter.hide()
            if self.current_tracker > 0 and not self.last_tracker_hidden_debug:
                print(f"DEBUG: tracker hidden despite having stacks - overlay_visible: {self.overlay_visible}, in_combat: {self.in_combat}")
                self.last_tracker_hidden_debug = True
            # Reset state tracking when hidden
            self.last_tracker_state = 0
        
        # Update rage display - always show if we have stacks (regardless of turn state)
        if self.current_rage > 0 and self.in_combat:
            self.rage_icon.show()
            self.rage_counter.setText(str(int(self.current_rage)))
            self.rage_counter.show()
            # Only print debug message when state changes
            if self.current_rage != self.last_rage_state:
                print(f"DEBUG: Préparation showing - stacks: {self.current_rage}, overlay_visible: {self.overlay_visible}, in_combat: {self.in_combat}")
                self.last_rage_state = self.current_rage
            # Reset hidden debug flag when rage becomes visible
            self.last_rage_hidden_debug = False
            
            # Apply slide animation for rage icon (initial slide down)
            if self.rage_slide_offset > 0:
                # Gradually reduce slide offset (slide down effect)
                self.rage_slide_offset -= self.rage_slide_speed
                if self.rage_slide_offset < 0:
                    self.rage_slide_offset = 0
            
            # Apply slide offset to rage icon position
            base_x, base_y = self.rage_bar.pos().x(), self.rage_bar.pos().y()
            rage_x = int(base_x + 290 + self.rage_offset_x)
            rage_y = int(base_y - 2 + self.rage_offset_y - self.rage_slide_offset + self.rage_bounce_offset)  # Slide + bounce offset
            
            # Move both icon and counter together
            self.rage_icon.move(rage_x, rage_y)
            self.rage_counter.move(rage_x, rage_y)  # Counter follows the icon
        else:
            self.rage_icon.hide()
            self.rage_counter.hide()
            if self.current_rage > 0 and not self.in_combat and not self.last_rage_hidden_debug:
                print(f"DEBUG: Préparation hidden due to combat end - stacks: {self.current_rage}")
                self.last_rage_hidden_debug = True
            # Reset state tracking when hidden
            self.last_rage_state = 0
        
        # Apply bounce animation for rage icon (continuous loop) - ALWAYS runs when rage exists
        if self.current_rage > 0 and self.rage_bounce_loop_active:
            # Only print debug occasionally to avoid spam
            if self.animation_frame % 30 == 0:  # Every 30 frames (0.5 seconds at 60fps)
                print(f"DEBUG: Préparation bouncing active - stacks: {self.current_rage}, overlay_visible: {self.overlay_visible}, in_combat: {self.in_combat}, loop_delay: {self.rage_bounce_loop_delay}, bounce_delay: {self.rage_bounce_delay}, velocity: {self.rage_bounce_velocity}, offset: {self.rage_bounce_offset}")
            # Handle delay between bounce loops
            if self.rage_bounce_loop_delay > 0:
                self.rage_bounce_loop_delay -= 1
                if self.rage_bounce_loop_delay == 0:
                    # Start new bounce sequence
                    self.trigger_rage_bounce()
            # Handle initial delay before first bounce
            elif self.rage_bounce_delay > 0:
                self.rage_bounce_delay -= 1
                if self.rage_bounce_delay == 0:
                    self.trigger_rage_bounce()
            # Handle active bouncing
            elif self.rage_bounce_velocity != 0 or self.rage_bounce_offset != 0:
                # Apply gravity to velocity
                self.rage_bounce_velocity += self.rage_bounce_gravity
                
                # Update position based on velocity
                self.rage_bounce_offset += self.rage_bounce_velocity
                
                # Check for ground collision (bounce)
                if self.rage_bounce_offset >= self.rage_bounce_ground_level:
                    # Hit the ground - reverse velocity and apply damping
                    self.rage_bounce_offset = self.rage_bounce_ground_level
                    self.rage_bounce_velocity = -self.rage_bounce_velocity * self.rage_bounce_damping
                    
                    # Stop bouncing if velocity is too small
                    if abs(self.rage_bounce_velocity) < self.rage_bounce_min_velocity:
                        self.rage_bounce_velocity = 0
                        self.rage_bounce_offset = self.rage_bounce_ground_level
                        # Start delay for next bounce loop
                        self.rage_bounce_loop_delay = self.rage_bounce_loop_delay_max
                        print("DEBUG: Préparation bounce sequence ended - starting loop delay")
            # If none of the above conditions are met, start bouncing immediately
            else:
                print("DEBUG: Préparation bouncing conditions not met - starting bounce immediately")
                self.trigger_rage_bounce()
            
            # Bounce offset is now applied in the rage display logic above to avoid duplicate positioning
        
        # Update tracker icon with fade animation (only during Iop's turn)
        if self.current_prey and self.overlay_visible and self.in_combat:
            # Set target alpha to 1.0 for fade in (only when it's Iop's turn)
            self.prey_target_alpha = 1.0
            self.prey_icon.show()
            if not self.prey_visible:
                print("DEBUG: Égaré icon showing (fade in)")
                self.prey_visible = True
                # Initialize slide-in from above
                self.prey_slide_offset = self.prey_slide_max
                # Start fade from 0 to make animation visible
                self.prey_fade_alpha = 0.0
            
            # Position tracker icon well above the first Tracker bar
            base_x, base_y = self.rage_bar.pos().x(), self.rage_bar.pos().y()
            prey_x = base_x  # Same X position as first Tracker bar
            prey_y = base_y - 50  # Much higher up above the Tracker bars
            self.prey_icon.move(prey_x, prey_y)
        elif not self.current_prey:
            # Set target alpha to 0.0 for fade out (when tracker is lost)
            self.prey_target_alpha = 0.0
        elif not self.overlay_visible:
            # Set target alpha to 0.0 for fade out when not Iop's turn
            self.prey_target_alpha = 0.0
        
        # Update fade animation (always process, regardless of combat status)
        if self.prey_fade_alpha < self.prey_target_alpha:
            # Fade in
            self.prey_fade_alpha += self.prey_fade_in_speed
            if self.prey_fade_alpha > self.prey_target_alpha:
                self.prey_fade_alpha = self.prey_target_alpha
        elif self.prey_fade_alpha > self.prey_target_alpha:
            # Fade out
            self.prey_fade_alpha -= self.prey_fade_out_speed
            if self.prey_fade_alpha < self.prey_target_alpha:
                self.prey_fade_alpha = self.prey_target_alpha
        
        # Update slide-in offset while fading in
        if self.prey_target_alpha > 0.0 and self.prey_fade_alpha > 0.0 and self.prey_slide_offset > 0:
            self.prey_slide_offset = max(0, self.prey_slide_offset - self.prey_slide_speed)

        # Reposition tracker icon after updating slide offset and fade
        base_x, base_y = self.rage_bar.pos().x(), self.rage_bar.pos().y()
        prey_x = base_x
        prey_y = base_y - 50 - self.prey_slide_offset
        self.prey_icon.move(prey_x, prey_y)

        # Apply fade alpha to icon (always process, regardless of combat status)
        self.prey_icon.setFadeAlpha(self.prey_fade_alpha)
        
        # Hide icon when fully faded out (always process, regardless of combat status)
        if self.prey_fade_alpha <= 0.0:
            self.prey_icon.hide()
            if self.prey_visible:
                print("DEBUG: Égaré icon hidden (fully faded out)")
                self.prey_visible = False
                self.prey_slide_offset = 0

        # Animate timeline: increase alpha/slide for newest, fade/slide out overflow if present in buffer
        if self.timeline_entries:
            # Newest entry is at end of list
            newest = self.timeline_entries[-1]
            if newest.get('alpha', 0.0) < 1.0:
                newest['alpha'] = min(1.0, newest.get('alpha', 0.0) + 0.15)
            if newest.get('slide', 0) < 0:
                newest['slide'] = min(0, newest.get('slide', 0) + 4)
            # If we have one extra (overflow), it's the oldest at index 0; animate out
            if len(self.timeline_entries) > self.timeline_max_slots:
                oldest = self.timeline_entries[0]
                oldest['alpha'] = max(0.0, oldest.get('alpha', 1.0) - 0.2)
                # Use positive slide to move right
                oldest['slide'] = oldest.get('slide', 0) + 4
                # When fully faded, drop it
                if oldest['alpha'] <= 0.0:
                    # Remove from buffer
                    self.timeline_entries.pop(0)
            # Refresh display to apply the updated alpha/positions
            self.update_timeline_display()

    def add_spell_to_timeline(self, spell_name: str):
        """Add a spell cast to the timeline (tracked player only)."""
        spell_key = spell_name.strip()
        cost = self.spell_cost_map.get(spell_key)
        icon_stem = self.spell_icon_stem_map.get(spell_key)
        if not cost or not icon_stem:
            return  # Unknown spell; ignore
        icon_path = self.base_path / "img" / f"{icon_stem}.png"
        pixmap = QPixmap(str(icon_path)) if icon_path.exists() else None
        # Build entry with animation state
        compact_cost = cost.replace(" ", "")  # e.g., "1 PA" -> "1PA"
        entry = { 'spell': spell_key, 'cost': compact_cost, 'pixmap': pixmap, 'alpha': 0.0, 'slide': -16 }
        # Append and clamp to last N; mark the oldest for fade-out/slide-right if overflow
        overflow_entry = None
        if len(self.timeline_entries) >= self.timeline_max_slots:
            overflow_entry = self.timeline_entries[0]
        self.timeline_entries.append(entry)
        if len(self.timeline_entries) > self.timeline_max_slots:
            # Keep one extra temporarily for animating out the oldest
            self.timeline_entries = self.timeline_entries[-(self.timeline_max_slots + 1):]
        
        # Trigger display refresh
        self.update_timeline_display()

    def update_timeline_display(self):
        """Refresh timeline labels to reflect current entries."""
        # Only update timeline if overlay is visible
        if not (self.overlay_visible and self.in_combat):
            # Hide all timeline elements if overlay is not visible
            for i in range(self.timeline_max_slots):
                self.timeline_icon_labels[i].hide()
                self.timeline_cost_labels[i].hide()
            return
        
        # Ensure positions are up-to-date
        self.position_elements()
        # Fill newest-to-oldest left-to-right (latest cast on the far left)
        for i in range(self.timeline_max_slots):
            entry_index = len(self.timeline_entries) - 1 - i
            if 0 <= entry_index < len(self.timeline_entries):
                entry = self.timeline_entries[entry_index]
                # Set cost text (outlined white, centered)
                self.timeline_cost_labels[i].setText(entry['cost'])
                self.timeline_cost_labels[i].show()
                # Set icon
                if entry['pixmap']:
                    self.timeline_icon_labels[i].setPixmap(entry['pixmap'].scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                else:
                    self.timeline_icon_labels[i].setText("?")
                self.timeline_icon_labels[i].show()
                # Ensure cost overlay stays on top of the icon
                self.timeline_icon_labels[i].raise_()
                self.timeline_cost_labels[i].raise_()
                # Apply opacity and slide based on entry animation state
                # Newest (i == 0) fades in and slides from the left; oldest (if overflow) fades out and slides right
                icon_label = self.timeline_icon_labels[i]
                cost_label = self.timeline_cost_labels[i]
                # Set opacity
                if not hasattr(icon_label, '_opacity'):
                    icon_label._opacity = QGraphicsOpacityEffect()
                    icon_label.setGraphicsEffect(icon_label._opacity)
                if not hasattr(cost_label, '_opacity'):
                    cost_label._opacity = QGraphicsOpacityEffect()
                    cost_label.setGraphicsEffect(cost_label._opacity)
                # Determine target alpha
                is_newest = (i == 0)
                icon_label._opacity.setOpacity(min(1.0, max(0.0, entry.get('alpha', 1.0) if is_newest else 1.0)))
                cost_label._opacity.setOpacity(min(1.0, max(0.0, entry.get('alpha', 1.0) if is_newest else 1.0)))
                # Apply slide offset for newest (both icon and cost move together)
                slide_offset = entry.get('slide', 0) if is_newest else 0
                # Always position cost relative to icon
                base_x, base_y = self.rage_bar.pos().x(), self.rage_bar.pos().y()
                timeline_icon_y = base_y + 30
                icon_x = base_x + (i * 32) + slide_offset
                icon_label.move(icon_x, timeline_icon_y)
                # Cost below icon, centered
                cost_x = icon_x + (32 - 32) // 2  # Center the 32px wide cost label under the 32px icon
                cost_y = timeline_icon_y + 32 - 2
                cost_label.move(cost_x, cost_y)
            else:
                self.timeline_icon_labels[i].hide()
                self.timeline_cost_labels[i].hide()
    
    def trigger_tracker_bounce(self):
        """Trigger a bounce animation when tracker is gained"""
        # Set initial upward velocity for the bounce (smaller jump)
        self.tracker_bounce_velocity = -6  # Negative velocity = upward movement (reduced from -12)
        self.tracker_bounce_offset = 0  # Start from ground level
    
    def trigger_rage_slide(self):
        """Trigger a slide animation when rage is gained"""
        # Start with slide offset (slide down effect)
        self.rage_slide_offset = self.rage_slide_max  # Start this many pixels above
        
        # Start bounce animation immediately (no delay)
        self.rage_bounce_delay = 0  # No delay - start bouncing immediately
        self.rage_bounce_velocity = -10  # Start with upward velocity immediately
        self.rage_bounce_offset = 0  # Start at ground level
        
        # Start continuous bouncing loop
        self.rage_bounce_loop_active = True
        self.rage_bounce_loop_delay = 0  # No delay for first bounce
        
        print("DEBUG: Préparation slide and immediate bounce loop triggered")
    
    def trigger_rage_bounce(self):
        """Trigger the actual bounce animation after delay"""
        # Start with upward velocity (negative = up) - bigger initial jump
        self.rage_bounce_velocity = -10  # Negative velocity = upward movement (faster than before)
        self.rage_bounce_offset = 0  # Start from ground level
        self.rage_bounce_delay = 0  # Clear the delay
        print(f"DEBUG: Préparation bounce animation started - overlay_visible: {self.overlay_visible}")
    
    def save_positions(self):
        """Save current positions to config file"""
        try:
            positions = {
                'rage_bar': {
                    'x': self.rage_bar.x(),
                    'y': self.rage_bar.y()
                },
                'tracker_group_offset': {
                    'x': self.tracker_group_offset_x,
                    'y': self.tracker_group_offset_y
                },
                'rage_offset': {
                    'x': self.rage_offset_x,
                    'y': self.rage_offset_y
                },
                'positions_locked': self.positions_locked
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(positions, f, indent=2)
            pass  # Positions saved silently
        except Exception as e:
            pass  # Silently handle save errors
    
    def load_positions(self):
        """Load positions from config file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    positions = json.load(f)
                
                if 'rage_bar' in positions:
                    x, y = positions['rage_bar']['x'], positions['rage_bar']['y']
                    self.rage_bar.move(x, y)
                
                if 'rage_offset' in positions:
                    self.rage_offset_x = positions['rage_offset']['x']
                    self.rage_offset_y = positions['rage_offset']['y']
                
                if 'positions_locked' in positions:
                    self.positions_locked = positions['positions_locked']
        except Exception as e:
            pass  # Silently handle load errors
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging rage bar or combo columns separately"""
        if event.button() == Qt.MouseButton.LeftButton and not self.positions_locked:
            click_pos = event.globalPosition().toPoint()
            
            # Check if click is on rage bar
            rage_rect = self.rage_bar.geometry()
            if rage_rect.contains(click_pos):
                self.drag_start_position = click_pos - self.rage_bar.frameGeometry().topLeft()
                self.dragging_rage = True

                print("DEBUG: Started dragging rage bar")
                return
            
            # Check if click is on rage icon
            if self.rage_icon.isVisible():
                rage_rect = self.rage_icon.geometry()
                if rage_rect.contains(click_pos):
                    # Calculate offset from rage bar for rage
                    rage_base_x = self.rage_bar.x() + 290 + self.rage_offset_x
                    rage_base_y = self.rage_bar.y() - 2 + self.rage_offset_y
                    self.drag_start_position = click_pos - QPoint(rage_base_x, rage_base_y)
                    self.dragging_rage = False
                    self.dragging_rage = True
                    print("DEBUG: Started dragging rage icon")
                    return
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging rage bar or tracker separately"""
        if event.buttons() == Qt.MouseButton.LeftButton and not self.positions_locked:
            if self.dragging_rage:
                # Move rage bar and all other elements
                new_pos = event.globalPosition().toPoint() - self.drag_start_position
                self.rage_bar.move(new_pos)
                self.position_elements()
                self.auto_save_positions()
                print(f"DEBUG: Moving rage bar to {new_pos}")
            elif self.dragging_rage:
                # Move only rage icon
                new_pos = event.globalPosition().toPoint() - self.drag_start_position
                rage_base_x = self.rage_bar.x() + 290  # Default rage position
                rage_base_y = self.rage_bar.y() - 2
                
                # Calculate new offset from rage bar
                self.rage_offset_x = new_pos.x() - rage_base_x
                self.rage_offset_y = new_pos.y() - rage_base_y
                
                # Update rage position
                self.position_elements()
                self.auto_save_positions()
                print(f"DEBUG: Moving rage icon - offset: ({self.rage_offset_x}, {self.rage_offset_y})")
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release to stop dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.dragging_rage:
                print("DEBUG: Stopped dragging rage bar")
            elif self.dragging_tracker:
                print("DEBUG: Stopped dragging tracker icon")
            elif self.dragging_rage:
                print("DEBUG: Stopped dragging rage icon")
            self.dragging_rage = False
            self.dragging_tracker = False
            self.dragging_rage = False
    
    def auto_save_positions(self):
        """Auto-save positions with a delay to avoid too frequent saves"""
        if self.auto_save_timer:
            self.auto_save_timer.stop()
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.save_positions)
        self.auto_save_timer.setSingleShot(True)
        self.auto_save_timer.start(500)
    
    def closeEvent(self, event):
        """Handle close event"""
        self.save_positions()
        self.log_monitor.stop_monitoring()
        self.log_monitor.wait()
        # Stop progress bar timer
        self.rage_bar.progress_timer.stop()
        event.accept()

def main():
    """Main function"""
    app = QApplication(sys.argv)
    
    # Check if running in hidden mode (from launcher)
    hidden_mode = "--hidden" in sys.argv
    
    # Set application properties
    app.setApplicationName("Wakfu Ougi Resource Tracker")
    app.setApplicationVersion("1.0")
    
    # Create and show main window
    window = WakfuOugiResourceTracker(hidden_mode=hidden_mode)

    # Only show window if not in hidden mode
    if not hidden_mode:
        window.show()
    else:
        # In hidden mode, show window but minimize it
        window.show()
        window.showMinimized()
    
    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
