"""
questions_loader.py
-------------------
Module de chargement des questions pour le Quizz multi-joueurs.

STRUCTURE DES DOSSIERS:
- questions/
  - user1/           <- Domaines du joueur 1
    - culture/
    - histoire/
    - ...
  - user2/           <- Domaines du joueur 2
    - geographie/
    - sport/
    - ...
  - malus/           <- Questions/effets malus
  - bonus/           <- Questions/effets bonus
  - neutre/          <- Questions neutres (pour les deux)

FORMAT DES QUESTIONS:
- Un fichier .txt par domaine
- Questions séparées par une ligne vide
"""

import os
from pathlib import Path
from typing import Dict, List, Set, Optional
import random


def get_base_path() -> Path:
    """Retourne le chemin de base (dossier de l'exe ou du script)."""
    if getattr(os.sys, 'frozen', False):
        # PyInstaller: utiliser le dossier de l'exe, pas _MEIPASS (temp)
        return Path(os.sys.executable).parent
    return Path(__file__).parent


def load_questions_by_category(questions_root: str = "questions") -> Dict[str, Dict[str, List[str]]]:
    """
    Charge toutes les questions organisées par catégorie et domaine.
    
    Returns:
        {
            "user1": {"culture": [...], "histoire": [...]},
            "user2": {"geographie": [...], "sport": [...]},
            "malus": {"malus": [...]},
            "bonus": {"bonus": [...]},
            "neutre": {"neutre": [...]}
        }
    """
    base_path = get_base_path()
    root_path = base_path / questions_root
    
    categories: Dict[str, Dict[str, List[str]]] = {}
    
    if not root_path.exists():
        print(f"[AVERTISSEMENT] Le dossier '{root_path}' n'existe pas.")
        return categories
    
    # Catégories principales à charger
    category_names = ["user1", "user2", "malus", "bonus", "neutre"]
    
    for category in category_names:
        category_path = root_path / category
        categories[category] = {}
        
        if not category_path.exists():
            continue
        
        # Pour malus, bonus, neutre: charger directement les .txt
        if category in ["malus", "bonus", "neutre"]:
            questions: List[str] = []
            for txt_file in category_path.glob("*.txt"):
                questions.extend(_parse_question_file(txt_file))
            if questions:
                categories[category][category] = questions
        else:
            # Pour user1, user2: charger les sous-dossiers comme domaines
            for domain_folder in sorted(category_path.iterdir()):
                if domain_folder.is_dir():
                    domain_name = domain_folder.name
                    domain_questions: List[str] = []
                    for txt_file in domain_folder.glob("*.txt"):
                        domain_questions.extend(_parse_question_file(txt_file))
                    if domain_questions:
                        categories[category][domain_name] = domain_questions
    
    return categories


def _parse_question_file(file_path: Path) -> List[str]:
    """Parse un fichier de questions (séparées par ligne vide)."""
    questions: List[str] = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        raw_questions = content.split("\n\n")
        for q in raw_questions:
            cleaned = q.strip()
            if cleaned:
                questions.append(cleaned)
    except Exception as e:
        print(f"[ERREUR] Impossible de lire '{file_path}': {e}")
    return questions


class QuestionManager:
    """
    Gestionnaire de questions avec anti-doublon.
    Une question posée ne sera plus proposée jusqu'à fermeture.
    """
    
    def __init__(self, questions_root: str = "questions"):
        self.all_questions = load_questions_by_category(questions_root)
        self.used_questions: Set[str] = set()  # Questions déjà posées
    
    def get_random_question(self, category: str, domain: str) -> Optional[str]:
        """
        Retourne une question aléatoire non encore posée.
        
        Args:
            category: "user1", "user2", "malus", "bonus", "neutre"
            domain: Nom du domaine ou catégorie elle-même pour malus/bonus/neutre
            
        Returns:
            Une question ou None si toutes ont été posées
        """
        if category not in self.all_questions:
            return None
        
        if domain not in self.all_questions[category]:
            return None
        
        available = [
            q for q in self.all_questions[category][domain]
            if q not in self.used_questions
        ]
        
        if not available:
            return None
        
        question = random.choice(available)
        self.used_questions.add(question)
        return question
    
    def get_domains(self, category: str) -> List[str]:
        """Retourne la liste des domaines d'une catégorie."""
        if category not in self.all_questions:
            return []
        return list(self.all_questions[category].keys())
    
    def get_domain_count(self, category: str, domain: str) -> int:
        """Retourne le nombre de questions dans un domaine."""
        if category not in self.all_questions:
            return 0
        if domain not in self.all_questions[category]:
            return 0
        return len(self.all_questions[category][domain])
    
    def get_remaining_count(self, category: str, domain: str) -> int:
        """Retourne le nombre de questions restantes (non posées)."""
        if category not in self.all_questions:
            return 0
        if domain not in self.all_questions[category]:
            return 0
        return len([
            q for q in self.all_questions[category][domain]
            if q not in self.used_questions
        ])


# Compatibilité avec l'ancien code
def load_questions_from_folder(questions_root: str = "questions") -> Dict[str, List[str]]:
    """Ancienne fonction de compatibilité."""
    categories = load_questions_by_category(questions_root)
    result: Dict[str, List[str]] = {}
    for cat, domains in categories.items():
        for domain, questions in domains.items():
            result[f"{cat}/{domain}"] = questions
    return result


def get_domain_names(questions_dict: Dict[str, List[str]], max_domains: int = 8) -> List[str]:
    """Ancienne fonction de compatibilité."""
    return sorted(questions_dict.keys())[:max_domains]
