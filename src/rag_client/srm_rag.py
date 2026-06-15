# ════════════════════════════════════════════
# RAG — MOTEUR DE RETRIEVAL SÉMANTIQUE
# Base de connaissance SRM Souss-Massa
# Embeddings : paraphrase-multilingual-MiniLM-L12-v2
# ════════════════════════════════════════════

import numpy as np
from sentence_transformers import SentenceTransformer
from rag_client.srm_chunks import SRM_CHUNKS

# ── Chargement du modèle (une seule fois au démarrage) ──
print("[RAG] Chargement du modèle d'embedding...")
_modele = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# ── Indexation des chunks (une seule fois au démarrage) ──
_textes_chunks = [c["theme"] + " " + c["texte"] for c in SRM_CHUNKS]
_embeddings_chunks = _modele.encode(_textes_chunks, normalize_embeddings=True)
print(f"[RAG] {len(SRM_CHUNKS)} chunks indexés.")


# ════════════════════════════════════════════
# FILTRAGE PAR INTENTION (post-retrieval)
# ════════════════════════════════════════════

def _filtrer_par_intention(question: str, chunks_texte: str) -> str:
    """
    Filtre les chunks pour ne garder que ceux qui correspondent à l'intention de la question.
    Ne supprime rien si l'intention n'est pas clairement détectée.
    """
    q = question.lower()
    
    # Détection de l'intention
    est_recrutement = any(mot in q for mot in [
        "travail", "emploi", "recrutement", "poste", "travailler", 
        "ingenieur", "cadre", "technicien", "bghit nkhdem"
    ])
    est_stage = any(mot in q for mot in [
        "stage", "stagiaire", "etudiant", "convention", "bghit ndir stage"
    ])
    est_abonnement = any(mot in q for mot in [
        "abonnement", "abonner", "devenir client", "ouvrir compte", "s abonner"
    ])
    est_branchement = any(mot in q for mot in [
        "branchement", "raccordement", "construction neuve", "nouveau branchement"
    ])
    est_eau = "eau" in q and not any(mot in q for mot in ["electricite", "electrique"])
    est_electricite = any(mot in q for mot in ["electricite", "electrique"])
    
    # Si aucune intention claire, retourner tout le contexte
    if not any([est_recrutement, est_stage, est_abonnement, est_branchement, est_eau, est_electricite]):
        return chunks_texte
    
    # Découper les chunks (séparés par \n\n)
    chunks = chunks_texte.split("\n\n")
    chunks_filtres = []
    
    for chunk in chunks:
        chunk_lower = chunk.lower()
        
        # Règle 1 : Recrutement vs Stage
        if est_recrutement and ("stage" in chunk_lower or "stagiaire" in chunk_lower):
            continue  # exclure stage
        if est_stage and ("recrutement" in chunk_lower or "emploi" in chunk_lower):
            continue  # exclure recrutement
            
        # Règle 2 : Abonnement vs Branchement
        if est_abonnement and "branchement" in chunk_lower:
            continue  # exclure branchement
        if est_branchement and "abonnement" in chunk_lower:
            continue  # exclure abonnement
            
        # Règle 3 : Eau uniquement → exclure électricité
        if est_eau and ("electricite" in chunk_lower or "electrique" in chunk_lower):
            continue
            
        # Règle 4 : Électricité uniquement → exclure eau
        if est_electricite and "eau" in chunk_lower and "assainissement" not in chunk_lower:
            continue
            
        # Sinon, garder le chunk
        chunks_filtres.append(chunk)
    
    # Si après filtrage il ne reste rien, retourner l'original
    if not chunks_filtres:
        return chunks_texte
    
    return "\n\n".join(chunks_filtres)


# ════════════════════════════════════════════
# FONCTION DE RETRIEVAL
# ════════════════════════════════════════════

def rechercher_chunks(question: str, top_k: int = 2) -> str:
    """
    Reçoit une question, retourne les top_k chunks les plus pertinents,
    filtrés par intention pour éviter les mélanges (stage/emploi, eau/électricité, etc.)
    """
    q_embedding = _modele.encode([question], normalize_embeddings=True)
    scores = np.dot(_embeddings_chunks, q_embedding.T).flatten()
    indices = np.argsort(scores)[::-1][:top_k]

    chunks_selectionnes = [SRM_CHUNKS[i]["texte"] for i in indices]
    contexte_brut = "\n\n".join(chunks_selectionnes)
    
    # Filtrage par intention
    contexte_filtre = _filtrer_par_intention(question, contexte_brut)
    
    return contexte_filtre