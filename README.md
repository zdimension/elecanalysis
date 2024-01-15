> [!NOTE]
> This is in French because this project is pretty much only useful for people living in France, since the systems it allows integrating with are only present in France.

# elecanalysis

Outil d'analyse de consommation électrique et de comparaison de tarifs.

À la base, conçu pour tester la rentabilité de Tempo face aux autres offres (spoiler : à moins de vivre en haute montagne et de se chauffer avec des convecteurs d'un autre temps, c'est rentable).

![image](https://github.com/zdimension/elecanalysis/assets/4533568/9e6795f3-db47-4d8d-82da-4b256476dd46)

![image](https://github.com/zdimension/elecanalysis/assets/4533568/a5e8efba-982a-4a3e-b90b-bef7fc493143)

## Fonctionnement

Récupère :
- les données de conso depuis Enedis via [myElectricalData](https://www.myelectricaldata.fr/)
- les données de tarifs Bleu depuis [data.gouv.fr](https://www.data.gouv.fr)
  - (pour les autres offres, c'est... codé en dur, je les mets à jour à la main tous les quelques mois en copiant depuis les PDF, je n'ai pas trouvé mieux)
- les données de jour Tempo depuis [api-couleur-tempo](https://www.api-couleur-tempo.fr/)

## Usage

Nécessite :
- Python ≥ 3.10
- les dépendances (`pip install -r requirements.txt`)
- un fichier `.env` à créer (voir `.env.example`)
  - `PORT`: port d'écoute (par défaut 8129)
  - `MED_TOKEN`: jeton myElectricalData
  - `METER_ID`: numéro de compteur myElectricalData
 
Le premier lancement prend un peu de temps, car toutes les informations de consommation depuis l'activation du compteur sont récupérées. Aux lancements suivants, seules les données manquantes sont récupérées.
