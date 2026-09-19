import type { ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "brass" | "ghost" | "verdigris" | "danger";
  size?: "md" | "sm";
}

export function Button({ variant = "brass", size = "md", className = "", type = "button", ...rest }: ButtonProps) {
  const variantClass = variant === "brass" ? "" : `btn--${variant}`;
  const sizeClass = size === "sm" ? "btn--sm" : "";
  return <button type={type} className={`btn ${variantClass} ${sizeClass} ${className}`.trim()} {...rest} />;
}
