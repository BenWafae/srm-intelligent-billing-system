// Gestionnaire de traductions SRM Client
const i18n = {
    currentLang: 'fr',
    translations: {},
    
    // Initialiser le système
    async init() {
        const savedLang = localStorage.getItem('srm_lang');
        const browserLang = navigator.language.split('-')[0];
        const defaultLang = 'fr';
        
        let lang = savedLang || browserLang;
        if (!['fr', 'en', 'ar'].includes(lang)) lang = defaultLang;
        
        await this.loadLanguage(lang);
        this.applyTranslations();
        this.setupLanguageSwitcher();
    },
    
    // Charger un fichier de langue
    async loadLanguage(lang) {
        try {
            const response = await fetch(`/static/locales/${lang}.js`);
            const scriptText = await response.text();
            const match = scriptText.match(/const translations = ({[\s\S]*?});/);
            if (match) {
                const translationsObj = eval('(' + match[1] + ')');
                this.translations = translationsObj;
                this.currentLang = lang;
                localStorage.setItem('srm_lang', lang);
                document.documentElement.lang = lang;
                if (lang === 'ar') {
                    document.body.style.direction = 'rtl';
                    document.body.style.textAlign = 'right';
                    document.body.classList.add('rtl');
                } else {
                    document.body.style.direction = 'ltr';
                    document.body.style.textAlign = 'left';
                    document.body.classList.remove('rtl');
                }
            }
        } catch (error) {
            console.error('Erreur chargement langue:', error);
            if (lang !== 'fr') await this.loadLanguage('fr');
        }
    },
    
    // Traduire un texte par sa clé
    t(key, params = {}) {
        let text = this.translations[key] || key;
        for (const [k, v] of Object.entries(params)) {
            text = text.replace(new RegExp(`{{${k}}}`, 'g'), v);
        }
        return text;
    },
    
    // Appliquer toutes les traductions dans la page
    applyTranslations() {
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            let params = {};
            
            if (key === 'welcome_title') {
                const nameAttr = el.getAttribute('data-name');
                if (nameAttr && nameAttr !== '') {
                    params = { name: nameAttr };
                }
            }
            
            if (key === 'days_left') {
                const days = el.getAttribute('data-days');
                if (days && days !== '—') {
                    params = { days: days };
                }
            }
            
            if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                el.placeholder = this.t(key, params);
            } else {
                el.innerHTML = this.t(key, params);
            }
        });
        
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            el.placeholder = this.t(key);
        });
        
        this.translateConversationDates();
        this.translateDaysBadge();
    },
    
    // Traduire les dates des conversations
    translateConversationDates() {
        const dateElements = document.querySelectorAll('.conv-date');
        dateElements.forEach(el => {
            const originalText = el.getAttribute('data-original-date') || el.textContent;
            if (!el.getAttribute('data-original-date')) {
                el.setAttribute('data-original-date', originalText);
            }
            
            let translated = originalText;
            if (this.currentLang === 'en') {
                translated = originalText
                    .replace("Aujourd'hui", "Today")
                    .replace("Hier", "Yesterday")
                    .replace(/Il y a (\d+) jours/, "$1 days ago");
            } else if (this.currentLang === 'ar') {
                translated = originalText
                    .replace("Aujourd'hui", "اليوم")
                    .replace("Hier", "أمس")
                    .replace(/Il y a (\d+) jours/, "قبل $1 أيام");
            }
            el.textContent = translated;
        });
    },
    
    // Traduire le badge
    translateDaysBadge() {
        const badgeSpan = document.querySelector('.dash-badge span[data-i18n="days_left"]');
        if (badgeSpan) {
            const days = badgeSpan.getAttribute('data-days');
            if (days && days !== '—') {
                if (this.currentLang === 'en') {
                    badgeSpan.innerHTML = `in ${days} days`;
                } else if (this.currentLang === 'ar') {
                    badgeSpan.innerHTML = `خلال ${days} أيام`;
                } else {
                    badgeSpan.innerHTML = `dans ${days} jours`;
                }
            }
        }
    },
    
    // Mettre à jour le contenu dynamique
    updateDynamicContent() {
        const welcomeTitle = document.querySelector('.welcome-title');
        if (welcomeTitle) {
            const nameSpan = document.querySelector('.user-name');
            let name = '';
            if (nameSpan) {
                name = nameSpan.textContent.split(' ')[0];
            }
            welcomeTitle.setAttribute('data-name', name);
            welcomeTitle.innerHTML = this.t('welcome_title', { name: name });
        }
        
        const suggestions = document.querySelectorAll('.suggestion-chip');
        const suggestionKeys = ['suggestion_invoice', 'suggestion_consumption_month', 'suggestion_consumption_total', 'suggestion_complaint'];
        suggestions.forEach((chip, idx) => {
            if (suggestionKeys[idx]) {
                chip.innerHTML = this.t(suggestionKeys[idx]);
            }
        });
        
        const questionInput = document.getElementById('question-input');
        if (questionInput) questionInput.placeholder = this.t('question_placeholder');
        
        const selectMois = document.getElementById('select-mois');
        if (selectMois && selectMois.options[0]) {
            selectMois.options[0].text = this.t('choose_month');
        }
        
        const modalTitle = document.querySelector('#modal-compte h3');
        if (modalTitle) modalTitle.innerHTML = this.t('my_account');
        
        const modalSub = document.querySelector('#modal-compte .modal-header p');
        if (modalSub) modalSub.innerHTML = this.t('account_subtitle');
        
        const pwdLabel = document.querySelector('#modal-compte .form-label');
        if (pwdLabel) pwdLabel.innerHTML = this.t('change_password');
        
        const ancienInput = document.getElementById('ancien-mdp');
        if (ancienInput) ancienInput.placeholder = this.t('current_password');
        
        const nouveauInput = document.getElementById('nouveau-mdp');
        if (nouveauInput) nouveauInput.placeholder = this.t('new_password');
        
        const confirmationInput = document.getElementById('confirmation-mdp');
        if (confirmationInput) confirmationInput.placeholder = this.t('confirm_password');
        
        const saveBtn = document.querySelector('#modal-compte .btn-primary');
        if (saveBtn) saveBtn.innerHTML = this.t('save');
        
        const closeBtn = document.querySelector('#modal-compte .btn-secondary');
        if (closeBtn) closeBtn.innerHTML = this.t('close');
        
        const successMsg = document.getElementById('success-msg');
        if (successMsg) successMsg.innerHTML = this.t('password_changed');
    },
    
    // Changer de langue
    async switchTo(lang) {
        if (lang === this.currentLang) return;
        await this.loadLanguage(lang);
        this.applyTranslations();
        this.updateDynamicContent();
        if (typeof window.updateRenameDeleteTexts === 'function') {
            window.updateRenameDeleteTexts();
        }
    },
    
    // Configurer le sélecteur de langue
    setupLanguageSwitcher() {
        const userCard = document.querySelector('.user-card');
        if (!userCard) return;
        if (document.querySelector('.lang-menu-btn')) return;
        
        const menuContainer = document.createElement('div');
        menuContainer.style.position = 'relative';
        menuContainer.style.marginLeft = 'auto';
        
        menuContainer.innerHTML = `
            <button class="lang-menu-btn" onclick="toggleLangMenu(event)" 
                style="width:28px;height:28px;border-radius:8px;background:none;border:none;cursor:pointer;
                       color:#c4b5fd;display:flex;align-items:center;justify-content:center;transition:all 0.15s;"
                onmouseover="this.style.background='#f5f3ff';this.style.color='#7c3aed'"
                onmouseout="this.style.background='none';this.style.color='#c4b5fd'">
                <svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                    <path d="M3 12h18M12 3v18M12 3a9 9 0 0 0 9 9M12 3a9 9 0 0 1 9 9M12 21a9 9 0 0 1-9-9M12 21a9 9 0 0 0 9-9"/>
                </svg>
            </button>
            <div id="lang-dropdown" class="lang-dropdown" style="display:none;position:absolute;bottom:45px;right:0;background:white;border:1px solid #ede9fe;border-radius:12px;padding:6px;z-index:100;min-width:140px;box-shadow:0 8px 24px rgba(109,40,217,0.12);">
                <div class="lang-option" data-lang="fr" style="display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:8px;cursor:pointer;font-size:13px;color:#374151;">
                    <span>🇫🇷</span> Français
                </div>
                <div class="lang-option" data-lang="en" style="display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:8px;cursor:pointer;font-size:13px;color:#374151;">
                    <span>🇬🇧</span> English
                </div>
                <div class="lang-option" data-lang="ar" style="display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:8px;cursor:pointer;font-size:13px;color:#374151;">
                    <span>🇲🇦</span> العربية
                </div>
                <div style="height:1px;background:#f3f0ff;margin:4px 0;"></div>
                <div class="lang-option" onclick="ouvrirCompte()" style="display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:8px;cursor:pointer;font-size:13px;color:#374151;">
                    <span>👤</span> <span>Mon compte</span>
                </div>
                <div class="lang-option" onclick="window.location.href='/logout'" style="display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:8px;cursor:pointer;font-size:13px;color:#ef4444;">
                    <span>🚪</span> <span>Déconnexion</span>
                </div>
            </div>
        `;
        
        userCard.appendChild(menuContainer);
        
        document.querySelectorAll('.lang-option[data-lang]').forEach(opt => {
            opt.addEventListener('click', (e) => {
                e.stopPropagation();
                const lang = opt.getAttribute('data-lang');
                i18n.switchTo(lang);
                document.getElementById('lang-dropdown').style.display = 'none';
            });
        });
    }
};

// Toggle menu langue
function toggleLangMenu(event) {
    event.stopPropagation();
    const dropdown = document.getElementById('lang-dropdown');
    if (dropdown) {
        const isOpen = dropdown.style.display === 'flex';
        dropdown.style.display = isOpen ? 'none' : 'flex';
        dropdown.style.flexDirection = 'column';
    }
}

document.addEventListener('click', () => {
    const dropdown = document.getElementById('lang-dropdown');
    if (dropdown) dropdown.style.display = 'none';
});

document.addEventListener('DOMContentLoaded', () => i18n.init());