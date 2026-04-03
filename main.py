"""
Jeu de Nim - Apprentissage par urnes

Règles : retirer 1 ou 2 bâtonnets, celui qui prend le DERNIER perd.

"""

import pygame
import random
import sys
from collections import deque

# ══════════════════════════════════════════════════════════════════════════════
#  PARAMÈTRES
# ══════════════════════════════════════════════════════════════════════════════

NB_BATONS_DEPART    = 10    
NB_BOULES_INITIALES = 3     
PARTIES_PAR_IMAGE   = 1     # parties simulées par frame (1 = lent, 10+ = rapide)
IMAGES_PAR_SECONDE  = 60

LARGEUR_FENETRE, HAUTEUR_FENETRE = 1100, 700

# ══════════════════════════════════════════════════════════════════════════════
#  PALETTE DE COULEURS
# ══════════════════════════════════════════════════════════════════════════════

COULEUR_FOND          = (250, 250, 248)
COULEUR_PANNEAU       = (242, 240, 235)
COULEUR_BORDURE       = (187, 186, 176)
COULEUR_TEXTE         = (44,  44,  42)
COULEUR_TEXTE_DISCRET = (136, 135, 128)

COULEUR_JAUNE         = (239, 159,  39)   # boule "retirer 1"
COULEUR_JAUNE_SOMBRE  = (186, 117,  23)
COULEUR_ROUGE         = (226,  75,  74)   # boule "retirer 2"
COULEUR_ROUGE_SOMBRE  = (163,  45,  45)

COULEUR_VERT          = ( 59, 109,  17)   # victoire / optimal
COULEUR_ROSE          = (153,  53,  86)   # défaite / sous-optimal
COULEUR_BLEU          = ( 24,  95, 165)   # joueur IA
COULEUR_BLEU_CLAIR    = (230, 241, 251)   # surbrillance urne active

COULEUR_BATON         = (200, 164, 110)
COULEUR_BATON_SOMBRE  = (139,  98,  32)
COULEUR_BATON_CHAPEAU = (120,  82,  20)

COULEUR_CARTE         = (255, 255, 253)

# ══════════════════════════════════════════════════════════════════════════════
#  LOGIQUE DU JEU ET APPRENTISSAGE
# ══════════════════════════════════════════════════════════════════════════════

def initialiser_urnes():
    """
    Crée un dictionnaire d'urnes, une par état possible (nb de bâtonnets restants).
    Chaque urne contient NB_BOULES_INITIALES boules jaunes (valeur 1 = retirer 1)
    et NB_BOULES_INITIALES boules rouges (valeur 2 = retirer 2).
    L'état 1 ne contient que des jaunes (on ne peut retirer qu'1 bâtonnet).
    """
    urnes = {}
    for nb_batons in range(1, NB_BATONS_DEPART + 1):
        boules_jaunes = [1] * NB_BOULES_INITIALES
        boules_rouges = [2] * NB_BOULES_INITIALES if nb_batons > 1 else []
        urnes[nb_batons] = boules_jaunes + boules_rouges
    return urnes


