"""Le code suivant a été conçu et développé en 2024-2025 par trois élèves en 3A mention PEG à CentraleSupélec dans le cadre de leur projet de mention :
 - Jean Dormois 
 - Julien Koenig
 - Sixtine Marrel
Alors encadrés par Martin Hennebel.
Vous pouvez nous contacter à l'adresse mail suivante : julienkoenig@protonmail.com
"""


import pandas as pa
import numpy as np 
from collections import defaultdict


#marche horaire renouvelable
def marche_horaire_ren(prodfadf:pa.DataFrame):
    """Création d\'une liste contenant pour chaque heure un dictionnaire avec la production fatale de chaque énergie renouvelable"""
    utilisation_cent = []
    for i in range(len(prodfadf)):
        utilisation_cent.append({
            'Hydr': prodfadf.loc[i, 'Hydro Run-of-river and poundage'],
            'Sola': prodfadf.loc[i, 'Solar'],
            'Dech': prodfadf.loc[i, 'Waste'],
            'Eoli': prodfadf.loc[i, 'Wind Onshore']
        })
    return utilisation_cent

# données des imports
def créa_liste_transfrontalier(fluxdf:pa.DataFrame):
    """Création d\'une liste contenant pour chaque heure un dictionnaire du flux d'électiricité entre la France et ses pays voisins"""
    # Les valeurs sont positives pour un import en France et négative pour un export depuis la France
    flux = []
    heure = fluxdf.loc[0, "MTU"]
    flux_heure = {}
    for i in range(len(fluxdf)):
        if fluxdf.loc[i, 'MTU'] != heure:
            heure = fluxdf.loc[i, "MTU"]
            flux.append(flux_heure)
            flux_heure = {}
        if fluxdf.loc[i, "In Area"] == "France (FR)":
            # >0 si import
            # <0 si export
            flux_heure[fluxdf.loc[i, "Out Area"]] = fluxdf.loc[i, "Physical Flow (MW)"]
    return flux

def crea_liste_prod_par_type(proddf:pa.DataFrame):
    """Création d'une liste contenant pour chaque heure un dictionnaire de la production de chaque type d'énergie"""
    prod_pays = []
    heure = proddf.loc[0, "MTU (CET/CEST)"]
    prod_heure = {}
    for i in range(len(proddf)):
        if proddf.loc[i, "MTU (CET/CEST)"] != heure:
            heure = proddf.loc[i, "MTU (CET/CEST)"]
            prod_pays.append(prod_heure)
            prod_heure = {}
        prod_heure[proddf.loc[i, "Production Type"]] = proddf.loc[i, "Generation (MW)"]
    return prod_pays

def safe_float(x:any):
    """Renvoie float(x) si c'est possible et 0.0 sinon"""
    try:
        return float(x)
    except:
        return 0.0

def donnees_import (prod_all:list, prod_esp:list, prod_bel:list, imports:list, temps:list, Prix_gaz:list):
    """Renvoie le prix horaire de l'importation, la capacité horaire d'importation et si l'on importe au prix du gaz ou du renouvelable"""
    # prod_all, prod_esp, et prod_bel : productions horaires de l'Allemagne, l'Espagne et la Belgique
    # imports : liste des échanges transfrontaliers
    # temps : échelle de temps 
    # Prix_gaz : prix horaire du gaz
    date = pa.to_datetime(temps)
    import_par_source = []
    prix_import = []
    capacite_importee = []
    limite_interco = 13e3 #capacité d'interconnexion totale de la France
    i = 0
    for d in date:
        i += 1
        importation = 0
        dico_import = {'Fossil Gaz': 0, 'Renewables': 0}
        prix = 0
        if (d.month<3 or d.month>10): # Cas de l'hiver : on importe au prix du gaz
            dico_import['TGCC'] = limite_interco #on dit que l'on peut toujours importer à la capacité max de la ligne
            importation += limite_interco
            prix = Prix_gaz[i] #on remplacera par le prix du gaz du jour

        else : # Cas de l'été, on adapte à la production d'ENR des pays voisins
            prod_solaire_espagne = float(prod_esp[i]['Solar'])
            prod_eolienne_espagne = float(prod_esp[i]['Wind Offshore'])+float(prod_esp[i]['Wind Onshore'])
            import_jour_espagne = float(imports[i]['Spain (ES)'])
            import_jour_allemaggne = float(imports[i]['Germany (DE)'])
            import_jour_belgique = float(imports[i]['Belgium (BE)'])
            if (prod_solaire_espagne > 15e3 or prod_eolienne_espagne > 10e3) and (import_jour_espagne>0):
                dico_import['Renewables'] += import_jour_espagne
                importation = dico_import['Renewables']
                prix = -500 # on considère que les pays vendent à prix négatif
                
            prod_solaire_allemagne = float(prod_all[i]['Solar'])
            prod_eolienne_allemagne = float(prod_all[i]['Wind Offshore'])+float(prod_all[i]['Wind Onshore'])
            if (prod_solaire_allemagne > 35e3 or prod_eolienne_allemagne > 30e3) and (import_jour_allemaggne>0):
                dico_import['Renewables'] += import_jour_allemaggne
                importation += dico_import['Renewables']
                prix = -500
            
            prod_eolienne_belge = (safe_float(prod_bel[i]['Wind Offshore']) + safe_float(prod_bel[i]['Wind Onshore']))
            prod_solaire_belge = safe_float(prod_bel[i]['Solar'])
            if (prod_solaire_belge > 5e3 or prod_eolienne_belge > 3e3) and (import_jour_belgique>0):
                dico_import['Renewables'] += import_jour_belgique
                importation += dico_import['Renewables']
                prix = -500
            if importation > limite_interco :
                importation = limite_interco
        prix_import.append(prix)
        capacite_importee.append(importation)
        import_par_source.append(dico_import)
    return(prix_import, capacite_importee, import_par_source) 

