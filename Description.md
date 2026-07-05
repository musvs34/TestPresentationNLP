# Description des branches d'analyse

## Objectif

Comparer 4 methodes de detection complementaires pour identifier des alertes dans des textes de conformite.

L'objectif n'est pas de choisir une seule methode, mais de comprendre ce que chacune sait bien detecter et comment elles se completent.

## Inputs

### Mots_interdits.csv

Referentiel metier principal. Il contient les mots ou expressions a surveiller, leur categorie et la justification metier associee.

### spacy_synonyms.csv

Fichier de synonymes. Il sert a elargir la detection a des mots proches ou equivalents.

### whitelist.csv

Liste d'expressions a ignorer. Elle permet de reduire les faux positifs, c'est-a-dire les alertes remontees a tort.

### test_cases.csv

Fichier de cas de test. Il permet de mesurer les performances des 4 branches : ce qui est bien detecte, ce qui est manque, et ce qui remonte a tort.

## Quelques termes utiles

### Synonyme

Mot ou expression proche d'un terme metier.

Exemple : "maladie" peut etre rapproche de "pathologie".

### Lemme

Forme de base d'un mot.

Exemple : "detectees", "detecter", "detection" sont rapproches d'une meme famille de sens.

### Formes flechies

Variations grammaticales d'un mot.

Exemples : singulier/pluriel, masculin/feminin, conjugaisons.

"Interdit", "interdite", "interdits", "interdites" sont des formes flechies.

### Fuzzy matching

Detection approximative.

Cela permet de reconnaitre un mot meme s'il est legerement different, mal orthographie ou proche.

Exemple : detecter une expression malgre une faute de frappe ou une petite variation.

### Zero-shot

Capacite d'un modele a detecter un concept sans avoir ete entraine specifiquement sur nos exemples metier.

On lui donne un label, par exemple "donnee de sante", et il cherche dans le texte des passages qui correspondent a cette idee.

### Faux positif

Alerte remontee alors qu'elle ne devrait pas l'etre.

Exemple : un mot sensible apparait dans une expression autorisee ou non pertinente.

## Branche 1 : generic

La branche `generic` applique des regles metier explicites.

Elle cherche principalement les termes presents dans le referentiel `Mots_interdits.csv`.

### Capacites de detection

Elle detecte :

- les mots ou expressions exacts ;
- les synonymes deja configures ;
- les variantes proches ;
- les mots ayant une racine similaire ;
- certaines petites differences d'ecriture grace au fuzzy matching.

### Lecture metier

C'est la methode la plus proche d'un controle par dictionnaire metier.

Elle repond a la question :

> Est-ce qu'un terme interdit ou un synonyme prevu apparait dans le texte ?

### Points forts

- Tres comprehensible.
- Facile a justifier.
- Fiable quand le referentiel est bien renseigne.
- Adaptee aux controles reglementaires explicites.
- Stable et reproductible.

### Limites

- Detecte surtout ce qui a ete prevu.
- Peut manquer une formulation trop differente.
- Sa qualite depend fortement du contenu du fichier metier.
- Moins adaptee aux formulations implicites ou tres reformulees.

## Branche 2 : spacy

La branche `spacy` ajoute une analyse linguistique.

Elle ne regarde pas seulement si un mot est present. Elle analyse aussi la forme des mots, leurs variantes et les synonymes.

Elle s'appuie notamment sur `spacy_synonyms.csv`.

### Capacites de detection

Elle detecte :

- les synonymes enrichis ;
- les formes flechies ;
- les lemmes ;
- les variantes lexicales proches ;
- certaines reformulations simples.

Elle realise aussi :

- l'enrichissement du fichier `spacy_synonyms.csv` a partir des termes metier ;
- l'exploitation de ce dictionnaire enrichi pour ameliorer la couverture.

### Lecture metier

C'est la methode qui permet de mieux couvrir les differentes facons d'ecrire ou de formuler une meme idee.

Elle repond a la question :

> Est-ce qu'une variante linguistique ou un synonyme enrichi du terme metier apparait ?

### Points forts

- Meilleure couverture que la detection simple par dictionnaire.
- Utile quand les redacteurs utilisent des formulations variees.
- Reste reliee aux termes metier.
- Enrichit progressivement les synonymes.
- Bon compromis entre regles metier et analyse linguistique.

### Limites

