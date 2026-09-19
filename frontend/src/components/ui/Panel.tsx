import type { HTMLAttributes } from "react";

export function Panel({ className = "", ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={`panel ${className}`.trim()} {...rest} />;
}