def capa_relle_avec_ren(capa_conv:dict, marche_horaire_ren:list, dispo_nucl:pa.DataFrame, capa_import:list):
    """Calcul de la capacité effective heure par heure disponible pour le spot"""
    capa_relle_avec_ren = []
    for i in range(len(marche_horaire_ren)):
        capa_conv_copy = capa_conv.copy()
        capa_conv_copy['TGCC'] = capa_conv['TGCC']*0.9 #on enlève les 10% de réserve
        jour = i//24
        capa_conv_copy['nucl'] = dispo_nucl.loc[jour][1]*1000*0.9 #on elève les 10% de réserve
        for techno in marche_horaire_ren[i]:
            capa_conv_copy[techno] = marche_horaire_ren[i][techno]
        capa_conv_copy['Importation'] = capa_import[i]
        capa_relle_avec_ren.append(capa_conv_copy)    
    return capa_relle_avec_ren

def capa_totale_instalée(capa_conv:dict, marche_horaire_ren:list, dispo_nucl:pa.DataFrame, capa_import:list):
    """Calcul de la capacité horaire de chaque type d'énergie, qui n'est pas forcément disponible pour le marché SPOT"""
    capa_totale_instalee = []
    for i in range(len(marche_horaire_ren)):
        capa_conv_copy = capa_conv.copy()
        capa_conv_copy['TGCC'] = capa_conv['TGCC']
        jour = i//24
        capa_conv_copy['nucl'] = dispo_nucl.loc[jour][1]*1000
        for techno in marche_horaire_ren[i]:
            capa_conv_copy[techno] = marche_horaire_ren[i][techno]
        capa_conv_copy['Importation'] = capa_import[i]
        capa_totale_instalee.append(capa_conv_copy)    
    return capa_totale_instalee

def cout_carbone(dico_cent:dict,cent:str,prix_CO2:pa.DataFrame, h_an:int):
    """Renvoie le coût horaire du carbone pour un type d'énergie"""
    mois=h_an//(31*24)
    prix = prix_CO2.loc[mois, "Prix Moyen"]*dico_cent[cent]['CO2']
    return prix

def qui_min_2(i:int,dY:dict, dY2:list):# dY : dictionnaire contenant les couts par heure de fonctionnement de chaque centrale
    """Renvoie la technologie qui à une heure donnée minimise le coût du MWH"""
    min = 500
    tech_min = ''
    for c in dY2:
        if dY[c][i]<min:
            min = dY[c][i]
            tech_min = c
    return tech_min

def qui_max(i:int,dY:dict, dY2:list):# dY : dictionnaire contenant les couts par heure de fonctionnement de chaque centrale
    """Renvoie la technologie qui à une heure donnée maximise le coût du MWH"""
    max = -500
    tech_max = ''
    for c in dY2:
        if dY[c][i]>max:
            max = dY[c][i]
            tech_max = c
    return tech_max

def quelle_cent_renouv(conso:float, capa_prod:list, i:int, dY:dict): 
    """Renvoie la liste des centrales appelées à une heure donnée i, ainsi que le prix SPOT associé à ce profil de production"""
    # Permet de choisir la centrale à mobiliser sur une heure donnée i
    prod = 0
    res = {}
    dispo = []
    Techno = ['nucl', 'char', 'TGCC', 'TFCO', 'Importation', 'Importation_autre', 'Hydr', 'Sola', 'Dech', 'Eoli']
    for cent in Techno:
        dispo.append(cent)
    while prod < conso: # On cherche à compléter le profil de production progressivement jusqu'à ce que production = consommation
        techno_min = qui_min_2(i, dY, dispo)
        cout_min = dY[techno_min][i]   
        if conso < capa_prod[i][techno_min]+prod:
            res[techno_min]=conso-prod
            prod += res[techno_min]
            dispo.remove(techno_min)
            break
        else:
            prod += capa_prod[i][techno_min]
            res[techno_min]=capa_prod[i][techno_min]
            dispo.remove(techno_min)
    for cent in dispo:
        res[cent] = 0
    return (res,cout_min)

def marche_horaire_sans_contrainte(conso, capa_prod:list, dY:dict):
    """Renvoie le prix SPOT horaire, la liste de la consommation horaire et le profil de production horaire, sans aucune contrainté. Cela correspond à la première étape du modèle"""
    l_cons = []
    prix_spot_conv = []
    prod = []
    for i in range(len(conso)): # On commence par convertir les données de consommation
        if type(conso) == list:
            l_cons.append(float(conso[i])*1000)
        else:
            l_cons.append(float(conso.loc[i, 'Load'])*1000)
    for i in range(len(l_cons)): # Pour chaque heure on calcule la production et le prix SPOT avec la fonction quelle_cent_renouv
        calcul = quelle_cent_renouv(l_cons[i], capa_prod, i, dY)
        prod_dic = {}
        for cent in calcul[0]:
            prod_dic[cent] = calcul[0][cent]
        prod.append(prod_dic)
        prix_spot_conv.append(calcul[1])
    return (prix_spot_conv, l_cons, prod)

