// parking-management/frontend/src/assets/icons/IconLoading.jsx

import IconBase from './IconBase';

const IconLoading = (props) => (
    <IconBase {...props} className={`parking-icon-loading ${props.className || ''}`}>
        <style>{`
            .parking-icon-loading {
                animation: spin 1s linear infinite;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        `}</style>
        <circle cx="12" cy="12" r="10" strokeDasharray="31.4 31.4" />
        <line x1="12" y1="2" x2="12" y2="6" />
        <line x1="12" y1="18" x2="12" y2="22" />
        <line x1="2" y1="12" x2="6" y2="12" />
        <line x1="18" y1="12" x2="22" y2="12" />
    </IconBase>
);

export default IconLoading;