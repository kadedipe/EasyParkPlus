// src/hooks/useGoogleFonts.js

import { useEffect, useState } from 'react';
import fontManager from '../utils/fontUtils';

/**
 * Custom hook for managing Google Fonts (Inter)
 */
export const useGoogleFonts = () => {
    const [fontsLoaded, setFontsLoaded] = useState(false);
    const [fontError, setFontError] = useState(false);

    useEffect(() => {
        let mounted = true;

        const loadFonts = async () => {
            try {
                const success = await fontManager.loadInterFont();
                if (mounted) {
                    setFontsLoaded(success);
                    setFontError(!success);
                }
            } catch (error) {
                if (mounted) {
                    setFontError(true);
                    setFontsLoaded(false);
                    console.error('Failed to load Inter font:', error);
                }
            }
        };

        loadFonts();

        return () => {
            mounted = false;
        };
    }, []);

    return {
        fontsLoaded,
        fontError,
        fontFamily: fontsLoaded ? 'Inter' : 'system-ui, -apple-system, sans-serif'
    };
};