def capa_cm_ou_capa_neg_totale(Prix:list, dY:dict, prod:list, capa_prod:list, capa_instalée:list, arret:dict, min_fonctionnement:dict, consodf:pa.DataFrame):
    """Renvoie les contraintes de capacité minimale et de temps de démarrage et d'arrêt sous forme de 2 listes. La première contient ce qui est vendu au cout de fonctionnement la seconde ce qui est vendu à tout prix (donc à prix négatif)"""
    capa_cm = []
    capa_neg = []
    for k in range(len(consodf)):
        dico_neg = {}
        dico_cm = {}
        for cent in capa_prod[k]:
            dico_neg[cent] = 0 #au départ on a pas d'heure négative
            dico_cm[cent] = prod[k][cent]
        capa_neg.append(dico_neg)  
        capa_cm.append(dico_cm)

    for i in range(len(consodf)):
        for cent in prod[i]:
            if (prod[i][cent]>0) and (dY[cent][i]>Prix[i]): #si le prix est inférieur à la techno marginale c'est que cette techno produit sous prix négatif
                capa_neg[i][cent] = prod[i][cent]
                capa_cm[i][cent] = 0

        for cent in arret:
            t_arret = arret[cent]

            if prod[i][cent] > 0: #on vérifie qu'on a besoin de la techno 'cent' à l'heure i
                
                # contrainte de capacité minimale (on considère la capacité totale instalée)
                
                if prod[i][cent] < min_fonctionnement[cent]*capa_instalée[i][cent]: #les centrales ne doivent pas produire à moins d'une certaine fraction de leur capa nominale
                    capa_neg[i][cent] = min_fonctionnement[cent]*capa_instalée[i][cent] #on vend la prod minimale de fonctionnement à prix negatif
                    capa_cm[i][cent] = capa_instalée[i][cent]-capa_neg[i][cent]
                    prod[i][cent] = min_fonctionnement[cent]*capa_instalée[i][cent] #la centrale se met à produire à son minimum requis
                 
                
                #contraintes de temps de démarrage et d'arrêt
                
                if i > (t_arret+1):
                    for j in range(int(i-t_arret), i): #on parcourt le temps nécessaire à l'arrêt avant i
                        if ((prod[j][cent] == 0) and (prod[j-1][cent] != 0)): #si on l'arrête alors qu'on ne devrait pas
                            for k in range(int(i-t_arret), i):
                                if prod[k][cent] == 0: #on allume la centrale aux heures où elle est éteinte
                                    capa_cm[k][cent] = 0 #on garde les centrales allumée mais on ne vend pas au Cm, on veut vendre à prix neg
                                    capa_neg[k][cent] += prod[i][cent] 
                                    prod[k][cent] = prod[i][cent] #la centrale se met à produire
                            break # les heures ont toutes été déjà modifiées
                
    return(capa_cm, capa_neg)

def quelle_cent_renouv_neg(conso:float, capa_prod_cm:list, capa_prod_negatif:list, i:int, dY:dict, prix_min:float, historique:list): #permet de choisir la centrale à mobiliser sur une heure donnée i
    """Renvoie la liste des centrales appelées à une heure donnée i, ainsi que le prix SPOT associé à ce profil de production, en prenant en compte les prix négatifs"""
    prod = 0
    res = {}
    dispo = []
    Techno = ['nucl', 'char', 'TGCC', 'TFCO', 'Importation', 'Importation_autre', 'Hydr', 'Sola', 'Dech', 'Eoli']
    for cent in Techno:
        dispo.append(cent)
        res[cent]=0
    for cent in capa_prod_negatif[i]: # On attribue en priorité les centrales à prix négatifs
            res[cent]+=capa_prod_negatif[i][cent]
            prod += res[cent]
            cout_min = prix_min
            if prod >= conso:
                res[cent] -= prod - conso
                prod = conso
                break
    for cent in historique[i]: # On attribue en priorité la prod pour laquelle on a atteint une contrainte de flexibilité,comme ça elle ne bouge plus
        if capa_prod_negatif[i][cent]==0 and historique[i][cent]==1:
            res[cent]+=capa_prod_cm[i][cent]
            prod += res[cent]
            cout_min = dY[cent][i] 
            if prod >= conso:
                res[cent] -= prod - conso
                prod = conso
                break
            dispo.remove(cent)
        
    while np.round(prod) < np.round(conso):
        techno_min = qui_min_2(i, dY, dispo)
        cout_min2 = dY[techno_min][i]
        if cout_min2>cout_min: # On teste pour voir si le nouveau prix est inférieur au précédent ou non 
            cout_min=cout_min2  
        if conso < capa_prod_cm[i][techno_min]+prod: # On attribue le reste des technologies au coût marginal
            res[techno_min]+=conso-prod
            prod += res[techno_min]
            dispo.remove(techno_min)
            break
        else:
            prod += capa_prod_cm[i][techno_min]
            res[techno_min]+=capa_prod_cm[i][techno_min]
            dispo.remove(techno_min)
    return (res,cout_min)

def marche_horaire_avec_contrainte(conso, capa_prod_cm:list, capa_prod_neg:list, dY:dict, prix_min:float, historique:list):
    """Renvoie le prix SPOT horaire, la liste de la consommation horaire et le profil de production horaire, avec les contraintes sur les centrales thermiques et nucléaires. Cela correspond à la deuxième étape du modèle"""
    # La fonction a la même structure que marche_horaire_sans_contraintes
    l_cons = []
    prix_spot_conv = []
    prod = []
    for i in range(len(conso)):
        if type(conso) == list:
            l_cons.append(float(conso[i])*1000)
        else:
            l_cons.append(float(conso.loc[i, 'Load'])*1000)
    for i in range(len(l_cons)):
        calcul = quelle_cent_renouv_neg(l_cons[i], capa_prod_cm, capa_prod_neg, i, dY, prix_min, historique)
        prod_dic = {}
        for cent in calcul[0]:
            prod_dic[cent] = calcul[0][cent]
        prod.append(prod_dic)
        prix_spot_conv.append(calcul[1])
    return (prix_spot_conv, l_cons, prod)