def jouer_une_partie(urnes):
    """
    Joue une partie complète entre l'IA (urnes) et un adversaire aléatoire.

    Pour chaque tour de l'IA :
      - on tire une boule au hasard dans l'urne correspondante
      - la boule est RETIRÉE de l'urne pendant la partie

    En fin de partie :
      - si l'IA gagne -> on remet chaque boule tirée + une boule identique (renforcement)
      - si l'IA perd  -> les boules restent retirées (punition)

    Retourne (ia_a_gagne: bool, journal_des_tours: list)
    Le journal contient des tuples (joueur, nb_batons_avant_coup, nb_batons_retires).
    """
    nb_batons_restants  = NB_BATONS_DEPART
    historique_coups_ia = []   # (etat, boule_tiree) pour le renforcement
    journal_des_tours   = []   # pour l'affichage

    tour_de_lia = random.choice([True, False])

    while nb_batons_restants > 0:
        if tour_de_lia:
            urne_courante = urnes[nb_batons_restants]
            boule_tiree   = random.choice(urne_courante) if urne_courante else 1
            boule_tiree   = min(boule_tiree, nb_batons_restants)
            if boule_tiree in urne_courante:
                urne_courante.remove(boule_tiree)   # retire physiquement la boule
            historique_coups_ia.append((nb_batons_restants, boule_tiree))
            journal_des_tours.append(("IA", nb_batons_restants, boule_tiree))
        else:
            coups_possibles = [1, 2] if nb_batons_restants >= 2 else [1]
            boule_tiree     = random.choice(coups_possibles)
            journal_des_tours.append(("Adv", nb_batons_restants, boule_tiree))

        nb_batons_restants -= boule_tiree
        tour_de_lia         = not tour_de_lia

    # Après la boucle, tour_de_lia a été inversé une dernière fois.
    # Si tour_de_lia vaut False -> c'est l'IA qui vient de jouer -> a pris le dernier -> a perdu.
    ia_a_gagne = not tour_de_lia

    if ia_a_gagne:
        for (etat, boule) in historique_coups_ia:
            urnes[etat].append(boule)   # remet la boule
            urnes[etat].append(boule)   # en ajoute une identique (renforcement)

    return ia_a_gagne, journal_des_tours


# ══════════════════════════════════════════════════════════════════════════════
#  CLASSE PARTICULE (boules animées au-dessus de l'urne active)
# ══════════════════════════════════════════════════════════════════════════════

class Particule:
    """Petite boule colorée qui tombe vers l'urne après un tirage."""

    def __init__(self, pos_depart_x, pos_depart_y, couleur, pos_arrivee_x, pos_arrivee_y):
        self.pos_x        = float(pos_depart_x)
        self.pos_y        = float(pos_depart_y)
        self.cible_x      = float(pos_arrivee_x)
        self.cible_y      = float(pos_arrivee_y)
        self.couleur      = couleur
        self.transparence = 255
        self.rayon        = 7
        self.age          = 0
        self.duree_vie    = 40

    def mettre_a_jour(self):
        """Déplace la particule vers sa cible et la fait disparaître en fin de vie."""
        self.pos_x += (self.cible_x - self.pos_x) * 0.18
        self.pos_y += (self.cible_y - self.pos_y) * 0.18
        self.age   += 1
        seuil_disparition = self.duree_vie * 0.7
        if self.age > seuil_disparition:
            ratio = (self.age - seuil_disparition) / (self.duree_vie * 0.3)
            self.transparence = max(0, int(255 * (1 - ratio)))

    def dessiner(self, surface):
        taille = self.rayon * 2 + 2
        calque = pygame.Surface((taille, taille), pygame.SRCALPHA)
        pygame.draw.circle(
            calque,
            (*self.couleur, self.transparence),
            (self.rayon + 1, self.rayon + 1),
            self.rayon
        )
        surface.blit(calque, (int(self.pos_x) - self.rayon - 1,
                               int(self.pos_y) - self.rayon - 1))

    def est_morte(self):
        return self.age >= self.duree_vie


# ══════════════════════════════════════════════════════════════════════════════
#  FONCTIONS DE DESSIN UTILITAIRES
# ══════════════════════════════════════════════════════════════════════════════

def dessiner_rectangle_arrondi(surface, couleur, rect, rayon=10):
    """Dessine un rectangle aux coins arrondis."""
    x, y, largeur, hauteur = rect
    pygame.draw.rect(surface, couleur, (x + rayon, y, largeur - 2 * rayon, hauteur))
    pygame.draw.rect(surface, couleur, (x, y + rayon, largeur, hauteur - 2 * rayon))
    for cx, cy in [
        (x + rayon,               y + rayon),
        (x + largeur - rayon - 1, y + rayon),
        (x + rayon,               y + hauteur - rayon - 1),
        (x + largeur - rayon - 1, y + hauteur - rayon - 1),
    ]:
        pygame.draw.circle(surface, couleur, (cx, cy), rayon)


