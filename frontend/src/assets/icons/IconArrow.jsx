// parking-management/frontend/src/assets/icons/IconArrow.jsx

import IconBase from './IconBase';

const IconArrow = ({ direction = 'right', ...props }) => {
    const getPath = () => {
        switch (direction) {
            case 'up':
                return <polyline points="18 15 12 9 6 15" />;
            case 'down':
                return <polyline points="6 9 12 15 18 9" />;
            case 'left':
                return <polyline points="15 18 9 12 15 6" />;
            case 'right':
            default:
                return <polyline points="9 18 15 12 9 6" />;
        }
    };
    
    return <IconBase {...props}>{getPath()}</IconBase>;
};

export default IconArrow;