def quelle_cent_contraintes_2(conso:pa.DataFrame, capa_prod:list, i:int, dY:dict, prod_cm:list, prod_neg:list, limites_flexibilité:dict, prix_min:int, historique:list): 
    """Renvoie pour une heure donnée et à partir de la production précédemment calculée, le nouveau profil de production tenant compte des contraintes sur la flexibilité, le nouveau prix SPOT, la variation de la production et la production historique"""
    # applicable uniquement pour une heure i>0
    conso_heure = float(conso.loc[i, 'Load'])*1000
    changement_de_production={}
    historique_h = historique[i] #si 0, alors pas de limite de flexibilité atteinte
    if i==0:
        prod_0, spot_0 = quelle_cent_renouv_neg(conso_heure, prod_cm, prod_neg, i, dY, prix_min, historique)
        return(prod_0, spot_0, changement_de_production, historique_h)
    h_avant = i-1
    conso_avant = float(conso.loc[h_avant, 'Load'])*1000
    prod_heure_avant, SPOT_avant = quelle_cent_renouv_neg(conso_avant, prod_cm, prod_neg, h_avant, dY, prix_min, historique)
    prod_heure_orinal, SPOT_jour = quelle_cent_renouv_neg(conso_heure, prod_cm, prod_neg, i, dY, prix_min, historique)
    prod_heure = prod_heure_orinal.copy()
    cout_min_secours = SPOT_jour
    dispo = []
    dispo_curtailment = ['Sola', 'Eoli', 'Dech', 'Hydr']
    cent_appelée = []
    Techno = ['nucl', 'char', 'TGCC', 'TFCO', 'Importation', 'Importation_autre'] #on ne prend que les énergies conventionnelles pilotables
    nouveau_mix = prod_heure
    for cent in Techno:
        dispo.append(cent)
    for cent in prod_heure :
         if (cent in Techno) and (prod_heure[cent] > 0):
            cent_appelée.append(cent)
    for cent in cent_appelée :
        capa_cent = capa_prod[i][cent]
        diff_prod = (prod_heure[cent] - prod_heure_avant[cent])/capa_cent
        

        ###### Calcul des contraintes de flexibilité et résolution de ces contraintes #######
        
        if abs(diff_prod)>limites_flexibilité[cent]: #si plus grand, on a un pb, il faut mettre à jour cela
            if diff_prod>0: # trop de production suplémentaire, il faut en retirer du marché
                capa_dispo = prod_heure_avant[cent] + limites_flexibilité[cent]*capa_cent #capacité accessible sur le marché
                C_residuelle = prod_heure[cent] - capa_dispo #capacité résiduelle à injecter dans le spot
                dispo.remove(cent) #la limite de flexibilité de la centrale est atteinte, on la retire des technos disponibles
                dispo_combler_la_prod = dispo.copy()
                while C_residuelle > 0 : #on cherche à combler le trou de capacité
                    techno_min = qui_min_2(i, dY, dispo_combler_la_prod)
                    reserve = capa_prod[i][techno_min]-prod_heure[techno_min]
                    if reserve>0: # on vérifie qu'il en reste
                        cout_min_secours = dY[techno_min][i] 
                        if 0 > (C_residuelle-reserve):                           
                            nouveau_mix[techno_min]=prod_heure[techno_min]+C_residuelle #on augmente la production
                            prod_heure[techno_min]=nouveau_mix[techno_min]
                            C_residuelle = 0 #besoin comblé
                            break
                        else:
                            C_residuelle -= reserve
                            nouveau_mix[techno_min]=prod_heure[techno_min]+reserve
                            prod_heure[techno_min]=prod_heure[techno_min]+C_residuelle
                            dispo_combler_la_prod.remove(techno_min)
                    else: 
                        dispo_combler_la_prod.remove(techno_min) #la centrale en question n'est pas apte à absorber cette demande de production
                nouveau_mix[cent]=prod_heure_avant[cent]+limites_flexibilité[cent]*capa_cent 
                cent_appelée.append(techno_min)

                       
            
            if diff_prod<0: #on demande de trop réduire par rapport à la capacité dispo, il faut évacuer l'élec
                q_a_evacuer = abs((prod_heure_avant[cent]-limites_flexibilité[cent]*capa_cent)-prod_heure[cent])
                
                dispo.remove(cent)
                dispo_reduire_la_prod = dispo.copy()
                dispo_curtailment = dispo_curtailment.copy()
                
                while q_a_evacuer > 0:
                    while len(dispo_reduire_la_prod)>0: # on préfere utiliser des énergies conventionnelles que de cuitail les enr
                        techno_max = qui_max(i, dY, dispo_reduire_la_prod) #on veur réduire la prod de la techno la + couteuse
                        if (techno_max == ''):
                            break                        
                        if prod_heure[techno_max]>0: # on ne peut réduire la prod que des centrales appelées
                            if 0 > (q_a_evacuer-prod_heure[techno_max]):                           
                                nouveau_mix[techno_max]=prod_heure[techno_max] - q_a_evacuer #on réduit la production
                                prod_heure[techno_max]= nouveau_mix[techno_max]
                                cout_min_secours = dY[techno_max][i]
                                q_a_evacuer = 0 #besoin comblé
                                break
                            else:
                                q_a_evacuer -= prod_heure[techno_max]
                                nouveau_mix[techno_max]= 0
                                prod_heure[techno_max] = 0
                                dispo_reduire_la_prod.remove(techno_max)
                        else:
                            dispo_reduire_la_prod.remove(techno_max)
                    
                    if q_a_evacuer ==0:
                        break

                    techno_max = qui_max(i, dY, dispo_curtailment)
                    
                    if prod_heure[techno_max]>0: # on ne peut réduire la prod que des centrales appelées
                        if 0 > (q_a_evacuer-prod_heure[techno_max]):                           
                            nouveau_mix[techno_max]=prod_heure[techno_max] - q_a_evacuer #on réduit la production
                            prod_heure[techno_max] = nouveau_mix[techno_max]
                            q_a_evacuer = 0 #besoin comblé
                            cout_min_secours = dY[techno_max][i]
                            break
                        else:
                            q_a_evacuer -= prod_heure[techno_max]
                            nouveau_mix[techno_max]= 0
                            prod_heure[techno_max] = 0
                            dispo_curtailment.remove(techno_max)
                    else: 
                        dispo_curtailment.remove(techno_max)
                        #dispo_reduire_la_prod.remove(techno_max)
                nouveau_mix[cent]=prod_heure_avant[cent]-limites_flexibilité[cent]*capa_cent
                historique_h[cent]=1 #il y a eu modification

        for cent in nouveau_mix:
            changement_de_production[cent] = nouveau_mix[cent]-prod_heure_orinal[cent]
        SPOT_jour = max(SPOT_jour, cout_min_secours) 
        
    return(nouveau_mix, SPOT_jour, changement_de_production, historique_h) #changement_de_production


