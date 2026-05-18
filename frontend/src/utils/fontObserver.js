// src/utils/fontObserver.js

/**
 * Fallback font observer for older browsers
 */

class FontObserver {
    constructor() {
        this.fontCheckInterval = null;
    }

    /**
     * Check if font is loaded by measuring element
     */
    checkFontLoaded(fontFamily, testString = 'mmmmmmmmmmlli') {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        
        const defaultFonts = ['monospace', 'sans-serif', 'serif'];
        const defaultWidths = {};
        
        // Measure default fonts
        defaultFonts.forEach(font => {
            context.font = `40px ${font}`;
            defaultWidths[font] = context.measureText(testString).width;
        });
        
        // Measure target font
        context.font = `40px ${fontFamily}, sans-serif`;
        const targetWidth = context.measureText(testString).width;
        
        // If width is different from default sans-serif, font is loaded
        return Math.abs(targetWidth - defaultWidths['sans-serif']) > 1;
    }

    /**
     * Wait for font to load
     */
    waitForFont(fontFamily, timeout = 3000) {
        return new Promise((resolve) => {
            const startTime = Date.now();
            
            const check = () => {
                if (this.checkFontLoaded(fontFamily)) {
                    resolve(true);
                    return;
                }
                
                if (Date.now() - startTime > timeout) {
                    resolve(false);
                    return;
                }
                
                setTimeout(check, 100);
            };
            
            check();
        });
    }
}

export default new FontObserver();