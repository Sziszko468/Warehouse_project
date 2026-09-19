import type { MouseEvent } from "react";
import { t } from "../../i18n/strings";
import { Button } from "./Button";
import { Panel } from "./Panel";

interface ConfirmDialogProps {
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  isDangerous?: boolean;
}

export function ConfirmDialog({ title, message, onConfirm, onCancel, isDangerous }: ConfirmDialogProps) {
  function stop(event: MouseEvent) {
    event.stopPropagation();
  }

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <Panel className="modal" style={{ width: "min(380px, 100%)" }} onClick={stop}>
        <h3>{title}</h3>
        <p>{message}</p>
        <div className="form-actions">
          <Button variant="ghost" onClick={onCancel}>
            {t.no}
          </Button>
          <Button variant={isDangerous ? "danger" : "brass"} onClick={onConfirm}>
            {t.yes}
          </Button>
        </div>
      </Panel>
    </div>
  );
}