def gain_hydro_min(spot_conso:list, dY:dict, capa_hydro_lac:float, vol_hydro_lac:int, val_hydro:float):
    "Renvoie le gain espéré sur une année pour les producteurs d'hydraulique de lac pour une valeur d'usage, un prix SPOT et un profil de production pré-établi"
    gain = 0
    sum = 0
    for l in range(len(spot_conso)):
        if spot_conso[l][0]<val_hydro or sum>vol_hydro_lac:
            break
        elif spot_conso[l][0]==val_hydro:
            reste = spot_conso[l][1] # On calcule ce qu'il reste à distribuer au prix spot
            for cent in spot_conso[l][2]:
                if dY[cent][l] < spot_conso[l][0]:
                    reste -= spot_conso[l][2][cent]
            gain += min(spot_conso[l][1],capa_hydro_lac,reste)*val_hydro
            sum += min(spot_conso[l][1],capa_hydro_lac,reste)
        else:
            reste = spot_conso[l][1] # On calcule ce qu'il reste à distribuer au prix de l'hydro de lac
            for cent in spot_conso[l][2]:
                if dY[cent][l] < val_hydro:
                    reste -= spot_conso[l][2][cent]
            gain += min(spot_conso[l][1],capa_hydro_lac,reste)*val_hydro # On considère comme hypothèse conservatrice que l'on vend toujours à la valeur d'usage
            sum += min(spot_conso[l][1],capa_hydro_lac,reste)
    return gain

                
def val_usage_hydro_lac_monotone(spot_horaire:list, conso_horaire:list, capa_hydro_lac:float, vol_hydro_lac:int, prod:list, dY:dict, i_init=0):
    """Renvoie la valeur d'usage optimale pour l'hydraulique de lac"""
    spot_conso = []
    for l in range(i_init, len(spot_horaire)):
        spot_conso.append([spot_horaire[l], conso_horaire[l], prod[l]])
    spot_conso.sort(key=lambda x: x[0])
    spot_conso.reverse() # On classe les prix SPOT par ordre décroissant en conservant le profil de prod associé
    l_mem = []
    max_gain = 0
    val_max = 0
    for l in range(len(spot_conso)): # On parcourt les prix SPOT en cherchant le gain maximal
        prixh = spot_conso[l][0] # La valeur d'usage est fixée au prix SPOT
        if not(prixh in l_mem):
            l_mem.append(prixh)
            gain = gain_hydro_min(spot_conso, dY, capa_hydro_lac, vol_hydro_lac, prixh)
            if gain > max_gain:
                max_gain = gain
                val_max = prixh
    return val_max

def quelle_cent_renouv_neg_avec_lac(conso:float, capa_prod_cm:list, capa_prod_negatif:list, i:int, dY:dict, capa_lac:float, prix_min:int, historique:list): #permet de choisir la centrale à mobiliser sur une heure donnée i
    """Renvoie la liste des centrales appelées à une heure donnée i, ainsi que le prix SPOT associé à ce profil de production, en prenant en compte les prix négatifs et de l'hydraulique de lac"""
    # Cette fonction a la même structure que quelle_cent_renouv_neg. Elle n'ajoute que l'hydraulique de lac
    prod = 0
    res = {}
    dispo = []
    Techno = ['nucl', 'char', 'TGCC', 'TFCO', 'Importation', 'Importation_autre', 'Hydr', 'Sola', 'Dech', 'Eoli', 'Lac']
    for cent in Techno:
        dispo.append(cent)
        res[cent]=0
    for cent in capa_prod_negatif[i]: #on attribue en priorité les centrales à prix négatifs
        res[cent]+=capa_prod_negatif[i][cent]
        prod += res[cent]
        cout_min = prix_min
        if prod >= conso:
            break

    for cent in historique[i]: #on attribue en priorité la prod pour laquelle on a atteint une contrainte de flexibilité,comme ça elle ne bouge plus
        if capa_prod_negatif[i][cent]==0 and historique[i][cent]==1:
            res[cent]+=capa_prod_cm[i][cent]
            prod += res[cent]
            cout_min = dY[cent][i] 
            if prod >= conso:
                res[cent] -= prod - conso
                prod = conso
                break
            dispo.remove(cent)
    while prod < conso:
        techno_min = qui_min_2(i, dY, dispo)
        cout_min = dY[techno_min][i]
        if techno_min == 'Lac': # Cas modifié par rapport à quelle_cent_renouv_neg. On ne peut pas le traiter comme les autres modes des production car il faut diminuer le stock
            if conso < capa_lac+prod:
                res['Lac'] += conso-prod
                prod += res['Lac']
                dispo.remove('Lac')
                break
            else:
                prod += capa_lac
                res['Lac'] += capa_lac
                dispo.remove('Lac')
        elif conso < capa_prod_cm[i][techno_min]+prod: # On attribue avec le reste des technologies au coût marginal
            res[techno_min]+=conso-prod
            prod += res[techno_min]
            dispo.remove(techno_min)
            break
        else:
            prod += capa_prod_cm[i][techno_min]
            res[techno_min]+=capa_prod_cm[i][techno_min]
            dispo.remove(techno_min)
    return (res,cout_min)

