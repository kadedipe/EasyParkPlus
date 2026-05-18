// parking-management/frontend/src/components/ThemeSwitcher.jsx

import { useState } from 'react';
import { themes, useTheme } from './ThemeProvider';

const ThemeSwitcher = () => {
    const { currentTheme, changeTheme, isTransitioning } = useTheme();
    const [isOpen, setIsOpen] = useState(false);

    const currentThemeData = themes.find(t => t.id === currentTheme);

    return (
        <div className="theme-switcher-container">
            <button 
                className="theme-switcher-trigger"
                onClick={() => setIsOpen(!isOpen)}
                disabled={isTransitioning}
                aria-label="Change theme"
            >
                <i className={`fas ${currentThemeData.icon}`}></i>
                <span className="theme-name">{currentThemeData.name}</span>
                <i className={`fas fa-chevron-${isOpen ? 'up' : 'down'}`}></i>
            </button>
            
            {isOpen && (
                <div className="theme-switcher-dropdown">
                    {themes.map(theme => (
                        <button
                            key={theme.id}
                            className={`theme-option ${currentTheme === theme.id ? 'active' : ''}`}
                            onClick={() => {
                                changeTheme(theme.id);
                                setIsOpen(false);
                            }}
                        >
                            <i className={`fas ${theme.icon}`}></i>
                            <div className="theme-info">
                                <span className="theme-name">{theme.name}</span>
                                <span className="theme-description">{theme.description}</span>
                            </div>
                            {currentTheme === theme.id && (
                                <i className="fas fa-check-circle"></i>
                            )}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
};

export default ThemeSwitcher;