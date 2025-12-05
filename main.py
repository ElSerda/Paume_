"""
main_qt.py
----------
Application de Quizz multi-joueurs avec interface graphique PySide6 (Qt).

Version Qt moderne avec animations et styles personnalisés.
"""

import sys
import random
import os
import ctypes
from pathlib import Path
from typing import Dict, List, Optional

# Fix pour l'icône dans la barre des tâches Windows
if sys.platform == 'win32':
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('elserda.paume.quizz.1.0')

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QPushButton, QLabel, QCheckBox, QTextEdit, QFrame
)
from PySide6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, Property, QSize
)
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap, QPainter, QBrush, QPalette

from questions_loader import QuestionManager
from image_button import ImageButton


def get_base_path() -> Path:
    """Retourne le chemin de base pour les fichiers modifiables (config, etc.)."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def get_resource_path(relative_path: str) -> Path:
    """Retourne le chemin pour les ressources empaquetées (compatible PyInstaller)."""
    if getattr(sys, '_MEIPASS', None):
        # PyInstaller: ressources dans le dossier temporaire
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).parent / relative_path


def load_config() -> Dict[str, str]:
    """Charge la configuration depuis config.txt."""
    config = {
        "user1_name": "Joueur 1",
        "user2_name": "Joueur 2",
        "window_width": "1200",
        "window_height": "800"
    }
    config_path = get_base_path() / "config.txt"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or not line:
                        continue
                    if ":" in line:
                        key, value = line.split(":", 1)
                        key = key.strip().lower()
                        value = value.strip()
                        if "joueur 1" in key or "player 1" in key:
                            config["user1_name"] = value
                        elif "joueur 2" in key or "player 2" in key:
                            config["user2_name"] = value
                        elif "largeur" in key or "width" in key:
                            config["window_width"] = value
                        elif "hauteur" in key or "height" in key:
                            config["window_height"] = value
        except Exception as e:
            print(f"Erreur lecture config: {e}")
    return config


# =============================================================================
# CONFIGURATION
# =============================================================================

QUESTIONS_FOLDER = "questions"
_CONFIG = load_config()
USER1_NAME = _CONFIG["user1_name"]
USER2_NAME = _CONFIG["user2_name"]
WINDOW_WIDTH = int(_CONFIG["window_width"])
WINDOW_HEIGHT = int(_CONFIG["window_height"])

NB_USER1 = 6
NB_USER2 = 6
NB_MALUS = 2
NB_BONUS = 2
NB_NEUTRE = 4

COLORS = {
    "bg_main": "#2C3E50",
    "bg_panel": "#34495E",
    "text_light": "#ECF0F1",
    "border": "#1ABC9C",
    "default_base": "#8E44AD",
    "default_hover": "#A569BD",
    "user1_base": "#3498DB",
    "user1_hover": "#5DADE2",
    "user2_base": "#E74C3C",
    "user2_hover": "#EC7063",
    "malus_base": "#8E44AD",
    "malus_hover": "#A569BD",
    "bonus_base": "#F39C12",
    "bonus_hover": "#F7DC6F",
    "neutre_base": "#1ABC9C",
    "neutre_hover": "#48C9B0",
    "disabled": "#7F8C8D",
}


# =============================================================================
# BOUTON ANIMÉ PERSONNALISÉ
# =============================================================================

class AnimatedButton(QPushButton):
    """Bouton avec animation de couleur au hover."""
    
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        
        self._base_color = QColor(COLORS["default_base"])
        self._hover_color = QColor(COLORS["default_hover"])
        self._current_color = QColor(COLORS["default_base"])
        self._is_disabled = False
        
        # Animation
        self._animation = QPropertyAnimation(self, b"buttonColor")
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        self._update_style()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.setMinimumHeight(60)
    
    def get_button_color(self) -> QColor:
        return self._current_color
    
    def set_button_color(self, color: QColor):
        self._current_color = color
        self._update_style()
    
    buttonColor = Property(QColor, get_button_color, set_button_color)
    
    def _update_style(self):
        if self._is_disabled:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['disabled']};
                    color: #AAAAAA;
                    border: none;
                    border-radius: 8px;
                    padding: 10px;
                    font-weight: bold;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self._current_color.name()};
                    color: {COLORS['text_light']};
                    border: none;
                    border-radius: 8px;
                    padding: 10px;
                    font-weight: bold;
                }}
            """)
    
    def set_colors(self, base: str, hover: str):
        """Change les couleurs du bouton."""
        self._base_color = QColor(base)
        self._hover_color = QColor(hover)
        self._current_color = QColor(base)
        self._update_style()
    
    def set_disabled_state(self):
        """Désactive définitivement le bouton."""
        self._is_disabled = True
        self.setEnabled(False)
        self._update_style()
    
    def enterEvent(self, event):
        if not self._is_disabled:
            self._animation.stop()
            self._animation.setStartValue(self._current_color)
            self._animation.setEndValue(self._hover_color)
            self._animation.start()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        if not self._is_disabled:
            self._animation.stop()
            self._animation.setStartValue(self._current_color)
            self._animation.setEndValue(self._base_color)
            self._animation.start()
        super().leaveEvent(event)


