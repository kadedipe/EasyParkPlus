// parking-management/frontend/src/components/ThemeProvider.jsx

import { createContext, useContext, useEffect, useState } from 'react';
import '../assets/styles/themes/index.css';

const ThemeContext = createContext();

export const themes = [
    { id: 'default', name: 'Default', description: 'Indigo/Purple Theme', icon: 'fa-palette' },
    { id: 'light', name: 'Light', description: 'Clean Light Theme', icon: 'fa-sun' },
    { id: 'dark', name: 'Dark', description: 'Modern Dark Theme', icon: 'fa-moon' },
    { id: 'corporate', name: 'Corporate', description: 'Professional Theme', icon: 'fa-briefcase' },
    { id: 'nature', name: 'Nature', description: 'Earthy Green Theme', icon: 'fa-leaf' },
    { id: 'ocean', name: 'Ocean', description: 'Calm Blue Theme', icon: 'fa-water' },
    { id: 'sunset', name: 'Sunset', description: 'Warm Orange Theme', icon: 'fa-sunset' }
];

export const ThemeProvider = ({ children }) => {
    const [currentTheme, setCurrentTheme] = useState(() => {
        const savedTheme = localStorage.getItem('parking-theme');
        return savedTheme && themes.find(t => t.id === savedTheme) ? savedTheme : 'default';
    });

    const [isTransitioning, setIsTransitioning] = useState(false);

    useEffect(() => {
        // Apply theme to document
        document.documentElement.setAttribute('data-theme', currentTheme);
        document.documentElement.classList.add(`theme-${currentTheme}`);
        
        // Save to localStorage
        localStorage.setItem('parking-theme', currentTheme);
        
        // Remove other theme classes
        themes.forEach(theme => {
            if (theme.id !== currentTheme) {
                document.documentElement.classList.remove(`theme-${theme.id}`);
            }
        });
        
        // Dispatch custom event for theme change
        window.dispatchEvent(new CustomEvent('theme-changed', { detail: { theme: currentTheme } }));
        
    }, [currentTheme]);

    const changeTheme = async (themeId) => {
        if (themeId === currentTheme) return;
        
        // Add transition class
        setIsTransitioning(true);
        document.documentElement.classList.add('theme-switching');
        
        // Small delay for visual feedback
        setTimeout(() => {
            setCurrentTheme(themeId);
            
            // Remove transition class after theme change
            setTimeout(() => {
                setIsTransitioning(false);
                document.documentElement.classList.remove('theme-switching');
            }, 300);
        }, 100);
    };

    const value = {
        currentTheme,
        changeTheme,
        themes,
        isTransitioning,
        getThemeVariables: () => {
            const root = getComputedStyle(document.documentElement);
            return {
                primary: root.getPropertyValue('--theme-primary').trim(),
                secondary: root.getPropertyValue('--theme-secondary').trim(),
                background: root.getPropertyValue('--theme-bg-primary').trim(),
                text: root.getPropertyValue('--theme-text-primary').trim()
            };
        }
    };

    return (
        <ThemeContext.Provider value={value}>
            {children}
            {isTransitioning && <div className="theme-transition-overlay active" />}
        </ThemeContext.Provider>
    );
};

export const useTheme = () => {
    const context = useContext(ThemeContext);
    if (!context) {
        throw new Error('useTheme must be used within ThemeProvider');
    }
    return context;
};