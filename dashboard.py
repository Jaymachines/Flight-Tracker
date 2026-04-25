import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
import datetime

# --- CONFIGURATION ---
DB_URL = "sqlite:///./flight_data.db"
engine = create_engine(DB_URL)
st.set_page_config(page_title="StreetPulse Analytics", layout="wide", page_icon="📈")

@st.cache_data(ttl=30)
def load_data():
    query = "SELECT * FROM prices"
    try:
        df = pd.read_sql(query, engine)
        df['scrape_date'] = pd.to_datetime(df['scrape_date'], errors='coerce')
        df['departure_date'] = pd.to_datetime(df['departure_date'], format='mixed', errors='coerce')
        return df.dropna(subset=['departure_date', 'scrape_date'])
    except Exception:
        return pd.DataFrame()

df = load_data()

st.title("📊 StreetPulse | Moteur d'Aubaines Temporel")

if df.empty:
    st.warning("Aucune donnée disponible. Le coffre-fort est vide !")
else:
    try:
        # --- LOGIQUE TEMPORELLE ---
        max_date = df['scrape_date'].max()
        date_1w = max_date - pd.Timedelta(days=7)
        date_3m = max_date - pd.Timedelta(days=90)
        date_6m = max_date - pd.Timedelta(days=180)

        stats_hist = df.groupby('route_id')['price'].mean().reset_index().rename(columns={'price': 'avg_hist'})
        stats_6m = df[df['scrape_date'] >= date_6m].groupby('route_id')['price'].mean().reset_index().rename(columns={'price': 'avg_6m'})
        stats_3m = df[df['scrape_date'] >= date_3m].groupby('route_id')['price'].mean().reset_index().rename(columns={'price': 'avg_3m'})
        stats_1w = df[df['scrape_date'] >= date_1w].groupby('route_id')['price'].mean().reset_index().rename(columns={'price': 'avg_1w'})

        route_stats = stats_hist.merge(stats_6m, on='route_id', how='left')\
                                .merge(stats_3m, on='route_id', how='left')\
                                .merge(stats_1w, on='route_id', how='left')
        analysis_df = df.merge(route_stats, on='route_id')

        analysis_df['baseline'] = analysis_df['avg_3m'].fillna(analysis_df['avg_hist'])
        analysis_df['discount_pct'] = ((analysis_df['baseline'] - analysis_df['price']) / analysis_df['baseline']) * 100
        
        analysis_df['baseline_1w'] = analysis_df['avg_1w'].fillna(analysis_df['baseline'])
        analysis_df['discount_1w_pct'] = ((analysis_df['baseline_1w'] - analysis_df['price']) / analysis_df['baseline_1w']) * 100
        
        recent_cutoff = max_date - pd.Timedelta(days=3)
        live_deals = analysis_df[analysis_df['scrape_date'] >= recent_cutoff]

        # =====================================================================
        # SECTION 1 : LE TABLEAU DE BORD DES AUBAINES 
        # =====================================================================
        st.subheader("🎯 Sniper de prix (Comparé aux tendances récentes)")
        st.markdown("Ce tableau affiche la **meilleure offre unique** pour chaque route. Trié par le plus gros rabais de la dernière semaine.")
        
        today = datetime.date.today()
        if live_deals.empty:
            min_dep, max_dep = today, today + datetime.timedelta(days=365)
        else:
            min_dep = live_deals['departure_date'].min().date()
            max_dep = live_deals['departure_date'].max().date()
            if min_dep >= max_dep: max_dep = min_dep + datetime.timedelta(days=30)
        
        col_filter, _ = st.columns([1, 2])
        with col_filter:
            selected_period = st.date_input(
                "Cible une fenêtre de départ précise :",
                value=(min_dep, max_dep),
                min_value=min_dep - datetime.timedelta(days=365),
                max_value=max_dep + datetime.timedelta(days=365)
            )
        
        if isinstance(selected_period, tuple) and len(selected_period) == 2:
            start_date, end_date = pd.to_datetime(selected_period[0]), pd.to_datetime(selected_period[1])
            filtered_deals = live_deals[(live_deals['departure_date'] >= start_date) & (live_deals['departure_date'] <= end_date)]
        else:
            filtered_deals = live_deals 

        if not filtered_deals.empty:
            best_live_deals = filtered_deals.loc[filtered_deals.groupby('route_id')['price'].idxmin()]
            top_deals = best_live_deals.sort_values(by='discount_1w_pct', ascending=False).head(15)
            display_deals = top_deals[['route_id', 'departure_date', 'price', 'avg_1w', 'avg_3m', 'avg_6m', 'avg_hist', 'discount_1w_pct', 'discount_pct']].copy()
            
            display_deals['departure_date'] = display_deals['departure_date'].dt.strftime('%Y-%m-%d')
            display_deals['discount_1w_pct'] = display_deals['discount_1w_pct'].map('{:.1f}%'.format)
            display_deals['discount_pct'] = display_deals['discount_pct'].map('{:.1f}%'.format)
            for col in ['price', 'avg_1w', 'avg_3m', 'avg_6m', 'avg_hist']:
                display_deals[col] = display_deals[col].map('${:.0f}'.format)
            
            display_deals.columns = ['Route', 'Départ Prévu', 'PRIX ACTUEL', 'Moy. (1 Sem)', 'Moy. (3 Mois)', 'Moy. (6 Mois)', 'Moy. (Absolue)', 'Rabais (vs 1 Sem)', 'Rabais (vs 3 Mois)']
            st.dataframe(display_deals.set_index('Route'), use_container_width=True)
        else:
            st.info("✈️ Aucun vol trouvé pour cette période précise.")

        # =====================================================================
        # SECTION 2 : MACHINE À REMONTER LE TEMPS 
        # =====================================================================
        st.markdown("---")
        st.subheader("🕰️ Historique de fluctuation (Vols spécifiques)")
        st.markdown("Sélectionne tes routes et une fenêtre dans le calendrier pour observer l'algorithme des prix à l'œuvre.")
        
        col1, col2 = st.columns(2)
        with col1:
            available_routes = sorted(df['route_id'].unique())
            selected_routes = st.multiselect("1. Cible la ou les routes", available_routes, default=available_routes[0:1] if available_routes else None)
        with col2:
            if selected_routes:
                filtered_by_route = df[df['route_id'].isin(selected_routes)]
                min_avail = filtered_by_route['departure_date'].min().date()
                max_avail = filtered_by_route['departure_date'].max().date()
                if min_avail >= max_avail: max_avail = min_avail + datetime.timedelta(days=7) 
                
                selected_dates_range = st.date_input(
                    "2. Cible une fenêtre de dates de départ",
                    value=(min_avail, max_avail),
                    min_value=min_avail - datetime.timedelta(days=365),
                    max_value=max_avail + datetime.timedelta(days=365)
                )
            else:
                selected_dates_range = []

        if selected_routes and isinstance(selected_dates_range, tuple) and len(selected_dates_range) == 2:
            s_date, e_date = pd.to_datetime(selected_dates_range[0]), pd.to_datetime(selected_dates_range[1])
            final_data = filtered_by_route[(filtered_by_route['departure_date'] >= s_date) & (filtered_by_route['departure_date'] <= e_date)].copy()
            
            if not final_data.empty:
                final_data['Tracé'] = final_data['route_id'] + " | Départ: " + final_data['departure_date'].dt.strftime('%Y-%m-%d')
                final_data = final_data.sort_values('scrape_date')
                
                # Le graphique
                fig2 = px.line(
                    final_data, x='scrape_date', y='price', color='Tracé', markers=True,
                    title=f"Fluctuation pour les départs entre {s_date.strftime('%Y-%m-%d')} et {e_date.strftime('%Y-%m-%d')}"
                )
                fig2.update_layout(hovermode="x unified", yaxis_tickformat="$", legend=dict(orientation="h", yanchor="bottom", y=-0.4, xanchor="center", x=0.5))
                st.plotly_chart(fig2, use_container_width=True)
                
                # --- NOUVEAU : LE TABLEAU RÉCAPITULATIF SOUS LE GRAPHIQUE ---
                st.markdown("##### 📋 Résumé des prix pour la sélection ci-dessus :")
                summary_df = final_data.groupby(['route_id', 'departure_date']).agg(
                    Prix_Actuel=('price', 'last'), # Dernier prix scanné
                    Prix_Plancher=('price', 'min'), # Le plus bas historique
                    Prix_Plafond=('price', 'max') # Le plus haut historique
                ).reset_index()
                
                summary_df['departure_date'] = summary_df['departure_date'].dt.strftime('%Y-%m-%d')
                summary_df.columns = ['Route', 'Date de Départ', 'Dernier Prix Scanné', 'Plus Bas Historique', 'Plus Haut Historique']
                
                # Formater en dollars
                for col in ['Dernier Prix Scanné', 'Plus Bas Historique', 'Plus Haut Historique']:
                    summary_df[col] = summary_df[col].map('${:.0f}'.format)
                
                st.dataframe(summary_df, use_container_width=True, hide_index=True)

            else:
                st.warning("Aucune donnée croisée pour ces routes dans cette fenêtre de temps.")
        
        # =====================================================================
        # SECTION 3 : LE PLANIFICATEUR ALLER-RETOUR (HACKER FARES)
        # =====================================================================
        st.markdown("---")
        st.subheader("🎒 Combo Aller-Retour (Hacker Fares Optimaux)")
        st.markdown("Trouve le voyage le moins cher en combinant un aller et un retour selon la durée exacte de ton séjour.")
        
        # Identifier automatiquement les aéroports disponibles depuis YQB
        destinations = sorted(list(set([route.split('-')[1] for route in df['route_id'].unique() if route.startswith('YQB-')])))
        
        if destinations:
            col_dest, col_dur = st.columns(2)
            with col_dest:
                cible = st.selectbox("Choisis ta destination depuis Québec (YQB) :", destinations)
            with col_dur:
                # Permet de choisir une fenêtre (ex: je veux voyager entre 28 et 31 jours)
                duree = st.slider("Durée du voyage (en jours) :", min_value=7, max_value=90, value=(28, 31))
            
            # 1. Obtenir les meilleurs prix d'ALLER (YQB -> CIBLE)
            aller = df[df['route_id'] == f"YQB-{cible}"].groupby('departure_date')['price'].min().reset_index()
            aller.columns = ['Date_Aller', 'Prix_Aller']
            
            # 2. Obtenir les meilleurs prix de RETOUR (CIBLE -> YQB)
            retour = df[df['route_id'] == f"{cible}-YQB"].groupby('departure_date')['price'].min().reset_index()
            retour.columns = ['Date_Retour', 'Prix_Retour']
            
            if not aller.empty and not retour.empty:
                # 3. Croiser toutes les dates possibles (Cross Join)
                combos = aller.merge(retour, how='cross')
                
                # 4. Calculer la durée entre l'aller et le retour
                combos['Duree_Reelle'] = (combos['Date_Retour'] - combos['Date_Aller']).dt.days
                
                # 5. Filtrer pour ne garder que la durée demandée par le curseur
                voyages_valides = combos[(combos['Duree_Reelle'] >= duree[0]) & (combos['Duree_Reelle'] <= duree[1])].copy()
                
                if not voyages_valides.empty:
                    # Calculer le Hacker Fare total
                    voyages_valides['PRIX_TOTAL'] = voyages_valides['Prix_Aller'] + voyages_valides['Prix_Retour']
                    
                    # Trier par le moins cher et prendre le Top 15
                    top_voyages = voyages_valides.sort_values('PRIX_TOTAL').head(15)
                    
                    # Formatage propre
                    top_voyages['Date_Aller'] = top_voyages['Date_Aller'].dt.strftime('%Y-%m-%d')
                    top_voyages['Date_Retour'] = top_voyages['Date_Retour'].dt.strftime('%Y-%m-%d')
                    top_voyages['Prix_Aller'] = top_voyages['Prix_Aller'].map('${:.0f}'.format)
                    top_voyages['Prix_Retour'] = top_voyages['Prix_Retour'].map('${:.0f}'.format)
                    top_voyages['PRIX_TOTAL'] = top_voyages['PRIX_TOTAL'].map('${:.0f}'.format)
                    
                    top_voyages = top_voyages[['Date_Aller', 'Date_Retour', 'Duree_Reelle', 'Prix_Aller', 'Prix_Retour', 'PRIX_TOTAL']]
                    top_voyages.columns = ['Décollage (YQB)', 'Retour au pays', 'Jours sur place', 'Prix du vol Aller', 'Prix du vol Retour', 'HACKER FARE TOTAL']
                    
                    st.success(f"Voici les 15 meilleures combinaisons pour un voyage de {duree[0]} à {duree[1]} jours vers {cible} :")
                    st.dataframe(top_voyages, use_container_width=True, hide_index=True)
                else:
                    st.warning(f"Aucune combinaison de vols trouvée pour un séjour de {duree[0]} à {duree[1]} jours vers {cible}.")
            else:
                st.warning("Il manque des données d'aller ou de retour pour cette destination.")

    except Exception as e:
        st.error(f"⚠️ Aïe ! Le code a planté à l'exécution : {e}")