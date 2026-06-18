// parking-management/frontend/src/assets/icons/index.js

/**
 * Icon System Index
 * Centralizes all icon exports for easy import throughout the app
 */

// Parking specific icons
export { default as IconCalendar } from './IconCalendar';
export { default as IconCar } from './IconCar';
export { default as IconClock } from './IconClock';
export { default as IconElectricCar } from './IconElectricCar';
export { default as IconHandicap } from './IconHandicap';
export { default as IconLocation } from './IconLocation';
export { default as IconMap } from './IconMap';
export { default as IconParking } from './IconParking';
export { default as IconParkingLot } from './IconParkingLot';

// Payment and booking icons
export { default as IconCreditCard } from './IconCreditCard';
export { default as IconPayment } from './IconPayment';
export { default as IconQrCode } from './IconQrCode';
export { default as IconReservation } from './IconReservation';
export { default as IconTicket } from './IconTicket';

// Navigation and actions
export { default as IconArrow } from './IconArrow';
export { default as IconFilter } from './IconFilter';
export { default as IconMenu } from './IconMenu';
export { default as IconMore } from './IconMore';
export { default as IconRefresh } from './IconRefresh';
export { default as IconSearch } from './IconSearch';

// User related icons
export { default as IconAnalytics } from './IconAnalytics';
export { default as IconBell } from './IconBell';
export { default as IconDashboard } from './IconDashboard';
export { default as IconHistory } from './IconHistory';
export { default as IconLogout } from './IconLogout';
export { default as IconSettings } from './IconSettings';
export { default as IconUser } from './IconUser';

// Action icons
export { default as IconCheck } from './IconCheck';
export { default as IconClose } from './IconClose';
export { default as IconDelete } from './IconDelete';
export { default as IconDownload } from './IconDownload';
export { default as IconEdit } from './IconEdit';
export { default as IconShare } from './IconShare';

// Utility icons
export { default as IconCamera } from './IconCamera';
export { default as IconError } from './IconError';
export { default as IconInfo } from './IconInfo';
export { default as IconLoading } from './IconLoading';
export { default as IconStar } from './IconStar';
export { default as IconSuccess } from './IconSuccess';
export { default as IconSupport } from './IconSupport';
export { default as IconWarning } from './IconWarning';

// Icon sizes and constants
export const ICON_SIZES = {
    xs: 12,
    sm: 16,
    md: 20,
    lg: 24,
    xl: 32,
    '2xl': 40,
    '3xl': 48,
    '4xl': 64
};

export const ICON_COLORS = {
    primary: 'var(--theme-primary)',
    secondary: 'var(--theme-secondary)',
    success: 'var(--theme-success)',
    warning: 'var(--theme-warning)',
    error: 'var(--theme-error)',
    info: 'var(--theme-info)',
    text: 'var(--theme-text-primary)',
    textSecondary: 'var(--theme-text-secondary)',
    disabled: 'var(--theme-text-disabled)',
    white: '#FFFFFF',
    black: '#000000'
};

// Icon registry for dynamic icon loading
export const iconRegistry = {
    parking: 'IconParking',
    car: 'IconCar',
    location: 'IconLocation',
    clock: 'IconClock',
    calendar: 'IconCalendar',
    creditCard: 'IconCreditCard',
    qrCode: 'IconQrCode',
    ticket: 'IconTicket',
    map: 'IconMap',
    search: 'IconSearch',
    filter: 'IconFilter',
    user: 'IconUser',
    settings: 'IconSettings',
    bell: 'IconBell',
    dashboard: 'IconDashboard',
    logout: 'IconLogout',
    edit: 'IconEdit',
    delete: 'IconDelete',
    check: 'IconCheck',
    close: 'IconClose',
    arrow: 'IconArrow',
    star: 'IconStar',
    menu: 'IconMenu'
};

// Helper function to get icon by name
export const getIcon = (name) => {
    return iconRegistry[name] || null;
};