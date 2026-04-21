# src/rag_general.py
# Ce fichier est conservé UNIQUEMENT pour ne pas casser les imports existants.
# Toute la logique est dans src/rag/

from rag.dispatcher import repondre_question_generale, repondre_question_client

__all__ = ["repondre_question_generale", "repondre_question_client"]