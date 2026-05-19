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
        // Traduire les éléments avec data-i18n
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            let params = {};
            
            if (key === 'welcome_title') {
                const nameAttr = el.getAttribute('data-name');
                if (nameAttr && nameAttr !== '') {
                    params = { name: nameAttr };
                }
            }
            
            if (key === 'welcome_title_employee') {
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
            } else if (el.tagName === 'BUTTON' && key === 'new_conversation') {
                // Gérer le bouton nouvelle conversation qui a un SVG à l'intérieur
                const svg = el.querySelector('svg');
                if (svg) {
                    el.innerHTML = '';
                    el.appendChild(svg);
                    const textNode = document.createTextNode(' ' + this.t(key, params));
                    el.appendChild(textNode);
                } else {
                    el.innerHTML = this.t(key, params);
                }
            } else {
                el.innerHTML = this.t(key, params);
            }
        });
        
        // Traduire les placeholders
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            el.placeholder = this.t(key);
        });
        
        // Traduire les éléments des statistiques de l'info-banner
        document.querySelectorAll('[data-i18n="invoices"]').forEach(el => {
            el.textContent = this.t('invoices');
        });
        document.querySelectorAll('[data-i18n="clients"]').forEach(el => {
            el.textContent = this.t('clients');
        });
        document.querySelectorAll('[data-i18n="periods"]').forEach(el => {
            el.textContent = this.t('periods');
        });
        document.querySelectorAll('[data-i18n="database_active"]').forEach(el => {
            el.innerHTML = `📈 ${this.t('database_active')}`;
        });
        document.querySelectorAll('[data-i18n="filter_label"]').forEach(el => {
            el.innerHTML = `📂 ${this.t('filter_label')}`;
        });
        document.querySelectorAll('[data-i18n="client_label"]').forEach(el => {
            el.innerHTML = `👤 ${this.t('client_label')}`;
        });
        
        // Traduire les onglets
        const excelTab = document.querySelector('.tab-btn[onclick*="excel"]');
        if (excelTab && excelTab.getAttribute('data-i18n') === 'excel_tab') {
            excelTab.innerHTML = `📊 ${this.t('excel_tab')}`;
        }
        const pdfTab = document.querySelector('.tab-btn[onclick*="pdf"]');
        if (pdfTab && pdfTab.getAttribute('data-i18n') === 'pdf_tab') {
            pdfTab.innerHTML = `📄 ${this.t('pdf_tab')}`;
        }
        
        // Traduire les filtres de la sidebar
        document.querySelectorAll('.filter-pill[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            el.textContent = this.t(key);
        });
        
        // Traduire le label des conversations
        const convLabel = document.querySelector('.conv-section-label[data-i18n="conversations_label"]');
        if (convLabel) {
            convLabel.textContent = this.t('conversations_label');
        }
        
        // Traduire le message "Aucune conversation"
        const noConvMsg = document.querySelector('#conv-list p[data-i18n="no_conversations"]');
        if (noConvMsg) {
            noConvMsg.textContent = this.t('no_conversations');
        }
        
        // Traduire les suggestions spécifiques employé
        document.querySelectorAll('[data-i18n="suggestion_top_consumer"]').forEach(el => {
            el.textContent = this.t('suggestion_top_consumer');
        });
        document.querySelectorAll('[data-i18n="suggestion_unpaid_clients"]').forEach(el => {
            el.textContent = this.t('suggestion_unpaid_clients');
        });
        document.querySelectorAll('[data-i18n="suggestion_consumption_period"]').forEach(el => {
            el.textContent = this.t('suggestion_consumption_period');
        });
        document.querySelectorAll('[data-i18n="suggestion_total_amount"]').forEach(el => {
            el.textContent = this.t('suggestion_total_amount');
        });
        document.querySelectorAll('[data-i18n="suggestion_period"]').forEach(el => {
            el.textContent = this.t('suggestion_period');
        });
        document.querySelectorAll('[data-i18n="suggestion_consumption_details"]').forEach(el => {
            el.textContent = this.t('suggestion_consumption_details');
        });
        
        // Traduire le select des fichiers
        const selectFichier = document.getElementById('select-fichier');
        if (selectFichier && selectFichier.options[0] && selectFichier.options[0].getAttribute('data-i18n') === 'all_files') {
            selectFichier.options[0].text = `🌐 ${this.t('all_files')}`;
        }
        
        // Traduire le label du fichier
        const labelFichier = document.getElementById('label-fichier');
        if (labelFichier && labelFichier.getAttribute('data-i18n') === 'all_database' && !window.nomFichierActif) {
            labelFichier.innerHTML = `🌐 ${this.t('all_database')}`;
        }
        
        this.translateEmployeeInterface();
        this.translateConversationDates();
        this.translateDaysBadge();
    },
    
    translateSidebarFilters() {
        // Pour l'interface client (ancienne méthode)
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
        // Traduire les badges Excel/PDF
        document.querySelectorAll('.conv-badge').forEach(badge => {
            if (badge.textContent === 'XLS') badge.textContent = this.t('badge_excel');
            if (badge.textContent === 'PDF') badge.textContent = this.t('badge_pdf');
        });
        
        // Traduire les titres de bienvenue Excel
        const excelWelcomeTitle = document.querySelector('#chat-excel .welcome-title');
        if (excelWelcomeTitle && excelWelcomeTitle.getAttribute('data-i18n') === 'welcome_title_employee') {
            const name = document.querySelector('.user-name')?.textContent.split(' ')[0] || 'Employé';
            excelWelcomeTitle.innerHTML = this.t('welcome_title_employee', { name: name });
        }
        
        // Traduire les sous-titres de bienvenue Excel
        const excelWelcomeSub = document.querySelector('#chat-excel .welcome-sub');
        if (excelWelcomeSub && excelWelcomeSub.getAttribute('data-i18n') === 'welcome_sub_excel') {
            excelWelcomeSub.innerHTML = this.t('welcome_sub_excel');
        }
        
        // Traduire les titres PDF
        const pdfWelcomeTitle = document.querySelector('#chat-pdf .welcome-title');
        if (pdfWelcomeTitle && pdfWelcomeTitle.getAttribute('data-i18n') === 'pdf_welcome_title') {
            pdfWelcomeTitle.innerHTML = this.t('pdf_welcome_title');
        }
        
        // Traduire les sous-titres PDF
        const pdfWelcomeSub = document.querySelector('#chat-pdf .welcome-sub');
        if (pdfWelcomeSub && pdfWelcomeSub.getAttribute('data-i18n') === 'pdf_welcome_sub') {
            pdfWelcomeSub.innerHTML = this.t('pdf_welcome_sub');
        }
        
        // Traduire le rôle utilisateur
        const userRole = document.querySelector('.user-role');
        if (userRole && userRole.getAttribute('data-i18n') === 'employee_role') {
            userRole.innerHTML = this.t('employee_role');
        }
        
        // Traduire les placeholders des inputs
        const inputExcel = document.getElementById('input-excel');
        if (inputExcel && inputExcel.getAttribute('data-i18n-placeholder') === 'excel_placeholder') {
            inputExcel.placeholder = this.t('excel_placeholder');
        }
        
        const inputPdf = document.getElementById('input-pdf');
        if (inputPdf && inputPdf.getAttribute('data-i18n-placeholder') === 'pdf_placeholder') {
            inputPdf.placeholder = this.t('pdf_placeholder');
        }
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
        // Pour l'interface client
        const welcomeTitle = document.querySelector('.welcome-title');
        if (welcomeTitle && welcomeTitle.getAttribute('data-i18n') === 'welcome_title') {
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
            if (suggestionKeys[idx] && chip.getAttribute('data-i18n') === suggestionKeys[idx]) {
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
        
        // Rafraîchir les dates
        this.refreshAllDates();
        
        // Mettre à jour le label du fichier si nécessaire
        const labelFichier = document.getElementById('label-fichier');
        if (labelFichier && labelFichier.getAttribute('data-i18n') === 'all_database' && !window.nomFichierActif) {
            labelFichier.innerHTML = `🌐 ${this.t('all_database')}`;
        }
        
        document.querySelectorAll('.lang-option').forEach(opt => {
            opt.classList.remove('active');
            if ((lang === 'fr' && opt.textContent.includes('Français')) ||
                (lang === 'en' && opt.textContent.includes('English')) ||
                (lang === 'ar' && opt.textContent.includes('العربية'))) {
                opt.classList.add('active');
            }
        });
    },
    
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

// Initialisation
document.addEventListener('DOMContentLoaded', () => i18n.init());