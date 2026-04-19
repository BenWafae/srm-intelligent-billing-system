"""
agent_app.py
============
Interface Streamlit de l'Agent IA SRM — Analyse & Comparaison de consommation.

Fonctionnalités :
  - Onglet 1 : Comparaison mensuelle (client + 2 mois → graphiques + rapport)
  - Onglet 2 : Surconsommation (détection automatique des anomalies)
  - Onglet 3 : Vue globale (stats + comparaison tous clients)
  - Onglet 4 : Chat Agent IA (questions complexes en langage naturel)

Lancer avec : streamlit run agent_app.py --server.port 8502
"""

import streamlit as st
import sys
import os
import json

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.agent_tools import (
    get_liste_clients,
    get_periodes_disponibles,
    get_historique_client,
    get_stats_globales,
    detecter_surconsommation,
)
from src.agent import (
    run_agent,
    run_comparaison_directe,
    run_detection_directe,
    run_comparaison_globale,
)

# ─────────────────────────────────────────────
# CONFIG PAGE
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="SRM — Agent IA",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CSS PERSONNALISÉ
# ─────────────────────────────────────────────

st.markdown("""
<style>
  :root {
    --srm-blue:    #1a3c5e;
    --srm-accent:  #00b4d8;
    --srm-green:   #2ecc71;
    --srm-orange:  #e67e22;
    --srm-red:     #e74c3c;
    --srm-bg:      #f4f7fb;
    --srm-card:    #ffffff;
    --srm-border:  #dde3ed;
    --srm-text:    #2d3748;
    --srm-muted:   #718096;
  }

  .stApp { background-color: var(--srm-bg); }

  div[data-testid="metric-container"] {
    background: var(--srm-card);
    border: 1px solid var(--srm-border);
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }
  div[data-testid="metric-container"] label {
    color: var(--srm-muted) !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    color: var(--srm-blue) !important;
  }

  .alerte-critique {
    background: #fef2f2; border-left: 4px solid var(--srm-red);
    border-radius: 8px; padding: 12px 16px; margin: 8px 0;
  }
  .alerte-elevee {
    background: #fff7ed; border-left: 4px solid var(--srm-orange);
    border-radius: 8px; padding: 12px 16px; margin: 8px 0;
  }
  .alerte-moderee {
    background: #fefce8; border-left: 4px solid #eab308;
    border-radius: 8px; padding: 12px 16px; margin: 8px 0;
  }

  .section-header {
    font-size: 1.1rem; font-weight: 700;
    color: var(--srm-blue);
    border-bottom: 2px solid var(--srm-accent);
    padding-bottom: 6px; margin: 24px 0 16px 0;
  }

  .badge-hausse  { background:#fef2f2; color:var(--srm-red);    padding:3px 10px; border-radius:20px; font-weight:700; font-size:0.85rem; }
  .badge-baisse  { background:#f0fdf4; color:var(--srm-green);  padding:3px 10px; border-radius:20px; font-weight:700; font-size:0.85rem; }
  .badge-stable  { background:#f0f9ff; color:var(--srm-accent); padding:3px 10px; border-radius:20px; font-weight:700; font-size:0.85rem; }

  /* ── Onglet 4 — styles chat améliorés ── */
  .intention-badge {
    display: inline-block;
    background: #e0f2fe; color: #0369a1;
    border-radius: 20px; padding: 3px 12px;
    font-size: 0.78rem; font-weight: 600;
    margin-bottom: 8px;
  }
  .suggestion-btn {
    background: var(--srm-card);
    border: 1px solid var(--srm-border);
    border-radius: 20px; padding: 6px 14px;
    font-size: 0.82rem; color: var(--srm-blue);
    cursor: pointer; margin: 4px;
    transition: all 0.2s;
  }
  .suggestion-btn:hover {
    background: var(--srm-blue); color: white;
  }
  .reponse-card {
    background: var(--srm-card);
    border: 1px solid var(--srm-border);
    border-radius: 12px; padding: 16px 20px;
    margin: 8px 0;
    box-shadow: 0 2px 6px rgba(0,0,0,0.04);
  }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🔍 SRM — Agent IA")
    st.markdown("---")
    st.markdown("### 🏠 Application principale")
    st.link_button("← Retour au chatbot", "http://localhost:8501", use_container_width=True)
    st.markdown("---")

    try:
        clients  = get_liste_clients()
        periodes = get_periodes_disponibles()
        st.success("✅ Base connectée")
        st.metric("Clients", len(clients))
        st.metric("Périodes", len(periodes))
        if periodes:
            st.caption(f"De {periodes[0]} à {periodes[-1]}")
    except Exception as e:
        st.error("❌ Base inaccessible")
        clients  = []
        periodes = []

    st.markdown("---")
    st.caption("Agent IA SRM — port 8502")

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────

if "chat_historique" not in st.session_state:
    st.session_state.chat_historique = []
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "question_suggeree" not in st.session_state:
    st.session_state.question_suggeree = ""

# ─────────────────────────────────────────────
# TITRE
# ─────────────────────────────────────────────

st.markdown("# 🔍 Agent IA — Analyse de Consommation")
st.markdown("Comparaisons, détections d'anomalies et rapports automatiques.")
st.markdown("---")

# ─────────────────────────────────────────────
# ONGLETS
# ─────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Comparaison mensuelle",
    "⚠️ Surconsommation",
    "🌍 Vue globale",
    "🤖 Agent IA",
])

# ═══════════════════════════════════════════════════════════
#  ONGLET 1 — COMPARAISON MENSUELLE (inchangé)
# ═══════════════════════════════════════════════════════════

with tab1:
    st.markdown('<div class="section-header">Comparaison mensuelle — Client</div>', unsafe_allow_html=True)

    if not clients or not periodes:
        st.warning("⚠️ Aucune donnée disponible. Importez d'abord un fichier Excel dans l'application principale.")
    else:
        col_c, col_m1, col_m2, col_btn = st.columns([3, 2, 2, 1])

        with col_c:
            client_sel = st.selectbox("👤 Client", options=clients, key="cmp_client")
        with col_m1:
            mois1_sel = st.selectbox("📅 Mois 1", options=periodes, key="cmp_mois1",
                                     index=max(0, len(periodes) - 2))
        with col_m2:
            mois2_sel = st.selectbox("📅 Mois 2", options=periodes, key="cmp_mois2",
                                     index=len(periodes) - 1)
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            btn_comparer = st.button("🔍 Comparer", use_container_width=True, type="primary")

        if btn_comparer or "cmp_result" in st.session_state:

            if btn_comparer:
                with st.spinner("Analyse en cours..."):
                    result = run_comparaison_directe(client_sel, mois1_sel, mois2_sel)
                st.session_state["cmp_result"] = result
                st.session_state["cmp_params"] = (client_sel, mois1_sel, mois2_sel)

            result = st.session_state.get("cmp_result", {})
            params = st.session_state.get("cmp_params", ("", "", ""))

            if "erreur" in result:
                st.error(f"❌ {result['erreur']}")
            else:
                client_nom = result.get("client", params[0])
                m1 = result["mois_1"]
                m2 = result["mois_2"]
                pct_c   = result.get("pct_conso")
                delta_c = result.get("delta_conso", 0)
                delta_m = result.get("delta_montant", 0)
                tendance = result.get("tendance", "stable")
                alerte   = result.get("alerte", False)

                if tendance == "hausse":
                    badge = f'<span class="badge-hausse">▲ Hausse {pct_c:+.1f}%</span>'
                elif tendance == "baisse":
                    badge = f'<span class="badge-baisse">▼ Baisse {pct_c:+.1f}%</span>'
                else:
                    badge = '<span class="badge-stable">→ Stable</span>'

                st.markdown(f"### 👤 {client_nom} &nbsp; {badge}", unsafe_allow_html=True)

                if alerte:
                    st.markdown(
                        f'<div class="alerte-critique">🔴 <strong>Alerte surconsommation</strong> — '
                        f'Hausse de <strong>{pct_c:.1f}%</strong> entre {params[1]} et {params[2]}</div>',
                        unsafe_allow_html=True
                    )

                st.markdown('<div class="section-header">Indicateurs clés</div>', unsafe_allow_html=True)
                col1, col2, col3, col4 = st.columns(4)
                unite = m1.get("unite", "")

                with col1:
                    st.metric(f"Consommation {params[1]}", f"{m1['consommation']:,.0f} {unite}")
                with col2:
                    st.metric(f"Consommation {params[2]}", f"{m2['consommation']:,.0f} {unite}",
                              delta=f"{delta_c:+.0f} {unite}" if delta_c else None,
                              delta_color="inverse" if delta_c > 0 else "normal")
                with col3:
                    st.metric(f"Montant {params[1]}", f"{m1['montant_ttc']:,.2f} Dhs")
                with col4:
                    st.metric(f"Montant {params[2]}", f"{m2['montant_ttc']:,.2f} Dhs",
                              delta=f"{delta_m:+.2f} Dhs" if delta_m else None,
                              delta_color="inverse" if delta_m > 0 else "normal")

                st.markdown('<div class="section-header">Visualisation</div>', unsafe_allow_html=True)

                try:
                    import plotly.graph_objects as go
                    col_g1, col_g2 = st.columns(2)
                    couleurs = ["#1a3c5e", "#00b4d8"]

                    with col_g1:
                        fig_c = go.Figure()
                        fig_c.add_trace(go.Bar(
                            x=[params[1], params[2]],
                            y=[m1["consommation"], m2["consommation"]],
                            marker_color=couleurs,
                            text=[f"{m1['consommation']:,.0f}", f"{m2['consommation']:,.0f}"],
                            textposition="outside",
                        ))
                        fig_c.update_layout(
                            title=f"Consommation ({unite})", showlegend=False, height=350,
                            plot_bgcolor="white", paper_bgcolor="white",
                            font=dict(family="sans-serif", size=13),
                            yaxis=dict(gridcolor="#eee"), margin=dict(t=50, b=30, l=40, r=20),
                        )
                        fig_c.add_hline(y=m1["consommation"], line_dash="dot",
                                        line_color="#e74c3c", annotation_text="Ref Mois 1",
                                        annotation_position="bottom right")
                        st.plotly_chart(fig_c, use_container_width=True)

                    with col_g2:
                        fig_m = go.Figure()
                        fig_m.add_trace(go.Bar(
                            x=[params[1], params[2]],
                            y=[m1["montant_ttc"], m2["montant_ttc"]],
                            marker_color=couleurs,
                            text=[f"{m1['montant_ttc']:,.0f}", f"{m2['montant_ttc']:,.0f}"],
                            textposition="outside",
                        ))
                        fig_m.update_layout(
                            title="Montant TTC (Dhs)", showlegend=False, height=350,
                            plot_bgcolor="white", paper_bgcolor="white",
                            font=dict(family="sans-serif", size=13),
                            yaxis=dict(gridcolor="#eee"), margin=dict(t=50, b=30, l=40, r=20),
                        )
                        fig_m.add_hline(y=m1["montant_ttc"], line_dash="dot",
                                        line_color="#e74c3c", annotation_text="Ref Mois 1",
                                        annotation_position="bottom right")
                        st.plotly_chart(fig_m, use_container_width=True)

                except ImportError:
                    import pandas as pd
                    df_chart = pd.DataFrame({
                        "Mois": [params[1], params[2]],
                        "Consommation": [m1["consommation"], m2["consommation"]],
                        "Montant TTC":  [m1["montant_ttc"], m2["montant_ttc"]],
                    }).set_index("Mois")
                    col_g1, col_g2 = st.columns(2)
                    with col_g1:
                        st.bar_chart(df_chart[["Consommation"]])
                    with col_g2:
                        st.bar_chart(df_chart[["Montant TTC"]])

                with st.expander("📋 Historique complet du client"):
                    try:
                        historique = get_historique_client(client_nom)
                        if historique:
                            import pandas as pd
                            df_hist = pd.DataFrame(historique)
                            cols_afficher = [c for c in [
                                "mois_source", "consommation", "unite",
                                "montant_ttc", "usage", "alerte"
                            ] if c in df_hist.columns]
                            df_hist = df_hist[cols_afficher]
                            df_hist.columns = [c.replace("_", " ").title() for c in df_hist.columns]
                            st.dataframe(df_hist, use_container_width=True, hide_index=True)
                            try:
                                df_trend = pd.DataFrame(historique)[["mois_source", "consommation"]].dropna()
                                df_trend = df_trend.set_index("mois_source")
                                st.line_chart(df_trend, height=200)
                            except Exception:
                                pass
                        else:
                            st.info("Aucun historique disponible.")
                    except Exception as e:
                        st.error(f"Erreur historique : {e}")

# ═══════════════════════════════════════════════════════════
#  ONGLET 2 — SURCONSOMMATION (inchangé)
# ═══════════════════════════════════════════════════════════

with tab2:
    st.markdown('<div class="section-header">Détection automatique des anomalies</div>', unsafe_allow_html=True)

    if not clients:
        st.warning("⚠️ Aucune donnée disponible.")
    else:
        col_s, col_btn2 = st.columns([2, 1])
        with col_s:
            seuil = st.slider("Seuil d'alerte (%)", min_value=5, max_value=100,
                              value=20, step=5,
                              help="Déclenche une alerte si la consommation dépasse la moyenne du client de X%")
        with col_btn2:
            st.markdown("<br>", unsafe_allow_html=True)
            btn_detect = st.button("🔍 Lancer la détection", use_container_width=True, type="primary")

        if btn_detect or "detect_result" in st.session_state:

            if btn_detect:
                with st.spinner("Analyse des anomalies en cours..."):
                    anomalies = run_detection_directe(float(seuil))
                st.session_state["detect_result"] = anomalies
                st.session_state["detect_seuil"]  = seuil

            anomalies  = st.session_state.get("detect_result", [])
            seuil_used = st.session_state.get("detect_seuil", seuil)

            if not anomalies:
                st.success(f"✅ Aucune anomalie détectée avec un seuil de {seuil_used}%.")
            else:
                critiques = [a for a in anomalies if a["gravite"] == "critique"]
                elevees   = [a for a in anomalies if a["gravite"] == "élevée"]
                moderees  = [a for a in anomalies if a["gravite"] == "modérée"]

                col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                with col_r1: st.metric("Total anomalies", len(anomalies))
                with col_r2: st.metric("🔴 Critiques (≥50%)", len(critiques))
                with col_r3: st.metric("🟠 Élevées (≥30%)", len(elevees))
                with col_r4: st.metric("🟡 Modérées", len(moderees))

                st.markdown('<div class="section-header">Détail des anomalies</div>', unsafe_allow_html=True)

                for gravite_label, liste, css_class, emoji in [
                    ("Critiques", critiques, "alerte-critique", "🔴"),
                    ("Élevées",   elevees,   "alerte-elevee",  "🟠"),
                    ("Modérées",  moderees,  "alerte-moderee", "🟡"),
                ]:
                    if liste:
                        st.markdown(f"**{emoji} {gravite_label}**")
                        for a in liste:
                            st.markdown(
                                f'<div class="{css_class}">'
                                f'<strong>{a["client"]}</strong> — {a["mois_anomalie"]} &nbsp;|&nbsp; '
                                f'Consommation : <strong>{a["consommation"]:,.0f}</strong> '
                                f'(moy. {a["moyenne_client"]:,.0f}) &nbsp;|&nbsp; '
                                f'Écart : <strong>+{a["ecart_pct"]:.1f}%</strong>'
                                f'</div>',
                                unsafe_allow_html=True
                            )

                st.markdown('<div class="section-header">Graphique des écarts</div>', unsafe_allow_html=True)
                try:
                    import plotly.graph_objects as go
                    import pandas as pd

                    df_a = pd.DataFrame(anomalies)
                    df_a["label"] = df_a["client"] + " (" + df_a["mois_anomalie"] + ")"
                    color_map = {"critique": "#e74c3c", "élevée": "#e67e22", "modérée": "#eab308"}
                    colors = [color_map.get(g, "#718096") for g in df_a["gravite"]]

                    fig_a = go.Figure(go.Bar(
                        x=df_a["label"], y=df_a["ecart_pct"],
                        marker_color=colors,
                        text=[f"+{v:.1f}%" for v in df_a["ecart_pct"]],
                        textposition="outside",
                    ))
                    fig_a.update_layout(
                        title="Anomalies — Écart par rapport à la moyenne client (%)",
                        xaxis_tickangle=-35, height=400,
                        plot_bgcolor="white", paper_bgcolor="white",
                        yaxis=dict(title="Écart (%)", gridcolor="#eee"),
                        margin=dict(t=50, b=120, l=50, r=20),
                    )
                    fig_a.add_hline(y=seuil_used, line_dash="dot", line_color="#1a3c5e",
                                    annotation_text=f"Seuil {seuil_used}%")
                    st.plotly_chart(fig_a, use_container_width=True)

                except ImportError:
                    import pandas as pd
                    df_a = pd.DataFrame(anomalies)[["client", "mois_anomalie", "ecart_pct"]]
                    st.dataframe(df_a, use_container_width=True, hide_index=True)

                with st.expander("📋 Tableau complet des anomalies"):
                    import pandas as pd
                    df_export = pd.DataFrame(anomalies)
                    st.dataframe(df_export, use_container_width=True, hide_index=True)
                    csv = df_export.to_csv(index=False).encode("utf-8")
                    st.download_button("⬇️ Télécharger CSV", data=csv,
                                       file_name=f"anomalies_seuil{seuil_used}pct.csv",
                                       mime="text/csv")

# ═══════════════════════════════════════════════════════════
#  ONGLET 3 — VUE GLOBALE (inchangé)
# ═══════════════════════════════════════════════════════════

with tab3:
    st.markdown('<div class="section-header">Statistiques globales & Comparaison tous clients</div>', unsafe_allow_html=True)

    if not clients:
        st.warning("⚠️ Aucune donnée disponible.")
    else:
        try:
            stats = get_stats_globales()
            col1, col2, col3, col4 = st.columns(4)
            with col1: st.metric("👥 Clients", stats["nb_clients"])
            with col2: st.metric("📅 Périodes", stats["nb_periodes"])
            with col3: st.metric("🧾 Factures", stats["nb_factures"])
            with col4: st.metric("💰 Montant total TTC", f"{stats['montant_total_ttc']:,.0f} Dhs")

            col5, col6, col7 = st.columns(3)
            with col5:
                if stats.get("client_plus_gros_consommateur"):
                    c = stats["client_plus_gros_consommateur"]
                    st.metric("📈 Plus gros consommateur", c["client"], f"{c['total_conso']:,.0f}")
            with col6:
                if stats.get("client_plus_petit_consommateur"):
                    c = stats["client_plus_petit_consommateur"]
                    st.metric("📉 Plus petit consommateur", c["client"], f"{c['total_conso']:,.0f}")
            with col7:
                if stats.get("periode_la_plus_chargee"):
                    p = stats["periode_la_plus_chargee"]
                    st.metric("📅 Période la plus chargée", p["mois"], f"{p['total_conso']:,.0f}")

        except Exception as e:
            st.error(f"Erreur stats : {e}")

        st.markdown('<div class="section-header">Comparaison tous clients — deux mois</div>', unsafe_allow_html=True)

        if len(periodes) >= 2:
            col_g1, col_g2, col_gbtn = st.columns([2, 2, 1])
            with col_g1:
                glob_m1 = st.selectbox("Mois 1", periodes, index=max(0, len(periodes) - 2), key="glob_m1")
            with col_g2:
                glob_m2 = st.selectbox("Mois 2", periodes, index=len(periodes) - 1, key="glob_m2")
            with col_gbtn:
                st.markdown("<br>", unsafe_allow_html=True)
                btn_glob = st.button("🔍 Comparer", key="btn_glob", use_container_width=True, type="primary")

            if btn_glob or "glob_result" in st.session_state:
                if btn_glob:
                    with st.spinner("Comparaison en cours..."):
                        glob_res = run_comparaison_globale(glob_m1, glob_m2)
                    st.session_state["glob_result"] = glob_res
                    st.session_state["glob_params"] = (glob_m1, glob_m2)

                glob_res = st.session_state.get("glob_result", [])
                glob_p   = st.session_state.get("glob_params", (glob_m1, glob_m2))

                if glob_res:
                    import pandas as pd

                    en_hausse = [r for r in glob_res if r.get("tendance") == "hausse"]
                    en_baisse = [r for r in glob_res if r.get("tendance") == "baisse"]
                    alertes   = [r for r in glob_res if r.get("alerte")]

                    col_r1, col_r2, col_r3 = st.columns(3)
                    with col_r1: st.metric("📈 En hausse", len(en_hausse))
                    with col_r2: st.metric("📉 En baisse", len(en_baisse))
                    with col_r3: st.metric("🔴 Alertes (>20%)", len(alertes))

                    try:
                        import plotly.graph_objects as go

                        df_g = pd.DataFrame([{
                            "Client":    r["client"],
                            "Variation": r.get("pct_conso", 0) or 0,
                            "Tendance":  r.get("tendance", "stable"),
                        } for r in glob_res if r.get("pct_conso") is not None])

                        if not df_g.empty:
                            df_g = df_g.sort_values("Variation", ascending=False)
                            colors = [
                                "#e74c3c" if v > 20 else "#e67e22" if v > 0 else "#2ecc71"
                                for v in df_g["Variation"]
                            ]
                            fig_g = go.Figure(go.Bar(
                                x=df_g["Client"], y=df_g["Variation"],
                                marker_color=colors,
                                text=[f"{v:+.1f}%" for v in df_g["Variation"]],
                                textposition="outside",
                            ))
                            fig_g.update_layout(
                                title=f"Variation de consommation — {glob_p[0]} vs {glob_p[1]}",
                                xaxis_tickangle=-35, height=420,
                                plot_bgcolor="white", paper_bgcolor="white",
                                yaxis=dict(title="Variation (%)", gridcolor="#eee", zeroline=True),
                                margin=dict(t=50, b=140, l=50, r=20),
                            )
                            fig_g.add_hline(y=0, line_color="#718096", line_width=1)
                            fig_g.add_hline(y=20, line_dash="dot", line_color="#e74c3c",
                                            annotation_text="Seuil alerte 20%")
                            st.plotly_chart(fig_g, use_container_width=True)

                    except ImportError:
                        pass

                    with st.expander("📋 Tableau détaillé"):
                        rows = []
                        for r in glob_res:
                            rows.append({
                                "Client":        r.get("client", ""),
                                "Conso Mois 1":  r["mois_1"]["consommation"],
                                "Conso Mois 2":  r["mois_2"]["consommation"],
                                "Variation (%)": r.get("pct_conso"),
                                "Delta Conso":   r.get("delta_conso"),
                                "Delta Montant": r.get("delta_montant"),
                                "Tendance":      r.get("tendance"),
                                "Alerte":        "🔴" if r.get("alerte") else "",
                            })
                        df_tab = pd.DataFrame(rows)
                        st.dataframe(df_tab, use_container_width=True, hide_index=True)
                        csv = df_tab.to_csv(index=False).encode("utf-8")
                        st.download_button("⬇️ Télécharger CSV", data=csv,
                                           file_name=f"comparaison_{glob_p[0]}_{glob_p[1]}.csv",
                                           mime="text/csv")
                else:
                    st.info("Aucun résultat disponible pour ces deux mois.")

# ═══════════════════════════════════════════════════════════
#  ONGLET 4 — AGENT IA (complètement refait)
# ═══════════════════════════════════════════════════════════

with tab4:
    st.markdown('<div class="section-header">Agent IA — Analyse intelligente</div>', unsafe_allow_html=True)

    if not clients:
        st.warning("⚠️ Aucune donnée disponible.")
    else:

        # ── Capacités de l'agent ──
        with st.expander("💡 Ce que l'agent peut faire pour vous", expanded=False):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("""
**📋 Rapports narratifs**
- *"Génère le rapport de janvier"*
- *"Bilan du mois dernier"*
- *"Rapport complet pour le client Dupont"*

**⚠️ Analyse des risques**
- *"Quels clients sont les plus à risque ?"*
- *"Y a-t-il des anomalies critiques ?"*
- *"Qui dépasse le seuil de 30% ?"*
""")
            with col_b:
                st.markdown("""
**🌍 Synthèse globale**
- *"Résume la situation de mes clients"*
- *"Vue d'ensemble de la consommation"*
- *"Quelles sont les tendances générales ?"*

**💡 Conseils personnalisés**
- *"Que faire pour le client Martin ?"*
- *"Recommandations pour réduire les risques"*
- *"Analyse l'historique de Dupont"*
""")

        # ── Suggestions rapides ──
        st.markdown("**Suggestions rapides :**")

        suggestions = [
            "📋 Rapport du dernier mois",
            "⚠️ Clients les plus à risque",
            "🌍 Résumé de la situation globale",
            "💡 Conseils pour réduire les anomalies",
        ]

        cols_sug = st.columns(len(suggestions))
        for i, (col, sug) in enumerate(zip(cols_sug, suggestions)):
            with col:
                if st.button(sug, key=f"sug_{i}", use_container_width=True):
                    st.session_state.question_suggeree = sug

        st.markdown("---")

        # ── Historique du chat ──
        for msg in st.session_state.chat_messages:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.write(msg["content"])
            else:
                with st.chat_message("assistant"):

                    # Badge intention détectée
                    if msg.get("intention"):
                        labels = {
                            "rapport":     "📋 Rapport mensuel",
                            "risque":      "⚠️ Analyse des risques",
                            "global":      "🌍 Synthèse globale",
                            "conseil":     "💡 Conseils",
                            "comparaison": "📊 Comparaison",
                            "historique":  "📈 Historique client",
                        }
                        label = labels.get(msg["intention"].get("type", ""), "🤖 Analyse")
                        st.markdown(
                            f'<span class="intention-badge">{label}</span>',
                            unsafe_allow_html=True
                        )

                    # Réponse principale
                    st.write(msg["content"])

                    # Données utilisées (expander)
                    if msg.get("outils"):
                        with st.expander(f"🔧 Données utilisées ({len(msg['outils'])} sources)"):
                            for o in msg["outils"]:
                                st.caption(f"**{o['outil']}**")
                                if isinstance(o["resultat"], list):
                                    st.caption(f"{len(o['resultat'])} enregistrements récupérés")
                                elif isinstance(o["resultat"], dict):
                                    st.caption(f"{len(o['resultat'])} champs récupérés")

        # ── Bouton effacer ──
        if st.session_state.chat_messages:
            col_reset, col_empty = st.columns([1, 4])
            with col_reset:
                if st.button("🗑️ Effacer", key="btn_reset_chat"):
                    st.session_state.chat_messages   = []
                    st.session_state.chat_historique = []
                    st.session_state.question_suggeree = ""
                    st.rerun()

        # ── Input utilisateur ──
        # Utiliser la suggestion si cliquée
        valeur_defaut = st.session_state.question_suggeree
        if valeur_defaut:
            st.session_state.question_suggeree = ""

        question = st.chat_input("Posez votre question à l'agent IA...")

        # Prendre la suggestion ou la saisie manuelle
        question_finale = valeur_defaut if valeur_defaut and not question else question

        if question_finale:
            # Afficher le message utilisateur
            with st.chat_message("user"):
                st.write(question_finale)
            st.session_state.chat_messages.append({
                "role": "user", "content": question_finale
            })

            # Appel à l'agent
            with st.chat_message("assistant"):
                with st.spinner("🤖 L'agent analyse et collecte les données..."):
                    try:
                        result = run_agent(
                            question_finale,
                            st.session_state.chat_historique
                        )
                        reponse    = result.get("reponse", "Désolé, je n'ai pas pu répondre.")
                        outils_app = result.get("outils_appeles", [])
                        intention  = result.get("intention", {})
                        st.session_state.chat_historique = result.get("messages", [])

                    except Exception as e:
                        reponse    = f"❌ Erreur agent : {str(e)}"
                        outils_app = []
                        intention  = {}

                # Badge intention
                if intention:
                    labels = {
                        "rapport":     "📋 Rapport mensuel",
                        "risque":      "⚠️ Analyse des risques",
                        "global":      "🌍 Synthèse globale",
                        "conseil":     "💡 Conseils",
                        "comparaison": "📊 Comparaison",
                        "historique":  "📈 Historique client",
                    }
                    label = labels.get(intention.get("type", ""), "🤖 Analyse")
                    st.markdown(
                        f'<span class="intention-badge">{label}</span>',
                        unsafe_allow_html=True
                    )

                # Réponse
                st.write(reponse)

                # Données utilisées
                if outils_app:
                    with st.expander(f"🔧 Données utilisées ({len(outils_app)} sources)"):
                        for o in outils_app:
                            st.caption(f"**{o['outil']}**")
                            if isinstance(o["resultat"], list):
                                st.caption(f"{len(o['resultat'])} enregistrements récupérés")
                            elif isinstance(o["resultat"], dict):
                                st.caption(f"{len(o['resultat'])} champs récupérés")

            # Sauvegarder dans l'historique
            st.session_state.chat_messages.append({
                "role":      "assistant",
                "content":   reponse,
                "outils":    outils_app,
                "intention": intention,
            })