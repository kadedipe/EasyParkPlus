// parking-management/frontend/src/assets/icons/IconParkingLot.jsx

import IconBase from './IconBase';

const IconParkingLot = (props) => (
    <IconBase {...props}>
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
        <line x1="9" y1="9" x2="9" y2="15" />
        <line x1="15" y1="9" x2="15" y2="15" />
        <line x1="9" y1="12" x2="15" y2="12" />
    </IconBase>
);

export default IconParkingLot;