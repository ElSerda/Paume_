"""
image_button.py
---------------
Classe ImageButton : bouton Qt basé sur des images avec 3 états (normal, hover, pressed).
Le texte est affiché PAR-DESSUS l'image de fond.
Animation de tilt (inclinaison) au hover et au clic.
"""

from pathlib import Path
from typing import Optional, Callable
import sys

from PySide6.QtWidgets import QPushButton
from PySide6.QtGui import QPixmap, QPainter, QFont, QColor
from PySide6.QtCore import Qt, QRect, QPropertyAnimation, Property, Signal, QAbstractAnimation, QEasingCurve


def get_asset_path(relative_path: str) -> Path:
    """
    Retourne le chemin absolu vers un asset.
    Compatible PyInstaller (_MEIPASS) et développement.
    """
    if getattr(sys, '_MEIPASS', None):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent
    return base / relative_path


class ImageButton(QPushButton):
    """
    Bouton personnalisé avec 3 états visuels basés sur des images :
    - normal : état par défaut
    - hover : survol de la souris (+ tilt animé)
    - pressed : clic enfoncé (+ tilt inverse)
    
    Le texte est dessiné PAR-DESSUS l'image de fond.
    
    Usage:
        btn = ImageButton(
            style="default",
            text="1",
            size=(280, 60),
            on_click=lambda: print("Cliqué!")
        )
    """
    
    # Signal pour notifier le changement d'angle
    angleChanged = Signal()
    
    # Cache global des pixmaps pour éviter de recharger les mêmes images
    _pixmap_cache: dict = {}
    
    def __init__(
        self,
        style: str = "default",
        text: str = "",
        size: tuple = (280, 60),
        on_click: Optional[Callable] = None,
        hover_angle: float = -3.0,
        pressed_angle: float = 3.0,
        tilt_duration: int = 120,
        parent=None
    ):
        super().__init__("", parent)  # Pas de texte natif Qt
        
        self._style = style
        self._size = size
        self._text = text  # On gère le texte nous-mêmes
        self._is_disabled = False
        self._mouse_inside = False
        self._current_state = "normal"
        
        # Animation de tilt
        self._tilt_angle = 0.0
        self._hover_angle = hover_angle
        self._pressed_angle = pressed_angle
        
        self._tilt_anim = QPropertyAnimation(self, b"tiltAngle", self)
        self._tilt_anim.setDuration(tilt_duration)
        self._tilt_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Charger les pixmaps pour les 3 états
        self._pixmaps = {
            "normal": self._load_pixmap(style, "normal"),
            "hover": self._load_pixmap(style, "hover"),
            "pressed": self._load_pixmap(style, "pressed"),
            "disabled": self._load_pixmap("disabled", "normal"),
        }
        
        # Configuration du bouton
        self.setFixedSize(*size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Style transparent pour laisser paintEvent dessiner
        self.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
            }
        """)
        
        # Connecter le callback
        if on_click:
            self.clicked.connect(on_click)
    
    # -------------------------------------------------------------------------
    # Propriété tiltAngle pour l'animation
    # -------------------------------------------------------------------------
    
    def getTiltAngle(self) -> float:
        return self._tilt_angle
    
    def setTiltAngle(self, value: float):
        self._tilt_angle = float(value)
        self.angleChanged.emit()
        self.update()  # Redessiner avec le nouvel angle
    
    tiltAngle = Property(float, getTiltAngle, setTiltAngle, notify=angleChanged)
    
    def _animate_tilt_to(self, target_angle: float):
        """Lance l'animation vers l'angle cible."""
        if self._tilt_anim.state() == QAbstractAnimation.State.Running:
            self._tilt_anim.stop()
        self._tilt_anim.setStartValue(self._tilt_angle)
        self._tilt_anim.setEndValue(target_angle)
        self._tilt_anim.start()
    
    # -------------------------------------------------------------------------
    # Texte
    # -------------------------------------------------------------------------
    
    def setText(self, text: str):
        """Override setText pour utiliser notre propre système."""
        self._text = text
        self.update()  # Redessiner
    
    def text(self) -> str:
        """Override text pour retourner notre texte."""
        return self._text
    
    # -------------------------------------------------------------------------
    # Chargement des images
    # -------------------------------------------------------------------------
    
    def _load_pixmap(self, style: str, state: str) -> Optional[QPixmap]:
        """Charge un pixmap depuis le cache ou le fichier."""
        cache_key = f"{style}/{state}/{self._size[0]}x{self._size[1]}"
        
        if cache_key in ImageButton._pixmap_cache:
            return ImageButton._pixmap_cache[cache_key]
        
        path = get_asset_path(f"assets/buttons/{style}/{state}.png")
        
        if path.exists():
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                # Redimensionner au besoin
                scaled = pixmap.scaled(
                    self._size[0], self._size[1],
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                ImageButton._pixmap_cache[cache_key] = scaled
                return scaled
        
        return None
    
    # -------------------------------------------------------------------------
    # Dessin avec rotation (tilt)
    # -------------------------------------------------------------------------
    
    def paintEvent(self, event):
        """Dessine l'image de fond avec rotation, puis le texte par-dessus."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # Appliquer la rotation autour du centre
        center = self.rect().center()
        painter.translate(center)
        painter.rotate(self._tilt_angle)
        painter.translate(-center)
        
        # 1. Dessiner l'image de fond
        pixmap = self._pixmaps.get(self._current_state)
        if pixmap and not pixmap.isNull():
            painter.drawPixmap(0, 0, pixmap)
        else:
            # Fallback : rectangle coloré
            colors = {
                "normal": "#8E44AD",
                "hover": "#A569BD",
                "pressed": "#7D3C98",
                "disabled": "#7F8C8D",
            }
            color = colors.get(self._current_state, colors["normal"])
            painter.setBrush(QColor(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(0, 0, self._size[0], self._size[1], 10, 10)
        
        # 2. Dessiner le texte par-dessus
        if self._text:
            if self._is_disabled:
                painter.setPen(QColor("#AAAAAA"))
            else:
                painter.setPen(QColor("white"))
            
            # Police
            font = QFont("Segoe UI", 12, QFont.Weight.Bold)
            painter.setFont(font)
            
            # Zone de texte (tout le bouton)
            text_rect = QRect(5, 0, self._size[0] - 10, self._size[1])
            
            # Dessiner le texte centré (supporte \n pour multi-lignes)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self._text)
        
        painter.end()
    
    def _apply_state(self, state: str):
        """Change l'état visuel du bouton."""
        self._current_state = state
        self.update()  # Déclenche paintEvent
    
    def set_style(self, style: str):
        """Change le style du bouton (recharge les images)."""
        self._style = style
        self._pixmaps = {
            "normal": self._load_pixmap(style, "normal"),
            "hover": self._load_pixmap(style, "hover"),
            "pressed": self._load_pixmap(style, "pressed"),
            "disabled": self._load_pixmap("disabled", "normal"),
        }
        self._apply_state("normal" if not self._is_disabled else "disabled")
    
    def set_disabled_state(self):
        """Désactive définitivement le bouton."""
        self._is_disabled = True
        self.setEnabled(False)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._apply_state("disabled")
        self._animate_tilt_to(0.0)  # Remettre à plat
    
    # -------------------------------------------------------------------------
    # Events pour gérer les 3 états + animation tilt
    # -------------------------------------------------------------------------
    
    def enterEvent(self, event):
        """Souris entre dans le bouton → hover + tilt."""
        if not self._is_disabled:
            self._mouse_inside = True
            self._apply_state("hover")
            self._animate_tilt_to(self._hover_angle)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Souris quitte le bouton → normal + angle 0."""
        if not self._is_disabled:
            self._mouse_inside = False
            self._apply_state("normal")
            self._animate_tilt_to(0.0)
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """Clic enfoncé → pressed + tilt inverse."""
        if not self._is_disabled and event.button() == Qt.MouseButton.LeftButton:
            self._apply_state("pressed")
            self._animate_tilt_to(self._pressed_angle)
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Clic relâché → hover/normal selon position souris."""
        if not self._is_disabled:
            if self._mouse_inside:
                self._apply_state("hover")
                self._animate_tilt_to(self._hover_angle)
            else:
                self._apply_state("normal")
                self._animate_tilt_to(0.0)
        super().mouseReleaseEvent(event)
