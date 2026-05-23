// Gestionnaire de thème SRM (Dark / Light)
// À placer dans /static/theme.js — même logique que i18n.js

const srmTheme = {
    current: 'light',

    init() {
        // Lire la préférence sauvegardée, sinon préférence système
        const saved = localStorage.getItem('srm_theme');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const theme = saved || (prefersDark ? 'dark' : 'light');
        this.apply(theme, false);
    },

    apply(theme, animate = true) {
        this.current = theme;
        localStorage.setItem('srm_theme', theme);

        const root = document.documentElement;

        if (animate) {
            // Transition douce entre les thèmes
            root.style.transition = 'background-color 0.35s ease, color 0.35s ease';
            setTimeout(() => root.style.transition = '', 400);
        }

        if (theme === 'dark') {
            root.setAttribute('data-theme', 'dark');
            root.classList.add('dark');
        } else {
            root.setAttribute('data-theme', 'light');
            root.classList.remove('dark');
        }

        // Mettre à jour tous les boutons toggle présents dans la page
        this.updateButtons();
    },

    toggle() {
        this.apply(this.current === 'light' ? 'dark' : 'light', true);
    },

    updateButtons() {
        // Icône soleil / lune selon le thème actif
        const isDark = this.current === 'dark';

        document.querySelectorAll('.srm-theme-btn').forEach(btn => {
            const iconSun  = btn.querySelector('.icon-sun');
            const iconMoon = btn.querySelector('.icon-moon');
            const label    = btn.querySelector('.theme-label');

            if (iconSun)  iconSun.style.display  = isDark  ? 'block' : 'none';
            if (iconMoon) iconMoon.style.display  = isDark  ? 'none'  : 'block';
            if (label)    label.textContent        = isDark  ? 'Mode clair' : 'Mode sombre';

            btn.setAttribute('aria-label', isDark ? 'Passer en mode clair' : 'Passer en mode sombre');
            btn.setAttribute('title',      isDark ? 'Mode clair'           : 'Mode sombre');
        });
    }
};

// Initialisation immédiate — avant le rendu pour éviter le flash
(function() {
    const saved = localStorage.getItem('srm_theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = saved || (prefersDark ? 'dark' : 'light');
    if (theme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        document.documentElement.classList.add('dark');
    }
})();

document.addEventListener('DOMContentLoaded', () => srmTheme.init());