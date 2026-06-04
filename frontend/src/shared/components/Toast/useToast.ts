import { useToastStore, type ToastType } from './toastStore';

export function useToast() {
  const addToast = useToastStore((s) => s.addToast);

  return {
    show: (message: string, type: ToastType = 'info') => addToast(type, message),
    success: (message: string) => addToast('success', message),
    error: (message: string) => addToast('error', message),
    info: (message: string) => addToast('info', message),
  };
}
