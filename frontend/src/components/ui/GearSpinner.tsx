import { GearIcon } from "./icons";

export function GearSpinner({ label }: { label?: string }) {
  return (
    <div className="loading-row">
      <GearIcon className="gear-spinner" />
      {label && <span>{label}</span>}
    </div>
  );
}