# =============================================================================
# FENÊTRE PRINCIPALE
# =============================================================================

class MainWindow(QMainWindow):
    """Fenêtre principale de l'application Quizz."""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Le Quizz de Paume__")
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        
        # Charger le fond d'écran
        self._set_background()
        
        # Charger l'icône
        self._set_window_icon()
        
        # Gestionnaire de questions
        self.question_manager = QuestionManager(QUESTIONS_FOLDER)
        
        # Variables d'état
        self.all_buttons: List[Dict] = []
        self.clicked_buttons: set = set()
        self.show_domains = False
        
        # Créer l'interface
        self._create_ui()
    
    def _set_background(self):
        """Charge l'image de fond si elle existe."""
        bg_path = get_resource_path("assets/backgrounds/background.png")
        
        if bg_path.exists():
            # Utiliser un QLabel comme fond
            self.bg_label = QLabel(self)
            pixmap = QPixmap(str(bg_path))
            # Redimensionner à la taille de la fenêtre
            scaled = pixmap.scaled(WINDOW_WIDTH, WINDOW_HEIGHT, 
                                   Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                   Qt.TransformationMode.SmoothTransformation)
            self.bg_label.setPixmap(scaled)
            self.bg_label.setGeometry(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)
            self.bg_label.lower()  # Mettre en arrière-plan
        else:
            # Fallback couleur si pas d'image
            self.setStyleSheet(f"background-color: {COLORS['bg_main']};")
    
    def _set_window_icon(self):
        """Charge l'icône de la fenêtre."""
        # Priorité au .ico pour Windows (barre des tâches)
        for icon_name in ["icon.ico", "assets/icons/icon.ico", "icon.png", "assets/icons/icon.png"]:
            icon_path = get_resource_path(icon_name)
            if icon_path.exists():
                icon = QIcon(str(icon_path))
                self.setWindowIcon(icon)
                # Aussi définir sur l'application
                QApplication.instance().setWindowIcon(icon)
                break
    
    def _create_ui(self):
        """Crée l'interface utilisateur."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 10, 20, 1)
        main_layout.setSpacing(8)
        
        # Titre
        title = QLabel("🎮 Le Quizz de Paume__")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_light']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)
        
        # Checkbox afficher domaines
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.domain_checkbox = QCheckBox("👁️ Afficher les domaines")
        self.domain_checkbox.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.domain_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {COLORS['text_light']};
                spacing: 10px;
                padding: 8px 15px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 5px;
                border: 2px solid {COLORS['border']};
                background-color: transparent;
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLORS['border']};
            }}
        """)
        self.domain_checkbox.stateChanged.connect(self._toggle_domains)
        checkbox_layout.addWidget(self.domain_checkbox)
        main_layout.addLayout(checkbox_layout)
        
        # Grille de boutons
        buttons_widget = QWidget()
        self.buttons_layout = QGridLayout(buttons_widget)
        self.buttons_layout.setSpacing(12)
        main_layout.addWidget(buttons_widget, stretch=1)
        
        self._create_all_buttons()
        
        # Panel de question
        question_panel = QFrame()
        question_panel.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(52, 73, 94, 230);
                border: 3px solid {COLORS['border']};
                border-radius: 15px;
            }}
        """)
        question_panel.setMinimumHeight(180)
        
        question_layout = QVBoxLayout(question_panel)
        question_layout.setContentsMargins(20, 15, 20, 15)
        
        # Label domaine
        self.domain_label = QLabel("Cliquez sur un numéro pour commencer")
        self.domain_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.domain_label.setStyleSheet(f"color: {COLORS['border']}; background: transparent; border: none;")
        self.domain_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        question_layout.addWidget(self.domain_label)
        
        # Zone de texte question
        self.question_text = QTextEdit()
        self.question_text.setReadOnly(True)
        self.question_text.setFont(QFont("Segoe UI", 16))
        self.question_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                color: {COLORS['text_light']};
                border: none;
            }}
        """)
        self.question_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.question_text.setMinimumHeight(120)
        question_layout.addWidget(self.question_text)
        
        main_layout.addWidget(question_panel)
        
        # Supprimer l'espacement avant le crédit
        main_layout.setSpacing(0)
        
        # Crédit discret (collé en bas)
        credit_label = QLabel("@El_Serda")
        credit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        credit_label.setFixedHeight(14)
        credit_label.setContentsMargins(0, 1, 0, 1)
        credit_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.12);
                font-size: 9px;
                background: transparent;
            }
        """)
        main_layout.addWidget(credit_label)
    
    def _create_all_buttons(self):
        """Crée les 20 boutons organisés en grille."""
        user1_domains = self.question_manager.get_domains("user1")
        user2_domains = self.question_manager.get_domains("user2")
        
        def fill_domains(domains: List[str], count: int) -> List[str]:
            if not domains:
                return ["???"] * count
            result = domains.copy()
            while len(result) < count:
                result.extend(domains)
            random.shuffle(result)
            return result[:count]
        
        user1_filled = fill_domains(user1_domains, NB_USER1)
        user2_filled = fill_domains(user2_domains, NB_USER2)
        
        button_configs = []
        
        for domain in user1_filled:
            button_configs.append({
                "category": "user1", "domain": domain, "label": USER1_NAME,
                "color_base": COLORS["user1_base"], "color_hover": COLORS["user1_hover"]
            })
        
        for domain in user2_filled:
            button_configs.append({
                "category": "user2", "domain": domain, "label": USER2_NAME,
                "color_base": COLORS["user2_base"], "color_hover": COLORS["user2_hover"]
            })
        
        for _ in range(NB_MALUS):
            button_configs.append({
                "category": "malus", "domain": "malus", "label": "MALUS",
                "color_base": COLORS["malus_base"], "color_hover": COLORS["malus_hover"]
            })
        
        for _ in range(NB_BONUS):
            button_configs.append({
                "category": "bonus", "domain": "bonus", "label": "BONUS",
                "color_base": COLORS["bonus_base"], "color_hover": COLORS["bonus_hover"]
            })
        
        for _ in range(NB_NEUTRE):
            button_configs.append({
                "category": "neutre", "domain": "neutre", "label": "NEUTRE",
                "color_base": COLORS["neutre_base"], "color_hover": COLORS["neutre_hover"]
            })
        
        random.shuffle(button_configs)
        
        for idx, config in enumerate(button_configs):
            row = idx // 4
            col = idx % 4
            
            # Utiliser ImageButton avec le style "default" au départ
            btn = ImageButton(
                style="default",
                text=str(idx + 1),
                size=(280, 60),
                on_click=lambda checked=False, i=idx: self._on_button_click(i)
            )
            
            self.buttons_layout.addWidget(btn, row, col)
            
            self.all_buttons.append({
                "button": btn,
                "category": config["category"],
                "domain": config["domain"],
                "label": config["label"],
                "number": idx + 1,
                "style": config["category"],  # Style pour ImageButton
                "color_base": config["color_base"],
                "color_hover": config["color_hover"]
            })
    
    def _toggle_domains(self, state):
        """Affiche ou cache les domaines sur les boutons."""
        self.show_domains = state == Qt.CheckState.Checked.value
        
        # Changer le texte et l'icône de la checkbox
        if self.show_domains:
            self.domain_checkbox.setText("🙈 Cacher les domaines")
        else:
            self.domain_checkbox.setText("👁️ Afficher les domaines")
        
        for info in self.all_buttons:
            btn = info["button"]
            number = info["number"]
            
            if number - 1 in self.clicked_buttons:
                continue
            
            if self.show_domains:
                if info["category"] in ["user1", "user2"]:
                    text = f"{info['label']}\n{info['domain']}"
                else:
                    text = info['label']
                # Changer le style du bouton vers sa catégorie
                btn.set_style(info["category"])
            else:
                text = str(number)
                # Revenir au style par défaut
                btn.set_style("default")
            
            btn.setText(text)
    
    def _on_button_click(self, button_index: int):
        """Gère le clic sur un bouton."""
        if button_index in self.clicked_buttons:
            return
        
        info = self.all_buttons[button_index]
        btn = info["button"]
        category = info["category"]
        domain = info["domain"]
        
        self.clicked_buttons.add(button_index)
        btn.set_disabled_state()
        
        question = self.question_manager.get_random_question(category, domain)
        
        if question:
            if category in ["user1", "user2"]:
                label_text = f"📖 {info['label']} - {domain.capitalize()}"
            else:
                label_text = f"📖 {info['label']}"
            
            self.domain_label.setText(label_text)
            self.question_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.question_text.setText(question)
        else:
            self.domain_label.setText(f"⚠️ {info['label']}")
            self.question_text.setText("Aucune question disponible pour cette catégorie.")


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Charger l'icône et l'appliquer à l'application (pour la barre des tâches)
    for icon_name in ["icon.ico", "assets/icons/icon.ico", "icon.png"]:
        icon_path = get_resource_path(icon_name)
        if icon_path.exists():
            icon = QIcon(str(icon_path))
            app.setWindowIcon(icon)  # Important pour la barre des tâches
            break
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
