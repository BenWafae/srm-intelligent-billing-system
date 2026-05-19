// Gestionnaire de traductions SRM (Client + Employé)
const i18n = {
    currentLang: 'fr',
    translations: {},
    
    async init() {
        const savedLang = localStorage.getItem('srm_lang');
        const browserLang = navigator.language.split('-')[0];
        const defaultLang = 'fr';
        
        let lang = savedLang || browserLang;
        if (!['fr', 'en', 'ar'].includes(lang)) lang = defaultLang;
        
        await this.loadLanguage(lang);
        this.applyTranslations();
        this.supprimerMenuAutomatique();
    },
    
    supprimerMenuAutomatique() {
        const oldMenu = document.querySelector('.lang-menu-btn');
        if (oldMenu) {
            const parent = oldMenu.closest('div');
            if (parent) parent.remove();
        }
        const langDropdown = document.getElementById('lang-dropdown');
        if (langDropdown) langDropdown.remove();
    },
    
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
    
    t(key, params = {}) {
        let text = this.translations[key] || key;
        for (const [k, v] of Object.entries(params)) {
            text = text.replace(new RegExp(`{{${k}}}`, 'g'), v);
        }
        return text;
    },
    
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
        
        this.translateEmployeeInterface();
        this.translateConversationDates();
        this.translateDaysBadge();
        this.translateSidebarFilters();
    },
    
    translateSidebarFilters() {
        const allBtn = document.getElementById('sb-all');
        if (allBtn && allBtn.textContent === 'Tout') allBtn.textContent = this.t('filter_all');
        
        const excelBtn = document.getElementById('sb-excel');
        if (excelBtn && excelBtn.textContent === 'Excel') excelBtn.textContent = this.t('filter_excel');
        
        const pdfBtn = document.getElementById('sb-pdf');
        if (pdfBtn && pdfBtn.textContent === 'PDF') pdfBtn.textContent = this.t('filter_pdf');
        
        const recentLabel = document.querySelector('.conv-list > p:first-child');
        if (recentLabel && recentLabel.textContent === 'Récentes') {
            recentLabel.innerHTML = this.t('recent');
        }
    },
    
    translateEmployeeInterface() {
        const btnExcel = document.getElementById('btn-excel');
        if (btnExcel && btnExcel.textContent.includes('Base clients Excel')) {
            btnExcel.innerHTML = `📊 ${this.t('excel_tab')}`;
        }
        
        const btnPdf = document.getElementById('btn-pdf');
        if (btnPdf && btnPdf.textContent.includes('Analyse facture PDF')) {
            btnPdf.innerHTML = `📄 ${this.t('pdf_tab')}`;
        }
        
        document.querySelectorAll('.badge-excel').forEach(badge => {
            if (badge.textContent === 'XLS') badge.textContent = this.t('badge_excel');
        });
        document.querySelectorAll('.badge-pdf').forEach(badge => {
            if (badge.textContent === 'PDF') badge.textContent = this.t('badge_pdf');
        });
        
        const excelWelcomeTitle = document.querySelector('#chat-excel .welcome-title');
        if (excelWelcomeTitle && excelWelcomeTitle.textContent.includes('Bonjour')) {
            const name = document.querySelector('.user-name')?.textContent.split(' ')[0] || 'Employé';
            excelWelcomeTitle.innerHTML = this.t('welcome_title_employee', { name: name });
        }
        
        const excelWelcomeSub = document.querySelector('#chat-excel .welcome-sub');
        if (excelWelcomeSub && excelWelcomeSub.textContent.includes('Posez une question')) {
            excelWelcomeSub.innerHTML = this.t('welcome_sub_excel');
        }
        
        const pdfWelcomeTitle = document.querySelector('#chat-pdf .welcome-title');
        if (pdfWelcomeTitle && pdfWelcomeTitle.textContent === 'Analyse PDF') {
            pdfWelcomeTitle.innerHTML = this.t('pdf_welcome_title');
        }
        
        const pdfWelcomeSub = document.querySelector('#chat-pdf .welcome-sub');
        if (pdfWelcomeSub && pdfWelcomeSub.textContent.includes('Sélectionnez un client')) {
            pdfWelcomeSub.innerHTML = this.t('pdf_welcome_sub');
        }
        
        const filterLabel = document.querySelector('.filter-label');
        if (filterLabel && filterLabel.textContent === 'Fichier source') {
            filterLabel.innerHTML = this.t('filter_label');
        }
        
        const clientLabel = document.querySelector('#onglet-pdf .filter-label');
        if (clientLabel && clientLabel.textContent === 'Client concerné') {
            clientLabel.innerHTML = this.t('client_label');
        }
        
        const inputExcel = document.getElementById('input-excel');
        if (inputExcel && inputExcel.placeholder === 'Ex: Qui consomme le plus ? Liste des clients...') {
            inputExcel.placeholder = this.t('excel_placeholder');
        }
        
        const inputPdf = document.getElementById('input-pdf');
        if (inputPdf && inputPdf.placeholder === 'Ex: Quel est le montant ? Quelle est la période ?') {
            inputPdf.placeholder = this.t('pdf_placeholder');
        }
        
        const selectFichier = document.getElementById('select-fichier');
        if (selectFichier && selectFichier.options[0] && selectFichier.options[0].text === '📂 Tous les fichiers') {
            selectFichier.options[0].text = `📂 ${this.t('all_files')}`;
        }
        
        const labelFichier = document.getElementById('label-fichier');
        if (labelFichier && labelFichier.innerHTML === '🌐 Toute la base') {
            labelFichier.innerHTML = `🌐 ${this.t('all_database')}`;
        }
        
        const userRole = document.querySelector('.user-role');
        if (userRole && userRole.textContent === 'Employé SRM') {
            userRole.innerHTML = this.t('employee_role');
        }
        
        const bannerText = document.querySelector('.info-banner span:first-child');
        if (bannerText && bannerText.textContent === 'Base de données active') {
            bannerText.innerHTML = this.t('database_active');
        }
        
        const statLabels = document.querySelectorAll('.info-banner-stat');
        statLabels.forEach(stat => {
            let text = stat.textContent;
            if (text.includes('factures') && !text.includes(this.t('invoices'))) {
                stat.innerHTML = text.replace('factures', this.t('invoices'));
            } else if (text.includes('clients') && !text.includes(this.t('clients'))) {
                stat.innerHTML = text.replace('clients', this.t('clients'));
            } else if (text.includes('périodes') && !text.includes(this.t('periods'))) {
                stat.innerHTML = text.replace('périodes', this.t('periods'));
            }
        });
    },
    
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
    
    async switchTo(lang) {
        if (lang === this.currentLang) return;
        await this.loadLanguage(lang);
        this.applyTranslations();
        this.updateDynamicContent();
        if (typeof window.updateRenameDeleteTexts === 'function') {
            window.updateRenameDeleteTexts();
        }
        // ✅ Rafraîchir les dates
        this.refreshAllDates();
        
        document.querySelectorAll('.lang-option').forEach(opt => {
            opt.classList.remove('active');
            if ((lang === 'fr' && opt.textContent.includes('Français')) ||
                (lang === 'en' && opt.textContent.includes('English')) ||
                (lang === 'ar' && opt.textContent.includes('العربية'))) {
                opt.classList.add('active');
            }
        });
    },
    
    // ✅ FONCTION pour rafraîchir toutes les dates (à l'intérieur de l'objet)
    refreshAllDates() {
        const dateElements = document.querySelectorAll('.conv-date');
        dateElements.forEach(el => {
            const originalDate = el.getAttribute('data-original-date');
            if (originalDate && typeof window.formaterDate === 'function') {
                const newFormatted = window.formaterDate(originalDate);
                if (newFormatted !== el.textContent) {
                    el.textContent = newFormatted;
                }
            }
        });
    }
};

// ✅ Initialisation
document.addEventListener('DOMContentLoaded', () => i18n.init());