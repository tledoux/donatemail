# donatemail : un outil de récupération de courriels depuis des plateformes WebMail

[![Python check](https://github.com/tledoux/donatemail/actions/workflows/python-app.yml/badge.svg)](https://github.com/tledoux/donatemail/actions/workflows/python-app.yml "Check workflow")
[![Release](https://github.com/tledoux/donatemail/actions/workflows/build-win-app.yml/badge.svg)](https://github.com/tledoux/donatemail/actions/workflows/build-win-app.yml "Release")
[![GitHub issues](https://img.shields.io/github/issues/tledoux/donatemail.svg)](https://github.com/tledoux/donatemail/issues "Open issues on GitHub")


Cet outil présente une IHM capable de se connecter à un WebMail via IMAP pour créer une livraison de courriels.
Une fois le paramétrage réalisé, il peut:
  * lister les dossiers dans la boite aux lettres,
  * récupérer les courriels pour un dossier sélectionné et les aggréger dans un fichier MBOX,
  * préparer une livraison sous forme d'un ZIP, conforme à la spécification BagIt, à transmettre à la bibliothèque.


L'IHM utilise les icones issues de la collection [Gartoon de wikimedia commons](https://commons.wikimedia.org/wiki/Category:Gartoon_icons).

Ce programme n'a été testé que sous Windows.

## LIMITATIONS

:warning: Ce programe ne fonctionne que dans ces conditions :
  * le port 993 doit être ouvert sur votre réseau pour permettre l'usage du protocole IMAP SSL,
  * il faut généralement créer et utiliser un mot de passe **applicatif** à votre messagerie pour permettre son accès depuis une application tierce comme celle-ci.



## RUN
Pour lancer l'IHM, faire

```
python donate_gui.py
```

L'option `-v` permet d'avoir de l'information sur la console de lancement.

## BUILD
Pour construire l'exécutable, installer le module pyinstaller, puis faire

```
pyinstaller donatemail.spec
```

Cela génère un exécutable `donatemail.exe` dans le répertoire `dist`


## TODO