def marche_horaire_an_full(conso:pa.DataFrame, capa_prod:list, capa_instalée:list, dY:dict, prix_min:int, limites_flexibilité:dict, contraintes_arret:dict, minimum_fonctionnement:dict, consodf:pa.DataFrame, capa_hydro_lac:float, hydro_lac=False, val_usage_lac=0, vol_hydro_lac=0):
    """Fonction principale du modèle. Elle calcule les étapes 1 et 2, et éventuellement 3. Elle renvoie le prix SPOT horaire, la production pour chaqu type d'énergie séparément, une liste contenant la consommation et l'écrêtement."""
    # Pour calculer l'étape 3 il faut assigner à hydro_lac la valeur True.
    # Étape 1 : sans contraintes
    prix_init, rien_init, prod_init = marche_horaire_sans_contrainte(conso, capa_prod, dY)
    # Etape 2 : calcul des contraintes
    prod_au_cm, prod_neg = capa_cm_ou_capa_neg_totale(prix_init, dY, prod_init, capa_prod, capa_instalée, contraintes_arret, minimum_fonctionnement, conso)
    marche_contrainte_allumage = []
    SPOT_1 = []
    dispo_curtailment = ['Sola', 'Eoli', 'Dech', 'Hydr']
    curtailment_total = []
    historique = []
    # Recalcul avec les contraintes sur la flexibilité
    for i in range(len(conso)):
        historique.append({'nucl': 0, 'TGCC': 0})
        centrale_jour = quelle_cent_contraintes_2(conso, capa_prod, i, dY, prod_au_cm, prod_neg, limites_flexibilité, prix_min, historique)
        marche_contrainte_allumage.append(centrale_jour[0])
        SPOT_1.append(centrale_jour[1])
        historique[i] = centrale_jour[3]
        #on stocke les valeurs de prod après contraintes de démarrage
        #à présent, on va traiter les nouvelles contraintes de flexibilité qui sont apparues
    
    # Recalcul avec toutes les contriantes
    nouvelle_prod_cm, nouvelle_prod_neg = capa_cm_ou_capa_neg_totale(SPOT_1, dY, marche_contrainte_allumage, capa_prod, capa_instalée, contraintes_arret, minimum_fonctionnement, consodf)
    marche_h_contrainte = marche_horaire_avec_contrainte(conso, nouvelle_prod_cm, nouvelle_prod_neg, dY, prix_min, historique)
    SPOT = marche_h_contrainte[0]
    l_cons = marche_h_contrainte[1]
    prod = marche_h_contrainte[2]

    # Étape 3 : ajout de l'hydraulique de lac
    if hydro_lac: # Si on prend en compte l'hydraulique de lac
        util_lac = []
        vol_hydro_actu = vol_hydro_lac
        for i in range(len(conso)):
            if SPOT[i] >= val_usage_lac  and vol_hydro_actu>0:
                prod_i, Spot_i = quelle_cent_renouv_neg_avec_lac(l_cons[i], nouvelle_prod_cm, nouvelle_prod_neg, i, dY, capa_hydro_lac, prix_min, historique)
                prod[i] = prod_i
                SPOT[i] = Spot_i
                util_lac.append(prod[i]['Lac'])
                vol_hydro_actu -= prod[i]['Lac']
            else:
                util_lac.append(0)
    else:
        util_lac = []

    # Définition de toutes les valeurs renvoyées par la fonction

    for i in range(len(conso)):
        curtailment_heure = {}
        for cent in dispo_curtailment:
            curtailment_heure[cent] = prod_init[i][cent]-prod[i][cent]
        curtailment_total.append(curtailment_heure)


    util_nucl = []
    util_gaz = []
    util_charbon = []
    util_fioul = []
    util_importation = []
    util_importation_autre = []
    util_hydr = []
    util_sola = []
    util_dech = []
    util_eoli = []
    
    for i in range(len(l_cons)):
        util_nucl.append(prod[i]['nucl'])
        util_gaz.append(prod[i]['TGCC'])
        util_charbon.append(prod[i]['char'])
        util_fioul.append(prod[i]['TFCO'])
        util_importation.append(prod[i]['Importation'])
        util_importation_autre.append(prod[i]['Importation_autre'])
        util_hydr.append(prod[i]['Hydr'])
        util_sola.append(prod[i]['Sola'])
        util_dech.append(prod[i]['Dech'])
        util_eoli.append(prod[i]['Eoli'])
        
    return (SPOT, util_nucl, util_gaz, util_charbon, util_fioul, util_importation, util_hydr, util_sola, util_dech, util_eoli, l_cons, curtailment_total, util_lac, util_importation_autre)

