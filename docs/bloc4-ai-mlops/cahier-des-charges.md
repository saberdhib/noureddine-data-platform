# Cahier des charges — Bloc 4 : IA / MLOps

> Document métier. Définit le besoin, les critères de succès et les contraintes du module
> de prévision de la demande de la plateforme NOUREDDINE.

---

## 1. Contexte et besoin métier

NOUREDDINE est une marque e-commerce D2C premium (~8–9 M€ de CA, ~30 collaborateurs) qui doit
**piloter un stock limité face à une demande irrégulière et événementielle**. Les pics de vente
ne sont pas aléatoires : ils se concentrent autour du **calendrier culturel islamique** et de
quelques temps forts du retail.

Événements structurants de la demande :

| Événement | Type | Effet attendu sur la demande |
|-----------|------|------------------------------|
| **Ramadan** | Religieux | Montée progressive, achats anticipés (qamis, grooming). |
| **Aïd al-Fitr** | Religieux | Pic marqué juste avant la date ; renouvellement vestimentaire. |
| **Aïd al-Adha** | Religieux | Second pic, profil distinct du Fitr. |
| **Saison des mariages (Nikah)** | Vie / saisonnier | Plateau soutenu (costumes, tenues de cérémonie). |
| **Black Friday** | Retail | Pic court et intense, sensible au prix. |
| **Summer Sale** | Retail | Écoulement de fin de saison. |

Sans prévision gouvernée, la marque subit deux risques symétriques : **rupture de stock** sur des
séries limitées (perte de chiffre d'affaires et de clients) ou **surstock** immobilisant la
trésorerie. Le besoin est donc une **prévision de la demande à 30 jours, par catégorie de
produit**, suffisamment fiable pour générer un **signal de réassort** exploitable par les
opérations.

### Objectif

Fournir, à l'équipe opérations, une prévision quotidienne du **nombre de commandes par catégorie
à horizon 30 jours**, intégrant explicitement les fenêtres du calendrier islamique, restituée dans
une application décisionnelle (Streamlit) et exposée via une API (FastAPI).

---

## 2. Périmètre

**Inclus :**
- Modèle de prévision **LightGBM** (catégorie × jour, horizon 30 j).
- Features calendaires + retards (lags) + moyennes glissantes, **sans aucune donnée personnelle**.
- API de service (FastAPI) avec authentification par clé.
- Application métier (Streamlit, 3 pages) — dont la page **Prévision de la demande** avec
  surimpression du calendrier islamique.
- Monitoring du modèle (Evidently) + panneau Grafana « Model Health ».
- Réentraînement automatisé (Airflow) : planifié + déclenché par dérive (drift).

**Exclus :** prévision au SKU individuel (granularité catégorie retenue), recommandation client,
pricing dynamique, streaming temps réel, Kubernetes (voir ADR-0013).

---

## 3. Critères de succès

### 3.1 Performance du modèle (cibles MAPE)

Le modèle est évalué sur les **30 derniers jours** (jeu de validation tenu à l'écart), par
catégorie et au global.

| Indicateur | Cible | Commentaire |
|------------|-------|-------------|
| **MAPE global** | **≤ 30 %** | Seuil d'acceptation principal ; aligné sur `MAPE_THRESHOLD=0.30`. |
| MAPE par catégorie à fort volume (ex. Qamis, Grooming) | ≤ 25–30 % | Catégories pilotables finement. |
| MAPE par catégorie à faible volume / forte irrégularité | indicatif | Tolérance plus large ; le signal de réassort prime sur la précision absolue. |
| sMAPE, RMSE | suivis | Métriques complémentaires, par catégorie + global. |

> La cible n'est pas la perfection statistique mais un **signal de réassort exploitable** :
> la prévision doit positionner correctement les pics calendaires et leur amplitude relative,
> de façon à éviter les ruptures sur séries limitées.

### 3.2 Utilisabilité du signal de réassort

- La page **Stock Pilot** affiche, par catégorie : stock courant, demande prévue à 30 j,
  **jours de couverture restants**, et un **signal 🟢 / 🟠 / 🔴** (seuils configurables par env).
- Critère de succès qualitatif : un responsable opérations peut, en lisant la page, **décider
  d'un réassort** sans consulter la base directement.

### 3.3 Exploitabilité MLOps

- Réentraînement de bout en bout (extract → train → validate → promote/hold) fonctionnel.
- Promotion **atomique** d'un nouveau modèle uniquement si MAPE_nouveau ≤ MAPE_courant × 1,05.
- Dérive détectée → réentraînement déclenché automatiquement (démontrable en live).
- Panneau Grafana « Model Health » alimenté (score de dérive, MAPE, horodatage du dernier
  entraînement).

---

## 4. Contraintes

| Contrainte | Détail |
|------------|--------|
| **Données synthétiques** | Aucune donnée réelle. La demande est simulée (Bloc 3), modélisée de façon réaliste autour du calendrier. |
| **DPIA #2 — zéro PII** | Le modèle n'utilise **aucune** donnée personnelle : pas de `customer_id`, pas d'e-mail, pas de profil. Uniquement des agrégats de demande par catégorie. Engagements DPIA #2 : carte modèle publiée, explicabilité SHAP, humain dans la boucle. |
| **Exécutable sur portable** | Toute la stack tourne en local via Docker Compose ; entraînement LightGBM en quelques secondes sur CPU. |
| **Zéro licence / coût** | Outils libres uniquement (LightGBM, FastAPI, Streamlit, Evidently, Airflow, PostgreSQL, Grafana). Aucun service cloud payant. |
| **Gouvernance Bloc 1** | Respect des politiques P-03 (clé d'API pour les endpoints protégés) et des portes qualité P-04 (le modèle ne s'entraîne pas si les tests dbt amont sont au rouge). |
| **Reproductibilité** | `docker compose up` + une commande d'entraînement documentée suffisent à reconstituer l'ensemble. |

---

## 5. Livrables

1. Modèle LightGBM entraîné + `current.pkl` (promotion atomique) + `shap_summary.png`.
2. API FastAPI (`/health`, `/model-info`, `/predict`, `/retrain`) avec OpenAPI sur `/docs`.
3. Application Streamlit 3 pages (Executive, **Demand Forecast**, Stock Pilot).
4. Monitoring Evidently + panneau Grafana « Model Health ».
5. DAGs Airflow `retrain_model` (planifié) et `monitor_model` (quotidien, drift-triggered).
6. Carte modèle (générée par le code) documentant performance, features et engagements DPIA #2.
7. Documentation (ce cahier des charges, architecture, ADR 0009–0013, diagrammes).
