// parking-management/frontend/src/assets/icons/Icon.jsx

import * as Icons from './index';

/**
 * Dynamic Icon Component
 * Renders any icon by name with consistent props
 */
const Icon = ({ name, ...props }) => {
    const IconComponent = Icons[`Icon${name.charAt(0).toUpperCase()}${name.slice(1)}`];
    
    if (!IconComponent) {
        console.warn(`Icon "${name}" not found`);
        return null;
    }
    
    return <IconComponent {...props} />;
};

// Icon groups for easier organization
export const ParkingIcons = {
    Parking: Icons.IconParking,
    ParkingLot: Icons.IconParkingLot,
    Car: Icons.IconCar,
    ElectricCar: Icons.IconElectricCar,
    Handicap: Icons.IconHandicap,
};

export const NavigationIcons = {
    Location: Icons.IconLocation,
    Map: Icons.IconMap,
    Search: Icons.IconSearch,
    Filter: Icons.IconFilter,
    Arrow: Icons.IconArrow,
};

export const ActionIcons = {
    Edit: Icons.IconEdit,
    Delete: Icons.IconDelete,
    Check: Icons.IconCheck,
    Close: Icons.IconClose,
    Refresh: Icons.IconRefresh,
    Download: Icons.IconDownload,
    Share: Icons.IconShare,
};

export const StatusIcons = {
    Success: Icons.IconSuccess,
    Warning: Icons.IconWarning,
    Error: Icons.IconError,
    Info: Icons.IconInfo,
    Loading: Icons.IconLoading,
};

export default Icon;