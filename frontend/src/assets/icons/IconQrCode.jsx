// parking-management/frontend/src/assets/icons/IconQrCode.jsx

import IconBase from './IconBase';

const IconQrCode = (props) => (
    <IconBase {...props}>
        <rect x="2" y="2" width="8" height="8" rx="1" ry="1" />
        <rect x="14" y="2" width="8" height="8" rx="1" ry="1" />
        <rect x="2" y="14" width="8" height="8" rx="1" ry="1" />
        <line x1="14" y1="18" x2="18" y2="18" />
        <line x1="18" y1="14" x2="18" y2="22" />
        <line x1="14" y1="22" x2="22" y2="22" />
    </IconBase>
);

export default IconQrCode;