// parking-management/frontend/src/assets/icons/IconBase.jsx

import { ICON_COLORS, ICON_SIZES } from './index';

/**
 * Base Icon Component
 * All icons extend this component for consistent props and behavior
 */
const IconBase = ({ 
    children, 
    size = 'md', 
    color = 'currentColor',
    className = '',
    style = {},
    onClick,
    title,
    role = 'img',
    'aria-label': ariaLabel,
    ...props 
}) => {
    // Resolve size
    const resolvedSize = typeof size === 'number' ? size : ICON_SIZES[size] || ICON_SIZES.md;
    
    // Resolve color
    const resolvedColor = ICON_COLORS[color] || color;
    
    // Combine classes
    const iconClasses = `parking-icon ${className}`.trim();
    
    return (
        <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            width={resolvedSize}
            height={resolvedSize}
            fill="none"
            stroke={resolvedColor}
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={iconClasses}
            style={style}
            onClick={onClick}
            role={role}
            aria-label={ariaLabel || title}
            {...props}
        >
            {title && <title>{title}</title>}
            {children}
        </svg>
    );
};

export default IconBase;