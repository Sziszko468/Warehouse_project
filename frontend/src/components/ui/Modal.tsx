import { useEffect, type MouseEvent, type ReactNode } from "react";
import { Button } from "./Button";
import { CloseIcon } from "./icons";
import { Panel } from "./Panel";

interface ModalProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
}

export function Modal({ title, onClose, children }: ModalProps) {
  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  function stop(event: MouseEvent) {
    event.stopPropagation();
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <Panel className="modal" onClick={stop}>
        <div className="panel-header">
          <h3>{title}</h3>
          <Button variant="ghost" size="sm" className="btn--icon" onClick={onClose} aria-label="Bezárás">
            <CloseIcon />
          </Button>
        </div>
        {children}
      </Panel>
    </div>
  );
}
