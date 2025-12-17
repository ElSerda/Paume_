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
        
        # Frameless + transparent
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        self.setWindowTitle("Le Quizz de Paume__")
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        
        # Pour drag de fenêtre
        self.drag_position = None
        
        # Charger le fond d'écran
        self._set_background()
        
        # Charger l'icône
        self._set_window_icon()
        
        # Gestionnaire de questions
        self.question_manager = QuestionManager(QUESTIONS_FOLDER)
        
        # Variables d'état
        self.all_buttons: List[Dict] = []
        self.clicked_buttons: set = set()
        self.last_clicked_button_index: Optional[int] = None
        self.show_domains = False
        
        # Créer l'interface
        self._create_ui()
    
    def _set_background(self):
        """Fond 100% transparent qui laisse voir le bureau."""
        # Couleur complètement transparente
        self.setStyleSheet("""
            QMainWindow {
                background-color: rgba(0, 0, 0, 0);
            }
            QWidget {
                background-color: rgba(0, 0, 0, 0);
            }
        """)

    
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
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ===== FAKE TITLE BAR (pour drag) =====
        title_bar = QFrame()
        title_bar.setStyleSheet(f"background-color: rgba(44, 62, 80, 200); border: none;")
        title_bar.setFixedHeight(30)
        title_bar.setCursor(Qt.CursorShape.OpenHandCursor)
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(10, 0, 10, 0)
        
        title_label = QLabel("🎮 Le Quizz de Paume__")
        title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #1ABC9C; background: transparent;")
        title_bar_layout.addWidget(title_label)
        
        # Bouton fermer
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #ECF0F1;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(231, 76, 60, 200);
            }
        """)
        close_btn.clicked.connect(self.close)
        title_bar_layout.addStretch()
        title_bar_layout.addWidget(close_btn)
        
        # Stocker la barre pour le drag
        self.title_bar = title_bar
        
        main_layout.addWidget(title_bar)
        
        # ===== CONTENU PRINCIPAL =====
        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 10, 20, 10)
        content_layout.setSpacing(8)
        
        # Layout du haut avec Refresh | Checkbox | Valider
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(10)
        
        # Bouton Refresh (à gauche)
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['border']};
                color: {COLORS['text_light']};
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
                min-width: 100px;
            }}
            QPushButton:hover {{
                background-color: #22D3EE;
            }}
        """)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self._refresh_buttons)
        top_layout.addWidget(self.refresh_btn)
        
        # Checkbox (au centre, stretch)
        top_layout.addStretch()
        
        self.domain_checkbox = QCheckBox("👁️ Afficher les domaines")
        self.domain_checkbox.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
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
        self.domain_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.domain_checkbox.setAutoFillBackground(True)  # Force à capturer les clics
        self.domain_checkbox.stateChanged.connect(self._toggle_domains)
        top_layout.addWidget(self.domain_checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
        
        top_layout.addStretch()
        
        # Bouton Valider (à droite)
        self.validate_btn = QPushButton("✅ Valider question")
        self.validate_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.validate_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #10B981;
                color: {COLORS['text_light']};
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
                min-width: 130px;
            }}
            QPushButton:hover {{
                background-color: #34D399;
            }}
            QPushButton:disabled {{
                background-color: #6B7280;
                color: #9CA3AF;
            }}
        """)
        self.validate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.validate_btn.setEnabled(False)  # Désactivé jusqu'à un clic
        self.validate_btn.clicked.connect(self._validate_current_question)
        top_layout.addWidget(self.validate_btn)
        
        content_layout.addLayout(top_layout)
        
        # Grille de boutons
        buttons_widget = QWidget()
        self.buttons_layout = QGridLayout(buttons_widget)
        self.buttons_layout.setSpacing(12)
        content_layout.addWidget(buttons_widget, stretch=1)
        
        self._create_all_buttons()
        
        # Supprimer l'espacement avant le crédit
        content_layout.setSpacing(0)
        
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
        content_layout.addWidget(credit_label)
        
        main_layout.addWidget(content_widget, stretch=1)
    
    def _create_all_buttons(self):
        """Crée les 20 boutons organisés en grille avec tailles dynamiques."""
        
        # ===== CALCUL DES TAILLES DYNAMIQUES =====
        # Marges horizontales
        horizontal_margins = 40  # 20 à gauche + 20 à droite
        # Espacement entre boutons (fixe)
        button_spacing = 12
        # 4 colonnes de boutons
        num_cols = 4
        
        # Largeur disponible
        available_width = WINDOW_WIDTH - horizontal_margins - (button_spacing * (num_cols - 1))
        button_width = available_width // num_cols
        
        # Hauteur des boutons (proportionnelle à la largeur pour garder les cercles)
        button_height = int(button_width * 0.35)  # ratio 280:60 ≈ 4.66:1, on fait 0.35 pour garder les proportions
        
        button_size = (button_width, button_height)
        
        # ===== CRÉATION DES CONFIGURATIONS =====
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
            
            # Utiliser ImageButton avec taille dynamique
            btn = ImageButton(
                style="default",
                text=str(idx + 1),
                size=button_size,
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
        
        # Tracker le dernier bouton cliqué
        self.last_clicked_button_index = button_index
        
        # Afficher la vraie couleur du bouton (style de sa catégorie)
        btn.set_style(info["category"])
        
        # Activer le bouton "Valider question"
        self.validate_btn.setEnabled(True)
    
    def _validate_current_question(self):
        """Valide la question en cours et désactive le bouton cliqué."""
        if self.last_clicked_button_index is None:
            return
        
        button_index = self.last_clicked_button_index
        info = self.all_buttons[button_index]
        btn = info["button"]
        
        # Marquer comme cliqué et grisé
        self.clicked_buttons.add(button_index)
        btn.set_disabled_state()
        
        # Réinitialiser
        self.last_clicked_button_index = None
        self.validate_btn.setEnabled(False)
    
    # =========================================================================
    # Drag de fenêtre (pour FramelessWindowHint)
    # =========================================================================
    
    def mousePressEvent(self, event):
        """Mémoriser la position de départ du drag (sur la title bar)."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Vérifier si le clic est sur la title bar
            if event.position().y() < 30:
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Bouger la fenêtre."""
        if self.drag_position is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Arrêter le drag."""
        self.drag_position = None
        super().mouseReleaseEvent(event)
    
    def _refresh_buttons(self):
        """Randomise les positions des boutons et réinitialise."""
        # Réinitialiser l'état
        self.clicked_buttons.clear()
        self.last_clicked_button_index = None
        self.validate_btn.setEnabled(False)
        self.domain_checkbox.setChecked(False)
        
        # Récupérer les configs
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
        
        # Réassigner les configs aux boutons existants
        for idx, config in enumerate(button_configs):
            info = self.all_buttons[idx]
            btn = info["button"]
            
            # Update info
            info["category"] = config["category"]
            info["domain"] = config["domain"]
            info["label"] = config["label"]
            info["style"] = config["category"]
            info["color_base"] = config["color_base"]
            info["color_hover"] = config["color_hover"]
            
            # Reset bouton
            btn.set_style("default")
            btn.setText(str(idx + 1))
            btn.setEnabled(True)


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
