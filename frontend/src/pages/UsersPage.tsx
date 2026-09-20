import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import * as usersApi from "../api/users";
import { PageHeader } from "../components/layout/PageHeader";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataTable, type Column } from "../components/ui/DataTable";
import { Pagination } from "../components/ui/Pagination";
import { Panel } from "../components/ui/Panel";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { t } from "../i18n/strings";
import { getErrorMessage } from "../lib/errors";
import { formatDateTime } from "../lib/format";
import type { User, UserRole } from "../types";

const LIMIT = 20;

export function UsersPage() {
  const { user: currentUser } = useAuth();
  const { showSuccess, showError } = useToast();
  const queryClient = useQueryClient();
  const [offset, setOffset] = useState(0);

  const query = useQuery({
    queryKey: ["users", { offset }],
    queryFn: () => usersApi.listUsers({ offset, limit: LIMIT }),
  });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ["users"] });
  }

  async function toggleRole(user: User) {
    const nextRole: UserRole = user.role === "admin" ? "staff" : "admin";
    try {
      await usersApi.updateUser(user.id, { role: nextRole });
      invalidate();
      showSuccess("Jogosultság frissítve.");
    } catch (err) {
      showError(getErrorMessage(err));
    }
  }

  async function toggleActive(user: User) {
    try {
      await usersApi.updateUser(user.id, { is_active: !user.is_active });
      invalidate();
      showSuccess("Állapot frissítve.");
    } catch (err) {
      showError(getErrorMessage(err));
    }
  }

  const columns: Column<User>[] = [
    {
      key: "name",
      header: t.name,
      render: (row) => (
        <>
          {row.full_name}
          {row.id === currentUser?.id && <span className="text-faint"> (Ön)</span>}
        </>
      ),
    },
    { key: "email", header: "E-mail", render: (row) => row.email },
    {
      key: "role",
      header: "Szerepkör",
      render: (row) => <Badge kind={row.role === "admin" ? "admin" : "staff"}>{row.role === "admin" ? "Admin" : "Munkatárs"}</Badge>,
    },
    {
      key: "status",
      header: "Állapot",
      render: (row) => (row.is_active ? <Badge kind="success">{t.active}</Badge> : <Badge kind="muted">{t.inactive}</Badge>),
    },
    { key: "created", header: "Regisztrált", render: (row) => formatDateTime(row.created_at) },
    {
      key: "actions",
      header: t.actions,
      render: (row) => (
        <div className="row-actions">
          <Button variant="ghost" size="sm" onClick={() => toggleRole(row)}>
            {row.role === "admin" ? "Munkatárssá tétel" : "Adminná tétel"}
          </Button>
          <Button variant="ghost" size="sm" onClick={() => toggleActive(row)}>
            {row.is_active ? "Letiltás" : "Engedélyezés"}
          </Button>
        </div>
      ),
    },
  ];

  return (
    <>
      <PageHeader title="Felhasználók" subtitle="Szerepkörök és hozzáférés kezelése." />
      <div className="page-content">
        <Panel>
          <DataTable columns={columns} rows={query.data?.items ?? []} rowKey={(row) => row.id} isLoading={query.isLoading} />
          {query.data && <Pagination total={query.data.total} limit={LIMIT} offset={offset} onOffsetChange={setOffset} />}
        </Panel>
      </div>
    </>
  );
}
