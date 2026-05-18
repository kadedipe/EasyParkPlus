// src/main.jsx or src/index.jsx
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './assets/styles/main.css'; // This imports after variables
import './assets/styles/themes/index.css';
import './assets/styles/variables.css';
import { ThemeProvider } from './context/ThemeContext.jsx';

ReactDOM.createRoot(document.getElementById('root')).render(
    <ThemeProvider>
        <App />
    </ThemeProvider>
);
