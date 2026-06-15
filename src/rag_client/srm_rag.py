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
# FONCTION DE RETRIEVAL
# ════════════════════════════════════════════
def rechercher_chunks(question: str, top_k: int = 2) -> str:
    """
    Reçoit une question, retourne les top_k chunks
    les plus pertinents sous forme de texte concaténé.
    """
    q_embedding = _modele.encode([question], normalize_embeddings=True)
    scores = np.dot(_embeddings_chunks, q_embedding.T).flatten()
    indices = np.argsort(scores)[::-1][:top_k]

    chunks_selectionnes = [SRM_CHUNKS[i]["texte"] for i in indices]
    return "\n\n".join(chunks_selectionnes)