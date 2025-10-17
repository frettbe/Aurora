# 🌅 Aurora

**La lumière de la connaissance**

Application moderne de gestion de fonds de bibliothèque personnelle ou associative, conçue dans l'esprit des grandes bibliothèques humanistes.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![PySide6](https://img.shields.io/badge/PySide6-Qt6-green.svg)](https://wiki.qt.io/Qt_for_Python)

---

## ✨ Fonctionnalités

### 📚 Gestion complète
- **Livres** : CRUD complet, métadonnées enrichies (ISBN, éditeur, année, etc.)
- **Membres** : Gestion des emprunteurs avec date de retour de prêt personnalisable
- **Emprunts** : Système de prêts avec dates d'échéance et gestion des retours

### 🔄 Import/Export
- Import CSV/Excel avec mapping de colonnes flexible
- Export CSV/XLSX avec métadonnées (date, auteur, app version)
- Recherche et filtres avancés

### 🌍 Multilingue
- Interface traduite en 4 langues : Français, Anglais, Allemand, Néerlandais
- Changement de langue à la volée

### 🎨 Interface moderne
- Thèmes sombre/clair avec support de détection automatique
- Design élégant basé sur PyQtDarkTheme
- Interface intuitive et responsive

### 📊 Audit & Métriques
- Logs d'audit complets (création, modification, suppression)
- Métriques de performance (temps d'import, export, etc.)
- Traçabilité de toutes les actions

---

## 🚀 Installation

### Prérequis
- Python 3.13 ou supérieur
- pip

### Installation des dépendances
pip install -r requirements.txt

### Lancement
python run.py

--

## 📦 Dépendances principales

- **PySide6** (Qt 6) - Interface graphique
- **SQLAlchemy** - ORM base de données
- **OpenPyXL** - Export Excel
- **PyQtDarkTheme** - Thèmes modernes
- **PyYAML** - Traductions i18n

---

## 🏗️ Architecture

Aurora suit une architecture en couches propre et maintenable :
libapp/
├── persistence/ # Modèles de données (SQLAlchemy)
├── services/ # Logique métier
├── views/ # Interface graphique (Qt)
├── translations/ # Fichiers i18n (YAML)
└── resources/ # Assets (icônes, images)

**Principes** :
- Séparation stricte des couches (MVC)
- Pas de logique métier dans les vues
- Services réutilisables et testables

---

## 🎯 Roadmap

### V1.0 (Actuelle)
- [x] CRUD complet (livres, membres, emprunts)
- [x] Import/Export CSV/Excel
- [x] Système d'audit et métriques
- [x] Interface multilingue (4 langues)
- [x] Thèmes modernes
- [x] Page "À propos"

### V1.1 (Prochaine)
- [ ] Interface de visualisation des logs d'audit
- [ ] Dashboard métriques de performance
- [ ] Recherche avancée avec filtres multiples
- [ ] Statistiques de la bibliothèque
- [ ] Export PDF des rapports

### V2.0 (Future)
- [ ] Mode multi-utilisateurs avec authentification
- [ ] API REST pour intégration externe
- [ ] Application mobile (Flutter)
- [ ] Synchronisation cloud
- [ ] Système de réservations

---

## 🤝 Contribuer

Les contributions sont les bienvenues ! Pour contribuer :

1. Fork le projet
2. Crée une branche pour ta fonctionnalité (`git checkout -b feature/AmazingFeature`)
3. Commit tes changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvre une Pull Request

**Guidelines** :
- Respect des standards Ruff
- Docstrings complètes pour toutes les fonctions
- Tests unitaires pour les nouvelles fonctionnalités



## 📜 Licence

Ce projet est distribué sous licence **GNU General Public License v3.0**.

Voir le fichier [LICENSE](LICENSE) pour plus de détails.


---

## 👤 Auteur

Développé par **6f4**

- 🌐 Site web : [www.6f4.be](https://www.6f4.be)
- 📧 Contact : contact@6f4.be
- 🐙 GitHub : [github.com/frettbe/Aurora](https://github.com/frettbe/Aurora)

---

## 🙏 Remerciements

- **OpenLibrary, BNF, Google Books** pour les APIs de métadonnées
- **Communauté Qt/PySide** pour le framework
- **Communauté open source** pour les bibliothèques utilisées

---

## 📸 Captures d'écran

*(À ajouter)*

---

## 🐛 Signaler un bug

Pour signaler un bug ou suggérer une amélioration, contactez : **contact@6f4.be**

---

**Aurora** - *Comme l'aurore chasse l'obscurité, Aurora préserve et partage la lumière de la connaissance.* 🌅

---

© 2025 6f4. Tous droits réservés.