def afficher_texte(surface, texte, x, y, police, couleur=None, ancre="topleft"):
    """Affiche du texte avec un point d'ancrage configurable."""
    if couleur is None:
        couleur = COULEUR_TEXTE
    rendu = police.render(texte, True, couleur)
    rect  = rendu.get_rect()
    setattr(rect, ancre, (x, y))
    surface.blit(rendu, rect)
    return rect


# ══════════════════════════════════════════════════════════════════════════════
#  COMPOSANTS VISUELS
# ══════════════════════════════════════════════════════════════════════════════

def dessiner_batons(surface, nb_restants, nb_total, zone, police_petite):
    """Dessine le tas de bâtonnets (bâtonnets retirés apparaissent grisés)."""
    x, y, largeur, hauteur = zone
    dessiner_rectangle_arrondi(surface, COULEUR_PANNEAU, zone, rayon=8)

    largeur_baton = min(22, (largeur - 20) // nb_total - 4)
    ecart_batons  = max(3, (largeur - 20 - largeur_baton * nb_total) // (nb_total + 1))
    hauteur_baton = min(hauteur - 40, 80)
    y_baton       = y + (hauteur - hauteur_baton) // 2 + 4
    x_premier_baton = x + (largeur - (largeur_baton * nb_total
                                       + ecart_batons * (nb_total - 1))) // 2

    for indice in range(nb_total):
        x_baton = x_premier_baton + indice * (largeur_baton + ecart_batons)
        if indice < nb_restants:
            pygame.draw.rect(surface, COULEUR_BATON,
                             (x_baton, y_baton, largeur_baton, hauteur_baton - 6),
                             border_radius=3)
            pygame.draw.rect(surface, COULEUR_BATON_CHAPEAU,
                             (x_baton, y_baton, largeur_baton, 8),
                             border_radius=3)
            pygame.draw.rect(surface, COULEUR_BATON_SOMBRE,
                             (x_baton, y_baton, largeur_baton, hauteur_baton - 6),
                             1, border_radius=3)
        else:
            pygame.draw.rect(surface, (220, 215, 205),
                             (x_baton, y_baton, largeur_baton, hauteur_baton - 6),
                             border_radius=3)
            pygame.draw.rect(surface, COULEUR_BORDURE,
                             (x_baton, y_baton, largeur_baton, hauteur_baton - 6),
                             1, border_radius=3)

    libelle = f"{nb_restants} bâtonnet{'s' if nb_restants != 1 else ''}"
    afficher_texte(surface, libelle, x + largeur // 2, y + hauteur - 18,
                   police_petite, COULEUR_TEXTE_DISCRET, ancre="midtop")


def dessiner_urnes(surface, urnes, polices, etat_surligne=None, liste_particules=None):
    """
    Dessine toutes les urnes dans la zone inférieure de la fenêtre.
    Chaque urne montre la proportion jaune/rouge sous forme de barre verticale
    et un indicateur de convergence vers la stratégie optimale (✓ ou ✗).
    """
    police_petite, police_moyenne, police_grande, police_titre = polices

    ZONE_X        = 20
    ZONE_Y        = 390
    ZONE_LARGEUR  = LARGEUR_FENETRE - 40
    ZONE_HAUTEUR  = 250

    dessiner_rectangle_arrondi(surface, COULEUR_PANNEAU,
                                (ZONE_X, ZONE_Y, ZONE_LARGEUR, ZONE_HAUTEUR), rayon=12)
    afficher_texte(surface, "Contenu des urnes",
                   ZONE_X + 16, ZONE_Y + 10, police_moyenne, COULEUR_TEXTE)

    largeur_urne  = (ZONE_LARGEUR - 40) // NB_BATONS_DEPART - 4
    hauteur_urne  = 160
    y_urne        = ZONE_Y + 36
    espacement_urnes = (ZONE_LARGEUR - 40 - largeur_urne * NB_BATONS_DEPART) // (NB_BATONS_DEPART - 1)

    for indice_urne, etat in enumerate(range(1, NB_BATONS_DEPART + 1)):
        contenu_urne      = urnes[etat]
        nb_boules_jaunes  = contenu_urne.count(1)
        nb_boules_rouges  = contenu_urne.count(2)
        nb_boules_total   = len(contenu_urne)
        proportion_jaune  = nb_boules_jaunes / nb_boules_total if nb_boules_total > 0 else 0.5

        x_urne    = ZONE_X + 20 + indice_urne * (largeur_urne + espacement_urnes)
        centre_x_urne = x_urne + largeur_urne // 2

        # Surbrillance de l'urne active
        if etat == etat_surligne:
            dessiner_rectangle_arrondi(
                surface, COULEUR_BLEU_CLAIR,
                (x_urne - 3, y_urne - 3, largeur_urne + 6, hauteur_urne + 6), rayon=8
            )

        # Fond blanc de l'urne
        dessiner_rectangle_arrondi(surface, COULEUR_CARTE,
                                    (x_urne, y_urne, largeur_urne, hauteur_urne), rayon=6)
        pygame.draw.rect(surface, COULEUR_BORDURE,
                         (x_urne, y_urne, largeur_urne, hauteur_urne), 1, border_radius=6)

        # Barre de proportion (jaune en haut, rouge en bas)
        hauteur_barre = hauteur_urne - 40
        y_barre       = y_urne + 8
        x_barre       = x_urne + 4
        largeur_barre = largeur_urne - 8

        if proportion_jaune > 0:
            hauteur_portion_jaune = max(2, int(hauteur_barre * proportion_jaune))
            dessiner_rectangle_arrondi(
                surface, COULEUR_JAUNE,
                (x_barre, y_barre, largeur_barre, hauteur_portion_jaune), rayon=4
            )

        if proportion_jaune < 1:
            hauteur_portion_rouge = max(2, int(hauteur_barre * (1 - proportion_jaune)))
            y_portion_rouge       = y_barre + int(hauteur_barre * proportion_jaune)
            dessiner_rectangle_arrondi(
                surface, COULEUR_ROUGE,
                (x_barre, y_portion_rouge, largeur_barre, hauteur_portion_rouge), rayon=4
            )

        # Ligne de col de l'urne
        pygame.draw.line(
            surface, COULEUR_BORDURE,
            (x_urne + 4, y_urne + hauteur_barre + 10),
            (x_urne + largeur_urne - 4, y_urne + hauteur_barre + 10), 1
        )

        # Compteurs de boules jaunes et rouges
        if nb_boules_jaunes > 0:
            afficher_texte(
                surface, str(nb_boules_jaunes),
                centre_x_urne - largeur_urne // 4,
                y_urne + hauteur_barre // 2,
                police_petite, (100, 70, 10), ancre="center"
            )
        if nb_boules_rouges > 0:
            afficher_texte(
                surface, str(nb_boules_rouges),
                centre_x_urne + largeur_urne // 4,
                y_urne + hauteur_barre // 2 + int(hauteur_barre * proportion_jaune) // 2,
                police_petite, (100, 30, 30), ancre="center"
            )

        # Numéro d'état sous l'urne
        afficher_texte(surface, str(etat),
                       centre_x_urne, y_urne + hauteur_urne - 18,
                       police_petite, COULEUR_TEXTE_DISCRET, ancre="center")

        # Indicateur de convergence vers la stratégie optimale
        # Stratégie optimale : laisser un multiple de 3 à l'adversaire
        if etat % 3 == 1:
            coup_optimal = 1   # retirer 1 laisse un multiple de 3
        elif etat % 3 == 2:
            coup_optimal = 2   # retirer 2 laisse un multiple de 3
        else:
            coup_optimal = None  # position perdue, aucun coup n'est optimal

        if coup_optimal is not None:
            coup_prefere_ia = 1 if nb_boules_jaunes >= nb_boules_rouges else 2
            ia_a_trouve_loptimal = coup_prefere_ia == coup_optimal
            symbole_convergence  = "✓" if ia_a_trouve_loptimal else "X"
            couleur_convergence  = COULEUR_VERT if ia_a_trouve_loptimal else COULEUR_ROSE
        else:
            symbole_convergence = "·"
            couleur_convergence = COULEUR_TEXTE_DISCRET

        afficher_texte(surface, symbole_convergence,
                       centre_x_urne, y_urne + hauteur_urne - 4,
                       police_petite, couleur_convergence, ancre="midbottom")

        # Dessin des particules appartenant à cette urne
        if liste_particules is not None:
            for particule in liste_particules:
                if abs(particule.cible_x - centre_x_urne) < largeur_urne // 2:
                    particule.dessiner(surface)

    # Légende
    x_legende = ZONE_X + 16
    y_legende  = ZONE_Y + ZONE_HAUTEUR - 22
    pygame.draw.circle(surface, COULEUR_JAUNE,  (x_legende + 6,   y_legende + 7), 6)
    afficher_texte(surface, "Jaune = retirer 1",
                   x_legende + 16,  y_legende, police_petite, COULEUR_TEXTE_DISCRET)
    pygame.draw.circle(surface, COULEUR_ROUGE,  (x_legende + 130, y_legende + 7), 6)
    afficher_texte(surface, "Rouge = retirer 2",
                   x_legende + 140, y_legende, police_petite, COULEUR_TEXTE_DISCRET)
    afficher_texte(surface, "✓ = coup optimal appris",
                   x_legende + 280, y_legende, police_petite, COULEUR_VERT)


def dessiner_courbe_apprentissage(surface, historique_victoires, zone, polices):
    """Dessine la courbe du taux de victoire au fil des parties."""
    police_petite, police_moyenne, police_grande, police_titre = polices
    x, y, largeur, hauteur = zone
    dessiner_rectangle_arrondi(surface, COULEUR_PANNEAU, zone, rayon=8)
    afficher_texte(surface, "Taux de victoire", x + 12, y + 10, police_moyenne, COULEUR_TEXTE)

    if len(historique_victoires) < 2:
        return

    largeur_graphe = largeur - 40
    hauteur_graphe = hauteur - 50
    x_origine      = x + 20
    y_origine      = y + hauteur - 28

    # Ligne de référence à 50%
    pygame.draw.line(
        surface, COULEUR_BORDURE,
        (x_origine, y_origine - hauteur_graphe // 2),
        (x_origine + largeur_graphe, y_origine - hauteur_graphe // 2), 1
    )
    afficher_texte(surface, "50%", x_origine - 2, y_origine - hauteur_graphe // 2,
                   police_petite, COULEUR_TEXTE_DISCRET, ancre="midright")
    afficher_texte(surface, "100%", x_origine - 2, y_origine - hauteur_graphe,
                   police_petite, COULEUR_TEXTE_DISCRET, ancre="midright")
    afficher_texte(surface, "0%", x_origine - 2, y_origine,
                   police_petite, COULEUR_TEXTE_DISCRET, ancre="midright")

    # Axes
    pygame.draw.line(surface, COULEUR_BORDURE,
                     (x_origine, y_origine - hauteur_graphe), (x_origine, y_origine + 1), 1)
    pygame.draw.line(surface, COULEUR_BORDURE,
                     (x_origine, y_origine + 1), (x_origine + largeur_graphe, y_origine + 1), 1)

    nb_points   = len(historique_victoires)
    points_courbe = []
    for indice_point, (total_parties, nb_victoires) in enumerate(historique_victoires):
        px = x_origine + int(indice_point / max(nb_points - 1, 1) * largeur_graphe)
        py = y_origine  - int((nb_victoires / total_parties) * hauteur_graphe)
        points_courbe.append((px, py))

    if len(points_courbe) > 1:
        # Aire sous la courbe (semi-transparente)
        polygone_aire = ([(x_origine, y_origine)]
                         + points_courbe
                         + [(points_courbe[-1][0], y_origine)])
        calque_aire   = pygame.Surface((largeur, hauteur), pygame.SRCALPHA)
        polygone_local = [(px - x, py - y) for px, py in polygone_aire]
        pygame.draw.polygon(calque_aire, (*COULEUR_VERT, 30), polygone_local)
        surface.blit(calque_aire, (x, y))
        pygame.draw.lines(surface, COULEUR_VERT, False, points_courbe, 2)

    if points_courbe:
        taux_final = historique_victoires[-1][1] / historique_victoires[-1][0] * 100
        afficher_texte(surface, f"{taux_final:.0f}%",
                       points_courbe[-1][0] + 4, points_courbe[-1][1] - 4,
                       police_petite, COULEUR_VERT)


def dessiner_journal_recent(surface, journal_recent, zone, polices):
    """Affiche le journal des dernières parties (résultat victoire/défaite)."""
    police_petite, police_moyenne, police_grande, police_titre = polices
    x, y, largeur, hauteur = zone
    dessiner_rectangle_arrondi(surface, COULEUR_PANNEAU, zone, rayon=8)
    afficher_texte(surface, "Dernières parties", x + 12, y + 10, police_moyenne, COULEUR_TEXTE)

    for indice_ligne, (texte_ligne, couleur_ligne) in enumerate(journal_recent):
        y_ligne = y + 36 + indice_ligne * 20
        if y_ligne + 20 > y + hauteur:
            break
        afficher_texte(surface, texte_ligne, x + 12, y_ligne, police_petite, couleur_ligne)


def dessiner_statistiques_globales(surface, nb_parties, nb_victoires, zone, polices):
    """Affiche les 4 compteurs principaux : parties, victoires, défaites, taux."""
    police_petite, police_moyenne, police_grande, police_titre = polices
    x, y, largeur, hauteur = zone
    dessiner_rectangle_arrondi(surface, COULEUR_PANNEAU, zone, rayon=8)

    nb_defaites   = nb_parties - nb_victoires
    taux_victoire = nb_victoires / max(nb_parties, 1) * 100
    couleur_taux  = COULEUR_VERT if taux_victoire > 50 else COULEUR_ROSE

    donnees_statistiques = [
        (str(nb_parties),          "parties",   COULEUR_BLEU),
        (str(nb_victoires),        "victoires", COULEUR_VERT),
        (str(nb_defaites),         "défaites",  COULEUR_ROSE),
        (f"{taux_victoire:.1f}%",  "taux",      couleur_taux),
    ]
    largeur_colonne = largeur // 4
    for indice, (valeur, libelle, couleur) in enumerate(donnees_statistiques):
        centre_colonne = x + largeur_colonne * indice + largeur_colonne // 2
        afficher_texte(surface, valeur,
                       centre_colonne, y + 14, police_grande, couleur, ancre="midtop")
        afficher_texte(surface, libelle,
                       centre_colonne, y + hauteur - 18,
                       police_petite, COULEUR_TEXTE_DISCRET, ancre="midbottom")


def dessiner_detail_derniere_partie(surface, journal_derniere_partie, zone, polices):
    """Affiche le détail tour par tour de la dernière partie jouée."""
    police_petite, police_moyenne, police_grande, police_titre = polices
    x, y, largeur, hauteur = zone
    dessiner_rectangle_arrondi(surface, COULEUR_PANNEAU, zone, rayon=8)
    afficher_texte(surface, "Dernière partie jouée",
                   x + 12, y + 10, police_moyenne, COULEUR_TEXTE)

    for indice_tour, (joueur, batons_avant, nb_retires) in enumerate(journal_derniere_partie[-9:]):
        couleur_joueur = COULEUR_BLEU if joueur == "IA" else COULEUR_TEXTE_DISCRET
        texte_tour = (f"[{joueur}] {batons_avant} bât."
                      f"  retire {nb_retires}"
                      f"  reste {batons_avant - nb_retires}")
        afficher_texte(surface, texte_tour,
                       x + 12, y + 34 + indice_tour * 19, police_petite, couleur_joueur)


# ══════════════════════════════════════════════════════════════════════════════
#  BOUCLE PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════

def lancer_simulation():
    pygame.init()
    fenetre = pygame.display.set_mode((LARGEUR_FENETRE, HAUTEUR_FENETRE))
    pygame.display.set_caption("Jeu de Nim — Apprentissage par urnes (MENACE)")
    horloge = pygame.time.Clock()

    police_petite  = pygame.font.SysFont("segoeui,helveticaneue,dejavusans", 13)
    police_moyenne = pygame.font.SysFont("segoeui,helveticaneue,dejavusans", 15, bold=True)
    police_grande  = pygame.font.SysFont("segoeui,helveticaneue,dejavusans", 22, bold=True)
    police_titre   = pygame.font.SysFont("segoeui,helveticaneue,dejavusans", 28, bold=True)
    polices        = (police_petite, police_moyenne, police_grande, police_titre)

    def reinitialiser_tout():
        return (
            initialiser_urnes(),  # urnes
            0,                    # nb_parties
            0,                    # nb_victoires
            [],                   # historique_victoires [(total, nb_victoires)]
            deque(maxlen=12),     # journal_recent
            [],                   # liste_particules
            [],                   # journal_derniere_partie
            None,                 # etat_urne_active
        )

    (urnes,
     nb_parties,
     nb_victoires,
     historique_victoires,
     journal_recent,
     liste_particules,
     journal_derniere_partie,
     etat_urne_active) = reinitialiser_tout()

    en_pause           = False
    vitesse_simulation = PARTIES_PAR_IMAGE

    while True:
        # ── Gestion des événements ────────────────────────────────────────────
        for evenement in pygame.event.get():
            if evenement.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if evenement.type == pygame.KEYDOWN:
                if evenement.key == pygame.K_SPACE:
                    en_pause = not en_pause
                if evenement.key == pygame.K_UP:
                    vitesse_simulation = min(vitesse_simulation * 2, 512)
                if evenement.key == pygame.K_DOWN:
                    vitesse_simulation = max(1, vitesse_simulation // 2)
                if evenement.key == pygame.K_r:
                    (urnes,
                     nb_parties,
                     nb_victoires,
                     historique_victoires,
                     journal_recent,
                     liste_particules,
                     journal_derniere_partie,
                     etat_urne_active) = reinitialiser_tout()

        # ── Simulation des parties ────────────────────────────────────────────
        if not en_pause:
            for _ in range(vitesse_simulation):
                ia_a_gagne, journal_partie = jouer_une_partie(urnes)
                nb_parties += 1
                if ia_a_gagne:
                    nb_victoires += 1

                resultat_texte   = "✓ Victoire" if ia_a_gagne else "✗ Défaite"
                couleur_resultat = COULEUR_VERT  if ia_a_gagne else COULEUR_ROSE
                journal_recent.appendleft(
                    (f"#{nb_parties:<5} {resultat_texte}", couleur_resultat)
                )

                if nb_parties % 5 == 0:
                    historique_victoires.append((nb_parties, nb_victoires))
                if len(historique_victoires) > 200:
                    historique_victoires = historique_victoires[-200:]

                journal_derniere_partie = journal_partie

                # Particules animées (seulement en mode lent pour la lisibilité)
                if vitesse_simulation <= 4:
                    premier_tour_ia = next(
                        (tour for tour in journal_partie if tour[0] == "IA"), None
                    )
                    if premier_tour_ia:
                        etat_joue      = premier_tour_ia[1]
                        boule_jouee    = premier_tour_ia[2]
                        etat_urne_active = etat_joue

                        largeur_urne   = (LARGEUR_FENETRE - 80) // NB_BATONS_DEPART - 4
                        espacement_urnes = max(
                            3,
                            (LARGEUR_FENETRE - 80 - largeur_urne * NB_BATONS_DEPART)
                            // (NB_BATONS_DEPART - 1)
                        )
                        centre_x_urne_active = (
                            20 + 20
                            + (etat_joue - 1) * (largeur_urne + espacement_urnes)
                            + largeur_urne // 2
                        )
                        centre_y_urne_active = 390 + 36 + 40
                        couleur_boule = COULEUR_JAUNE if boule_jouee == 1 else COULEUR_ROUGE

                        for _ in range(3):
                            decalage_x = random.randint(-largeur_urne // 3, largeur_urne // 3)
                            decalage_y = random.randint(-20, 20)
                            liste_particules.append(Particule(
                                centre_x_urne_active + decalage_x,
                                centre_y_urne_active - 30,
                                couleur_boule,
                                centre_x_urne_active + decalage_x,
                                centre_y_urne_active + decalage_y
                            ))
                else:
                    etat_urne_active = None

        # ── Mise à jour des particules ────────────────────────────────────────
        for particule in liste_particules:
            particule.mettre_a_jour()
        liste_particules = [p for p in liste_particules if not p.est_morte()]

        # ── Dessin de la scène ────────────────────────────────────────────────
        fenetre.fill(COULEUR_FOND)

        afficher_texte(fenetre, "Jeu de Nim — Apprentissage par urnes",
                       LARGEUR_FENETRE // 2, 6,
                       police_moyenne, COULEUR_TEXTE_DISCRET, ancre="midtop")

        # Bâtonnets restants à la fin de la dernière partie
        nb_batons_fin_partie = 0
        if journal_derniere_partie:
            dernier_tour         = journal_derniere_partie[-1]
            nb_batons_fin_partie = max(0, dernier_tour[1] - dernier_tour[2])
        dessiner_batons(fenetre, nb_batons_fin_partie, NB_BATONS_DEPART,
                        (20, 22, 360, 115), police_petite)

        dessiner_statistiques_globales(fenetre, nb_parties, nb_victoires,
                                        (395, 22, 440, 115), polices)
        dessiner_journal_recent(fenetre, list(journal_recent)[:9],
                                 (850, 22, 230, 340), polices)
        dessiner_courbe_apprentissage(fenetre, historique_victoires,
                                       (395, 150, 440, 215), polices)
        dessiner_detail_derniere_partie(fenetre, journal_derniere_partie,
                                         (20, 150, 360, 215), polices)
        dessiner_urnes(fenetre, urnes, polices, etat_urne_active, liste_particules)

        # Barre de raccourcis clavier
        y_raccourcis = HAUTEUR_FENETRE - 24
        raccourcis_clavier = [
            ("ESPACE", "pause/reprendre"),
            ("↑ / ↓",  f"vitesse : {vitesse_simulation}x"),
            ("R",       "réinitialiser"),
        ]
        x_courant = 20
        for touche, description in raccourcis_clavier:
            dessiner_rectangle_arrondi(
                fenetre, COULEUR_PANNEAU,
                (x_courant, y_raccourcis - 4, 28, 20), rayon=4
            )
            afficher_texte(fenetre, touche,
                           x_courant + 14, y_raccourcis + 6,
                           police_petite, COULEUR_TEXTE, ancre="center")
            x_courant += 34
            afficher_texte(fenetre, description,
                           x_courant, y_raccourcis + 6,
                           police_petite, COULEUR_TEXTE_DISCRET, ancre="midleft")
            x_courant += len(description) * 8 + 24

        if en_pause:
            afficher_texte(fenetre, "⏸ PAUSE",
                           LARGEUR_FENETRE // 2, y_raccourcis + 6,
                           police_moyenne, COULEUR_ROSE, ancre="center")

        pygame.display.flip()
        horloge.tick(IMAGES_PAR_SECONDE)


if __name__ == "__main__":
    lancer_simulation()
