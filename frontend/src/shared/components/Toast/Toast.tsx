import { useToastStore, type Toast as ToastItem } from './toastStore';
import styles from './Toast.module.css';

interface ToastProps {
  toast: ToastItem;
}

export function Toast({ toast }: ToastProps) {
  const removeToast = useToastStore((s) => s.removeToast);

  return (
    <div className={`${styles.toast} ${styles[toast.type]}`}>
      <span className={styles.message}>{toast.message}</span>
      <button
        type="button"
        className={styles.closeBtn}
        onClick={() => removeToast(toast.id)}
        aria-label="关闭"
      >
        ×
      </button>
    </div>
  );
}
