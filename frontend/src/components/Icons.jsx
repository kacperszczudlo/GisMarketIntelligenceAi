import React from "react";

export function GisMarketLogo({ size = 36 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      {/* Top solid GIS layer */}
      <path d="M20 5L35 12.2L20 19.4L5 12.2L20 5Z" fill="#0F4C81" />
      {/* Middle outlined GIS layer */}
      <path
        d="M11.2 17.4L5 20.4L20 27.6L35 20.4L28.8 17.4L20 21.6L11.2 17.4Z"
        fill="#FFFFFF"
        stroke="#0F4C81"
        strokeWidth="1.75"
        strokeLinejoin="round"
      />
      {/* Bottom solid GIS layer */}
      <path
        d="M11.2 25.4L5 28.4L20 35.6L35 28.4L28.8 25.4L20 29.6L11.2 25.4Z"
        fill="#0F4C81"
      />
      {/* Precision GIS node accent on top plane */}
      <circle cx="20" cy="12.2" r="2.1" fill="#FFFFFF" />
    </svg>
  );
}

const iconProps = (size = 18) => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: "1.75",
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
});

export function HomeIcon({ size = 18 }) {
  return (
    <svg {...iconProps(size)}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  );
}

export function SettingsIcon({ size = 18 }) {
  return (
    <svg {...iconProps(size)}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}

export function InfoIcon({ size = 18 }) {
  return (
    <svg {...iconProps(size)}>
      <circle cx="12" cy="12" r="9" />
      <line x1="12" y1="16" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
  );
}

export function LogoutIcon({ size = 18 }) {
  return (
    <svg {...iconProps(size)}>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  );
}

export function SearchIcon({ size = 16 }) {
  return (
    <svg {...iconProps(size)}>
      <circle cx="11" cy="11" r="7" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

export function ArrowLeftIcon({ size = 18 }) {
  return (
    <svg {...iconProps(size)}>
      <line x1="19" y1="12" x2="5" y2="12" />
      <polyline points="12 19 5 12 12 5" />
    </svg>
  );
}

export function DownloadIcon({ size = 16 }) {
  return (
    <svg {...iconProps(size)}>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  );
}

export function ShieldAlertIcon({ size = 18 }) {
  return (
    <svg {...iconProps(size)}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

export function WalletIcon({ size = 18 }) {
  return (
    <svg {...iconProps(size)}>
      <rect x="2" y="6" width="20" height="14" rx="2" />
      <path d="M2 10h20" />
      <circle cx="16.5" cy="14.5" r="1" />
    </svg>
  );
}

export function ScaleIcon({ size = 18 }) {
  return (
    <svg {...iconProps(size)}>
      <line x1="12" y1="3" x2="12" y2="21" />
      <path d="M5 7h14" />
      <path d="M3 14l2-7 2 7a2 2 0 0 1-4 0z" />
      <path d="M17 14l2-7 2 7a2 2 0 0 1-4 0z" />
      <line x1="8" y1="21" x2="16" y2="21" />
    </svg>
  );
}

export function CheckBadgeIcon({ size = 18 }) {
  return (
    <svg {...iconProps(size)}>
      <path d="M12 2l2.4 2.4 3.4-.5.5 3.4L20.7 9.7 19 12.6l1.7 2.9-2.4 2.4-.5 3.4-3.4-.5L12 22l-2.4-1.2-3.4.5-.5-3.4L3.3 15.5 5 12.6 3.3 9.7l2.4-2.4.5-3.4 3.4.5L12 2z" />
      <polyline points="9 12 11 14 15 10" />
    </svg>
  );
}

export function SparklesIcon({ size = 16 }) {
  return (
    <svg {...iconProps(size)}>
      <path d="M12 3l1.6 4.4L18 9l-4.4 1.6L12 15l-1.6-4.4L6 9l4.4-1.6L12 3z" />
      <path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15z" />
    </svg>
  );
}

export function SendIcon({ size = 17 }) {
  return (
    <svg {...iconProps(size)}>
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  );
}

export function ChevronDownIcon({ size = 16, rotated = false }) {
  return (
    <svg
      {...iconProps(size)}
      style={{
        transform: rotated ? "rotate(180deg)" : "rotate(0deg)",
        transition: "transform 160ms cubic-bezier(0.16, 1, 0.3, 1)",
      }}
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

export function CopyIcon({ size = 14 }) {
  return (
    <svg {...iconProps(size)}>
      <rect x="9" y="9" width="13" height="13" rx="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

export function EyeIcon({ size = 16 }) {
  return (
    <svg {...iconProps(size)}>
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

export function EyeOffIcon({ size = 16 }) {
  return (
    <svg {...iconProps(size)}>
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  );
}

export function SaveIcon({ size = 16 }) {
  return (
    <svg {...iconProps(size)}>
      <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
      <polyline points="17 21 17 13 7 13 7 21" />
      <polyline points="7 3 7 8 15 8" />
    </svg>
  );
}

export function CheckIcon({ size = 16 }) {
  return (
    <svg {...iconProps(size)} strokeWidth="2.2">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

export function LockIcon({ size = 16 }) {
  return (
    <svg {...iconProps(size)}>
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  );
}

export function UnlockIcon({ size = 16 }) {
  return (
    <svg {...iconProps(size)}>
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 9.9-1" />
    </svg>
  );
}

export function TrashIcon({ size = 16 }) {
  return (
    <svg {...iconProps(size)}>
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
      <path d="M10 11v6" />
      <path d="M14 11v6" />
      <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
    </svg>
  );
}

export function PlusIcon({ size = 16 }) {
  return (
    <svg {...iconProps(size)} strokeWidth="2.2">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}
