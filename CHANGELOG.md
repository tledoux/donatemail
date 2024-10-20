# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Removed

## [1.5.0] - 2024-10-20

### Added

- Ajout de la gestion du délai de connexion (timeout)
- Ajout d'un timer pour les opérations longues
- Ajout d'un seuil de messages pour forcer la reconnexion, pour éviter le 'BYE'
- Gestion du BYE (abort) lors du fetch des mails
- Gestion du NO lors du fetch des mails
- Omission des messages après 2 NO consécutifs
- Ajout des zones de saisie pour le délai de connexion et le seuil de messages
- Génération d'un fichier json pour documenter la récupération
- Ajout du fichier json dans la livraison comme de la métadonnée

### Changed

- Correction pour les noms de dossiers avec un espace

### Removed


## [1.4.0] - 2024-08-14

### Added

- Récupération des contenus des sous-dossiers

### Changed

- Correction du parsing de la liste des dossiers

### Removed

## [1.3.1] - 2024-08-09

### Added

- Ajout de badges sur la page README

### Changed

- Correction des liens de comparaison de version

### Removed

## [1.3.0] - 2024-08-09

### Added

- Ajout du CHANGELOG
- Ajout du CONTRIBUTING
- Ajout de l'action `release-notes-from-changelog` pour générer les notes de release

### Changed

- Explicitation des limites du programme dans le README

### Removed

## [1.2.9] - 2024-08-08

### Added

- Utilisation des GitHub Actions pour générer les binaires

### Changed

### Removed

## [1.2.0] - 2024-08-08

### Added

- Passage sur Github pour la gestion du projet

### Changed

- Amélioration de l'interface pour les hautes résolutions d'écran
- Meilleure gestion des polices de caractères présentes
- Remplacement des emoji par des images
- Utilisation du module mutf7 sous licence WTFPL pour la gestion de l'encodage _modified UTF-7_
- Passage en texte du fichier `file_version_info` de description du binaire Windows

### Removed

## [1.1.0] - 2024-08-06

### Added

- Ajout de dialog_utils pour centraliser les utilitaires graphiques
- Ajout d'une explication pour les mots de passe applicatifs
- Gestion des préférences utilisateurs

### Changed

- Opérations longues portées par des threads séparés pour garder une interface fluide

### Removed

## [1.0.0] - 2024-08-04

### Added

- Version initiale de l'IHM
- Serveurs d'IMAP connus
- Récupération des dossiers
- Récupération des courriels d'un dossier
- Création de la livraison

### Changed

### Removed

[Unreleased]: https://github.com/tledoux/donatemail/compare/v1.5.0..HEAD
[1.5.0]: https://github.com/tledoux/donatemail/compare/v1.4.0..v1.5.0
[1.4.0]: https://github.com/tledoux/donatemail/compare/v1.3.1..v1.4.0
[1.3.1]: https://github.com/tledoux/donatemail/compare/v1.3.0..v1.3.1
[1.3.0]: https://github.com/tledoux/donatemail/compare/v1.2.9..v1.3.0
[1.2.9]: https://github.com/tledoux/donatemail/compare/v1.2.0..v1.3.9
[1.2.0]: https://github.com/tledoux/donatemail/releases/tag/v1.2.0