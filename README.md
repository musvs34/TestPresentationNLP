# pocComplianceNLP

POC simple pour experimentation autour du traitement NLP applique a la compliance.

## Structure

- `src/` : code source
- `tests/` : tests
- `data/raw/` : donnees brutes
- `data/processed/` : donnees preparees
- `notebooks/` : notebooks d'exploration
- `scripts/` : scripts de lancement
- `outputs/` : sorties, rapports et artefacts

## Demarrage

Creer un environnement Python puis installer les dependances :

```bash
pip install -r requirements.txt
```

## Organisation du besoin

Le coeur du traitement est dans `src/compliance_nlp/` :

- extraction du texte PDF
- analyse du document complet dans une section unique `document`
- lecture du dictionnaire central dans `configs/Mots_interdits.csv`
- application optionnelle de la whitelist dans `configs/article9_whitelist.csv`
- serialisation des resultats
- helpers d'exploitation pour notebook

Le notebook sert uniquement a :

- lancer l'analyse
- charger les resultats
- filtrer et explorer les findings

## Lancer l'analyse

```bash
python scripts/run_analysis.py
```

Le resultat JSON est ecrit dans `outputs/analysis/results.json`.

## Chaine centrale de controle par referentiel

Les controles de mots interdits et Article 9 sont pilotes par le meme dictionnaire.
Ils sont appliques au document complet, sans fichier de configuration de sections.

Regles centrales a appliquer :

- `configs/Mots_interdits.csv`

Le fichier `Mots_interdits.csv` est le referentiel metier principal :

- `Terme interdit` : mot ou expression a detecter
- `Categorie` : famille utilisee pour classer l'alerte
- `Justification` : libelle explicatif remonte dans les resultats

Le chargeur reste compatible avec l'ancien format technique `generic_detection_rules.csv`
pour les tests et les experimentations avancees.

Le moteur central gere les detections `exact`, `synonym`, `root` et `fuzzy`.

## Controle Article 9 RGPD dans la chaine centrale

Les donnees sensibles Article 9 sont les lignes dont la colonne `Categorie`
contient `article 9`. La whitelist peut neutraliser certaines expressions
metier non sensibles.

Les expressions a ne pas remonter sont parametrees dans :

- `configs/article9_whitelist.csv`

Cette approche reste volontairement explicable et 100 % locale. Elle ne fait aucun appel externe.

## Evolution ML locale

Les regles Article 9 de la chaine centrale peuvent ensuite etre completees par un module ML optionnel, lui aussi local :

- modele francais embarque dans le SI
- classification de phrases par domaine sensible
- detection de formulations indirectes, par exemple `traitement par insuline`
- score combine entre regles explicables et prediction ML
- revue humaine obligatoire au-dessus d'un seuil configure

Le ML ne doit pas remplacer les regles : il doit remonter des suspicions supplementaires, avec un score et une trace de decision.

## Utiliser depuis notebook

Des notebooks sont disponibles dans :

- `notebooks/01_lancer_traitement.ipynb` : lance le traitement PDF et genere `outputs/analysis/results.json`
- `notebooks/02_analyser_resultats_scores.ipynb` : analyse les alertes, scores, categories Article 9 et files de revue humaine
- `notebooks/03_tester_performance_detection.ipynb` : teste les detecteurs a partir d'un tableau pandas saisi dans le notebook, sans lire de PDF

Exemple de flux :

```python
from compliance_nlp import analyze_directory, results_to_dataframe

results = analyze_directory("data/raw", output_path="outputs/analysis/results.json")
df = results_to_dataframe(results)
df[df["code"] == "beneficiary_clause_imprecise"]
df[df["matched_term"] == "sans risque"]
df[df["rule_scope"] == "article9"]
df[df["score"] >= 0.85]
```