def prix_moyen(T:int, prix_horaires:list):
    """Renvoie une liste contenant le prix moyenné sur une certaine période"""
    # T : nombre d'heures sur lesquelles on fait la moyenne
    # prix_horaires : prix spot sur une certaine durée
    prix_moy = []
    for i in range(int(len(prix_horaires)/T)):
        prix_moy.append(np.mean(prix_horaires[(i*T):((i+1)*T)]))
    return prix_moy

def conversion_prod(prod_init:pa.DataFrame):
    """Conversion des données de production en un DataFrame adapté à notre modèle"""
    prod_fin = pa.DataFrame()
    heure = -1
    heure_prec = prod_init.loc[0, "MTU (CET/CEST)"]
    prod_heure = {}
    for i in range(len(prod_init)):
        if prod_init.loc[i, "MTU (CET/CEST)"] != heure_prec:
            heure_prec = prod_init.loc[i, "MTU (CET/CEST)"]
            heure += 1
            prod_fin.loc[heure, "Heure"] = heure_prec
            prod_fin.loc[heure, "Hydro Run-of-river and poundage"] = float(prod_heure["Hydro Run-of-river and poundage"])
            prod_fin.loc[heure, "Solar"] = float(prod_heure["Solar"])
            prod_fin.loc[heure, "Waste"] = float(prod_heure["Waste"])
            prod_fin.loc[heure, "Wind Onshore"] = float(prod_heure["Wind Onshore"])
        if prod_init.loc[i, "Generation (MW)"] != 'n/e':
            prod_heure[prod_init.loc[i, "Production Type"]] = prod_init.loc[i, "Generation (MW)"]
        else:
            prod_heure[prod_init.loc[i, "Production Type"]] = 0
    return prod_fin


def marche_horaire_an_full_usage_lac_dyna(conso:pa.DataFrame, capa_prod:list, capa_instalée:list, dY:dict, prix_min:int, limites_flexibilité:dict, contraintes_arret:dict, minimum_fonctionnement:dict, capa_hydro_lac:float, hydro_lac=False, val_usage_lac_init=0, conso_prec=pa.DataFrame(), spot_prec = [], vol_hydro_lac = 0):
    """Même fonction que marche_horaire_an_full mais avec une valeur d'usage de l'hydraulique de lac qui est initialisée puis mise à jour régulièremen"""
    prix_init, rien_init, prod_init = marche_horaire_sans_contrainte(conso, capa_prod, dY)
    prod_au_cm, prod_neg = capa_cm_ou_capa_neg_totale(prix_init, dY, prod_init, capa_prod, capa_instalée, contraintes_arret, minimum_fonctionnement, conso)
    marche_contrainte_allumage = []
    SPOT_1 = []
    dispo_curtailment = ['Sola', 'Eoli', 'Dech', 'Hydr']
    curtailment_total = []
    historique = []
    for i in range(len(conso)):
        historique.append({'nucl': 0, 'TGCC': 0})
        centrale_jour = quelle_cent_contraintes_2(conso, capa_prod, i, dY, prod_au_cm, prod_neg, limites_flexibilité, prix_min, historique)
        marche_contrainte_allumage.append(centrale_jour[0])
        SPOT_1.append(centrale_jour[1])
        historique[i] = centrale_jour[3]
        #on stocke les valeurs de prod après contraintes de démarrage
        #à présent, on va traiter les nouvelles contraintes de flexibilité qui sont apparues

    nouvelle_prod_cm, nouvelle_prod_neg = capa_cm_ou_capa_neg_totale(SPOT_1, dY, marche_contrainte_allumage, capa_prod, capa_instalée, contraintes_arret, minimum_fonctionnement, conso)
    marche_h_contrainte = marche_horaire_avec_contrainte(conso, nouvelle_prod_cm, nouvelle_prod_neg, dY, prix_min, historique)
    SPOT = marche_h_contrainte[0]
    l_cons = marche_h_contrainte[1]
    prod = marche_h_contrainte[2]

    if hydro_lac: # Si on prend en compte l'hydraulique de lac
        l_valeurs_hydro_lac = [val_usage_lac_init]
        util_lac = []
        vol_hydro_actu = vol_hydro_lac
        for i in range(len(conso)):
            if (int(i/100) == i/100) and i>0:
                # On ajuste la valeur d'usage en calculant ce qu'on devrait gagner sur l'année avec le stock qu'il nous reste et ce qu'on prévoit (avec les données de l'années précédente)
                val_new = val_usage_hydro_lac_monotone(spot_prec, conso_prec, capa_hydro_lac, vol_hydro_actu, prod, dY, i_init=i)
                l_valeurs_hydro_lac.append(val_new)
                Cm_lac_new = []
                for j in range(len(dY['nucl'])):
                    Cm_lac_new.append(val_new)
                dY['Lac'] = Cm_lac_new
            if (SPOT[i] >= l_valeurs_hydro_lac[-1]) and vol_hydro_actu>0:
                prod_i, Spot_i = quelle_cent_renouv_neg_avec_lac(l_cons[i], nouvelle_prod_cm, nouvelle_prod_neg, i, dY, capa_hydro_lac, prix_min, historique)
                prod[i] = prod_i
                SPOT[i] = Spot_i
                util_lac.append(prod[i]['Lac'])
                vol_hydro_actu -= prod[i]['Lac']
            else:
                util_lac.append(0)
    else:
        util_lac = []
    for i in range(len(conso)):
        curtailment_heure = {}
        for cent in dispo_curtailment:
            curtailment_heure[cent] = prod_init[i][cent]-prod[i][cent]
        curtailment_total.append(curtailment_heure)


    util_nucl = []
    util_gaz = []
    util_charbon = []
    util_fioul = []
    util_importation = []
    util_hydr = []
    util_sola = []
    util_dech = []
    util_eoli = []
    
    for i in range(len(l_cons)):
        util_nucl.append(prod[i]['nucl'])
        util_gaz.append(prod[i]['TGCC'])
        util_charbon.append(prod[i]['char'])
        util_fioul.append(prod[i]['TFCO'])
        util_importation.append(prod[i]['Importation'])
        util_hydr.append(prod[i]['Hydr'])
        util_sola.append(prod[i]['Sola'])
        util_dech.append(prod[i]['Dech'])
        util_eoli.append(prod[i]['Eoli'])
        
    return (SPOT, util_nucl, util_gaz, util_charbon, util_fioul, util_importation, util_hydr, util_sola, util_dech, util_eoli, l_cons, curtailment_total, util_lac, l_valeurs_hydro_lac)


