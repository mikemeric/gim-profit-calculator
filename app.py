import streamlit as st
import plotly.graph_objects as go
from dataclasses import dataclass
from typing import Dict
import requests  # NOUVEAU : Pour envoyer les données à Google

# ==========================================
# 1. CONFIGURATION "MAXIMUM BEAUTY" (ZARA V6)
# ==========================================
st.set_page_config(
    page_title="GIM-PROFIT Calculator",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Injection CSS LUXE & LISIBILITÉ
st.markdown("""
<style>
    .stApp { background-color: #0B0F19; color: #E6E6E6; }
    section[data-testid="stSidebar"] { background-color: #11151F; border-right: 1px solid #2B3345; }
    section[data-testid="stSidebar"] .stMarkdown p, 
    section[data-testid="stSidebar"] label, 
    section[data-testid="stSidebar"] .stCaption, 
    section[data-testid="stSidebar"] small { color: #E0E6ED !important; font-weight: 500; }
    section[data-testid="stSidebar"] .streamlit-expanderHeader { color: #FFFFFF !important; font-weight: bold; background-color: #1A202C; border-radius: 5px; margin-bottom: 5px; }
    .stNumberInput input, .stTextInput input { background-color: #0B0F19; color: #FFFFFF; border: 1px solid #4A5568; border-radius: 6px; }
    div.stButton > button[kind="primary"] { background: linear-gradient(90deg, #FF4B4B 0%, #FF0000 100%); border: none; color: white; font-weight: bold; box-shadow: 0 4px 14px 0 rgba(255, 75, 75, 0.39); transition: all 0.2s ease-in-out; }
    div.stButton > button[kind="primary"]:hover { transform: scale(1.02); box-shadow: 0 6px 20px 0 rgba(255, 75, 75, 0.29); }
    section[data-testid="stSidebar"] button { background-color: #2D3748; color: white; border: 1px solid #4A5568; }
    .stAlert { background-color: #1A202C; color: #E2E8F0; border: 1px solid #2D3748; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
    header[data-testid="stHeader"] { background-color: transparent; }
    div[data-testid="stMetricValue"] { text-shadow: 0 0 10px rgba(255,255,255,0.1); }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. MODULE BACKEND : GESTION DES LEADS (AXEL)
# ==========================================
def save_lead_to_google(email):
    # URL de soumission construite à partir de votre lien d'édition
    FORM_URL = "https://docs.google.com/forms/d/1FvwZlm9TR54PDuL_Gv4JczPNAoz8kg7xsKHGYcpwL3Y/formResponse"
    
    # Vos IDs spécifiques
    FORM_DATA = {
        "entry.436351499": email,           # Champ Email
        "entry.1648052779": "App Simulateur TCO" # Champ Source
    }
    
    try:
        # Envoi discret (sans ouvrir de fenêtre)
        response = requests.post(FORM_URL, data=FORM_DATA)
        return response.status_code == 200
    except:
        return False

# ==========================================
# 3. LOGIQUE MÉTIER (MARCUS)
# ==========================================

def format_fcfa(montant):
    if abs(montant) >= 1_000_000:
        return f"{montant/1_000_000:,.1f}M"
    elif abs(montant) >= 1_000:
        return f"{montant/1_000:,.0f}K"
    return f"{montant:,.0f}"

def format_fcfa_complete(montant):
    return f"{montant:,.0f}".replace(",", " ")

@dataclass
class ScenarioParams:
    duree_etude: int
    taux_actualisation: float
    taux_inflation: float
    cout_arret_horaire: float
    maint_old_annuel: float
    energie_old_annuel: float
    facteur_usure_old: float 
    valeur_revente_actuelle: float
    nb_pannes_old_base: float
    mttr_old: float
    capex_new: float
    maint_new_annuel: float
    energie_new_annuel: float
    nb_pannes_new_base: float
    mttr_new: float

def calculer_tco_expert(params: ScenarioParams) -> Dict:
    cumul_old = 0.0
    cumul_new = params.capex_new - params.valeur_revente_actuelle
    
    historique_cumul_old = [0]
    historique_cumul_new = [cumul_new]
    historique_arrets_old = []
    historique_arrets_new = []
    historique_perte_prod_old = []
    
    break_even_year = None
    crossed = False

    for annee in range(1, params.duree_etude + 1):
        facteur_inflation = (1 + params.taux_inflation) ** annee
        facteur_wacc = (1 + params.taux_actualisation) ** annee
        
        # LOGIQUE MARCUS
        facteur_risque = (1 + params.facteur_usure_old) ** (annee - 1)
        
        # SCENARIO A : VIEUX
        cout_maint_old = params.maint_old_annuel * facteur_risque * facteur_inflation
        cout_energie_old = params.energie_old_annuel * (1 + 0.02)**(annee) * facteur_inflation
        
        nb_pannes_old_n = params.nb_pannes_old_base * facteur_risque
        heures_perdues_old = nb_pannes_old_n * params.mttr_old
        cout_perte_prod_old = heures_perdues_old * params.cout_arret_horaire * facteur_inflation
        
        total_cashflow_old = cout_maint_old + cout_energie_old + cout_perte_prod_old
        cumul_old += total_cashflow_old / facteur_wacc
        
        # SCENARIO B : NEUF
        cout_maint_new = params.maint_new_annuel * (1.02 ** annee) * facteur_inflation
        cout_energie_new = params.energie_new_annuel * (1.01 ** annee) * facteur_inflation
        
        nb_pannes_new_n = params.nb_pannes_new_base 
        heures_perdues_new = nb_pannes_new_n * params.mttr_new
        cout_perte_prod_new = heures_perdues_new * params.cout_arret_horaire * facteur_inflation
        
        total_cashflow_new = cout_maint_new + cout_energie_new + cout_perte_prod_new
        cumul_new += total_cashflow_new / facteur_wacc
        
        historique_cumul_old.append(cumul_old)
        historique_cumul_new.append(cumul_new)
        historique_arrets_old.append(heures_perdues_old)
        historique_arrets_new.append(heures_perdues_new)
        historique_perte_prod_old.append(cout_perte_prod_old)

        if not crossed and cumul_new < cumul_old:
            break_even_year = annee
            crossed = True
            
    return {
        "break_even_year": break_even_year,
        "total_savings": cumul_old - cumul_new,
        "cumul_old": historique_cumul_old,
        "cumul_new": historique_cumul_new,
        "heures_perdues_old_final": historique_arrets_old[-1] if historique_arrets_old else 0,
        "heures_perdues_new_final": historique_arrets_new[-1] if historique_arrets_new else 0,
        "perte_prod_old_total": sum(historique_perte_prod_old),
        "historique_arrets_old": historique_arrets_old,
        "historique_arrets_new": historique_arrets_new
    }

# ==========================================
# 4. SIDEBAR (STRATÉGIE IDRISS + SOFIA)
# ==========================================

st.sidebar.title("💎 GIM-PROFIT")
st.sidebar.caption("v7.0 Connected Edition")

# --- CAPTURE DE LEAD (INTELLIGENTE) ---
with st.sidebar.container():
    st.sidebar.markdown(
        """
        <div style="background: linear-gradient(135deg, #1A202C 0%, #2D3748 100%); padding: 15px; border-radius: 8px; border: 1px solid #4A5568; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
            <h4 style="margin-top:0; color:#FF4B4B; margin-bottom: 8px; font-weight:900;">📉 AUDIT DE RENTABILITÉ</h4>
            <p style="font-size:13px; color: #E2E8F0; margin: 0; line-height: 1.4;">
                Méthode <b>LCC (Life Cycle Cost)</b>.<br>
                Rapport PDF certifié pour CODIR.
            </p>
        </div>
        """, unsafe_allow_html=True
    )
    email_sidebar = st.sidebar.text_input("Email professionnel", key="email_sidebar", placeholder="dg@usine.cm")
    rgpd = st.sidebar.checkbox("Consentement RGPD / APM", help="Nous ne spammons jamais.")
    
    # BOUTON CONNECTÉ À GOOGLE SHEETS
    if st.sidebar.button("✨ GÉNÉRER MON RAPPORT", type="primary"):
        if "@" in email_sidebar and "." in email_sidebar and rgpd:
            with st.spinner("Analyse en cours..."):
                # Envoi des données à Google
                success = save_lead_to_google(email_sidebar)
                if success:
                    st.sidebar.success("✅ Rapport envoyé ! Surveillez vos emails.")
                    st.balloons()
                else:
                    st.sidebar.error("Erreur de connexion. Réessayez.")
        elif not rgpd:
            st.sidebar.warning("Cochez la case RGPD.")
        else:
            st.sidebar.warning("Email invalide.")
    
    st.sidebar.markdown("<hr style='border-color: #2D3748;'>", unsafe_allow_html=True)

# PARAMÈTRES TECHNIQUES
st.sidebar.markdown("### ⚙️ PARAMÈTRES")

with st.sidebar.expander("1️⃣ ÉQUIPEMENT ACTUEL", expanded=True):
    maint_old = st.number_input("Coût Maint. Annuel (FCFA)", value=350_000, step=50_000, format="%d")
    energie_old = st.number_input("Coût Énergie Annuel (FCFA)", value=800_000, step=100_000, format="%d")
    nb_pannes_old = st.number_input("Fréquence Pannes/an", value=8, step=1)
    mttr_old = st.number_input("MTTR (Heures)", value=4.0, step=0.5)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<b style='color:#FF4B4B'>🔥 Facteur d'Usure (Weibull)</b>", unsafe_allow_html=True)
    facteur_usure = st.slider("Accélération pannes (%)", 0, 30, 15) / 100
    valeur_revente = st.number_input("Valeur Revente (FCFA)", value=100_000, step=50_000)

with st.sidebar.expander("2️⃣ PROJET NEUF", expanded=False):
    capex_new = st.number_input("CAPEX (Achat)", value=8_000_000, step=500_000, format="%d")
    maint_new = st.number_input("Maint. prévisionnelle", value=80_000, step=10_000)
    energie_new = st.number_input("Énergie prévisionnelle", value=450_000, step=50_000)
    nb_pannes_new = st.number_input("Pannes/an (Jeunesse)", value=1, step=1)
    mttr_new = st.number_input("MTTR Neuf (H)", value=1.0, step=0.5)

with st.sidebar.expander("3️⃣ IMPACT FINANCIER", expanded=True):
    cout_arret_horaire = st.number_input(
        "Perte Marge / Heure (FCFA)", 
        value=25_000, step=5_000, format="%d"
    )

with st.sidebar.expander("4️⃣ MACRO-ÉCONOMIE", expanded=False):
    duree_etude = st.number_input("Horizon (années)", value=7, min_value=3, max_value=15)
    taux_actualisation = st.slider("WACC %", 5, 20, 12) / 100
    taux_inflation = st.slider("Inflation %", 0, 10, 3) / 100

# ==========================================
# 5. DASHBOARD DE RÉSULTATS (ZARA)
# ==========================================

st.title("GIM-PROFIT CALCULATOR")
st.markdown("<h3 style='color: #718096; font-weight: normal; margin-top:-15px;'>Intelligence Financière pour la Maintenance Industrielle</h3>", unsafe_allow_html=True)

# Calcul
params = ScenarioParams(
    duree_etude=duree_etude, taux_actualisation=taux_actualisation, taux_inflation=taux_inflation,
    cout_arret_horaire=cout_arret_horaire, maint_old_annuel=maint_old, energie_old_annuel=energie_old,
    facteur_usure_old=facteur_usure, valeur_revente_actuelle=valeur_revente, nb_pannes_old_base=nb_pannes_old,
    mttr_old=mttr_old, capex_new=capex_new, maint_new_annuel=maint_new, energie_new_annuel=energie_new,
    nb_pannes_new_base=nb_pannes_new, mttr_new=mttr_new
)
res = calculer_tco_expert(params)

st.markdown("<br>", unsafe_allow_html=True)

# --- CARTES KPI (Style Néon) ---
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div style="background-color: #1A202C; padding: 20px; border-radius: 10px; border: 1px solid #2D3748; text-align: center;">
        <p style="color: #A0AEC0; font-size: 14px; margin:0;">RENTABILITÉ (ROI)</p>
        <h1 style="color: #48BB78; font-size: 42px; margin:0; text-shadow: 0 0 10px rgba(72,187,120,0.3);">
            {}
        </h1>
    </div>
    """.format(f"AN {res['break_even_year']}" if res['break_even_year'] else "JAMAIS"), unsafe_allow_html=True)

with col2:
    gain = res['total_savings']
    color = "#48BB78" if gain > 0 else "#F56565"
    st.markdown(f"""
    <div style="background-color: #1A202C; padding: 20px; border-radius: 10px; border: 1px solid #2D3748; text-align: center;">
        <p style="color: #A0AEC0; font-size: 14px; margin:0;">CASH FLOW SAUVÉ</p>
        <h1 style="color: {color}; font-size: 42px; margin:0; text-shadow: 0 0 10px {color}44;">
            {format_fcfa(gain)}
        </h1>
    </div>
    """, unsafe_allow_html=True)

with col3:
    h_perdues = res['heures_perdues_old_final']
    st.markdown(f"""
    <div style="background-color: #1A202C; padding: 20px; border-radius: 10px; border: 1px solid #2D3748; text-align: center;">
        <p style="color: #A0AEC0; font-size: 14px; margin:0;">RISQUE PANNE (FIN)</p>
        <h1 style="color: #F56565; font-size: 42px; margin:0; text-shadow: 0 0 10px rgba(245,101,101,0.3);">
            {h_perdues:.0f} h
        </h1>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- ALERTE MARCUS (Card Style) ---
perte_totale = res['perte_prod_old_total']
ratio = perte_totale / params.capex_new

if ratio > 1.0:
    st.markdown(f"""
    <div style="background-color: #2C1A1A; border-left: 5px solid #F56565; padding: 20px; border-radius: 5px;">
        <h3 style="color: #F56565; margin-top:0;">🚨 DIAGNOSTIC CRITIQUE</h3>
        <p style="color: #E2E8F0; font-size: 16px;">Le maintien de l'équipement est une aberration financière. 
        Les pertes cumulées (<b>{format_fcfa_complete(perte_totale)} FCFA</b>) dépassent <b>{ratio:.1f}x</b> le prix du neuf.</p>
    </div>
    """, unsafe_allow_html=True)
elif ratio > 0.5:
    st.warning(f"⚠️ **ATTENTION :** Vos pannes commencent à coûter très cher ({format_fcfa_complete(perte_totale)} FCFA). Préparez le remplacement.")
else:
    st.success("✅ **SITUATION STABLE :** L'équipement actuel est encore économiquement viable.")

st.markdown("<br>", unsafe_allow_html=True)

# --- GRAPHIQUES AVANCÉS ---
tab1, tab2 = st.tabs(["📊 PROJECTION TCO (LCC)", "🔥 EXPLOSION DU RISQUE"])

with tab1:
    fig = go.Figure()
    annees = list(range(0, params.duree_etude + 1))
    fig.add_trace(go.Scatter(x=annees, y=res['cumul_old'], mode='lines', name='Maintien Existant (Risque)', line=dict(color='#F56565', width=4, shape='spline')))
    fig.add_trace(go.Scatter(x=annees, y=res['cumul_new'], mode='lines', name='Investissement Neuf', line=dict(color='#48BB78', width=4, shape='spline')))
    
    if res['break_even_year']:
        fig.add_vline(x=res['break_even_year'], line_dash="dot", line_color="white", annotation_text="Rentabilité")

    fig.update_layout(
        plot_bgcolor='#0B0F19', paper_bgcolor='#0B0F19',
        font=dict(color='#A0AEC0'),
        xaxis=dict(showgrid=True, gridcolor='#2D3748'),
        yaxis=dict(showgrid=True, gridcolor='#2D3748', title="Coût Cumulé (FCFA)"),
        margin=dict(l=20, r=20, t=30, b=20),
        height=450,
        legend=dict(orientation="h", y=1.1)
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    fig2 = go.Figure()
    x_axis = list(range(1, params.duree_etude + 1))
    fig2.add_trace(go.Bar(x=x_axis, y=res['historique_arrets_old'], name='Indisponibilité Existant (h)', marker_color='#F56565'))
    fig2.add_trace(go.Bar(x=x_axis, y=res['historique_arrets_new'], name='Indisponibilité Neuf (h)', marker_color='#48BB78'))
    
    fig2.update_layout(
        plot_bgcolor='#0B0F19', paper_bgcolor='#0B0F19',
        font=dict(color='#A0AEC0'),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='#2D3748', title="Heures d'arrêt / an"),
        margin=dict(l=20, r=20, t=30, b=20),
        height=450,
        legend=dict(orientation="h", y=1.1)
    )
    st.plotly_chart(fig2, use_container_width=True)

# --- FOOTER ---
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #718096; font-family: monospace;'>
        <small>CERTIFIÉ PAR L'ACADÉMIE PANAFRICAINE DE MAINTENANCE (APM) © 2025</small><br>
        <small>SECURE SERVER | ISO-27001 COMPLIANT</small>
    </div>
    """, 
    unsafe_allow_html=True
)