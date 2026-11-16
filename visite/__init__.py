"""Moteur « visite douane » — un dossier JSON, toutes les sorties.

Couches :
  1. data      : dossier.json (source unique) + schéma de validation
  2. calc/ocr  : contrôles automatiques, extraction OCR, contrôle de fidélité
     render    : fiche technique PDF ; verify : relecture du PDF produit
  3. mobile    : page de visite pour téléphone (check-list, photos, PV)
  4. registry  : registre des dossiers + tableau de bord
"""
__version__ = "0.1.0"