def fig_plotly_save(fig, name_file:str, largeur=1200):
    """Sauvegarde la figure fig aux formats html et svg dans un dossier figures qui doit déjà exister"""
    fig.write_html("figures/"+name_file+".html")
    fig.write_image("figures/"+name_file+".svg", width=largeur)

def lissage(max:float, reserve:float, YM_nuc:list, capa_instalée:list, minimum_fonctionnement:dict):
    """Prise en compte de la contrainte sur le nombre de cycles annuels du nucléaire, la fonction renvoie le seuil à partir duquel un changement de palier a lieu, la nouvelle production de nucléaire et les différents paliers"""
    seuil = 0
    diff = -1
    while diff < 0:
        seuil += 0.01
        S = 0
        S2 = max * 0.5 * 61.4e3  # capacité moyenne du parc

        nouveau_nucl = [YM_nuc[0]]
        pallier = [YM_nuc[0]]
        limite_basse = []
        
        for i in range(1, len(YM_nuc)):
            reserve_secondaire = reserve * capa_instalée[i]['nucl']
            limite_basse.append(minimum_fonctionnement['nucl'] * capa_instalée[i]['nucl'])
            diff_prod = abs(pallier[i-1] - YM_nuc[i])
            
            if diff_prod <= seuil * pallier[i-1]:
                pallier.append(pallier[i-1])
                nouveau_nucl.append(pallier[i-1])
            else:
                pallier.append(YM_nuc[i])
                nouveau_nucl.append(YM_nuc[i])

            if diff_prod <= reserve_secondaire:
                nouveau_nucl[i] = YM_nuc[i]

        for i in range(1, len(nouveau_nucl)):
            var_prod = abs(nouveau_nucl[i] - nouveau_nucl[i-1])
            if var_prod > reserve * capa_instalée[i]['nucl']:
                S += var_prod

        diff = S2 - S

    return seuil, nouveau_nucl, pallier

def analyse_detection(X:list, SPOT_réel:list, SPOT_model:list, seuil_negatif=5, label="Modèle"):
    """Analyse de la détection des jours auxquels on a des prix négatifs dans le modèle par rapport à la réalité observée. Le résultat est imprimé"""
    # Regrouper les valeurs réelles et modélisées par jour
    jours = defaultdict(lambda: {'réel': [], 'modèle': []})
    for i in range(len(X)):
        jour = str(X[i].astype('datetime64[D]'))
        jours[jour]['réel'].append(SPOT_réel[i])
        jours[jour]['modèle'].append(SPOT_model[i])

    # Initialisation des compteurs
    jours_total = 0
    jours_correctement_detectes = 0
    jours_faux_positifs = 0
    jours_faux_negatifs = 0

    liste_jours = []
    statuts_jours = []

    for jour, valeurs in jours.items():
        negatif_reel = any(p <= seuil_negatif for p in valeurs['réel'])
        negatif_modele = any(p == 0 for p in valeurs['modèle'])

        if negatif_reel:
            jours_total += 1
            if negatif_modele:
                jours_correctement_detectes += 1
                statuts_jours.append("Correctement détecté")
            else:
                jours_faux_negatifs += 1
                statuts_jours.append("Non détecté (faux négatif)")
        else:
            if negatif_modele:
                jours_faux_positifs += 1
                statuts_jours.append("Faux positif")
            else:
                statuts_jours.append("Aucun prix négatif")

        liste_jours.append(jour)

    # Résumé
    print(f"--- Résultats pour {label} ---")
    print(f"Nombre total de jours avec au moins une heure à prix ≤ {seuil_negatif} (réel) : {jours_total}")
    print(f"Nombre de jours correctement détectés : {jours_correctement_detectes}")
    print(f"Nombre de faux négatifs : {jours_faux_negatifs}")
    print(f"Nombre de faux positifs : {jours_faux_positifs}")

    if jours_total > 0:
        taux_detection = 100 * jours_correctement_detectes / jours_total
        taux_non_detection = 100 * jours_faux_negatifs / jours_total
        taux_faux_positifs = 100 * jours_faux_positifs / jours_total
        print(f"Taux de détection correcte : {taux_detection:.2f} %")
        print(f"Taux de non détection : {taux_non_detection:.2f} %")
        print(f"Taux de détection en trop (faux positifs) : {taux_faux_positifs:.2f} %")

    return liste_jours, statuts_jours