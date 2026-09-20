import type { SVGProps } from "react";

/**
 * A small hand-drawn, line-based icon set in a shared visual language
 * (1.8 stroke, 24x24 grid, currentColor) so the whole app reads as one
 * consistent steampunk instrument panel rather than a mixed icon library.
 */
type IconProps = SVGProps<SVGSVGElement>;

const base = {
  viewBox: "0 0 24 24",
  // 1em default so every icon scales with its surrounding text unless a specific
  // CSS rule (.sidebar-link svg, .btn svg, etc.) or inline style overrides it —
  // without this, a bare <Icon /> dropped outside those contexts renders at the
  // SVG's unconstrained intrinsic size (huge) instead of a sensible glyph size.
  width: "1em",
  height: "1em",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export function GearIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M12 3.5c.5 0 .9.35 1 .84l.3 1.55a6.6 6.6 0 0 1 1.72.71l1.3-.9c.42-.3.98-.24 1.33.13l.82.85c.35.36.4.92.12 1.33l-.88 1.3c.35.53.61 1.11.76 1.73l1.55.29c.49.09.85.52.85 1.02v1.2c0 .5-.36.93-.85 1.02l-1.55.29a6.6 6.6 0 0 1-.76 1.73l.88 1.3c.28.41.23.97-.12 1.33l-.82.85c-.35.37-.91.43-1.33.13l-1.3-.9a6.6 6.6 0 0 1-1.72.71l-.3 1.55c-.1.49-.5.84-1 .84h-1.2c-.5 0-.9-.35-1-.84l-.3-1.55a6.6 6.6 0 0 1-1.72-.71l-1.3.9c-.42.3-.98.24-1.33-.13l-.82-.85a1.05 1.05 0 0 1-.12-1.33l.88-1.3a6.6 6.6 0 0 1-.76-1.73l-1.55-.29A1.05 1.05 0 0 1 2 13.4v-1.2c0-.5.36-.93.85-1.02l1.55-.29c.15-.62.41-1.2.76-1.73l-.88-1.3a1.05 1.05 0 0 1 .12-1.33l.82-.85c.35-.37.91-.43 1.33-.13l1.3.9a6.6 6.6 0 0 1 1.72-.71l.3-1.55c.1-.49.5-.84 1-.84z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

export function DashboardIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M3 13a9 9 0 0 1 18 0" />
      <path d="M12 13l4-4" />
      <circle cx="12" cy="13" r="1.1" fill="currentColor" stroke="none" />
      <path d="M4 20h16" />
    </svg>
  );
}

export function CrateIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M3 8l9-4.5L21 8v8l-9 4.5L3 16z" />
      <path d="M3 8l9 4.5L21 8" />
      <path d="M12 12.5V21" />
    </svg>
  );
}

export function TagIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M12 3h6a2 2 0 0 1 2 2v6a1 1 0 0 1-.3.7l-8.2 8.2a1.5 1.5 0 0 1-2.12 0L3.1 13.62a1.5 1.5 0 0 1 0-2.12L11.3 3.3A1 1 0 0 1 12 3z" />
      <circle cx="16.2" cy="7.8" r="1.4" />
    </svg>
  );
}

export function TruckIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M2.5 6.5h11v9h-11z" />
      <path d="M13.5 10h3.5l3.5 3v2.5h-2" />
      <circle cx="6.5" cy="17.5" r="1.6" />
      <circle cx="16" cy="17.5" r="1.6" />
    </svg>
  );
}

export function WarehouseIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M3 10.5 12 4l9 6.5V20a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z" />
      <path d="M9 21v-6h6v6" />
    </svg>
  );
}

export function LayersIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M12 3l9 5-9 5-9-5z" />
      <path d="M3 13l9 5 9-5" />
    </svg>
  );
}

export function TransferIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M4 8h13" />
      <path d="M13 4l4 4-4 4" />
      <path d="M20 16H7" />
      <path d="M11 12l-4 4 4 4" />
    </svg>
  );
}

