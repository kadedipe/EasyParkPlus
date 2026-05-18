// scripts/optimize-google-fonts.js
// Generates optimized Google Fonts URL

const fontFamily = 'Inter';
const weights = [100, 200, 300, 400, 500, 600, 700, 800, 900];
const styles = ['normal', 'italic'];

const generateFontUrl = () => {
    const weightsStr = weights.map(w => `0,${w}`).join(';');
    const stylesStr = styles.join(',');
    
    return `https://fonts.googleapis.com/css2?family=${fontFamily}:ital,wght@${weightsStr}&display=swap`;
};

console.log('Optimized Google Fonts URL:');
console.log(generateFontUrl());