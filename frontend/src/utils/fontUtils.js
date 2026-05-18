// src/utils/fontUtils.js

/**
 * Google Fonts (Inter) Utility Module
 * Handles font loading, monitoring, and optimization
 */

class GoogleFontsManager {
    constructor() {
        this.fontFamily = 'Inter';
        this.fontsLoaded = false;
        this.fontLoadingPromise = null;
    }

    /**
     * Check if browser supports Font Loading API
     */
    isFontLoadingSupported() {
        return 'fonts' in document;
    }

    /**
     * Load Inter font with specific weights
     */
    async loadInterFont() {
        if (this.fontsLoaded) return Promise.resolve();
        
        if (this.fontLoadingPromise) return this.fontLoadingPromise;

        if (!this.isFontLoadingSupported()) {
            console.warn('Font Loading API not supported, using fallback');
            this.fontsLoaded = true;
            return Promise.resolve();
        }

        const weights = [400, 500, 600, 700];
        
        this.fontLoadingPromise = Promise.all(
            weights.map(weight => 
                document.fonts.load(`${weight} 1em ${this.fontFamily}`)
            )
        ).then(() => {
            this.fontsLoaded = true;
            document.documentElement.classList.add('inter-font-loaded');
            console.log('Inter font loaded successfully');
            return true;
        }).catch(err => {
            console.warn('Inter font loading failed:', err);
            document.documentElement.classList.add('inter-font-failed');
            return false;
        });

        return this.fontLoadingPromise;
    }

    /**
     * Get font CSS variable for dynamic styling
     */
    getFontCSSVariable() {
        return this.fontsLoaded ? this.fontFamily : 'system-ui, -apple-system, sans-serif';
    }

    /**
     * Preload critical font weights for better performance
     */
    preloadCriticalFonts() {
        const criticalWeights = [400, 600, 700];
        
        criticalWeights.forEach(weight => {
            const link = document.createElement('link');
            link.rel = 'preload';
            link.as = 'font';
            link.type = 'font/woff2';
            link.crossOrigin = 'anonymous';
            link.href = `https://fonts.gstatic.com/s/inter/v12/UcC73FwrK3iLTeHuS_fvQtMwCp50KnMa1ZL7W0Q5nw.woff2`;
            document.head.appendChild(link);
        });
    }

    /**
     * Check font status
     */
    getFontStatus() {
        return {
            fontFamily: this.fontFamily,
            loaded: this.fontsLoaded,
            supported: this.isFontLoadingSupported(),
            usingGoogleFonts: true
        };
    }
}

// Create singleton instance
const fontManager = new GoogleFontsManager();

export default fontManager;