export function AlertIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M12 3.5 21.5 20h-19z" />
      <path d="M12 9.5v4.2" />
      <circle cx="12" cy="16.7" r="0.9" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function CheckIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M8 12.3l2.6 2.6L16.2 9" />
    </svg>
  );
}

export function LedgerIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M5 3.5h11l3 3V20a.7.7 0 0 1-.7.7H5.7A.7.7 0 0 1 5 20z" />
      <path d="M16 3.5V6a.7.7 0 0 0 .7.7H19" />
      <path d="M8 11h8M8 14h8M8 17h5" />
    </svg>
  );
}

export function UserIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <circle cx="12" cy="8" r="3.3" />
      <path d="M5 20c1-3.6 3.8-5.5 7-5.5s6 1.9 7 5.5" />
    </svg>
  );
}

export function UsersIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <circle cx="9" cy="8" r="3" />
      <path d="M3.5 19c.8-3.1 3-4.7 5.5-4.7s4.7 1.6 5.5 4.7" />
      <path d="M15.2 4.6a3 3 0 0 1 0 5.8" />
      <path d="M16.5 14.6c2 .5 3.4 1.9 4 4.4" />
    </svg>
  );
}

export function LogoutIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M9 21H5a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h4" />
      <path d="M16 17l5-5-5-5" />
      <path d="M21 12H9" />
    </svg>
  );
}

export function PlusIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

export function EditIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M4 20l.9-3.9L15.6 5.4a1.5 1.5 0 0 1 2.1 0l1 1a1.5 1.5 0 0 1 0 2.1L8 19.2z" />
      <path d="M13.5 7.5l3 3" />
    </svg>
  );
}

export function TrashIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M5 7h14" />
      <path d="M9 7V4.8c0-.4.4-.8.9-.8h4.2c.5 0 .9.4.9.8V7" />
      <path d="M6.5 7l.7 12.2c0 .5.5.8 1 .8h7.6c.5 0 .9-.3 1-.8L17.5 7" />
      <path d="M10 11v5M14 11v5" />
    </svg>
  );
}

export function CloseIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  );
}

export function SearchIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="M20 20l-4.5-4.5" />
    </svg>
  );
}

export function ChevronDownIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M6 9l6 6 6-6" />
    </svg>
  );
}

export function ClipboardIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M8 4.5h8a1 1 0 0 1 1 1V19a1 1 0 0 1-1 1H8a1 1 0 0 1-1-1V5.5a1 1 0 0 1 1-1z" />
      <path d="M9.5 3.5h5a.5.5 0 0 1 .5.5v1.5h-6V4a.5.5 0 0 1 .5-.5z" />
      <path d="M9 10h6M9 13h6M9 16h4" />
    </svg>
  );
}

export function CartIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M3 4h2l2.2 11.2a1.5 1.5 0 0 0 1.5 1.3h7.6a1.5 1.5 0 0 0 1.5-1.2L20 8H6" />
      <circle cx="10" cy="20" r="1.2" />
      <circle cx="17" cy="20" r="1.2" />
    </svg>
  );
}

export function ShipmentIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M4 7.5h10v8H4z" />
      <path d="M14 11h3l3 3v1.5h-2" />
      <circle cx="7.5" cy="16.7" r="1.5" />
      <circle cx="17" cy="16.7" r="1.5" />
      <path d="M1 8.5h1M1 11h1.5M1 13.5h2" />
    </svg>
  );
}

export function ChartIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M4 20V4" />
      <path d="M4 20h16" />
      <path d="M8 20v-7" />
      <path d="M13 20V9" />
      <path d="M18 20v-4" />
    </svg>
  );
}

export function DownloadIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M12 3.5v11" />
      <path d="M7.5 10.5 12 15l4.5-4.5" />
      <path d="M4.5 17.5v2a1 1 0 0 0 1 1h13a1 1 0 0 0 1-1v-2" />
    </svg>
  );
}

export function ArchiveIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M3.5 5.5h17v3.5h-17z" />
      <path d="M4.5 9v9.2c0 .5.4.9.9.9h13.2c.5 0 .9-.4.9-.9V9" />
      <path d="M10 13h4" />
    </svg>
  );
}
