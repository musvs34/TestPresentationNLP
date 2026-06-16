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
- lecture des sections configurees dans `configs/sections.csv`
- lecture des controles generiques dans `configs/generic_detection_rules.csv`
- lecture des fichiers Article 9 `configs/article9_terms.csv` et `configs/article9_whitelist.csv`
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

## Controle generique par referentiel

Les controles de sections, de clauses, de conseil et de mots interdits sont pilotes par configuration.
Ils ne sont plus codes en dur dans le pipeline.

Sections a extraire :

- `configs/sections.csv`

Regles a appliquer :

- `configs/generic_detection_rules.csv`

Chaque regle peut contenir :

- `rule_id` : identifiant stable de la regle
- `section_scope` : section cible, par exemple `beneficiaires`, `conseil` ou `document`
- `category` : famille de controle
- `terms` : mots ou mots composes separes par `|`
- `synonyms` : synonymes separes par `|`
- `alert_level` : `interdit`, `alerte` ou `ambigue`
- `severity` : `high`, `medium` ou `low`
- `base_score` : score de depart
- `fuzzy_threshold` : seuil de rapprochement pour fautes d'orthographe

Le moteur generique gere les detections `exact`, `synonym`, `root` et `fuzzy`.

## Controle Article 9 RGPD

Le projet contient un premier bloc de detection locale des donnees sensibles Article 9.
Il analyse le texte extrait du document et produit des alertes avec :

- categorie Article 9, par exemple `sante`, `opinions_politiques`, `appartenance_syndicale`
- regle declenchee via `rule_id`
- type de detection : `exact`, `synonym`, `root` ou `fuzzy`
- score numerique entre `0` et `1`
- terme detecte et extrait justificatif

Le dictionnaire est parametre dans :

- `configs/article9_terms.csv`

Colonnes principales :

- `rule_id` : identifiant stable de la regle
- `category` : categorie Article 9
- `label` : libelle lisible
- `terms` : termes separes par `|`
- `synonyms` : synonymes separes par `|`
- `alert_level` : `interdit`, `alerte` ou `ambigue`
- `base_score` : score de depart
- `fuzzy_threshold` : seuil de detection des fautes probables

Les expressions a ne pas remonter sont parametrees dans :

- `configs/article9_whitelist.csv`

Ce premier bloc reste volontairement explicable et 100 % local. Il ne fait aucun appel externe.

## Evolution ML locale

Le bloc Article 9 peut ensuite etre complete par un module ML optionnel, lui aussi local :

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
- `notebooks/analysis_workflow_example.ipynb` : exemple historique plus compact

Exemple de flux :

```python
from compliance_nlp import analyze_directory, results_to_dataframe

results = analyze_directory("data/raw", output_path="outputs/analysis/results.json")
df = results_to_dataframe(results)
df[df["code"] == "beneficiary_clause_imprecise"]
df[df["matched_term"] == "sans risque"]
df[df["code"].str.startswith("article9_", na=False)]
df[df["score"] >= 0.85]
```
