import { RoleManagementPanel } from '@/features/roles';
import styles from './RoleManagement.module.css';

export function RoleManagement() {
  return (
    <div className={styles.roleManagement}>
      <RoleManagementPanel />
    </div>
  );
}
