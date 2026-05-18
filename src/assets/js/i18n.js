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
        // SUPPRIME LE MENU AUTOMATIQUE S'IL EXISTE DANS LE HTML
        this.supprimerMenuAutomatique();
    },
    
    // NOUVELLE FONCTION : Supprime le menu ajouté automatiquement
    supprimerMenuAutomatique() {
        // Supprimer le menu avec l'icône globe qui est ajouté par l'ancien script
        const oldMenu = document.querySelector('.lang-menu-btn');
        if (oldMenu) {
            const parent = oldMenu.closest('div');
            if (parent) parent.remove();
        }
        
        // Supprimer tout élément qui pourrait être un menu de langue flottant
        const langDropdown = document.getElementById('lang-dropdown');
        if (langDropdown) langDropdown.remove();
        
        // Supprimer les conteneurs de menu supplémentaires
        const menuContainers = document.querySelectorAll('.sidebar-footer > div:not(.user-card):not(#userMenuDropdown)');
        menuContainers.forEach(container => {
            if (container.innerHTML.includes('lang') || container.innerHTML.includes('globe')) {
                container.remove();
            }
        });
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
    
    // Changer de langue (appelé par votre menu HTML)
    async switchTo(lang) {
        if (lang === this.currentLang) return;
        await this.loadLanguage(lang);
        this.applyTranslations();
        this.updateDynamicContent();
        if (typeof window.updateRenameDeleteTexts === 'function') {
            window.updateRenameDeleteTexts();
        }
        // Mettre à jour la classe active dans le sous-menu
        document.querySelectorAll('.lang-option').forEach(opt => {
            opt.classList.remove('active');
            if ((lang === 'fr' && opt.textContent.includes('Français')) ||
                (lang === 'en' && opt.textContent.includes('English')) ||
                (lang === 'ar' && opt.textContent.includes('العربية'))) {
                opt.classList.add('active');
            }
        });
    }
};

// Initialisation au chargement
document.addEventListener('DOMContentLoaded', () => i18n.init());