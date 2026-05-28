# init_admin.py
from src.database import init_db, creer_user

# Initialiser la base de données
init_db()

# Créer le compte admin par défaut
succes = creer_user(
    email="admin@srm.ma",
    password="admin123",
    role="admin"
)

if succes:
    print("✅ Compte admin créé avec succès")
    print("📧 Email    : admin@srm.ma")
    print("🔑 Password : admin123")
    print("⚠️  Changez le mot de passe après connexion !")
else:
    print("ℹ️  Compte admin existe déjà")