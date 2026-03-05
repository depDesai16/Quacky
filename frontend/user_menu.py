"""
user_menu.py - User profile menu for switching users and registration
"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QListWidget, QListWidgetItem,
                              QLineEdit, QMessageBox)
from PyQt6.QtGui import QFont
from theme import ThemeManager


class UserMenu(QDialog):
    """Menu for switching users and registering new faces"""
    
    user_selected = pyqtSignal(str)  # Emits selected user name
    register_requested = pyqtSignal()  # Emits when user wants to register
    
    def __init__(self, current_user, registered_users, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.registered_users = registered_users
        self._tokens = ThemeManager.tokens()
        
        self.setWindowTitle("User Profile")
        self.setModal(True)
        self.setFixedSize(350, 400)
        
        # Frameless with rounded corners
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._build_ui()
        self._apply_theme()
        ThemeManager.subscribe(self._on_theme)
    
    def _build_ui(self):
        """Build the user menu UI"""
        from PyQt6.QtWidgets import QWidget, QFrame
        
        # Main container for rounded corners
        container = QWidget(self)
      