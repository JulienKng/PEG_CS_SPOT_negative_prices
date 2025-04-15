# PEG_CS_SPOT_negative_prices
Projet de la mention PEG sur la modélisation des prix négatifs

Ce modèle a été conçu et développé en 2024-2025 par trois élèves en 3A mention PEG à CentraleSupélec dans le cadre de leur projet de mention :
 - Jean Dormois 
 - Julien Koenig
 - Sixtine Marrel
Alors encadrés par Martin Hennebel.
Vous pouvez nous contacter à l'adresse mail suivante : julienkoenig@protonmail.com

### Utilisation du modèle :

Le modèle est composé de deux fichiers :
- "calculs_marches.py" contient toutes les fonctions nécessaires au fonctionnement du modèle.
- "main_model.ipynb" est un notebook permettant de faire tourner le modèle et de tracer les figures nécessaires.

### Données d'entrée

Les fichiers suivants sont fournis. Il s'agit à chaque fois des données pour 2023 :
- Baril de Brendt_mensuel_2023_insee.csv 
- Charbon_2023.csv 
- Consommation_test.csv : source Entso-e
- Coûts_marginaux_actualisés.csv : source auteurs
- Dispo_nucléaire_2023.csv : 
- Dutch_TTF_Natural_Gas_Futures_Historical_Data_2023_2.csv : 
- Flux_transfrontaliers.csv : 
- Observed_day_ahead_prices_entsoe_2023.csv : source Entso-e
- Prix carbone mensuel_2023_clean.csv : 
- Prod_par_type_BE.csv : source Entso-e
- Prod_par_type_DE.csv : source Entso-e
- Prod_par_type_ES.csv : source Entso-e
- Prod_par_type_FR.csv : source Entso-e
- Production_Fatales_2023.csv : source Entso-e

### Description des fonctions : 

marche_horaire_ren :
Création d'une liste contenant pour chaque heure un dictionnaire avec la production fatale de chaque énergie renouvelable

créa_liste_transfrontalier :
Création d\'une liste contenant pour chaque heure un dictionnaire du flux d'électiricité entre la France et ses pays voisins

crea_liste_prod_par_type : 
Création d'une liste contenant pour chaque heure un dictionnaire de la production de chaque type d'énergie

safe_float : 
Renvoie float(x) si c'est possible et 0.0 sinon

donnees_import : 
Renvoie le prix horaire de l'importation, la capacité horaire d'importation et si l'on importe au prix du gaz ou du renouvelable

capa_relle_avec_ren : 
Calcul de la capacité effective heure par heure disponible pour le spot

capa_totale_instalée : 
Calcul de la capacité horaire de chaque type d'énergie, qui n'est pas forcément disponible pour le marché SPOT

cout_carbone : 
Renvoie le coût horaire du carbone pour un type d'énergie

qui_min_2 : 
Renvoie la technologie qui à une heure donnée minimise le coût du MWH

qui_max : 
Renvoie la technologie qui à une heure donnée maximise le coût du MWH

quelle_cent_renouv : 
Renvoie la liste des centrales appelées à une heure donnée i, ainsi que le prix SPOT associé à ce profil de production

marche_horaire_sans_contrainte :
Renvoie le prix SPOT horaire, la liste de la consommation horaire et le profil de production horaire, sans aucune contrainté. Cela correspond à la première étape du modèle

capa_cm_ou_capa_neg_totale : 
Renvoie les contraintes de capacité minimale et de temps de démarrage et d'arrêt sous forme de 2 listes. La première contient ce qui est vendu au cout de fonctionnement la seconde ce qui est vendu à tout prix (donc à prix négatif)

quelle_cent_renouv_neg :
Renvoie la liste des centrales appelées à une heure donnée i, ainsi que le prix SPOT associé à ce profil de production, en prenant en compte les prix négatifs

marche_horaire_avec_contrainte : 
Renvoie le prix SPOT horaire, la liste de la consommation horaire et le profil de production horaire, avec les contraintes sur les centrales thermiques et nucléaires. Cela correspond à la deuxième étape du modèle

quelle_cent_contraintes_2 : 
Renvoie pour une heure donnée et à partir de la production précédemment calculée, le nouveau profil de production tenant compte des contraintes sur la flexibilité, le nouveau prix SPOT, la variation de la production et la production historique

gain_hydro_min :
Renvoie le gain espéré sur une année pour les producteurs d'hydraulique de lac pour une valeur d'usage, un prix SPOT et un profil de production pré-établi

val_usage_hydro_lac_monotone : 
Renvoie la valeur d'usage optimale pour l'hydraulique de lac

quelle_cent_renouv_neg_avec_lac : 
Renvoie la liste des centrales appelées à une heure donnée i, ainsi que le prix SPOT associé à ce profil de production, en prenant en compte les prix négatifs et de l'hydraulique de lac

marche_horaire_an_full :
Fonction principale du modèle. Elle calcule les étapes 1 et 2, et éventuellement 3. 
Elle renvoie le prix SPOT horaire, la production pour chaqu type d'énergie séparément, une liste contenant la consommation et l'écrêtement.

prix_moyen :
Renvoie une liste contenant le prix moyenné sur une certaine période

conversion_prod : 
Conversion des données de production en un DataFrame adapté à notre modèle

marche_horaire_an_full_usage_lac_dyna :
Même fonction que marche_horaire_an_full mais avec une valeur d'usage de l'hydraulique de lac qui est initialisée puis mise à jour régulièrement

fig_plotly_save : 
Sauvegarde la figure fig aux formats html et svg dans un dossier figures qui doit déjà exister

lissage :
Prise en compte de la contrainte sur le nombre de cycles annuels du nucléaire, la fonction renvoie le seuil à partir duquel un changement de palier a lieu, la nouvelle production de nucléaire et les différents paliers

analyse_detection :
Analyse de la détection des jours auxquels on a des prix négatifs dans le modèle par rapport à la réalité observée. Le résultat est imprimé.