- Plus complexe a expliquer qu'une regle exacte.
- Peut remonter plus de faux positifs si les synonymes sont trop larges.
- Depend d'un moteur linguistique francais.
- Plus lourde a executer que la branche `generic`.

## Branche 3 : gliner

La branche `gliner` detecte des concepts a partir de labels.

Au lieu de chercher uniquement un mot exact, on lui donne une notion a reperer, par exemple :

- donnee de sante ;
- appartenance religieuse ;
- origine ethnique ;
- conseil non professionnel ;
- promesse de performance.

Elle peut reperer un passage meme si les mots exacts du referentiel ne sont pas presents.

### Capacites de detection

Elle detecte :

- des concepts ;
- des entites ;
- des formulations indirectes ;
- des signaux faibles ;
- des passages proches d'une categorie metier.

### Technologie utilisee

La branche s'appuie sur un modele GLiNER.

GLiNER est utilise ici pour faire de la detection par labels. Le modele recoit une liste de labels metier et cherche dans le texte les passages qui semblent correspondre a ces labels.

### Lecture metier

C'est la methode qui comprend le mieux l'intention ou le theme general d'un passage.

Elle repond a la question :

> Est-ce qu'un passage correspond a une idee ou une categorie metier, meme si les mots exacts ne sont pas utilises ?

### Points forts

- Utile pour detecter des formulations non prevues.
- Permet d'elargir fortement la couverture.
- Fonctionne par categories metier comprehensibles.
- Interessant pour reperer des signaux implicites.

### Limites

- Moins facile a justifier qu'une regle exacte.
- Peut produire davantage de faux positifs.
- Necessite un seuil de confiance bien regle.
- Depend d'un modele d'intelligence artificielle.
- Plus difficile a auditer qu'une detection par regle.

## Branche 4 : regex

La branche `regex` detecte des formats tres structures.

Elle ne cherche pas a comprendre le texte. Elle cherche des formes reconnaissables.

### Capacites de detection

Elle detecte par exemple :

- adresse email ;
- numero de telephone francais ;
- IBAN francais ;
- NIR francais.

### Technologie utilisee

La branche s'appuie sur des expressions regulieres.

Une expression reguliere est une regle de recherche qui decrit une forme attendue. Par exemple, une adresse email ou un IBAN ont une structure reconnaissable.

### Lecture metier

C'est la methode la plus fiable pour reperer des donnees qui ont un format precis.

Elle repond a la question :

> Est-ce qu'un format structure sensible est present dans le texte ?

### Points forts

- Tres precise.
- Tres rapide.
- Tres explicable.
- Ideale pour les identifiants ou donnees personnelles structurees.
- Faible risque de faux positif lorsque le format est bien defini.

### Limites

- Ne detecte que les formats prevus.
- Ne comprend pas le contexte.
- Ne couvre pas les formulations metier.
- Ne detecte pas les concepts implicites.

## Comparaison simple

### generic

Repond a la question :

> Est-ce qu'un terme interdit ou un synonyme prevu apparait dans le texte ?

### spacy

Repond a la question :

> Est-ce qu'une variante linguistique ou un synonyme enrichi du terme metier apparait ?

### gliner

Repond a la question :

> Est-ce qu'un passage correspond a une idee ou une categorie metier, meme si les mots exacts ne sont pas utilises ?

### regex

Repond a la question :

> Est-ce qu'un format structure sensible est present dans le texte ?

## Synthese comparative

| Branche | Meilleure pour | Points forts | Limites principales |
| --- | --- | --- | --- |
| `generic` | Regles metier explicites | Explicable, stable, auditable | Depend du referentiel |
| `spacy` | Variantes linguistiques et synonymes | Meilleure couverture lexicale | Peut generer des faux positifs |
| `gliner` | Concepts implicites et labels metier | Detection plus large et conceptuelle | Moins explicable, depend d'un modele IA |
| `regex` | Formats structures | Precise, rapide, deterministe | Limitee aux formats prevus |

## Message cle

Les 4 methodes sont complementaires.

`generic` apporte la rigueur metier.

`spacy` elargit la couverture linguistique.

`gliner` capte les formulations plus implicites.

`regex` securise les donnees structurees.

L'interet du notebook de comparaison est de mesurer, sur les memes cas de test, ce que chaque branche detecte, ce qu'elle manque, et les alertes qu'elle remonte a tort.
